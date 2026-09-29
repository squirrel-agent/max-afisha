from __future__ import annotations

from typing import TypedDict


class City(TypedDict):
    id: str
    name: str
    region: str
    aliases: list[str]


CITIES: list[City] = [
    {
        "id": "moscow",
        "name": "Москва",
        "region": "Москва",
        "aliases": ["москва", "мск", "moscow"],
    },
    {
        "id": "saint-petersburg",
        "name": "Санкт-Петербург",
        "region": "Санкт-Петербург",
        "aliases": [
            "санкт-петербург",
            "санкт петербург",
            "спб",
            "питер",
            "saint-petersburg",
            "st petersburg",
        ],
    },
]
CITY_IDS = frozenset(city["id"] for city in CITIES)


def is_supported_city(city_id: str) -> bool:
    return city_id in CITY_IDS
