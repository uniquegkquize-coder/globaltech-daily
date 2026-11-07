"""Section recommendations must not inherit Sports from their discovery page."""
import ast
import json
from pathlib import Path
import unittest

from scripts.news_config import classify, memberships, sports_correction

ROOT = Path(__file__).resolve().parents[1]


class SportsRoutingTests(unittest.TestCase):
    def test_anant_singh_court_story(self):
        title = "Supreme Court to Hear Plea Challenging Anant Singh's Bail in Murder Case"
        self.assertEqual(classify(title, 'sports'), 'india-news')
        self.assertEqual(sports_correction(title, 'sports', 'https://news.abplive.com/videos/news/india-bihar-news-court-1873908'), 'india-news')

    def test_cross_section_recommendations(self):
        cases = [
            ('Yogi Adityanath Invites Public to Run for Unity', '/news/india/yogi-1874151', 'india-news'),
            ('Iran Warns US and Israel', '/news/world/iran-1874156', 'world-news'),
            ('Singapore Court Fines Indian Woman', '/news/indian-woman-1874007', 'world-news'),
            ('Serbia Election Results Announced', '/news/articles/123', 'world-news'),
        ]
        for title, path, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(sports_correction(title, 'sports', 'https://news.abplive.com'+path), expected)

    def test_genuine_sport_stays(self):
        for title in ['India adds Auqib Nabi to ODI squad', 'Jemimah Rodrigues Returns After Hamstring Recovery', 'Football club wins court appeal', 'Tennis star granted bail']:
            self.assertEqual(sports_correction(title, 'sports'), 'sports')
        title = 'Court dismisses appeal over eligibility'
        self.assertEqual(sports_correction(title, 'sports', 'https://bbc.com/sport/tennis/articles/abc'), 'sports')

    def test_old_wrong_membership_removed(self):
        post = {'category': 'sports', 'en_title': 'Supreme Court to hear Anant Singh bail plea', 'source': 'https://news.abplive.com/videos/news/india-bihar-court-1873908'}
        self.assertNotIn('sports', memberships(post))
        self.assertIn('india-news', memberships(post))

    def test_collector_uses_article_url(self):
        # Load just the router; importing the collector initializes external services.
        tree = ast.parse((ROOT/'scripts/collect.py').read_text())
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'category', 'category_for_url'}]
        from urllib.parse import urlparse
        from authority_sources import authority_url, authority_category, UPDATE
        namespace = dict(classify=classify, sports_correction=sports_correction, urlparse=urlparse,
                         authority_url=authority_url, authority_category=authority_category, AUTHORITY_UPDATE=UPDATE)
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<router>', 'exec'), namespace)
        route = namespace['category_for_url']
        self.assertEqual(route('Supreme Court to hear Anant Singh bail plea', 'sports', 'https://news.abplive.com/news/india/court-123'), 'india-news')
        self.assertEqual(route('Court dismisses bail appeal', 'sports', 'https://bbc.com/sport/tennis/articles/abc'), 'sports')

    def test_repaired_post_keeps_legacy_category(self):
        post = json.loads((ROOT/'content/posts/429db6c1364f.json').read_text())
        self.assertEqual(post['category'], 'india-news')
        self.assertIn('sports', post['previous_categories'])


if __name__ == '__main__':
    unittest.main()
