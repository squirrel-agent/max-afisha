from pathlib import Path

from app.sources.jsonld import event_jsonld
from app.sources.normalizer import location_from_jsonld, parse_age, parse_datetime, parse_price


def test_event_jsonld_fixture():
    html = (Path(__file__).parent / "fixtures" / "afisha_event.html").read_text(encoding="utf-8")
    event = event_jsonld(html)
    assert event is not None
    assert event["name"] == "Ночной джаз"
    assert parse_price(event["offers"]["price"]) == 1800
    assert parse_age(event["typicalAgeRange"]) == 16
    assert parse_datetime(event["startDate"]) is not None
    venue, address, _, _ = location_from_jsonld(event["location"])
    assert venue == "Планетарий"
    assert "Тестовая" in address


def test_music_event_jsonld():
    html = '<script type="application/ld+json">{"@type":"MusicEvent","name":"Концерт"}</script>'
    event = event_jsonld(html)
    assert event is not None
    assert event["name"] == "Концерт"
