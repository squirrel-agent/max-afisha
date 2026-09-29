from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.encoder import get_text_encoder
from app.ml.texts import event_passage
from app.models.event import Event


async def embed_missing_events(
    db: AsyncSession,
    *,
    city: str | None = None,
    limit: int = 200,
    force: bool = False,
) -> dict:
    stmt = select(Event).where(Event.is_active.is_(True))

    if not force:
        stmt = stmt.where(Event.embedding.is_(None))

    if city:
        stmt = stmt.where(Event.city == city)

    stmt = stmt.order_by(Event.updated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    events = list(result.scalars().all())

    if not events:
        return {"embedded": 0, "model": "none-needed"}

    passages = [event_passage(event) for event in events]
    encoder = get_text_encoder()
    vectors = await asyncio.to_thread(encoder.encode_passages, passages)

    for event, vector in zip(events, vectors, strict=True):
        event.embedding = vector.astype(float).tolist()

    await db.commit()

    return {
        "embedded": len(events),
        "model": encoder.model._first_module().auto_model.config._name_or_path
        if hasattr(encoder.model, "_first_module")
        else "configured-model",
    }
