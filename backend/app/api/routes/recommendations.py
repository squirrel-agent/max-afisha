from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.event import Event
from app.models.interaction import Interaction
from app.models.recommendation import (
    RecommendationItem,
    RecommendationRating,
    RecommendationRequest,
)
from app.models.user import User, UserPreference

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
MODEL = "hybrid-semantic-behavior-v3-thresholded"
LABELS = {
    "concert": "Концерты",
    "exhibition": "Выставки",
    "theatre": "Театр",
    "cinema": "Кино",
    "sport": "Спорт",
    "lecture": "Лекции",
    "festival": "Фестивали",
    "standup": "Стендап",
    "kids": "Для детей",
    "quest": "Квесты",
    "show": "Шоу",
    "excursion": "Экскурсии",
    "other": "События",
}
PARENTS = {
    "concert": "culture",
    "exhibition": "culture",
    "theatre": "culture",
    "cinema": "culture",
    "lecture": "culture",
    "festival": "fun",
    "standup": "fun",
    "show": "fun",
    "sport": "active",
    "quest": "active",
    "kids": "family",
    "excursion": "culture",
}


def haversine(a: float, b: float, c: float, d: float) -> float:
    p = radians(c - a)
    q = radians(d - b)
    x = sin(p / 2) ** 2 + cos(radians(a)) * cos(radians(c)) * sin(q / 2) ** 2
    return 6371 * 2 * asin(sqrt(x))


def period_ok(event: Event, pref: UserPreference | None, now: datetime) -> bool:
    """Apply explicit questionnaire time constraints conservatively.

    When the user selected a concrete period, an event without a known start time
    is not claimed to match that request.  Custom/free-form periods remain a
    semantic signal because the MVP does not parse arbitrary natural-language
    dates into a reliable hard filter.
    """
    if not pref or not pref.when or pref.when in {"any", "custom"}:
        return True
    if not event.start_at:
        return False

    dt = event.start_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    city_tz = ZoneInfo("Europe/Moscow")
    local = dt.astimezone(city_tz)
    today = now.astimezone(city_tz).date()

    if pref.when == "today_evening":
        return local.date() == today and local.hour >= 16
    if pref.when == "tomorrow":
        return local.date() == today + timedelta(days=1)
    if pref.when == "weekend":
        if today.weekday() == 6:  # Sunday: current weekend started yesterday.
            saturday = today - timedelta(days=1)
        else:
            saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        return saturday <= local.date() <= saturday + timedelta(days=1)
    return True


def duration_ok(event: Event, pref: UserPreference | None) -> bool:
    """Return True only when a constrained event duration is known to fit.

    This intentionally fails closed for short/medium duration requests.  The
    previous implementation let events with unknown end time pass, which could
    produce a recommendation that contradicted one of the five onboarding
    answers.  For the broad "whole day" option we still accept unknown duration
    because it acts as an effectively unconstrained day-level choice.
    """
    if not pref or pref.duration_max is None:
        return True
    if pref.duration_max >= 1440:
        return True
    if not event.start_at or not event.end_at:
        return False

    start_dt = event.start_at if event.start_at.tzinfo else event.start_at.replace(tzinfo=UTC)
    end_dt = event.end_at if event.end_at.tzinfo else event.end_at.replace(tzinfo=UTC)
    event_minutes = (end_dt - start_dt).total_seconds() / 60
    return event_minutes > 0 and event_minutes <= pref.duration_max


def passes_relevance_threshold(semantic_similarity: float | None, final_score: float) -> bool:
    """Do not pad a personalized result with low-confidence events.

    multilingual-e5 cosine similarities are compressed toward the upper part of
    the scale, so a threshold materially below ~0.7 would not reject many weak
    matches.  Both values are configurable through environment variables so the
    team can calibrate them on validation data without changing code.
    """
    if semantic_similarity is None:
        return False
    return (
        semantic_similarity >= settings.recommendation_min_semantic_similarity
        and final_score >= settings.recommendation_min_final_score
    )


def serialize(event: Event, score: float, distance: float | None, semantic: float) -> dict:
    price = (
        "Бесплатно"
        if event.is_free
        else (f"от {event.price_min} ₽" if event.price_min is not None else "Цена уточняется")
    )
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "city": event.city,
        "category": event.category,
        "venue_name": event.venue_name,
        "address": event.address,
        "start_at": event.start_at,
        "end_at": event.end_at,
        "price_min": event.price_min,
        "price_max": event.price_max,
        "is_free": event.is_free,
        "age_min": event.age_min,
        "image_url": event.image_url,
        "primary_source": event.primary_source,
        "source_url": event.source_url,
        "ticket_url": event.ticket_url,
        "score": round(score, 4),
        "semantic_similarity": round(semantic, 4),
        "distance_km": round(distance, 1) if distance is not None else None,
        "next_session": event.start_at,
        "price_label": price,
    }


class RatingPayload(BaseModel):
    rating: int = Field(ge=1, le=5)
    run_id: UUID | None = None


@router.get("/{user_id}")
async def recommendations(
    user_id: UUID,
    limit: int = Query(40, ge=1, le=100),
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = Query(5, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    pref = await db.get(UserPreference, user_id)
    history = (
        await db.execute(
            select(Interaction, Event.category)
            .join(Event, Event.id == Interaction.event_id)
            .where(Interaction.user_id == user_id)
        )
    ).all()

    affinity: Counter[str] = Counter()
    seen = set()
    weights = {"like": 3.0, "save": 4.0, "share": 3.0, "view": 0.35, "dislike": -5.0}
    for interaction, category in history:
        seen.add(interaction.event_id)
        if category:
            affinity[category] += weights.get(interaction.action, 0)

    now = datetime.now(UTC)
    semantic_enabled = bool(pref and pref.profile_embedding is not None)

    if lat is not None and lon is not None:
        initial = float(radius_km)
        radius_steps = [initial] + [candidate for candidate in (5.0, 10.0, 25.0) if candidate > initial]
    else:
        radius_steps = [float(radius_km)]
    max_radius = max(radius_steps)

    # If the profile embedding is missing, do not manufacture a personalized
    # answer from generic freshness/novelty signals.  The frontend will show the
    # explicit "no variants" state and a separate city feed instead.
    semantic_expr = (
        Event.embedding.cosine_distance(pref.profile_embedding).label("semantic_distance")
        if semantic_enabled
        else None
    )
    stmt = (
        select(Event, semantic_expr) if semantic_enabled else select(Event)
    ).where(Event.is_active.is_(True), Event.city == (user.city or "moscow"))

    if semantic_enabled:
        stmt = stmt.where(Event.embedding.is_not(None))

    if pref and pref.budget_max is not None:
        if pref.budget_max == 0:
            stmt = stmt.where(Event.is_free.is_(True))
        else:
            stmt = stmt.where(
                or_(
                    Event.is_free.is_(True),
                    Event.price_min <= pref.budget_max,
                )
            )

    raw_rows = (
        await db.execute(stmt.order_by(Event.start_at.asc().nullslast()).limit(800))
    ).all()

    hard_filter_candidates = 0
    semantic_scored_candidates = 0
    rejected_low_relevance = 0
    ranked: list[tuple[float, Event, float | None, float]] = []

    for raw in raw_rows:
        event = raw[0]
        raw_semantic = raw[1] if semantic_enabled else None

        if event.start_at:
            event_start = event.start_at if event.start_at.tzinfo else event.start_at.replace(tzinfo=UTC)
            if event_start < now - timedelta(hours=1):
                continue
        if not period_ok(event, pref, now):
            continue
        if not duration_ok(event, pref):
            continue

        distance = (
            haversine(lat, lon, event.lat, event.lon)
            if lat is not None
            and lon is not None
            and event.lat is not None
            and event.lon is not None
            else None
        )
        if lat is not None and lon is not None and distance is None:
            continue
        if distance is not None and distance > max_radius:
            continue

        hard_filter_candidates += 1

        if raw_semantic is None:
            continue
        semantic_scored_candidates += 1
        semantic = max(0.0, min(1.0, 1.0 - float(raw_semantic)))

        category = event.category or "other"
        category_match = 1.0 if pref and category in (pref.categories or []) else 0.25
        behavior = max(-1.0, min(1.0, affinity.get(category, 0) / 8))
        freshness = 0.0
        if event.start_at:
            event_start = event.start_at if event.start_at.tzinfo else event.start_at.replace(tzinfo=UTC)
            days = max(0.0, (event_start - now).total_seconds() / 86400)
            freshness = max(0.0, 1.0 - days / 60)

        distance_score = max(0.0, 1.0 - (distance / max_radius)) if distance is not None else 0.5
        novelty = 1.0 if event.id not in seen else 0.15

        if pref and pref.categories:
            score = (
                0.25 * semantic
                + 0.25 * category_match
                + 0.20 * ((behavior + 1) / 2)
                + 0.15 * freshness
                + 0.10 * distance_score
                + 0.05 * novelty
            )
        else:
            score = (
                0.50 * semantic
                + 0.20 * ((behavior + 1) / 2)
                + 0.15 * freshness
                + 0.10 * distance_score
                + 0.05 * novelty
            )

        if not passes_relevance_threshold(semantic, score):
            rejected_low_relevance += 1
            continue

        ranked.append((score, event, distance, semantic))

    def sort_start(event: Event):
        if not event.start_at:
            return datetime.max.replace(tzinfo=UTC)
        return event.start_at if event.start_at.tzinfo else event.start_at.replace(tzinfo=UTC)

    ranked.sort(key=lambda item: (-item[0], sort_start(item[1]), str(item[1].id)))

    grouped: dict[str, list[dict]] = {}
    used = set()
    for score, event, distance, semantic in ranked:
        category = event.category or "other"
        if event.id in used:
            continue
        grouped.setdefault(category, []).append(serialize(event, score, distance, semantic))
        used.add(event.id)

    requested = list((pref.categories or []) if pref else [])

    def groups_for(radius: float) -> dict[str, list[dict]]:
        allowed = {
            str(event.id)
            for _, event, distance, _ in ranked
            if distance is None or distance <= radius
        }
        return {
            category: [item for item in values if str(item["id"]) in allowed]
            for category, values in grouped.items()
            if any(str(item["id"]) in allowed for item in values)
        }

    radius_used = radius_steps[-1]
    selected_grouped = grouped
    for candidate in radius_steps:
        candidate_grouped = groups_for(candidate)
        if len(candidate_grouped) >= 3 or (
            candidate == radius_steps[-1] and candidate_grouped
        ):
            radius_used = candidate
            selected_grouped = candidate_grouped
            break
    grouped = selected_grouped

    categories: list[str] = []
    for category in requested + list(grouped):
        if category in grouped and category not in categories:
            categories.append(category)
    categories = categories[:3]

    podium = [
        {
            "rank": index + 1,
            "type": category,
            "label": LABELS.get(category, category.title()),
            "parent": PARENTS.get(category),
            "items": grouped[category][
                : max(1, min(5, limit // max(1, len(categories))))
            ],
        }
        for index, category in enumerate(categories)
    ]
    items = [item for group in podium for item in group["items"]]
    effective_radius = radius_used if lat is not None and lon is not None else None

    if items:
        fallback_reason = None
    elif not semantic_enabled:
        fallback_reason = "profile_embedding_unavailable"
    elif semantic_scored_candidates == 0:
        fallback_reason = "event_embeddings_unavailable"
    elif hard_filter_candidates == 0:
        fallback_reason = "no_events_after_constraints"
    else:
        fallback_reason = "no_relevant_events"

    run = RecommendationRequest(
        user_id=user_id,
        mode="questionnaire_podium",
        query=None,
        filters={
            "radius_km": effective_radius,
            "lat": lat,
            "lon": lon,
            "min_semantic_similarity": settings.recommendation_min_semantic_similarity,
            "min_final_score": settings.recommendation_min_final_score,
            "fallback_reason": fallback_reason,
        },
        model_version=MODEL,
    )
    db.add(run)
    await db.flush()

    position = 1
    for group in podium:
        for item in group["items"]:
            db.add(
                RecommendationItem(
                    request_id=run.id,
                    event_id=item["id"],
                    position=position,
                    final_score=item.get("score"),
                )
            )
            position += 1
    await db.commit()

    return {
        "model_version": MODEL,
        "run_id": run.id,
        "has_relevant": bool(items),
        "fallback_reason": fallback_reason,
        "relevance": {
            "min_semantic_similarity": settings.recommendation_min_semantic_similarity,
            "min_final_score": settings.recommendation_min_final_score,
            "hard_filter_candidates": hard_filter_candidates,
            "semantic_scored_candidates": semantic_scored_candidates,
            "rejected_low_relevance": rejected_low_relevance,
        },
        "podium": podium,
        "items_by_type": {group["type"]: group["items"] for group in podium},
        "radius_used_km": effective_radius,
        "location_source": "browser" if lat is not None and lon is not None else "city",
        "items": items[:limit],
    }


@router.post("/{user_id}/rating")
async def rating(
    user_id: UUID,
    payload: RatingPayload,
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(404, "User not found")
    if payload.run_id is not None:
        run = await db.get(RecommendationRequest, payload.run_id)
        if run is None or run.user_id != user_id:
            raise HTTPException(400, "Unknown recommendation run")
    db.add(
        RecommendationRating(
            user_id=user_id,
            request_id=payload.run_id,
            rating=payload.rating,
            model_version=MODEL,
        )
    )
    await db.commit()
    return {"ok": True, "rating": payload.rating, "run_id": payload.run_id}
