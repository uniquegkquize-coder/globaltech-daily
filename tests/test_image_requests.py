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
if __name__=='__main__':unittest.main()
