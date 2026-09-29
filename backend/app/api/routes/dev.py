from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.session import get_db
from app.models.event import Event

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/seed")
async def seed_demo_events(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    exists = await db.execute(
        select(Event).where(Event.canonical_key == "demo:night-jazz")
    )
    if exists.scalar_one_or_none():
        return {"status": "already_seeded", "created": 0}

    now = datetime.now(UTC)

    events = [
        Event(
            canonical_key="demo:night-jazz",
            city="moscow",
            title="Ночной джаз в планетарии",
            description="Камерный концерт живого джаза под звездным куполом. Атмосферный вечер для пары или небольшой компании.",
            category="concert",
            genres=["jazz"],
            tags=["music", "atmospheric", "night", "date"],
            venue_name="Планетарий",
            start_at=now + timedelta(hours=5),
            end_at=now + timedelta(hours=6, minutes=30),
            price_min=1800,
            price_max=2500,
            is_free=False,
            age_min=16,
            primary_source="demo",
            source_url="https://example.com/night-jazz",
            ticket_url="https://example.com/night-jazz/tickets",
        ),
        Event(
            canonical_key="demo:modern-art",
            city="moscow",
            title="Выставка цифрового искусства",
            description="Иммерсивная мультимедийная выставка о технологиях, свете и современной визуальной культуре.",
            category="exhibition",
            genres=["digital-art"],
            tags=["art", "technology", "immersive", "unusual"],
            venue_name="Центр современного искусства",
            start_at=now + timedelta(days=2),
            end_at=now + timedelta(days=2, hours=2),
            price_min=900,
            price_max=1200,
            is_free=False,
            age_min=12,
            primary_source="demo",
            source_url="https://example.com/digital-art",
            ticket_url="https://example.com/digital-art/tickets",
        ),
        Event(
            canonical_key="demo:standup-spb",
            city="saint-petersburg",
            title="Новый стендап",
            description="Вечер экспериментального стендапа молодых комиков в небольшом клубе.",
            category="standup",
            genres=["standup"],
            tags=["comedy", "new", "evening"],
            venue_name="Клуб на Невском",
            start_at=now + timedelta(days=1, hours=3),
            end_at=now + timedelta(days=1, hours=4, minutes=30),
            price_min=1000,
            price_max=1600,
            is_free=False,
            age_min=18,
            primary_source="demo",
            source_url="https://example.com/standup",
            ticket_url="https://example.com/standup/tickets",
        ),
        Event(
            canonical_key="demo:rock-club",
            city="moscow",
            title="Инди-рок в маленьком клубе",
            description="Живой энергичный концерт независимых групп без стадионного масштаба.",
            category="concert",
            genres=["indie", "rock"],
            tags=["music", "club", "friends", "energetic"],
            venue_name="Небольшой музыкальный клуб",
            start_at=now + timedelta(hours=7),
            end_at=now + timedelta(hours=9),
            price_min=1400,
            price_max=2000,
            is_free=False,
            age_min=18,
            primary_source="demo",
            source_url="https://example.com/indie-rock",
            ticket_url="https://example.com/indie-rock/tickets",
        ),
        Event(
            canonical_key="demo:basketball",
            city="moscow",
            title="Вечерний баскетбольный матч",
            description="Динамичный матч профессиональных команд на большой спортивной арене.",
            category="sport",
            genres=["basketball"],
            tags=["sport", "arena", "friends", "energy"],
            venue_name="Спортивная арена",
            start_at=now + timedelta(days=3),
            end_at=now + timedelta(days=3, hours=2),
            price_min=700,
            price_max=3500,
            is_free=False,
            age_min=6,
            primary_source="demo",
            source_url="https://example.com/basketball",
            ticket_url="https://example.com/basketball/tickets",
        ),
    ]

    db.add_all(events)
    await db.commit()

    return {"status": "ok", "created": len(events)}
