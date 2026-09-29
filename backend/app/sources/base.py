from __future__ import annotations

from abc import ABC, abstractmethod

from app.sources.http import SourceHttpClient
from app.sources.types import DiscoveredEvent, NormalizedEvent


class EventSourceAdapter(ABC):
    name: str

    def __init__(self, client: SourceHttpClient) -> None:
        self.client = client

    @abstractmethod
    async def discover(self, city: str, limit: int) -> list[DiscoveredEvent]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_event(self, item: DiscoveredEvent) -> NormalizedEvent | None:
        raise NotImplementedError
