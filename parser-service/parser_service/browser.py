from __future__ import annotations

import asyncio

import httpx
from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import BrowserContext, Playwright, async_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36"


class Browser:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9"},
            follow_redirects=True,
            timeout=30,
        )
        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None

    async def _ensure_context(self) -> BrowserContext:
        if self._context is not None:
            return self._context
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            user_agent=UA,
            locale="ru-RU",
            viewport={"width": 1440, "height": 1200},
        )
        return self._context

    async def get(self, url: str, dynamic: bool = False) -> str:
        if not dynamic:
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                if len(response.text) > 1000:
                    return response.text
            except Exception:
                pass

        context = await self._ensure_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(1200)
            return await page.content()
        finally:
            await page.close()

    async def close(self):
        await self.client.aclose()
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None


async def polite_pause():
    await asyncio.sleep(0.25)
