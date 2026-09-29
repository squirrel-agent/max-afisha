from __future__ import annotations

import argparse
import asyncio
import json

from app.db.session import AsyncSessionLocal
from app.services.ingestion import sync_source


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["afisha_ru", "yandex_afisha"], required=True)
    parser.add_argument("--city", choices=["moscow", "saint-petersburg"], required=True)
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        result = await sync_source(db, source=args.source, city=args.city, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
