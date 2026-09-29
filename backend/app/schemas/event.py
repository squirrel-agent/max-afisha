from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    city: str
    title: str
    description: str | None = None
    category: str | None = None
    genres: list = Field(default_factory=list)
    tags: list = Field(default_factory=list)
    venue_name: str | None = None
    address: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    price_min: int | None = None
    price_max: int | None = None
    is_free: bool
    age_min: int | None = None
    image_url: str | None = None
    primary_source: str | None = None
    source_url: str | None = None
    ticket_url: str | None = None
