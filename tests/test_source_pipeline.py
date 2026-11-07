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

    def test_embedded_json_survives_article_cleanup(self):
        import json
        text=' '.join('sourcefact'+str(i) for i in range(90))
        markup='<title>News</title><script id="__NEXT_DATA__" type="application/json">'+json.dumps({'props':{'articleBody':text}})+'</script>'
        class Response:
            url='https://embedded.example/news/story'
            headers={'content-type':'text/html'}
            text=markup
            def raise_for_status(self):pass
        collect.source_text.cache_clear()
        with patch.object(collect.requests,'get',return_value=Response()),patch.dict('os.environ',{'ENABLE_PUBLIC_BROWSER_FALLBACK':'0'}):
            self.assertEqual(collect.source_text(Response.url,'embedded.example'),text)
    def test_successful_html_shell_can_use_same_url_renderer(self):
        text=' '.join('sourcefact'+str(i) for i in range(90))
        class Response:
            url='https://rendered.example/news/story'
            headers={'content-type':'text/html'}
            text='<title>Public article</title><div id="app"></div>'
            def raise_for_status(self):pass
        collect.source_text.cache_clear()
        with patch.object(collect.requests,'get',return_value=Response()),patch.object(collect,'fetch_public_html',return_value=('<article><p>'+text+'</p></article>',Response.url,'browser')) as render,patch.dict('os.environ',{'ENABLE_PUBLIC_BROWSER_FALLBACK':'1'}):
            self.assertEqual(collect.source_text(Response.url,'rendered.example'),text)
            self.assertEqual(render.call_args.args[0],Response.url)
            self.assertTrue(render.call_args.kwargs['render'])
    def test_rejected_article_is_not_sent_to_renderer(self):
        import requests
        collect.source_text.cache_clear()
        error=requests.HTTPError(response=requests.Response())
        error.response.status_code=403
        with patch.object(collect.requests,'get',side_effect=error),patch.object(collect,'fetch_public_html') as render,patch.dict('os.environ',{'ENABLE_PUBLIC_BROWSER_FALLBACK':'1'}):
            self.assertEqual(collect.source_text('https://blocked-source.example/news/story','blocked-source.example'),'')
            render.assert_not_called()
    def test_focused_sources_are_used_by_the_publisher(self):
        from focused_sources import PAGES,NATIVE_FEEDS,LOCAL_FEEDS,LOCAL_SEARCH_SOURCES
        self.assertIn(('https://www.bikewale.com/news/','automobiles','bikewale.com'),collect.DIRECT_SOURCES)
        self.assertTrue(all(item in collect.DIRECT_SOURCES for item in PAGES))
        self.assertTrue(all(item in NATIVE_FEEDS for item in LOCAL_FEEDS))
        self.assertGreaterEqual(len(LOCAL_SEARCH_SOURCES),40)
        self.assertEqual(collect.category_for_url('Hero Xtreme 125R Stealth Edition Launched at Rs 116250','automobiles','https://www.bikewale.com/news/hero-xtreme/'),'automobiles')


    def test_requested_publishers_and_mobile_identity(self):
        from focused_sources import PAGES, SEARCH_SOURCES
        from story_identity import canonical_lead_key
        for domain in ('carwale.com', 'gsmarena.com', '91mobiles.com'):
            self.assertTrue(any(row[2] == domain for row in PAGES))
            self.assertTrue(any(row[0] == domain for row in SEARCH_SOURCES))
        self.assertEqual(canonical_lead_key('https://m.gsmarena.com/example-news-123.php'),
                         canonical_lead_key('https://www.gsmarena.com/example-news-123.php'))

    def test_publisher_body_wins_over_longer_related_stories(self):
        text = ' '.join('launchfact'+str(i) for i in range(90))
        for domain, container in [('carwale.com', 'articleContent'),
                                  ('91mobiles.com', 'td-post-content'),
                                  ('gsmarena.com', 'news-text')]:
            class Response:
                url = 'https://' + domain + '/news/test-article'
                headers = {'content-type': 'text/html'}
                def raise_for_status(self): pass
            response = Response()
            response.text = '<main><div class="'+container+'"><p>'+text+'</p></div><p>'+('Related clutter. '*300)+'</p></main>'
            collect.source_text.cache_clear()
            with patch.object(collect.requests, 'get', return_value=response):
                self.assertEqual(collect.source_text(response.url, domain), text)

    def test_transient_connection_failure_gets_one_bounded_retry(self):
        import requests
        text=' '.join('sourcefact'+str(i) for i in range(90))
        class Response:
            url='https://retry-source.example/news/story'
            headers={'content-type':'text/html'}
            def raise_for_status(self):pass
        response=Response()
        response.text='<article><p>'+text+'</p></article>'
        collect.source_text.cache_clear()
        with patch.object(collect.requests,'get',side_effect=[requests.ReadTimeout(),response]) as fetch:
            self.assertEqual(collect.source_text(Response.url,'retry-source.example'),text)
            self.assertEqual(fetch.call_count,2)
            self.assertEqual(fetch.call_args.kwargs['timeout'],(4,8))


    def test_bike_news_route_stays_out_of_car_launches(self):
        self.assertEqual(collect.category_for_url('BMW F 450 GS Sport variant launched in India','automobiles','https://www.autocarindia.com/bike-news/bmw-f-450-gs-441276'),'automobiles')
    def test_metadata_schema_alone_does_not_disable_rendering(self):
        from public_page_fetch import needs_render
        self.assertTrue(needs_render('<title>Newsroom</title><script type="application/ld+json">{"@type":"WebSite","name":"Newsroom"}</script><div id="app"></div>'))
        self.assertFalse(needs_render('<table><tr><td>Engine</td><td>125 cc</td></tr></table>'))

if __name__=='__main__':unittest.main()
