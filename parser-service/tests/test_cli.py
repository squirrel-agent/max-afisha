import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from parser_service import cli


class ParserRunTests(unittest.IsolatedAsyncioTestCase):
    async def test_source_failure_does_not_drop_events_from_other_sources(self):
        class FakeBrowser:
            close = AsyncMock()

        class FakeSource:
            def __init__(self, name, browser):
                self.name = name

            async def crawl(self, city, limit):
                if self.name == 'vk_events':
                    raise RuntimeError('blocked')
                return [object()]

        args = SimpleNamespace(source='all', city='moscow', limit=10, dry_run=True)
        with patch.object(cli, 'Browser', FakeBrowser), patch.object(cli, 'WebSource', FakeSource):
            result = await cli.run(args)

        self.assertEqual(result['parsed'], 2)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['sources'][2]['source'], 'vk_events')
        self.assertEqual(len(result['errors']), 1)


if __name__ == '__main__':
    unittest.main()
