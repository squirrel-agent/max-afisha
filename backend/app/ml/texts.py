from __future__ import annotations

from app.models.event import Event


def event_passage(event: Event) -> str:
    genres = ", ".join(str(x) for x in (event.genres or []))
    tags = ", ".join(str(x) for x in (event.tags or []))

    parts = [
        f"Название: {event.title}.",
        f"Категория: {event.category}." if event.category else "",
        f"Жанры: {genres}." if genres else "",
        f"Теги: {tags}." if tags else "",
        f"Площадка: {event.venue_name}." if event.venue_name else "",
        f"Город: {event.city}.",
        f"Описание: {event.description}." if event.description else "",
    ]
    return "passage: " + " ".join(part for part in parts if part)


def user_query(text: str) -> str:
    return "query: " + text.strip()
