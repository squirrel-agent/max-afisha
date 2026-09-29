from __future__ import annotations

import asyncio
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.encoder import get_text_encoder
from app.models.event import Event
from app.schemas.search import NeuralSearchRequest

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def _period_range(period: str) -> tuple[datetime | None, datetime | None]:
    if period == "any":
        return None, None

    now_local = datetime.now(MOSCOW_TZ)
    today = now_local.date()

    if period == "today":
        start = datetime.combine(today, time.min, tzinfo=MOSCOW_TZ)
        return start, start + timedelta(days=1)

    weekday = today.weekday()
    if weekday == 5:
        saturday = today
    elif weekday == 6:
        saturday = today - timedelta(days=1)
    else:
        saturday = today + timedelta(days=(5 - weekday))
    start = datetime.combine(saturday, time.min, tzinfo=MOSCOW_TZ)
    return start, start + timedelta(days=2)


async def neural_search(db: AsyncSession, request: NeuralSearchRequest) -> dict:
    encoder = get_text_encoder()
    query_vector = await asyncio.to_thread(encoder.encode_query, request.query)
    distance = Event.embedding.cosine_distance(query_vector).label("distance")

    stmt = select(Event, distance).where(
        Event.is_active.is_(True),
        Event.embedding.is_not(None),
        Event.city == request.city,
    )

    # Do not offer events that are already clearly in the past. Events without a
    # known start time stay eligible for free-form search, but not for dated periods.
    now = datetime.now(UTC)
    stmt = stmt.where(or_(Event.start_at.is_(None), Event.start_at >= now - timedelta(hours=1)))

    start, end = _period_range(request.period)
    if start is not None and end is not None:
        stmt = stmt.where(Event.start_at.is_not(None), Event.start_at >= start, Event.start_at < end)

    if request.categories:
        stmt = stmt.where(Event.category.in_(request.categories))
    if request.exclude_categories:
        stmt = stmt.where(Event.category.not_in(request.exclude_categories))
    if request.budget_max is not None:
        stmt = stmt.where(
            or_(
                Event.is_free.is_(True),
                and_(Event.price_min.is_not(None), Event.price_min <= request.budget_max),
            )
        )

    # Pull a wider candidate pool, then keep only results above the calibrated
    # similarity gate. This prevents a nearest-neighbour query from returning a
    # weak match merely because it is the least-bad option in the database.
    candidate_limit = min(250, max(request.limit * 5, request.limit))
    result = await db.execute(stmt.order_by(distance.asc()).limit(candidate_limit))

    items = []
    rejected_low_relevance = 0
    for event, raw_distance in result.all():
        similarity = max(-1.0, min(1.0, 1.0 - float(raw_distance)))
        if similarity < settings.neural_search_min_similarity:
            rejected_low_relevance += 1
            continue
        items.append(
            {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "city": event.city,
                "category": event.category,
                "venue_name": event.venue_name,
                "start_at": event.start_at,
                "price_min": event.price_min,
                "price_max": event.price_max,
                "is_free": event.is_free,
                "image_url": event.image_url,
                "primary_source": event.primary_source,
                "source_url": event.source_url,
                "ticket_url": event.ticket_url,
                "similarity": round(similarity, 6),
            }
        )
        if len(items) >= request.limit:
            break

    return {
        "query": request.query,
        "model_version": settings.model_version,
        "has_relevant": bool(items),
        "fallback_reason": None if items else "no_relevant_events",
        "min_similarity": settings.neural_search_min_similarity,
        "rejected_low_relevance": rejected_low_relevance,
        "items": items,
    }
