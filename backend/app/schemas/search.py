from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class NeuralSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    city: Literal["moscow", "saint-petersburg"]
    period: Literal["any", "today", "weekend"] = "any"
    categories: list[str] = Field(default_factory=list)
    exclude_categories: list[str] = Field(default_factory=list)
    budget_max: int | None = Field(default=None, ge=0, le=1_000_000)
    limit: int = Field(default=20, ge=1, le=50)


class NeuralSearchItem(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    city: str
    category: str | None = None
    venue_name: str | None = None
    start_at: datetime | None = None
    price_min: int | None = None
    price_max: int | None = None
    is_free: bool = False
    image_url: str | None = None
    primary_source: str | None = None
    source_url: str | None = None
    ticket_url: str | None = None
    similarity: float


class NeuralSearchResponse(BaseModel):
    query: str
    model_version: str
    has_relevant: bool
    fallback_reason: str | None = None
    min_similarity: float
    rejected_low_relevance: int = 0
    items: list[NeuralSearchItem]
