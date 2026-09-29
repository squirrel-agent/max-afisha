from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import dateparser

CATEGORY_ALIASES = {
    "concert": "concert",
    "концерт": "concert",
    "music": "concert",
    "theater": "theatre",
    "theatre": "theatre",
    "спектакль": "theatre",
    "театр": "theatre",
    "exhibition": "exhibition",
    "выставка": "exhibition",
    "museum": "exhibition",
    "sport": "sport",
    "sports": "sport",
    "спорт": "sport",
    "standup": "standup",
    "стендап": "standup",
    "festival": "festival",
    "фестиваль": "festival",
    "show": "show",
    "шоу": "show",
    "movie": "cinema",
    "film": "cinema",
    "кино": "cinema",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def absolute_url(base: str, value: str | None) -> str | None:
    if not value:
        return None
    return urljoin(base, value)


def normalize_category(*values: str | None) -> str | None:
    joined = " ".join(v for v in values if v).lower()
    for token, category in CATEGORY_ALIASES.items():
        if token in joined:
            return category
    return None


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = dateparser.parse(
            str(value),
            languages=["ru", "en"],
            settings={"RETURN_AS_TIMEZONE_AWARE": True, "TO_TIMEZONE": "UTC"},
        )
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def parse_price(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return max(0, int(value))
    match = re.search(r"(\d[\d\s\xa0]*)", str(value))
    if not match:
        return None
    return int(re.sub(r"\D", "", match.group(1)))


def parse_age(value: Any) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d{1,2})\s*\+", str(value))
    return int(match.group(1)) if match else None


def source_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    # Prefer trailing numeric ID when present because Afisha URLs contain one.
    numeric = re.search(r"-(\d+)$", path)
    if numeric:
        return numeric.group(1)
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:20]


def canonical_key(city: str, title: str, venue: str | None, start_at: datetime | None) -> str:
    day = start_at.date().isoformat() if start_at else "no-date"
    raw = "|".join([
        city.lower().strip(),
        title.lower().strip(),
        (venue or "").lower().strip(),
        day,
    ])
    normalized = re.sub(r"[^a-zа-яё0-9|]+", " ", raw, flags=re.IGNORECASE)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def image_from_jsonld(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        first = value[0]
        return image_from_jsonld(first)
    if isinstance(value, dict):
        return value.get("url") or value.get("contentUrl")
    return None


def location_from_jsonld(value: Any) -> tuple[str | None, str | None, float | None, float | None]:
    if not isinstance(value, dict):
        return None, None, None, None
    name = clean_text(value.get("name"))
    address_value = value.get("address")
    if isinstance(address_value, dict):
        parts = [
            address_value.get("streetAddress"),
            address_value.get("addressLocality"),
            address_value.get("addressRegion"),
        ]
        address = clean_text(", ".join(str(x) for x in parts if x))
    else:
        address = clean_text(address_value)
    geo = value.get("geo") if isinstance(value.get("geo"), dict) else {}
    try:
        lat = float(geo.get("latitude")) if geo.get("latitude") is not None else None
        lon = float(geo.get("longitude")) if geo.get("longitude") is not None else None
    except (TypeError, ValueError):
        lat = lon = None
    return name, address, lat, lon
