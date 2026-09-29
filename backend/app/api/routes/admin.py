from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import require_admin
from app.db.session import get_db
from app.services.ingestion import _upsert_event
from app.services.embeddings import embed_missing_events
from app.sources.types import NormalizedEvent

router = APIRouter(prefix="/admin", tags=["admin"])



class BatchIngest(BaseModel):
    events: list[NormalizedEvent]


@router.post("/ingest")
async def ingest_batch(payload: BatchIngest, _: None = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    created = updated = 0
    errors: list[str] = []
    for item in payload.events:
        try:
            async with db.begin_nested():
                _, was_created = await _upsert_event(db, item)
            created += int(was_created)
            updated += int(not was_created)
        except Exception as exc:
            errors.append(f"{item.source_url}: {type(exc).__name__}: {exc}")
    await db.commit()
    embedded = 0
    embedding_error = None
    if payload.events and settings.auto_embed_after_ingest:
        try:
            result = await embed_missing_events(db, city=payload.events[0].city, limit=min(len(payload.events), 500), force=False)
            embedded = int(result.get("embedded", 0))
        except Exception as exc:
            await db.rollback()
            embedding_error = f"{type(exc).__name__}: {exc}"
    return {"received": len(payload.events), "created": created, "updated": updated, "embedded": embedded, "embedding_error": embedding_error, "errors": errors[:20]}


class ParserRun(BaseModel):
    source: Literal["all", "yandex_afisha", "afisha_ru", "vk_events"] = "all"
    city: Literal["moscow", "saint-petersburg"] = "moscow"
    limit: int = Field(default=700, ge=1, le=5000)

@router.post("/parser/run")
async def run_parser(payload: ParserRun, _: None = Depends(require_admin)):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.parser_service_url}/run",
                headers={"Authorization": f"Bearer {settings.admin_token}"},
                json=payload.model_dump(),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Parser service unavailable: {exc}") from exc
    if response.is_error:
        raise HTTPException(status_code=502, detail=f"Parser service: {response.text}")
    return response.json()
