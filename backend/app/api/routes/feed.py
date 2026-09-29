from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.event import Event
from app.schemas.feed import FeedResponse

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=FeedResponse)
async def feed(
    city: str = "moscow",
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(UTC)
    stmt = select(Event).where(
        Event.is_active.is_(True),
        Event.city == city,
        or_(Event.start_at.is_(None), Event.start_at >= now - timedelta(hours=1)),
    )
    if category:
        stmt = stmt.where(Event.category == category)
    stmt = stmt.order_by(Event.start_at.asc().nullslast()).limit(limit)
    result = await db.execute(stmt)
    items = [
        {
            "id": event.id,
            "title": event.title,
            "category": event.category,
            "description": event.description,
            "venue_name": event.venue_name,
            "start_at": event.start_at,
            "price_min": event.price_min,
            "similarity": None,
        }
        for event in result.scalars()
    ]
    return {"mode": "baseline-feed", "items": items}
