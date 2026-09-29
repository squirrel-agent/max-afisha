from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from selectolax.parser import HTMLParser


def _walk_jsonld(value: Any) -> Iterable[dict]:
    if isinstance(value, dict):
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _walk_jsonld(item)
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_jsonld(item)


def jsonld_objects(html: str) -> list[dict]:
    tree = HTMLParser(html)
    objects: list[dict] = []
    for node in tree.css('script[type="application/ld+json"]'):
        raw = node.text(strip=True)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        objects.extend(_walk_jsonld(parsed))
    return objects


def event_jsonld(html: str) -> dict | None:
    for obj in jsonld_objects(html):
        value = obj.get("@type")
        types = value if isinstance(value, list) else [value]
        if any(str(t).rsplit("/", 1)[-1].lower().endswith("event") for t in types if t):
            return obj
    return None
