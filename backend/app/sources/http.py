from __future__ import annotations

import asyncio

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings


class SourceHttpClient:
    def __init__(self) -> None:
        transport = httpx.AsyncHTTPTransport(retries=1)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.source_timeout_seconds),
            transport=transport,
            follow_redirects=True,
            headers={
                "User-Agent": settings.source_user_agent,
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Cache-Control": "no-cache",
            },
        )
        self._delay = settings.source_request_delay_seconds

    async def __aenter__(self) -> "SourceHttpClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        reraise=True,
    )
    async def get_text(self, url: str) -> str:
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        response = await self._client.get(url)
        response.raise_for_status()
        return response.text
