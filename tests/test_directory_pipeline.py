import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import public_page_fetch as fetcher
import publish_directory_guides as publisher
import research_directory_sources as research
from bs4 import BeautifulSoup

class DirectoryTests(unittest.TestCase):
 def test_explicit_pairs_cover_structured_and_table_fields(self):
  pairs=research.extract_pairs(BeautifulSoup('<script type="application/ld+json">{"additionalProperty":[{"name":"Chipset","value":"Example CPU"}]}</script><table><tr><td>Battery</td><td>5000 mAh</td></tr></table><dl><dt>RAM</dt><dd>8 GB</dd></dl>','html.parser'))
  self.assertEqual(pairs['chipset'],'Example CPU');self.assertEqual(pairs['battery'],'5000 mAh');self.assertEqual(pairs['ram'],'8 GB')
 def test_course_tables_keep_course_fees_and_eligibility_associated(self):
  soup=BeautifulSoup('<table><tr><th>Course</th><th>Duration</th><th>Total Fees</th></tr><tr><td>BTech</td><td>4 Years</td><td>INR 800000</td></tr></table>','html.parser')
  rows=research.extract_course_rows(soup)
  self.assertEqual(rows,[{'course':'BTech','duration':'4 Years','total fees':'INR 800000'}])
 def test_units_in_labels_are_preserved_and_image_sizes_ignored(self):
  html='<title>Test Phone</title><script type="application/ld+json">{"@type":"ImageObject","width":"900"}</script><table><tr><td>Battery capacity (mAh)</td><td>5000</td></tr></table>'
  with patch.object(research,'fetch_public_html',return_value=(html,'https://example.com/test-phone','http')):
   facts=research.enrich('phones','Test Phone',{},Mock(),'https://example.com/test-phone')
  self.assertEqual(facts['battery'],'5000 mAh')
  self.assertNotIn('dimensions',facts)
 def test_new_limit_updates_and_dates(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(publisher,'ROOT',Path(tmp)),patch.object(publisher,'POSTS',Path(tmp)/'content/posts'):
   content=Path(tmp)/'content';content.mkdir()
   details={'phones':{f'Phone {i}':{'display':'6 inches','battery':'5000 mAh','source_url':'https://example.com/phone'} for i in range(3)}}
   (content/'directory-details.json').write_text(json.dumps(details))
   publisher.main();status=json.loads((content/'directory-guide-status.json').read_text());self.assertEqual(status['published'],2)
   first=next((content/'posts').glob('*.json'));old=json.loads(first.read_text())
   details['phones'][old['directory_name']]['battery']='5100 mAh';(content/'directory-details.json').write_text(json.dumps(details))
   publisher.main();status=json.loads((content/'directory-guide-status.json').read_text());self.assertEqual(status['published'],1);self.assertEqual(status['updated'],1)
   self.assertEqual(json.loads(first.read_text())['date'],old['date'])
   publisher.main();status=json.loads((content/'directory-guide-status.json').read_text());self.assertEqual(status['published'],0);self.assertEqual(status['updated'],0)
 def test_access_denied_never_launches_browser(self):
  response=Mock(status_code=403,url='https://example.com');client=Mock();client.get.return_value=response
  with tempfile.TemporaryDirectory() as tmp,patch.object(fetcher,'CACHE',Path(tmp)),patch.dict('os.environ',{'ENABLE_PUBLIC_BROWSER_FALLBACK':'1'}):
   self.assertEqual(fetcher.fetch_public_html('https://example.com',session=client)[2],'access-denied-403')
   self.assertEqual(client.get.call_count,1)
   self.assertTrue(fetcher.fetch_public_html('https://example.com',session=client)[2].startswith('cached-'))
   self.assertEqual(client.get.call_count,1)
 def test_wikidata_identifier_does_not_hide_official_evidence(self):
  record={'source_url':'http://www.wikidata.org/entity/Q1','official_url':'https://manufacturer.example/model'}
  self.assertEqual(publisher.evidence_source(record),record['official_url'])
  self.assertEqual(research.evidence_source(record),record['official_url'])
 def test_js_shell_requests_rendering(self):
  self.assertTrue(fetcher.needs_render('<div id="root"></div><script src="app.js"></script>'))
 def test_authorized_import_is_not_replaced(self):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'scripts/build.py').read_text())
  names={'image_for','image_caption'}
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  from PIL import Image
  import shutil,re
  from urllib.parse import urlparse
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'content/featured';folder.mkdir(parents=True)
   Image.new('RGB',(1280,720),'red').save(folder/'abc.jpg')
   (folder/'abc.json').write_text(json.dumps({'kind':'licensed_source','attribution':'Photographer','license':'CC BY 4.0'}))
   scope=dict(R=root,OUT=root/'dist',slug=lambda p:'abc',json=json,shutil=shutil,re=re,urlparse=urlparse)
   exec(compile(ast.Module(body=nodes,type_ignores=[]),'image-test','exec'),scope)
   scope['image_for']({});self.assertEqual((root/'dist/images/abc.jpg').read_bytes(),(folder/'abc.jpg').read_bytes())
   self.assertIn('Photographer',scope['image_caption']({},'en'))
if __name__=='__main__':unittest.main()
