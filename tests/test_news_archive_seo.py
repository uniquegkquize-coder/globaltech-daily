"""Guard against a multi-megabyte news archive page without removing old stories."""
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.news_hub import render_hubs, ALL_NEWS_PREVIEW_LIMIT


class ArchiveSeoTests(unittest.TestCase):
    def test_all_news_uses_bounded_listing_and_preserves_archive_path(self):
        base = dt.datetime(2026, 11, 11, tzinfo=dt.timezone.utc)
        posts = [
            {
                'id': f'{i:03d}',
                'category': 'technology',
                'date': (base - dt.timedelta(minutes=i)).isoformat(),
                'en_title': f'Test headline {i}',
                'hi_title': f'खबर {i}',
            }
            for i in range(140)
        ]
        def shell(lang, title, description, url, body):
            return body
        def article_path(post, lang):
            return f"/{lang}/news/{post['id']}/"
        def title(post, lang):
            return post[f'{lang}_title']
        def write(path, body):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding='utf-8')

        with tempfile.TemporaryDirectory() as temp, patch('scripts.news_hub.load_notices', return_value=[]):
            render_hubs(Path(temp), 'https://globewiredaily.org', posts, shell, article_path, title, write)
            for lang in ('en', 'hi'):
                page = (Path(temp)/lang/'all-news'/'index.html').read_text(encoding='utf-8')
                self.assertEqual(page.count('<li class="hub-item"'), ALL_NEWS_PREVIEW_LIMIT)
                self.assertIn(f'/{lang}/page/6/', page)
                self.assertIn(f'/{lang}/news/000/', page)
                self.assertNotIn(f'/{lang}/news/139/', page)

if __name__ == '__main__':
    unittest.main()
