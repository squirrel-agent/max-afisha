from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import require_admin
from app.db.session import get_db
from app.models.event import Event
from app.services.embeddings import embed_missing_events

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/status")
async def ml_status(
    db: AsyncSession = Depends(get_db),
) -> dict:
    total_result = await db.execute(
        select(func.count(Event.id)).where(Event.is_active.is_(True))
    )
    embedded_result = await db.execute(
        select(func.count(Event.id)).where(
            Event.is_active.is_(True),
            Event.embedding.is_not(None),
        )
    )

    total = int(total_result.scalar_one())
    embedded = int(embedded_result.scalar_one())

    return {
        "text_encoder_model": settings.text_encoder_model,
        "model_version": settings.model_version,
        "events_total": total,
        "events_embedded": embedded,
        "events_missing_embedding": total - embedded,
    }


@router.post("/embed-events")
async def embed_events(
    _: None = Depends(require_admin),
    city: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    force: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await embed_missing_events(
        db,
        city=city,
        limit=limit,
        force=force,
    )
