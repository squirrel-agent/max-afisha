from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class FeedItem(BaseModel):
    id: UUID
    title: str
    category: str | None = None
    description: str | None = None
    venue_name: str | None = None
    start_at: datetime | None = None
    price_min: int | None = None
    similarity: float | None = None

class FeedResponse(BaseModel):
    mode: str
    items: list[FeedItem]
