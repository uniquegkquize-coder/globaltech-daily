import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import generate_images

class ImageRequestTests(unittest.TestCase):
 def test_source_article_photo_is_saved_first_with_explicit_rights_status(self):
  from io import BytesIO
  from PIL import Image
  class Page:
   ok=True
   url='https://example.org/story'
   headers={'content-type':'text/html; charset=utf-8'}
   text='<html><head><meta property="og:image" content="https://cdn.example.org/story-photo.jpg"><meta property="og:site_name" content="Example News"></head></html>'
  class Photo:
   ok=True
   url='https://cdn.example.org/story-photo.jpg'
   headers={'content-type':'image/jpeg'}
   def __init__(self):
    buf=BytesIO()
    Image.new('RGB',(1280,720),'gray').save(buf,format='JPEG')
    self.raw=buf.getvalue()
   def iter_content(self,n):yield self.raw
  post={'id':'abcdef012345','source':'https://example.org/story'}
  with tempfile.TemporaryDirectory() as tmp,patch.object(generate_images,'IMAGES',Path(tmp)):
   with patch.object(generate_images.requests,'get',side_effect=[Page(),Photo()]) as get:
    self.assertTrue(generate_images.licensed_source_image(post))
    self.assertEqual(get.call_count,2)
   metadata=json.loads((Path(tmp)/'abcdef012345.json').read_text())
   self.assertEqual(metadata['kind'],'publisher_source')
   self.assertEqual(metadata['rights_status'],'source_rights_unverified')
   self.assertEqual(metadata['source_image'],'https://cdn.example.org/story-photo.jpg')
   self.assertTrue((Path(tmp)/'abcdef012345.jpg').is_file())

 def test_generic_app_store_share_image_is_rejected(self):
  class Page:
   ok=True
   url='https://apps.apple.com/mx/iphone/apps'
   headers={'content-type':'text/html'}
   text='<meta property="og:image" content="https://apps.apple.com/assets/images/share/app-store.png">'
  post={'id':'abcdef012345','source':'https://apps.apple.com/mx/iphone/apps'}
  with tempfile.TemporaryDirectory() as tmp,patch.object(generate_images,'IMAGES',Path(tmp)):
   with patch.object(generate_images.requests,'get',return_value=Page()) as get:
    self.assertFalse(generate_images.licensed_source_image(post))
    self.assertEqual(get.call_count,1)
   self.assertFalse((Path(tmp)/'abcdef012345.jpg').exists())

 def test_representative_commons_photo_is_not_mistaken_for_source_original(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(generate_images,'IMAGES',Path(tmp)):
   (Path(tmp)/'abcdef012345.jpg').write_bytes(b'representative photo')
   (Path(tmp)/'abcdef012345.json').write_text('{"kind":"licensed_photo"}')
   self.assertFalse(generate_images.resolved_featured('abcdef012345'))
   (Path(tmp)/'abcdef012345.json').write_text('{"kind":"publisher_source"}')
   self.assertTrue(generate_images.resolved_featured('abcdef012345'))
   code=(ROOT/'scripts/build.py').read_text()
   self.assertIn("get('kind')!='licensed_photo'",code)
   self.assertIn('Editorial illustration',code)

 def test_zero_budget_makes_no_external_requests(self):
  with patch.object(generate_images,'MAX_NEW',0),patch.dict('os.environ',{'MAX_LICENSED_PHOTOS_PER_RUN':'0'}),patch.object(generate_images.requests,'get') as get,patch.object(generate_images.requests,'post') as post:
   generate_images.main()
   get.assert_not_called();post.assert_not_called()
 def test_missing_image_license_is_not_labelled_creative_commons(self):
  tree=ast.parse((ROOT/'scripts/build.py').read_text())
  fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='image_caption')
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);folder=root/'content/featured';folder.mkdir(parents=True)
   (folder/'sample.json').write_text(json.dumps({'kind':'publisher_source','attribution':'Example publisher','license':''}))
   context={'R':root,'slug':lambda p:'sample','json':json}
   exec(compile(ast.Module(body=[fn],type_ignores=[]),'caption','exec'),context)
   self.assertEqual(context['image_caption']({},'en'),'Image: Example publisher')
   self.assertNotIn('Creative Commons',context['image_caption']({},'hi'))
 def test_commons_search_uses_real_subject_names(self):
  queries=generate_images.commons_queries("Atlanta Dream and Golden State Valkyries Face Off in Historic WNBA Finals Game 7")
  self.assertTrue(queries)
  self.assertIn("Atlanta Dream",queries[0])
  self.assertNotIn(" and ",queries[0])
  self.assertEqual(generate_images.commons_queries("!!!"),[])

 def test_commons_license_requires_commercial_reuse_rights(self):
  allowed=generate_images.commons_reuse_allowed
  self.assertTrue(allowed('CC BY-SA 4.0','https://creativecommons.org/licenses/by-sa/4.0/'))
  self.assertTrue(allowed('CC0',''))
  self.assertFalse(allowed('CC BY-NC 4.0','https://creativecommons.org/licenses/by-nc/4.0/'))
  self.assertFalse(allowed('All rights reserved',''))

 def test_backfill_reserves_capacity_for_old_posts(self):
  import datetime
  now=datetime.datetime(2026,11,1,12,tzinfo=datetime.timezone.utc)
  fresh=[{'id':format(i,'012x'),'date':'2026-11-01T10:00:00+00:00'} for i in range(1,9)]
  old=[{'id':format(i,'012x'),'date':'2025-04-01T10:00:00+00:00'} for i in range(20,28)]
  with tempfile.TemporaryDirectory() as temp,patch.object(generate_images,'IMAGES',Path(temp)):
   selected,nfresh,nolder=generate_images.choose_backfill(fresh+old,now=now,limit=8)
   self.assertEqual((nfresh,nolder),(8,8))
   self.assertEqual(len(selected),8)
   self.assertTrue(any(p in fresh for p in selected))
   self.assertTrue(any(p in old for p in selected))
   # Existing real photos must never be overwritten by backfill.
   (Path(temp)/(fresh[0]['id']+'.jpg')).write_bytes(b'photo exists')
   selected,nfresh,nolder=generate_images.choose_backfill(fresh+old,now=now,limit=8)
   self.assertNotIn(fresh[0],selected)

 def test_archive_cursor_advances_and_does_not_repeat_same_chunk(self):
  import datetime
  now=datetime.datetime(2026,11,1,12,tzinfo=datetime.timezone.utc)
  older=[{'id':format(i,'012x'),'date':'2025-01-01T10:00:00+00:00'} for i in range(1,25)]
  cursor={}
  with tempfile.TemporaryDirectory() as temp,patch.object(generate_images,'IMAGES',Path(temp)):
   first,_,_=generate_images.choose_backfill(older,now=now,limit=6,cursor=cursor,mode='archive')
   second,_,_=generate_images.choose_backfill(older,now=now,limit=6,cursor=cursor,mode='archive')
   self.assertEqual(len(first),6)
   self.assertEqual(len(second),6)
   self.assertFalse({p['id'] for p in first}&{p['id'] for p in second})
   self.assertEqual(cursor.get('archive_offset'),12)

 def test_original_source_credit_visible_under_publisher_images(self):
  tree=ast.parse((ROOT/'scripts/build.py').read_text())
  fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='image_caption')
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);folder=root/'content/featured';folder.mkdir(parents=True)
   (folder/'sample.json').write_text(json.dumps({'kind':'publisher_source','attribution':'Jane Photographer','license':'CC BY 4.0'}))
   context={'R':root,'slug':lambda p:'sample','json':json}
   exec(compile(ast.Module(body=[fn],type_ignores=[]),'caption','exec'),context)
   self.assertIn('Jane Photographer',context['image_caption']({},'en'))
   self.assertIn('CC BY 4.0',context['image_caption']({},'en'))

 def test_source_original_has_clickable_photo_source_and_license(self):
  import html
  tree=ast.parse((ROOT/'scripts/build.py').read_text())
  fns=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('image_caption','image_caption_html')]
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);folder=root/'content/featured';folder.mkdir(parents=True)
   (folder/'sample.json').write_text(json.dumps({
     'kind':'publisher_source','attribution':'Jane Photographer','license_name':'CC BY-SA 4.0',
     'license':'https://creativecommons.org/licenses/by-sa/4.0/',
     'source_image':'https://commons.wikimedia.org/wiki/File:Example.jpg'}))
   context={'R':root,'slug':lambda p:'sample','json':json,'e':html.escape}
   exec(compile(ast.Module(body=fns,type_ignores=[]),'caption','exec'),context)
   caption=context['image_caption_html']({},'en')
   self.assertIn('Jane Photographer',caption)
   self.assertIn('Photo source',caption)
   self.assertIn('License terms',caption)
   self.assertIn('Cropped to 16:9',caption)

 def test_generic_job_listing_never_receives_unrelated_commons_photo(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(generate_images,'IMAGES',Path(temp)),patch.object(generate_images.requests,'get') as get:
   post={'id':'abcdef012345','category':'private-vacancy','source_title':'Administrative Assistant Jobs in Boydton'}
   self.assertFalse(generate_images.commons_photo(post))
   get.assert_not_called()

 def test_commons_search_rejects_seals_and_pdf_previews(self):
  class ApiResponse:
   def raise_for_status(self):pass
   def json(self):
    return {'query':{'pages':{
      '1':{'title':'File:Atlanta Dream press office seal.gif'},
      '2':{'title':'File:Atlanta Dream planning document.pdf'}
    }}}
  with tempfile.TemporaryDirectory() as temp,patch.object(generate_images,'IMAGES',Path(temp)),patch.object(generate_images.requests,'get',return_value=ApiResponse()) as get:
   post={'id':'abcdef012345','category':'sports','source_title':'Atlanta Dream New Season'}
   self.assertFalse(generate_images.commons_photo(post))
   self.assertEqual(get.call_count,len(generate_images.commons_queries(post['source_title'])))

if __name__=='__main__':unittest.main()
