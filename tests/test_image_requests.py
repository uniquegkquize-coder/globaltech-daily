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

 def test_commons_credit_visible_under_licensed_images(self):
  tree=ast.parse((ROOT/'scripts/build.py').read_text())
  fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='image_caption')
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);folder=root/'content/featured';folder.mkdir(parents=True)
   (folder/'sample.json').write_text(json.dumps({'kind':'licensed_photo','attribution':'Jane Photographer','license':'CC BY 4.0'}))
   context={'R':root,'slug':lambda p:'sample','json':json}
   exec(compile(ast.Module(body=[fn],type_ignores=[]),'caption','exec'),context)
   self.assertIn('Jane Photographer',context['image_caption']({},'en'))
   self.assertIn('CC BY 4.0',context['image_caption']({},'en'))

if __name__=='__main__':unittest.main()
