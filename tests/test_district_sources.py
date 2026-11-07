import datetime as dt
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import district_sources as d
import collect

class DistrictSourcesTests(unittest.TestCase):
 def test_catalog_uses_only_real_district_feed_links(self):
  good='https://api.livehindustan.com/feeds/rss/uttar-pradesh/gorakhpur/rssfeed.xml'
  html=''.join('<a href="'+u+'">RSS</a>' for u in [good,good,good.replace('api.livehindustan.com','evil.example'),'https://api.livehindustan.com/feeds/rss/crime/rssfeed.xml'])
  self.assertEqual(d.catalog_feeds(html),[good])
 def test_catalog_failure_retains_verified_seed(self):
  import requests
  with tempfile.TemporaryDirectory() as root,patch.object(d.requests,'get',side_effect=requests.Timeout()):
   rows=d.district_feeds(root,1000000,6)
   self.assertTrue(any('/gorakhpur/' in row[0] for row in rows))
   self.assertEqual(d.district_feeds(root,1000001,6),rows)
 def test_city_search_pins_small_towns_and_rotates_publishers(self):
  regions={'Uttar Pradesh':['Gorakhpur','Deoria'],'Bihar':['Patna']}
  a=d.district_search_feeds(regions,1000000)
  b=d.district_search_feeds(regions,1007200)
  self.assertNotEqual(a,b)
  from urllib.parse import unquote_plus
  queries=' '.join(unquote_plus(row[0]) for row in a)
  for term in ('bhaskar.com/local/','Sahjanwa','Gola Bazar','गोरखपुर'):
   self.assertIn(term,queries)
  self.assertTrue(all(row[1]=='india-news' for row in a))
 def test_requested_story_priority_expires(self):
  stamp=dt.datetime.fromtimestamp(1000000,dt.timezone.utc).isoformat()
  self.assertTrue(collect.is_requested_draft({'requested_at':stamp},1000001))
  self.assertFalse(collect.is_requested_draft({'requested_at':stamp},1200000))
  self.assertFalse(collect.is_requested_draft({'requested_at':'bad'},1000001))
 def test_local_publishers_are_eligible_in_isolated_india_run(self):
  domains={domain for _,cat,domain in collect.FEEDS if cat=='india-news'}
  self.assertTrue({'bhaskar.com','livehindustan.com','amarujala.com'}.issubset(domains))


 def test_worldwide_city_search_is_bounded_and_rotates(self):
  from urllib.parse import unquote_plus
  publishers=[('bbc.com','GB','en-GB','en'),('patch.com','US','en-US','en')]
  first=d.world_city_feeds(publishers,now=14400,limit=4)
  second=d.world_city_feeds(publishers,now=28800,limit=4)
  self.assertEqual(len(first),4)
  self.assertNotEqual(first,second)
  self.assertTrue(all(row[1]=='world-news' for row in first+second))
  covered=set()
  for cycle in range(3):
   covered.update(row[0] for row in d.world_city_feeds(publishers,now=cycle*14400,limit=4))
  self.assertEqual(len(covered),12)
  self.assertTrue(any('Amherst' in unquote_plus(url) for url in covered))
  self.assertEqual(d.world_city_feeds([],now=14400),[])

 def test_world_local_publishers_pass_main_source_guard(self):
  for domain in ('patch.com','groundup.org.za','nation.africa','antaranews.com','japantimes.co.jp'):
   self.assertTrue(any(cat=='world-news' and publisher==domain for _,cat,publisher in collect.FEEDS),domain)
