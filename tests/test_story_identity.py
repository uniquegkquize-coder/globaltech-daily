import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import collect
from story_identity import canonical_lead_key, collapse_posts, same_story


class StoryIdentityTests(unittest.TestCase):
    def test_bbc_global_and_domestic_links_share_identity(self):
        a = 'https://www.bbc.com/sport/football/articles/ckz7x8z1e9y9o'
        b = 'https://www.bbc.co.uk/sport/football/articles/ckz7x8z1e9y9o?at_medium=RSS&at_campaign=rss'
        self.assertEqual(canonical_lead_key(a), canonical_lead_key(b))
        self.assertTrue(collect.duplicate_story(a, 'Rewritten headline', 'cricket', [(b, 'Original headline', 'sports')]))

    def test_document_ids_and_query_order(self):
        self.assertNotEqual(canonical_lead_key('https://example.com/news?id=1'), canonical_lead_key('https://example.com/news?id=2'))
        self.assertEqual(canonical_lead_key('http://example.com/news?b=2&a=1'), canonical_lead_key('https://example.com/news?a=1&b=2'))

    def test_same_headline_is_blocked_across_categories(self):
        headline = 'City police arrest three suspects following market robbery'
        self.assertTrue(collect.duplicate_story('https://a.example/story', headline, 'india-news', [('https://b.example/story', headline, 'sports')]))

    def test_hearing_and_surrender_order_remain_separate(self):
        self.assertFalse(same_story('Supreme Court to hear Anant Singh bail plea in Dularchand Yadav murder case', 'Supreme Court orders Anant Singh surrender in Dularchand Yadav murder case'))

    def test_different_models_and_generic_publisher_titles(self):
        self.assertFalse(same_story('Samsung Galaxy S24 full specifications launch price details', 'Samsung Galaxy S25 full specifications launch price details'))
        self.assertFalse(same_story('Breaking News, World News and Video from Al Jazeera', 'Breaking News, World News and Video from Al Jazeera'))

    def test_index_checks_generated_headlines_too(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            title = 'City police arrest three suspects following market robbery'
            (root / 'one.json').write_text(json.dumps(dict(source='https://a.example/story', source_title='Publisher headline', en_title=title, category='sports')))
            with patch.object(collect, 'POSTS', root):
                index = collect.published_story_index()
            self.assertTrue(collect.duplicate_story('https://b.example/story', title, 'india-news', index))

    def test_build_keeps_source_records_and_produces_redirect_pair(self):
        a = dict(id='one', source='https://www.bbc.com/news/articles/abc', en_title='First headline', en_body='Body')
        b = dict(id='two', source='https://www.bbc.co.uk/news/articles/abc?at_medium=RSS', en_title='Rewritten headline', en_body='Longer body')
        posts = [a, b]
        kept, redirects = collapse_posts(posts)
        self.assertEqual(kept, [b])
        self.assertEqual(redirects, [(a, b)])
        self.assertEqual(posts, [a, b])

    def test_build_preserves_query_identified_articles(self):
        posts = [dict(id=str(i), source='https://example.com/news?id='+str(i), en_title='Headline '+str(i)) for i in (1, 2)]
        self.assertEqual(len(collapse_posts(posts)[0]), 2)


if __name__ == '__main__':
    unittest.main()
