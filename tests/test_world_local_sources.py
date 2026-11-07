import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs,urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import world_local_sources as w
import collect as n
import trending_watch as t

class WorldwideLocalSourcesTests(unittest.TestCase):
 def test_full_registry_and_small_settlements_are_present(self):
  stats=w.registry_stats()
  self.assertEqual(stats['country_territory_count'],250)
  self.assertGreater(stats['place_name_count'],200000)
  self.assertEqual(stats['countries_with_places'],246)
  for code in ('IN','CN','RU','SA','NP','IS','FJ','GL','AQ','XK'):
   self.assertIn(code,w.world_registry())

 def test_every_country_is_reached_in_bounded_rotation(self):
  queries=[]
  for cycle in range(8):
   rows=w.world_city_feeds([],now=cycle*7200,limit=32)
   self.assertEqual(len(rows),32)
   queries.extend(parse_qs(urlparse(row[0]).query)['q'][0] for row in rows)
  for country in w.world_registry().values():
   self.assertTrue(any('"'+country['name'].replace('"','')+'"' in query for query in queries),country['name'])

 def test_unknown_news_edition_uses_supported_fallback(self):
  fixture={'AQ':{'name':'Antarctica','languages':'en','places':[]}}
  with patch.object(w,'world_registry',return_value=fixture):
   rows=w.world_city_feeds([],now=0,limit=32)
  self.assertEqual(len(rows),1)
  params=parse_qs(urlparse(rows[0][0]).query)
  self.assertEqual(params['ceid'],['US:en'])
  self.assertIn('Antarctica',params['q'][0])
  self.assertEqual(rows[0][2],'')

 def test_known_and_new_publishers_alternate(self):
  fixture={'GB':{'name':'United Kingdom','languages':'en','places':['Amherst']}}
  with patch.object(w,'world_registry',return_value=fixture):
   first=w.world_city_feeds([('bbc.com','GB','en-GB','en')],now=0,limit=1)
   second=w.world_city_feeds([('bbc.com','GB','en-GB','en')],now=7200,limit=1)
  self.assertEqual(first[0][2],'bbc.com')
  self.assertEqual(second[0][2],'')
  self.assertIn('Amherst',parse_qs(urlparse(second[0][0]).query)['q'][0])

 def test_publisher_metadata_must_match_the_original_article(self):
  self.assertEqual(w.matched_publisher('https://regionalpaper.org','https://regionalpaper.org/news/story'),'regionalpaper.org')
  self.assertEqual(w.matched_publisher('https://regionalpaper.org','https://regionalpaper.org.evil.net/news/story'),'')
  self.assertEqual(w.matched_publisher('https://bbc.co.uk','https://www.bbc.com/news/story'),'bbc.co.uk')
  for value in ('http://regionalpaper.org','https://127.0.0.1','https://169.254.169.254','https://[::1]','https://localhost','https://news.google.com','https://paper.internal','https://user:password@regionalpaper.org'):
   self.assertEqual(w.public_publisher_host(value),'',value)

 def test_learned_publishers_survive_the_next_run(self):
  with tempfile.TemporaryDirectory() as root:
   w.save_local_publishers(root,{'regionalpaper.org','127.0.0.1','news.google.com'})
   self.assertEqual(w.load_local_publishers(root),{'regionalpaper.org'})

 def test_main_publisher_registers_only_matching_rss_sources(self):
  link='https://news.google.com/rss/articles/example'
  row=(link,'Local district police report a village fire','world-news','','https://regionalpaper.org')
  with patch.object(n,'DISCOVERED_LOCAL_DOMAINS',set()),patch.object(n,'resolve_google_news',return_value='https://regionalpaper.org/news/fire'):
   result=n.resolve_rss_story(row)
   self.assertEqual(result[3],'regionalpaper.org')
   self.assertTrue(n.approved_news_publisher(result[0],'world-news'))
  with patch.object(n,'DISCOVERED_LOCAL_DOMAINS',set()),patch.object(n,'resolve_google_news',return_value='https://unrelated.org/news/fire'):
   self.assertIsNone(n.resolve_rss_story(row))
   self.assertFalse(n.DISCOVERED_LOCAL_DOMAINS)

 def test_arabic_russian_and_bengali_incidents_are_detected(self):
  for headline in ('حريق في قرية قريبة','В деревне произошел пожар','গ্রামে অগ্নিকাণ্ড'):
   self.assertIsNotNone(t.LOCAL_INCIDENT.search(headline),headline)

 def test_worldwide_rss_registers_an_original_local_publisher(self):
  import datetime as dt
  date=dt.datetime.now(dt.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
  xml=('<rss><channel><item><title>Village fire reported by local district authorities</title>'
       '<link>https://news.google.com/rss/articles/example</link><pubDate>'+date+'</pubDate>'
       '<source url="https://regionalpaper.org">Regional Paper</source></item></channel></rss>').encode()
  response=type('Response',(),{'content':xml,'raise_for_status':lambda self:None})()
  feeds=[('https://news.google.com/rss/search?q=local','world-news','')]
  with tempfile.TemporaryDirectory() as root,patch.object(n,'ROOT',Path(root)),patch.object(n,'DISCOVERED_LOCAL_DOMAINS',set()),patch.object(n,'DISCOVERY_DEADLINE',0),patch.dict(n.os.environ,{'NEWS_CATEGORY':''}),patch.object(n,'world_city_feeds',return_value=feeds),patch.object(n.requests,'get',return_value=response),patch.object(n,'resolve_google_news',return_value='https://regionalpaper.org/news/fire'):
   rows=n.worldwide_local_stories()
   self.assertEqual(rows[0][3],'regionalpaper.org')
   self.assertEqual(w.load_local_publishers(root),{'regionalpaper.org'})

 def test_country_discovery_precedes_broad_search(self):
  sample=('https://regionalpaper.org/news/fire','Village fire reported by local district authorities','world-news','regionalpaper.org')
  with tempfile.TemporaryDirectory() as root,patch.object(n,'PENDING',Path(root)),patch.object(n,'published_categories',return_value={}),patch.object(n,'google_trending_terms',return_value=set()),patch.object(n,'worldwide_local_stories',return_value=[sample]),patch.object(n,'authority_boards',return_value=[]),patch.object(n,'save_board_evidence'),patch.object(n,'native_feed_stories',side_effect=AssertionError('native scan called too early')):
   generator=n.candidates()
   self.assertEqual(next(generator),sample)
   generator.close()
