import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from staging_capsule import make_capsule,validate_capsule
class CapsuleTests(unittest.TestCase):
 def fixture(self,root):
  for name in ('404.html','_redirects','_headers','robots.txt','sitemap.xml','news-sitemap.xml'):(root/name).write_text('public bytes')
  package={'release_id':'a'*64,'url_inventory':{'/en/news/a/':{'key':'object','sha256':'b'*64}}}
  receipt={'release_id':'a'*64,'verified':True}
  return make_capsule(root,package,receipt,'c'*40,'d'*64)
 def test_exact_handoff_and_asset_checksums(self):
  with tempfile.TemporaryDirectory() as tmp:
   v=self.fixture(Path(tmp));self.assertIn('/en/news/a/',validate_capsule(v));self.assertEqual(v['pages_files'],6)
 def test_corrupt_asset_and_missing_receipt_are_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   v=self.fixture(Path(tmp));bad=copy.deepcopy(v);bad['files'][0]['sha256']='wrong'
   with self.assertRaises(ValueError):validate_capsule(bad)
   v['receipt']['verified']=False
   with self.assertRaises(ValueError):validate_capsule(v)
 def test_path_traversal_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   v=self.fixture(Path(tmp));v['files'][0]['path']='../source.json'
   with self.assertRaises(ValueError):validate_capsule(v)
