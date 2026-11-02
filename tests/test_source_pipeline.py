import pathlib
import sys
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from bs4 import BeautifulSoup
from focused_sources import structured_article_data,content_candidates
import collect

class SourcePipelineTests(unittest.TestCase):
    def test_nested_article_schema_and_nonarticle_rejection(self):
        soup=BeautifulSoup('<script type="application/ld+json">{"@graph":[{"@type":"WebPage","mainEntity":{"@type":"NewsArticle","datePublished":"2026-10-31T10:00:00Z","articleBody":"Official launch details"}},{"@type":"Organization","articleBody":"navigation"}]}</script>','html.parser')
        bodies,dates=structured_article_data(soup)
        self.assertEqual(bodies,['Official launch details'])
        self.assertEqual(dates,['2026-10-31T10:00:00Z'])
        self.assertEqual(structured_article_data(BeautifulSoup('<script type="application/ld+json">{"@type":null}</script>','html.parser')),([],[]))
        self.assertTrue(collect.allowed('https://www.bbc.com/news/article','bbc.co.uk'))
        self.assertFalse(collect.allowed('https://bbc.com.evil.example/news','bbc.co.uk'))
    def test_actual_article_container_not_metadata_only(self):
        soup=BeautifulSoup('<div class="news-text"><p>'+('Launch specifications and regional prices. '*6)+'</p></div>','html.parser')
        self.assertGreater(collect.words(max(content_candidates(soup,collect.clean),key=len)),20)
        generic=BeautifulSoup('<meta property="og:type" content="article"><div class="custom">'+'<p>'+('Launch details and technical specifications. '*20)+'</p></div>','html.parser')
        self.assertTrue(content_candidates(generic,collect.clean))
        listing=BeautifulSoup('<div class="custom"><p>'+('Menu and listing links. '*20)+'</p></div>','html.parser')
        self.assertFalse(content_candidates(listing,collect.clean))
    def test_routing_independent_of_discovery_method(self):
        self.assertEqual(collect.category('New Hyundai SUV launch price and mileage','automobiles'),'car-launches')
        self.assertEqual(collect.category('Samsung Galaxy phone launched with new battery','technology'),'mobile-launches')
        self.assertEqual(collect.category('First trailer arrives for the new film','movies-entertainment'),'movie-releases')
        self.assertEqual(collect.category('Actor responds to public controversy and allegations','movies-entertainment'),'controversies')
        self.assertEqual(collect.category('Company share price rises after earnings','business'),'business')
        self.assertNotEqual(collect.category('Pixel Watch 5 specifications and battery price','technology'),'mobile-launches')
        self.assertEqual(collect.category('Pixel 11 deal hits a low price','technology'),'deals-offers')
        self.assertEqual(collect.category('OnePlus smartphone goes official with new features','technology'),'mobile-launches')
        self.assertEqual(collect.category('New thriller gets a release date','movies-entertainment'),'movie-releases')
        self.assertNotEqual(collect.category('Samsung Wallet announces new cash card for Galaxy users','technology'),'mobile-launches')
        self.assertNotEqual(collect.category('Samsung Wallet announces new cash card for Galaxy users','mobile-launches'),'mobile-launches')
        self.assertEqual(collect.category('Manufacturer quarterly earnings report','car-launches'),'automobiles')
        self.assertNotEqual(collect.category_for_url('Simpsons debut release date announced','movies-entertainment','https://example.com/tv/news/announcement'),'movie-releases')
    def test_website_leads_are_classified_before_queueing(self):
        class Response:
            status_code=200
            encoding='utf-8'
            def close(self):pass
            def iter_content(self,n):yield self.text.encode()
            url='https://www.cardekho.com/india-car-news.htm'
            headers={'content-type':'text/html'}
            text='<main><a href="/india-car-news/new-suv-launch-12345.htm">New Hyundai SUV launch price and mileage details</a></main>'
            def raise_for_status(self):pass
        with patch.object(collect.requests,'get',return_value=Response()):
            item,rows=collect.website_stories(('https://www.cardekho.com/india-car-news.htm','automobiles','cardekho.com'))
        self.assertEqual(rows[0][2],'car-launches')
    def test_blocked_publisher_is_not_replaced_by_feed_text(self):
        import requests
        collect.source_text.cache_clear()
        with patch.object(collect.requests,'get',side_effect=requests.HTTPError('403')):
            self.assertEqual(collect.source_text('https://example.com/news/article','example.com'),'')
    def test_native_discovery_runs_before_search(self):
        source=(ROOT/'scripts/collect.py').read_text()
        body=source[source.index('def candidates():'):]
        self.assertLess(body.index('native_feed_stories()'),body.index('google_news_stories'))
if __name__=='__main__':unittest.main()
