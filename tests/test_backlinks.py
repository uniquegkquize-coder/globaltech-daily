import copy
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
try:
 import yaml
except ImportError:
 yaml=None
from scripts.backlinks import common, discover, score, outreach, verify, report

class BacklinkTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.old=common.DATA; common.DATA=Path(self.temp.name); report.DATA=common.DATA
 def tearDown(self): common.DATA=self.old; report.DATA=self.old; self.temp.cleanup()
 def test_domain_deduplication(self):
  self.assertEqual(common.domain('https://www.Example.com/a#b'),common.domain('http://example.com/b'))
  self.assertNotEqual(common.domain('https://a.example.com'),common.domain('https://b.example.com'))
 def test_scoring_missing_evidence(self): self.assertFalse(score.score({'evidence':{'spam_risk':True}})['qualified'])
 def test_score_weights_and_reject(self):
  row={'contact_page':'https://example.com/contact','evidence':{'topical':True,'policy_page':'x','byline':True,'article_markup':True,'words':1200,'editorial_invitation':True}}
  self.assertEqual(score.score(row)['quality_score'],100)
  row['evidence']['spam_risk']=True; self.assertFalse(score.score(row)['qualified'])
 def test_no_target_match_no_draft(self):
  self.assertIsNone(outreach.choose({'category':'sports','name':'cricket'},[{'category':'education','words':900,'language':'en'}]))
 def test_drafts_idempotent_no_send(self):
  row={'id':'1','domain':'example.com','name':'AI software research','category':'tech-ai','language':'en','topic_excerpt':'AI software research','qualified':True,'contact_page':'https://example.com/contact','evidence':{'editorial_invitation':True}}
  target={'url':common.SITE+'/en/news/ai-software/','title':'AI software research','category':'tech-ai','words':500,'language':'en','evergreen':False}
  common.save('prospects.json',[row]); common.save('targets.json',[target])
  first=outreach.run(); second=outreach.run()
  self.assertEqual(first,second); self.assertEqual(len(second),1); self.assertIsNone(second[0]['sent_at']); self.assertIsNone(second[0]['recipient'])
  self.assertEqual(second[0]['body'].count(target['url']),1)
 def test_exact_target_and_rel_and_placement(self):
  url=common.SITE+'/en/a/'
  yes,other=verify.inspect_html('https://example.com/',url,f'<article><a href="{url}" rel="nofollow ugc">Read more</a></article><a href="{url}?wrong=1">Other</a>')
  self.assertEqual(len(yes),1); self.assertEqual(yes[0]['rel'],['nofollow','ugc']); self.assertEqual(yes[0]['placement'],'article'); self.assertEqual(len(other),1)
 def test_changed_removed_and_inaccessible(self):
  class Fake:
   def get(self,u): return u,'<a href="https://globewiredaily.org/en/other/">Other</a>'
  item={'source_url':'https://example.com/article','target_url':common.SITE+'/en/a/'}
  old={'status':'live','first_seen':'2026-01-01'}
  self.assertEqual(verify.verify_one(Fake(),item,old)['status'],'changed')
  with patch.object(Fake,'get',return_value=(item['source_url'],'<p>No link</p>')):
   self.assertEqual(verify.verify_one(Fake(),item,old)['status'],'removed')
  with patch.object(Fake,'get',side_effect=ValueError('403')):
   got=verify.verify_one(Fake(),item,old); self.assertEqual(got['status'],'inaccessible'); self.assertEqual(got['first_seen'],'2026-01-01')
 def test_internal_link_rejected(self):
  got=verify.verify_one(None,{'source_url':common.SITE+'/en/','target_url':common.SITE+'/en/a/'})
  self.assertEqual(got['status'],'rejected_internal')
 def test_robots_failure_closed(self):
  f=common.Fetcher()
  with patch.object(f,'raw',side_effect=ValueError('blocked')):
   self.assertFalse(f.allowed('https://example.com/'))
 def test_robots_404_and_disallow(self):
  f=common.Fetcher()
  with patch.object(f,'raw',return_value=(404,'')): self.assertTrue(f.allowed('https://example.com/'))
  f=common.Fetcher()
  with patch.object(f,'raw',return_value=(200,'User-agent: *\nDisallow: /')): self.assertFalse(f.allowed('https://example.com/'))
 def test_ssrf(self):
  with self.assertRaises(ValueError): common.Fetcher().public('http://127.0.0.1/a')
  with self.assertRaises(ValueError): common.Fetcher().public('file:///etc/passwd')
 def test_report_only_verified_and_snapshot(self):
  common.save('backlinks.json',[{'status':'inaccessible','first_seen':'2026-01-01','target_url':common.SITE+'/en/a/'}])
  result=report.run(True); self.assertEqual(result['confirmed_live_backlinks'],0); self.assertEqual(result['lost_backlinks'],0)
  paths=list((common.DATA/'history').glob('*.json')); before=paths[0].read_bytes(); report.run(True); self.assertEqual(before,paths[0].read_bytes())
 @unittest.skipUnless(yaml, "PyYAML validated by dedicated workflow")
 def test_yaml_safe_scope(self):
  raw=(common.ROOT/'.github/workflows/backlink-automation.yml').read_text(); doc=yaml.safe_load(raw)
  self.assertEqual(doc['permissions']['contents'],'read'); self.assertIn('HEAD:backlink-data',raw); self.assertNotIn('HEAD:main',raw)
 def test_csv_formula_escape(self):
  common.save('prospects.json',[{'name':'=HYPERLINK("bad")'}]); report.run()
  self.assertIn("'=HYPERLINK",(common.DATA/'prospects.csv').read_text())
 def test_research_no_guess_contacts(self):
  class Fake:
   def get(self,u): return u,'<title>Technology software analysis</title><article>'+('Software technology coverage. '*150)+'</article>'
  row,_=discover.research(Fake(),{'url':'https://example.com/story','discovered_from':'search'})
  self.assertEqual(row['public_emails'],[]); self.assertEqual(row['contact_page'],'')
 def test_resource_no_fabricated_values(self):
  from scripts.link_resources import directory_rows
  rows=directory_rows('colleges'); self.assertTrue(rows)
  self.assertTrue(all('href=' in r[5] for r in rows))
if __name__=='__main__': unittest.main()
