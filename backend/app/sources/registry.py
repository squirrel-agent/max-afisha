from app.sources.afisha_ru import AfishaRuAdapter
from app.sources.base import EventSourceAdapter
from app.sources.http import SourceHttpClient
from app.sources.yandex_afisha import YandexAfishaAdapter


def build_adapter(name: str, client: SourceHttpClient) -> EventSourceAdapter:
    if name == "afisha_ru":
        return AfishaRuAdapter(client)
    if name == "yandex_afisha":
        return YandexAfishaAdapter(client)
    raise ValueError(f"Unknown source: {name}")
