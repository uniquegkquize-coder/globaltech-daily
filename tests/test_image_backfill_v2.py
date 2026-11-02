import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import generate_images as g
from bs4 import BeautifulSoup

class BackfillV2Tests(unittest.TestCase):
 def test_all_mode_includes_recent_and_archived_directory_profiles(self):
  posts=[{'id':'abc123','date':'2026-11-02T01:00:00+00:00','directory_name':'Test Phone','content_type':'evergreen_directory_guide'}, {'id':'abc124','date':'2020-01-01T00:00:00+00:00'}]
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   selected,_,_=g.choose_backfill(posts,now=datetime.datetime(2026,11,2,tzinfo=datetime.timezone.utc),limit=1000,mode='all')
  self.assertEqual({p['id'] for p in selected},{'abc123','abc124'})
 def test_new_mode_prioritizes_latest_news(self):
  posts=[{'id':'aaa001','date':'2026-11-02T00:00:00+00:00'},{'id':'aaa002','date':'2026-11-01T00:00:00+00:00'},{'id':'aaa003','date':'2020-01-01T00:00:00+00:00'}]
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   selected,_,_=g.choose_backfill(posts,now=datetime.datetime(2026,11,2,tzinfo=datetime.timezone.utc),limit=2,mode='new')
  self.assertEqual([p['id'] for p in selected],['aaa001','aaa002'])
 def test_new_publication_batch_is_not_cut_off_by_old_photo_cap(self):
  posts=[{'id':format(i,'06x'),'date':'2026-11-02T00:00:00+00:00'} for i in range(1,5)]
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   selected,_,_=g.choose_backfill(posts,now=datetime.datetime(2026,11,2,tzinfo=datetime.timezone.utc),limit=1,mode='new')
  self.assertEqual(len(selected),4)
 def test_structured_product_image_and_largest_srcset_are_candidates(self):
  html='<script type="application/ld+json">{"@type":"Product","image":{"url":"/product.jpg","license":"https://creativecommons.org/licenses/by/4.0/"}}</script><article><img src="/tiny.jpg" srcset="/large.jpg 1600w, /small.jpg 400w"></article>'
  rows=g.source_candidates(BeautifulSoup(html,'html.parser'),'https://example.org/page')
  self.assertEqual(rows[0]['url'],'https://example.org/product.jpg')
  urls=[r['url'] for r in rows];self.assertLess(urls.index('https://example.org/large.jpg'),urls.index('https://example.org/small.jpg'))
 def test_wrong_generation_camera_samples_and_dzire_are_not_swift(self):
  self.assertFalse(g.subject_matches('Google Pixel 9','File:Google Pixel 9 Pro.jpg',{}))
  self.assertFalse(g.subject_matches('Maruti Swift','File:Maruti Swift Dzire.jpg',{}))
  self.assertFalse(g.subject_matches('Samsung Galaxy S24','File:Lake.jpg',{'ImageDescription':{'value':'Taken with Samsung Galaxy S24'}}))
  self.assertTrue(g.subject_matches('Samsung Galaxy S24','File:Samsung Galaxy S24 01.jpg',{}))
 def test_access_restrictions_are_not_retried_in_browser(self):
  class Page:status_code=403;ok=False
  with patch.object(g.requests,'get',return_value=Page()) as get:
   self.assertFalse(g.licensed_source_image({'id':'abcdef','source':'https://example.org/denied'}))
  self.assertEqual(get.call_count,1)
 def test_small_open_graph_does_not_hide_valid_article_image(self):
  class Page:
   status_code=200;ok=True;url='https://example.org/story';headers={'content-type':'text/html'}
   text='<meta name="license" content="https://creativecommons.org/licenses/by/4.0/"><meta property="og:image" content="https://example.org/tiny.jpg"><article><img src="https://example.org/real.jpg" alt="Actual product"></article>'
  class Photo:
   ok=True;headers={'content-type':'application/octet-stream'}
   def __init__(self,size):
    buf=io.BytesIO();Image.new('RGB',size,'red').save(buf,'JPEG');self.raw=buf.getvalue()
   def iter_content(self,n):yield self.raw
   def close(self):pass
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   with patch.object(g.requests,'get',side_effect=[Page(),Photo((100,60)),Photo((1280,720))]):
    self.assertTrue(g.licensed_source_image({'id':'abcdef','source':'https://example.org/story'}))
   meta=json.loads((Path(tmp)/'abcdef.json').read_text())
   self.assertEqual(meta['source_image'],'https://example.org/real.jpg')
 def test_institution_photos_are_campus_not_cats_or_portraits(self):
  self.assertFalse(g.subject_matches('IIT Delhi','File:2d cat at IITD.jpg',{'ImageDescription':{'value':'Cat at IIT Delhi campus'}}))
  self.assertFalse(g.subject_matches('IIT Bombay','File:14-InOffice.jpg',{'ImageDescription':{'value':'Professor in his office at IIT Bombay'}}))
  self.assertTrue(g.subject_matches('IIT Delhi','File:Indian Institute of Technology Delhi.jpg',{'ImageDescription':{'value':'Main campus building'}}))
  self.assertTrue(g.subject_matches('IIT Bombay','File:IIT Bombay Manas Apartments.jpg',{}))
 def test_rejected_photo_is_researched_instead_of_marked_complete(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   (Path(tmp)/'abcdef.jpg').write_bytes(b'wrong image')
   (Path(tmp)/'abcdef.json').write_text(json.dumps({'kind':'licensed_photo','subject':'Mahindra Thar','review_status':'replace'}))
   self.assertFalse(g.resolved_featured('abcdef'))
 def test_saved_generic_social_banner_is_not_resolved(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   (Path(tmp)/'abcdef.jpg').write_bytes(b'old image')
   (Path(tmp)/'abcdef.json').write_text(json.dumps({'kind':'publisher_source','source_image':'https://example.org/assets/images/share/app-store.png'}))
   self.assertFalse(g.resolved_featured('abcdef'))

if __name__=='__main__':unittest.main()

class ArticleOriginalPriorityTests(unittest.TestCase):
 def test_representative_stays_eligible_but_publisher_photo_is_preserved(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   for ident,kind in [('abcdef','licensed_photo'),('abcdee','publisher_source')]:
    Image.new('RGB',(1280,720)).save(Path(tmp)/(ident+'.jpg'))
    (Path(tmp)/(ident+'.json')).write_text(json.dumps({'kind':kind,'source_image':'https://example.org/photo.jpg'}))
   selected,_,_=g.choose_backfill([{'id':'abcdef'},{'id':'abcdee'}],limit=10,mode='all')
   self.assertEqual([p['id'] for p in selected],['abcdef'])
 def test_failed_original_lookup_keeps_existing_representative(self):
  class Page:status_code=403;ok=False
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'IMAGES',Path(tmp)):
   photo=Path(tmp)/'abcdef.jpg';Image.new('RGB',(1280,720)).save(photo)
   before=photo.read_bytes()
   (Path(tmp)/'abcdef.json').write_text(json.dumps({'kind':'licensed_photo','source_image':'https://example.org/photo.jpg'}))
   with patch.object(g.requests,'get',return_value=Page()) as get:
    self.assertFalse(g.licensed_source_image({'id':'abcdef','source':'https://example.org/story'}))
   self.assertEqual(get.call_count,1)
   self.assertEqual(photo.read_bytes(),before)
