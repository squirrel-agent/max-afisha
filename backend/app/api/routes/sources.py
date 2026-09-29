from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cities import CITY_IDS
from app.core.security import require_admin
from app.db.session import get_db
from app.models.recommendation import SourceSyncLog
from app.services.ingestion import sync_source

router = APIRouter(prefix="/sources", tags=["sources"])

SUPPORTED_SOURCES = {"afisha_ru", "yandex_afisha"}
SUPPORTED_CITIES = CITY_IDS


@router.post("/{source}/sync")
async def run_sync(
    source: str,
    _: None = Depends(require_admin),
    city: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if source not in SUPPORTED_SOURCES:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
    if city not in SUPPORTED_CITIES:
        raise HTTPException(status_code=400, detail=f"Unsupported city: {city}")
    try:
        return await sync_source(db=db, source=source, city=city, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Source sync failed: {type(exc).__name__}: {exc}") from exc


@router.get("/status")
async def source_status(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(SourceSyncLog).order_by(desc(SourceSyncLog.started_at)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": row.id,
            "source": row.source,
            "status": row.status,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "items_received": row.items_received,
            "items_created": row.items_created,
            "items_updated": row.items_updated,
            "error": row.error,
        }
        for row in rows
    ]
