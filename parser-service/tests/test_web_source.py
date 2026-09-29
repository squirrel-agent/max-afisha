import asyncio
from hashlib import sha1
import unittest
from unittest.mock import AsyncMock

from parser_service.sources.common import event_ld, fallback, from_ld, page_has_city, price_from_html, source_id
from parser_service.sources.web import WebSource


class WebSourceTests(unittest.TestCase):
    def setUp(self):
        self.yandex = WebSource('yandex_afisha', browser=None)
        self.afisha = WebSource('afisha_ru', browser=None)

    def test_yandex_accepts_current_city_section_event_urls(self):
        self.assertTrue(self.yandex.is_event_url(
            'https://afisha.yandex.ru/moscow/concert/teodor-kurentzis', 'moscow'
        ))
        self.assertTrue(self.yandex.is_event_url(
            'https://afisha.yandex.ru/saint-petersburg/theatre/example', 'saint-petersburg'
        ))
        self.assertFalse(self.yandex.is_event_url(
            'https://afisha.yandex.ru/moscow/concert', 'moscow'
        ))
        self.assertFalse(self.yandex.is_event_url(
            'https://afisha.yandex.ru/saint-petersburg/concert/example', 'moscow'
        ))

    def test_city_listing_paths_match_source_routes(self):
        self.assertIn('/saint-petersburg/concert/', self.yandex.listing_paths('saint-petersburg'))
        self.assertIn('/spb/schedule_concert/', self.afisha.listing_paths('saint-petersburg'))
        self.assertTrue(page_has_city('\"Schedule\":[{\"Place\":{\"City\":{\"ShortName\":\"spb\"}}}]', 'saint-petersburg'))

    def test_discover_skips_a_failed_listing_page(self):
        browser = type('FakeBrowser', (), {})()
        calls = 0

        async def get(url, dynamic=False):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError('temporary failure')
            if calls == 2:
                return '<a href="/moscow/concert/example">Show</a>'
            return ''

        browser.get = AsyncMock(side_effect=get)
        source = WebSource('yandex_afisha', browser)
        source.listing_paths = lambda city: ['/moscow/', '/moscow/concert/']
        events = asyncio.run(source.discover('moscow', 10))
        self.assertEqual(events, [('https://afisha.yandex.ru/moscow/concert/example', 'Show')])

    def test_afisha_excludes_category_indexes_from_event_results(self):
        self.assertTrue(self.afisha.is_event_url('https://www.afisha.ru/concert/example/', 'moscow'))
        self.assertFalse(self.afisha.is_event_url('https://www.afisha.ru/movie/', 'moscow'))

    def test_afisha_page_city_marker_matches_event_schedule(self):
        html = '\"Schedule\":[{\"Place\":{\"City\":{\"ShortName\":\"spb\"}}}]'
        self.assertTrue(page_has_city(html, 'saint-petersburg'))
        self.assertFalse(page_has_city(html, 'moscow'))

    def test_jsonld_accepts_music_event_subtypes(self):
        html = '<script type="application/ld+json">{"@type":"MusicEvent","name":"Концерт"}</script>'
        self.assertEqual(event_ld(html)['name'], 'Концерт')

    def test_afisha_price_interval_is_used_without_jsonld_offers(self):
        self.assertEqual(price_from_html('\"PriceInterval\":\"Вход 450–900 р.\"'), 450)

    def test_embedded_schedule_price_uses_matching_city(self):
        html = 'window.__nrpBoot={\"Schedule\":[{\"Place\":{\"City\":{\"ShortName\":\"spb\"}},\"MinPriceFormatted\":\"1200\"},{\"Place\":{\"City\":{\"ShortName\":\"msk\"}},\"MinPriceFormatted\":\"2400\"}]} </script>'
        self.assertEqual(price_from_html(html, city='saint-petersburg'), 1200)
        self.assertEqual(price_from_html(html, city='moscow'), 2400)

    def test_jsonld_event_uses_afisha_embedded_price_interval(self):
        event = from_ld(
            'afisha_ru', 'https://www.afisha.ru/exhibition/example/', 'moscow',
            {'@type': 'Event', 'name': 'Выставка', 'offers': []},
            html='\"PriceInterval\":\"Вход 450–900 р.\"',
        )
        self.assertEqual(event.price_min, 450)


    def test_free_text_is_recognized(self):
        event = fallback(
            'yandex_afisha',
            'https://afisha.yandex.ru/moscow/exhibitions/free-event',
            'moscow',
            '<html><body><h1>Бесплатная выставка</h1><p>Вход бесплатно</p></body></html>',
        )
        self.assertIsNotNone(event)
        self.assertTrue(event.is_free)
        self.assertEqual(event.price_min, 0)

    def test_jsonld_free_flag_is_recognized(self):
        event = from_ld(
            'yandex_afisha',
            'https://afisha.yandex.ru/moscow/exhibitions/free-event',
            'moscow',
            {'@type': 'Event', 'name': 'Бесплатная выставка', 'isAccessibleForFree': True},
        )
        self.assertTrue(event.is_free)
        self.assertEqual(event.price_min, 0)

    def test_id_for_category_root_is_stable(self):
        url = 'https://www.afisha.ru/'
        self.assertEqual(source_id(url), sha1(url.encode('utf-8')).hexdigest()[:20])


if __name__ == '__main__':
    unittest.main()
