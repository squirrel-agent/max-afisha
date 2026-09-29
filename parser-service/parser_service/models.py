from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

class EventPayload(BaseModel):
    source: str
    source_event_id: str
    source_url: str
    city: str = "moscow"
    title: str
    description: str | None = None
    category: str | None = None
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    venue_name: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    price_min: int | None = None
    price_max: int | None = None
    is_free: bool = False
    age_min: int | None = None
    image_url: str | None = None
    ticket_url: str | None = None
    raw_payload: dict = Field(default_factory=dict)
