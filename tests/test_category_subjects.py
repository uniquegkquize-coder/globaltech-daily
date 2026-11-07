import json
from pathlib import Path
import tempfile
import unittest

from scripts.news_config import route_category, memberships
from scripts.repair_categories import repair


class CategorySubjectsTests(unittest.TestCase):
    def test_real_cross_section_and_ambiguous_keywords(self):
        cases = [
            ('Equitas SFB Shares Fall 27% as CEO Exit Overshadows Q2 Earnings', 'military-tech', '/markets/news/equitas', 'business'),
            ('Nifty IT Index Slips as Infosys Faces Downgrades', 'military-tech', '/markets/news/nifty', 'business'),
            ('Shark Tank Reality Series Returns to ABC', 'military-tech', '/tv/sharktank', 'movies-entertainment'),
            ('De-Armor Open-Source Release for AI Response Calibration', 'military-tech', '/ninetyhe-90/de-armor', 'ai-news'),
            ('Indian Army Announces TGC 145 Recruitment', 'defence', '/indian-army-tgc/', 'sarkari-naukri'),
            ('BBC Football Daily Discusses Striker Recruitment', 'cricket', '/sport/football/articles/123', 'sports'),
            ('Police Recover Buried Cash in Prayagraj Raid', 'sports', '/cities/prayagraj/story', 'india-news'),
            ('Supreme Court Hints at Orders on Delhi Firecrackers', 'sports', '/cities/delhi/story', 'india-news'),
            ('Serbia Election Results Announced', 'cricket', '/news/articles/123', 'world-news'),
            ('Nitish Kumar Reddy Concedes Expensive T20I Over', 'government-schemes', '/sports/cricket/news/story', 'cricket'),
            ('Leylah Fernandez Reaches Pan Pacific Open Final', 'conflict-news', '/sports/2026/10/31/story', 'sports'),
            ('England Begin Wheelchair Rugby World Cup Defence', 'defence', '/sport/rugby/story', 'sports'),
            ('Court dismisses eligibility appeal', 'sports', '/sport/tennis/articles/abc', 'sports'),
            ('BMW F 450 GS Sport variant launched', 'automobiles', '/bike-news/story', 'automobiles'),
            ('Jemimah Rodrigues Returns After Hamstring Recovery', 'cricket', '/news/story', 'cricket'),
            ('Dell Laptop Sees $300 Discount', 'gadgets', '/news/story', 'deals-offers'),
            ('AI Mode Gives Evasive Answers on US Elections', 'ai-news', '/news/story', 'ai-news'),
            ('Tamil Nadu Government Plans Higher Education Framework', 'education', '/education/story', 'education'),
            ('Unclear new development announced', 'travel', '/news/story', 'travel'),
        ]
        for title, old, path, expected in cases:
            with self.subTest(title=title):
                source = 'https://publisher.example' + path
                self.assertEqual(route_category(title, old, source), expected)
                self.assertEqual(route_category(title, expected, source), expected)

    def test_membership_drops_unrelated_seed(self):
        self.assertEqual(memberships({'category': 'military-tech', 'en_title': 'Shark Tank returns'}), {'movies-entertainment'})
        self.assertEqual(memberships({'category': 'government-schemes', 'en_title': 'India wins ODI series'}), {'cricket'})
        self.assertEqual(memberships({'category': 'automobiles', 'en_title': 'Car specifications', 'directory_kind': 'car'}), {'automobiles'})

    def test_repair_preserves_article_and_redirect_history_and_is_idempotent(self):
        post = {'id': 'abc', 'category': 'sports', 'en_title': 'Supreme Court reviews Anant Singh bail',
                'en_body': 'Unchanged body', 'hi_title': 'शीर्षक', 'date': '2026-11-07',
                'source': 'https://publisher.example/news/india/story', 'previous_categories': ['cricket']}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'abc.json'
            path.write_text(json.dumps(post))
            self.assertEqual(len(repair(directory)), 1)
            self.assertEqual(json.loads(path.read_text()), post)
            self.assertEqual(len(repair(directory, write=True)), 1)
            updated = json.loads(path.read_text())
            self.assertEqual(updated['category'], 'india-news')
            self.assertEqual(updated['previous_categories'], ['cricket', 'sports'])
            for key in post.keys() - {'category', 'previous_categories'}:
                self.assertEqual(updated[key], post[key])
            self.assertEqual(repair(directory, write=True), [])
