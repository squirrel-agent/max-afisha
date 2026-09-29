from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.event import Event
from app.schemas.event import EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
async def list_events(
    city: str | None = None,
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[Event]:
    now = datetime.now(UTC)
    stmt = select(Event).where(
        Event.is_active.is_(True),
        or_(Event.start_at.is_(None), Event.start_at >= now - timedelta(hours=1)),
    )

    if city:
        stmt = stmt.where(Event.city == city)

    if category:
        stmt = stmt.where(Event.category == category)

    stmt = stmt.order_by(Event.start_at.asc().nullslast()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
