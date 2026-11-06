import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from redirect_assets import write_redirects
class RedirectBudgetTests(unittest.TestCase):
 def test_over_limit_legacy_url_still_resolves_to_canonical_article(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   def write(path,body):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
   lines=['/ /en/ 301']+[f'/en/news/{i:012x}/ /en/news/science/article-{i}/ 301' for i in range(2001)]
   result=write_redirects(root,lines,write,'https://example.com')
   self.assertEqual(result,{'server_redirects':2000,'html_redirects':2})
   self.assertEqual(len((root/'_redirects').read_text().splitlines()),2000)
   page=(root/f'en/news/{2000:012x}/index.html').read_text()
   self.assertIn('content="0;url=/en/news/science/article-2000/"',page)
   self.assertIn('href="https://example.com/en/news/science/article-2000/"',page)
 def test_duplicate_descriptive_url_takes_priority(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v)
   write_redirects(root,['/en/news/abcdef/ /en/news/business/canonical/ 301','/en/news/business/duplicate/ /en/news/business/canonical/ 301'],write,'https://example.com',limit=1)
   self.assertTrue((root/'_redirects').read_text().startswith('/en/news/business/duplicate/'))
   self.assertTrue((root/'en/news/abcdef/index.html').exists())
 def test_migration_redirects_never_generate_per_url_html(self):
  import json
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'rendered';root.mkdir()
   def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v)
   rows=['/ /en/ 301']+[f'/en/news/{i:012x}/ /en/news/science/article-{i}/ 301' for i in range(5000)]
   result=write_redirects(root,rows,write,'https://example.com',external=True)
   self.assertEqual(result['html_redirects'],0)
   self.assertEqual(len(list(root.rglob('*.html'))),0)
   self.assertEqual(len(json.loads((root.parent/'redirects.json').read_text())),5001)
if __name__=='__main__':unittest.main()
