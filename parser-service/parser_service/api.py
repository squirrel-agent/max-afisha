from __future__ import annotations

import asyncio
import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from parser_service.cli import run

app = FastAPI(title="MAX Afisha Parser")
lock = asyncio.Lock()
last_run: dict = {}
background_tasks: set[asyncio.Task] = set()


class RunRequest(BaseModel):
    source: Literal["all", "yandex_afisha", "afisha_ru", "vk_events"] = "all"
    city: Literal["moscow", "saint-petersburg"] = "moscow"
    limit: int = Field(default=500, ge=1, le=5000)


class Args:
    def __init__(self, payload: RunRequest):
        self.source = payload.source
        self.city = payload.city
        self.limit = payload.limit
        self.dry_run = False


def start_background(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task


async def execute(payload: RunRequest):
    global last_run
    if lock.locked():
        return
    async with lock:
        last_run = {"status": "running", "source": payload.source, "city": payload.city}
        try:
            result = await run(Args(payload))
            last_run = {
                **last_run,
                **(result or {}),
                "status": (result or {}).get("status", "ok"),
            }
        except Exception as exc:
            last_run = {
                **last_run,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }


@app.on_event("startup")
async def startup():
    if os.getenv("DAILY_SYNC", "1") != "1":
        return

    async def loop():
        await asyncio.sleep(20)
        while True:
            # Keep both supported city catalogues fresh. Run them sequentially so
            # the global lock still prevents overlapping browser crawls.
            try:
                limit = int(os.getenv("PARSER_LIMIT", "700"))
            except ValueError:
                limit = 700
            limit = max(1, min(5000, limit))
            for city in ("moscow", "saint-petersburg"):
                while lock.locked():
                    await asyncio.sleep(1)
                await execute(RunRequest(city=city, limit=limit))
            await asyncio.sleep(86400)

    app.state.sync_task = start_background(loop())


@app.on_event("shutdown")
async def shutdown():
    tasks = list(background_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@app.get("/health")
async def health():
    return {"status": "ok", "last_run": last_run}


@app.post("/run")
async def start(payload: RunRequest, authorization: str | None = Header(None)):
    token = os.getenv("ADMIN_TOKEN", "change-me-local-admin")
    if authorization != f"Bearer {token}":
        raise HTTPException(401, "Invalid admin token")
    if lock.locked():
        return {"status": "already_running", "last_run": last_run}
    start_background(execute(payload))
    return {
        "status": "started",
        "source": payload.source,
        "city": payload.city,
        "limit": payload.limit,
    }
