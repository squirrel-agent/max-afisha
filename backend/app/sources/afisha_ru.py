from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from app.sources.base import EventSourceAdapter
from app.sources.jsonld import event_jsonld
from app.sources.normalizer import (
    absolute_url,
    clean_text,
    image_from_jsonld,
    location_from_jsonld,
    normalize_category,
    parse_age,
    parse_datetime,
    parse_price,
    source_id_from_url,
)
from app.sources.types import DiscoveredEvent, NormalizedEvent


class AfishaRuAdapter(EventSourceAdapter):
    name = "afisha_ru"
    base_url = "https://www.afisha.ru"

    city_slugs = {
        "moscow": "msk",
        "saint-petersburg": "spb",
    }

    discovery_paths = (
        "events/concerts/",
        "schedule_concert/",
        "schedule_exhibition/",
    )

    allowed_detail_prefixes = (
        "/concert/",
        "/performance/",
        "/exhibition/",
        "/sport/",
        "/movie/",
        "/event/",
    )

    async def discover(self, city: str, limit: int) -> list[DiscoveredEvent]:
        city_slug = self.city_slugs.get(city)
        if not city_slug:
            raise ValueError(f"Unsupported city for Afisha.ru: {city}")

        discovered: dict[str, DiscoveredEvent] = {}
        urls = [
            f"{self.base_url}/{city_slug}/",
            *[f"{self.base_url}/{city_slug}/{path}" for path in self.discovery_paths],
        ]

        for listing_url in urls:
            html = await self.client.get_text(listing_url)
            tree = HTMLParser(html)
            for anchor in tree.css("a[href]"):
                href = anchor.attributes.get("href")
                if not href:
                    continue
                absolute = urljoin(self.base_url, href)
                parsed = urlparse(absolute)
                if parsed.netloc not in {"www.afisha.ru", "afisha.ru"}:
                    continue
                if not any(parsed.path.startswith(prefix) for prefix in self.allowed_detail_prefixes):
                    continue
                source_id = source_id_from_url(absolute)
                title_hint = clean_text(anchor.text(separator=" ", strip=True))
                if source_id not in discovered:
                    discovered[source_id] = DiscoveredEvent(
                        source=self.name,
                        source_event_id=source_id,
                        source_url=absolute,
                        city=city,
                        title_hint=title_hint,
                    )
                if len(discovered) >= limit:
                    return list(discovered.values())

        return list(discovered.values())

    async def fetch_event(self, item: DiscoveredEvent) -> NormalizedEvent | None:
        html = await self.client.get_text(item.source_url)
        tree = HTMLParser(html)
        data = event_jsonld(html)

        if data:
            title = clean_text(data.get("name")) or item.title_hint
            if not title:
                return None
            venue, address, lat, lon = location_from_jsonld(data.get("location"))
            offers = data.get("offers")
            offer_list = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
            prices = [parse_price(o.get("lowPrice") or o.get("price")) for o in offer_list]
            prices = [p for p in prices if p is not None]
            ticket_url = None
            for offer in offer_list:
                if offer.get("url"):
                    ticket_url = absolute_url(item.source_url, offer.get("url"))
                    break
            return NormalizedEvent(
                source=self.name,
                source_event_id=item.source_event_id,
                source_url=item.source_url,
                city=item.city,
                title=title,
                description=clean_text(data.get("description")),
                category=normalize_category(item.category_hint, data.get("eventType"), data.get("@type"), tree.css_first("h1").text() if tree.css_first("h1") else None),
                venue_name=venue,
                address=address,
                lat=lat,
                lon=lon,
                start_at=parse_datetime(data.get("startDate")),
                end_at=parse_datetime(data.get("endDate")),
                price_min=min(prices) if prices else None,
                price_max=max(prices) if prices else None,
                is_free=bool(data.get("isAccessibleForFree") is True or (prices and min(prices) == 0)),
                age_min=parse_age(data.get("typicalAgeRange")),
                image_url=absolute_url(item.source_url, image_from_jsonld(data.get("image"))),
                ticket_url=ticket_url or item.source_url,
                raw_payload={"jsonld": data},
            )

        # Fallback based on stable semantic/meta markup. It intentionally avoids brittle CSS class names.
        h1 = tree.css_first("h1")
        title = clean_text(h1.text(separator=" ", strip=True) if h1 else None) or item.title_hint
        if not title:
            return None
        description_node = tree.css_first('meta[name="description"]')
        image_node = tree.css_first('meta[property="og:image"]')
        description = clean_text(description_node.attributes.get("content") if description_node else None)
        image = image_node.attributes.get("content") if image_node else None
        page_text = clean_text(tree.body.text(separator=" ", strip=True) if tree.body else "") or ""
        price_match = re.search(r"(?:От|от)\s*([0-9\s\xa0]+)\s*₽", page_text)
        age_match = re.search(r"Возраст\s+(\d{1,2})\+", page_text)
        category = normalize_category(page_text[:300], item.source_url)
        is_free = bool(re.search(r"бесплатн\w*|free admission", page_text, re.IGNORECASE))
        parsed_price = parse_price(price_match.group(1)) if price_match else None

        return NormalizedEvent(
            source=self.name,
            source_event_id=item.source_event_id,
            source_url=item.source_url,
            city=item.city,
            title=title,
            description=description,
            category=category,
            price_min=parsed_price if parsed_price is not None else (0 if is_free else None),
            price_max=parsed_price if parsed_price is not None else (0 if is_free else None),
            is_free=is_free,
            age_min=int(age_match.group(1)) if age_match else None,
            image_url=image,
            ticket_url=item.source_url,
            raw_payload={"fallback": True},
        )
