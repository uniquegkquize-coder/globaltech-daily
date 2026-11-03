import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from article_layout import render, guide_body, excerpt
from publish_directory_guides import article


class ArticleLayoutTests(unittest.TestCase):
    def test_legacy_guide_keeps_units_variants_and_removes_scraped_controls(self):
        raw = '''## Overview

A source-backed model guide.

## Source-listed information

- **Battery:** Model: 4750 mAh; Pro: 5000 mAh
- **Os:** [ edit ]

## Specification Rows

- section: caption clutter; label: Battery; value: Model: 4750 mAh; Pro: 5000 mAh; source url: https://example.com
- section: caption clutter; label: Rear camera; value: 50 MP; source url: https://example.com
- section: navigation; label: Other, software; value: unrelated products; source url: https://example.com
'''
        migrated = guide_body(raw)
        self.assertEqual(guide_body(migrated), migrated)
        body, toc, minutes = render(migrated)
        soup = BeautifulSoup(body, 'html.parser')
        self.assertEqual(len(soup.select('tbody tr')), 2)
        self.assertIn('Model: 4750 mAh; Pro: 5000 mAh', soup.text)
        self.assertNotIn('caption clutter', soup.text)
        self.assertNotIn('[ edit ]', soup.text)
        self.assertNotIn('unrelated products', soup.text)
        self.assertGreaterEqual(minutes, 1)

    def test_heading_links_resolve_even_with_duplicates_and_hindi(self):
        body, toc, _ = render('## विवरण\n\nFirst.\n\n## विवरण\n\nSecond.\n\n### Child', 'hi')
        soup = BeautifulSoup(toc + body, 'html.parser')
        ids = [h['id'] for h in soup.select('h2,h3')]
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual([a['href'][1:] for a in soup.select('nav a')], ids)

    def test_semantic_lists_tables_quotes_and_escaped_html(self):
        body, _, _ = render('## Steps\n\n1. First\n2. Second\n\n- Separate\n\n| Item | Detail |\n| --- | --- |\n| Screen | <script>alert(1)</script> |\n\n> Attributed quote\n\n[Unsafe](javascript:alert(1))')
        soup = BeautifulSoup(body, 'html.parser')
        self.assertEqual(len(soup.select('ol li')), 2)
        self.assertEqual(len(soup.select('ul li')), 1)
        self.assertTrue(soup.select_one('th[scope="row"]'))
        self.assertTrue(soup.blockquote)
        self.assertIsNone(soup.script)
        self.assertFalse(soup.select('a[href^="javascript:"]'))

    def test_summary_uses_prose_without_markdown_fragments(self):
        self.assertEqual(excerpt('## Overview\n\n**Phone** has [details](https://example.com).\n\n- List'), 'Phone has details.')
        self.assertNotIn('**', excerpt('', '**Short** summary'))

    def test_new_guides_use_same_clean_tables(self):
        _, post = article('phones', 'Example phone', {'battery': '5000 mAh', 'ram': '8 GB', 'os': '[ edit ]'}, 'https://example.com')
        self.assertIn('| Battery | 5000 mAh |', post['en_body'])
        self.assertNotIn('[ edit ]', post['en_body'])
        self.assertIn('| Battery | 5000 mAh |', post['hi_body'])


if __name__ == '__main__':
    unittest.main()
