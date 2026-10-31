import datetime as dt
import pathlib
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from news_sitemap import write_news_sitemap

NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'n': 'http://www.google.com/schemas/sitemap-news/0.9'}


class NewsSitemapTests(unittest.TestCase):
    def test_split_preserves_every_language_url_and_escapes_xml(self):
        now = dt.datetime(2026, 10, 31, tzinfo=dt.timezone.utc)
        posts = [{'id': str(i), 'date': now.isoformat()} for i in range(1101)]
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            write_news_sitemap(out, 'https://example.org', posts,
                lambda p, lang: f'/{lang}/{p["id"]}/', lambda p, lang: 'News & <analysis>', now)
            index = ET.parse(out / 'news-sitemap.xml').getroot()
            urls = []
            for loc in index.findall('s:sitemap/s:loc', NS):
                child = ET.parse(out / loc.text.rsplit('/', 1)[1]).getroot()
                entries = child.findall('s:url', NS)
                self.assertLessEqual(len(entries), 1000)
                self.assertEqual(child.find('.//n:title', NS).text, 'News & <analysis>')
                urls.extend(x.find('s:loc', NS).text for x in entries)
            self.assertEqual(len(urls), 2202)
            self.assertEqual(len(set(urls)), 2202)
            write_news_sitemap(out, 'https://example.org', [], lambda p, lang: '', lambda p, lang: '', now)
            self.assertEqual(list(out.glob('news-sitemap-[0-9]*.xml')), [])

    def test_recent_only_and_single_file(self):
        now = dt.datetime(2026, 10, 31, tzinfo=dt.timezone.utc)
        dates = [now.isoformat(), (now-dt.timedelta(days=3)).isoformat(),
                 (now+dt.timedelta(days=1)).isoformat(), 'invalid', '2026-10-31']
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            write_news_sitemap(out, 'https://example.org', [{'date': x} for x in dates],
                lambda p, lang: f'/{lang}/', lambda p, lang: 'News', now)
            root = ET.parse(out / 'news-sitemap.xml').getroot()
            self.assertEqual(len(root.findall('s:url', NS)), 2)
