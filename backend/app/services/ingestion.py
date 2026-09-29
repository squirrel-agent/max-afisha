from __future__ import annotations

from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventSource
from app.models.recommendation import SourceSyncLog
from app.sources.http import SourceHttpClient
from app.sources.normalizer import canonical_key
from app.sources.registry import build_adapter
from app.sources.types import NormalizedEvent


async def _upsert_event(db: AsyncSession, payload: NormalizedEvent) -> tuple[Event, bool]:
    existing_source_result = await db.execute(
        select(EventSource).where(
            EventSource.source == payload.source,
            EventSource.source_event_id == payload.source_event_id,
        )
    )
    source_row = existing_source_result.scalar_one_or_none()

    if source_row is not None:
        event = await db.get(Event, source_row.event_id)
        created = False
    else:
        key = canonical_key(payload.city, payload.title, payload.venue_name, payload.start_at)
        existing_event_result = await db.execute(select(Event).where(Event.canonical_key == key))
        event = existing_event_result.scalar_one_or_none()
        # Cross-source fuzzy dedupe: sources often spell the same title slightly differently.
        if event is None and payload.start_at is not None:
            start = payload.start_at - timedelta(hours=12)
            end = payload.start_at + timedelta(hours=12)
            candidates = (await db.execute(select(Event).where(Event.city == payload.city, Event.start_at >= start, Event.start_at <= end).limit(150))).scalars().all()
            def norm(value: str | None) -> str:
                return re.sub(r"[^a-zа-я0-9]+", " ", (value or "").lower()).strip()
            wanted = norm(payload.title)
            best = None
            best_score = 0.0
            for candidate in candidates:
                score = SequenceMatcher(None, wanted, norm(candidate.title)).ratio()
                if payload.venue_name and candidate.venue_name:
                    score = score * 0.8 + SequenceMatcher(None, norm(payload.venue_name), norm(candidate.venue_name)).ratio() * 0.2
                if score > best_score:
                    best, best_score = candidate, score
            if best is not None and best_score >= 0.88:
                event = best
        created = event is None
        if event is None:
            event = Event(canonical_key=key, city=payload.city, title=payload.title)
            db.add(event)
            await db.flush()
        source_row = EventSource(
            event_id=event.id,
            source=payload.source,
            source_event_id=payload.source_event_id,
        )
        db.add(source_row)

    # Keep canonical event populated with the freshest non-empty source fields.
    event.city = payload.city
    event.title = payload.title
    event.description = payload.description or event.description
    event.category = payload.category or event.category
    event.genres = payload.genres or event.genres or []
    event.tags = payload.tags or event.tags or []
    event.venue_name = payload.venue_name or event.venue_name
    event.address = payload.address or event.address
    event.lat = payload.lat if payload.lat is not None else event.lat
    event.lon = payload.lon if payload.lon is not None else event.lon
    event.start_at = payload.start_at or event.start_at
    event.end_at = payload.end_at or event.end_at
    event.price_min = payload.price_min if payload.price_min is not None else event.price_min
    event.price_max = payload.price_max if payload.price_max is not None else event.price_max
    event.is_free = payload.is_free
    event.age_min = payload.age_min if payload.age_min is not None else event.age_min
    event.image_url = payload.image_url or event.image_url
    event.primary_source = event.primary_source or payload.source
    event.source_url = event.source_url or payload.source_url
    event.ticket_url = payload.ticket_url or event.ticket_url or payload.source_url
    event.is_active = True
    event.updated_at = datetime.now(UTC)

    source_row.source_url = payload.source_url
    source_row.raw_payload = payload.raw_payload
    source_row.fetched_at = datetime.now(UTC)

    await db.flush()
    return event, created


async def sync_source(
    db: AsyncSession,
    source: str,
    city: str,
    limit: int = 30,
) -> dict:
    log = SourceSyncLog(source=source, status="running")
    db.add(log)
    await db.commit()
    await db.refresh(log)

    received = created = updated = skipped = 0
    errors: list[str] = []

    try:
        async with SourceHttpClient() as client:
            adapter = build_adapter(source, client)
            discovered = await adapter.discover(city=city, limit=limit)
            received = len(discovered)

            for item in discovered:
                try:
                    payload = await adapter.fetch_event(item)
                    if payload is None:
                        skipped += 1
                        continue
                    _, was_created = await _upsert_event(db, payload)
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                    await db.commit()
                except Exception as exc:  # isolate a broken detail page from the entire sync
                    await db.rollback()
                    skipped += 1
                    errors.append(f"{item.source_url}: {type(exc).__name__}: {exc}")

        log = await db.get(SourceSyncLog, log.id)
        log.status = "ok" if not errors else "partial"
        log.finished_at = datetime.now(UTC)
        log.items_received = received
        log.items_created = created
        log.items_updated = updated
        log.error = "\n".join(errors[:20]) or None
        await db.commit()

        return {
            "source": source,
            "city": city,
            "status": log.status,
            "discovered": received,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:10],
        }
    except Exception as exc:
        await db.rollback()
        log = await db.get(SourceSyncLog, log.id)
        log.status = "error"
        log.finished_at = datetime.now(UTC)
        log.items_received = received
        log.items_created = created
        log.items_updated = updated
        log.error = f"{type(exc).__name__}: {exc}"
        await db.commit()
        raise
