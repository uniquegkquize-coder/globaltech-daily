import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import requests
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import generate_images as g

class OriginalReliabilityTests(unittest.TestCase):
 def test_unlicensed_page_original_is_saved_without_invented_rights(self):
  class Page:
   status_code=200;ok=True;url='https://example.org/story';headers={'content-type':'text/html'}
   text='<meta property="og:image" content="https://example.org/broken.jpg"><article><img src="/actual.jpg"></article>'
  class Photo:
   ok=True
   def iter_content(self,n):
    buf=io.BytesIO();Image.new('RGB',(480,270),'red').save(buf,'JPEG');yield buf.getvalue()
   def close(self):pass
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   with patch.object(g.requests,'get',side_effect=[Page(),requests.Timeout(),Photo()]):
    self.assertTrue(g.licensed_source_image({'id':'abcdef','source':Page.url}))
   meta=json.loads((Path(tmp)/'abcdef.json').read_text())
   self.assertEqual(meta['source_image'],'https://example.org/actual.jpg')
   self.assertEqual(meta['rights_status'],'publisher_original_unverified')
   self.assertEqual(meta['license'],'')
   self.assertEqual(meta['authorization'],{})
 def test_all_mode_advances_past_recent_failed_attempts(self):
  posts=[{'id':format(n,'06x')} for n in range(1,5)]
  cursor={'attempts':{'000001':{'retry_after':100},'000002':{'retry_after':200}}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   rows,_,_=g.choose_backfill(posts,limit=2,cursor=cursor,mode='all')
  self.assertEqual({p['id'] for p in rows},{'000003','000004'})

class PublisherMarkupTests(unittest.TestCase):
 def test_press_release_and_lazy_background_images_are_found(self):
  from bs4 import BeautifulSoup
  soup=BeautifulSoup('''<div class="release-body"><img data-src="/release.jpg"></div><main><div style="background-image:url('/hero.jpg')"></div><div data-bg="/lazy.jpg"></div></main>''','html.parser')
  urls={row['url'] for row in g.source_candidates(soup,'https://example.org/story')}
  self.assertTrue({'https://example.org/release.jpg','https://example.org/hero.jpg','https://example.org/lazy.jpg'} <= urls)
 def test_tracking_and_generic_publisher_badges_are_not_photo_candidates(self):
  for url in ['https://rt.prnewswire.com/rt.gif?NewsItemId=123','https://example.org/subject-and-industry-code-images/CPR.jpg','https://cdn.example.org/is/image/site/Facebook?qlt=82']:
   self.assertTrue(g.generic_image(url),url)
