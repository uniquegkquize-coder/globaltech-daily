import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import trending_watch as w
import collect as n

NOW=1793628000
TITLE='Saudi authorities intercept Houthi missile near Riyadh airport'
def row(domain='bbc.co.uk',title=TITLE,summary='Authorities issue new emergency warning.',published=NOW-60):
 return dict(domain=domain,title=title,url='https://'+domain+'/news/story',category='world-news',summary=summary,published=published,author='')
def pair():return [row(),row('theguardian.com')]

class TrendDetectionTests(unittest.TestCase):
 def test_two_publishers_form_signal(self):
  groups=w.clusters(pair(),NOW);self.assertEqual(len(groups),1);self.assertEqual(groups[0]['signal'],'multiple_publishers')
 def test_one_publisher_two_feeds_is_not_trending(self):
  self.assertEqual(w.clusters([row(),row()],NOW),[])
 def test_syndicated_wire_is_one_signal(self):
  rows=pair()
  for r in rows:r['author']='Reuters'
  self.assertEqual(w.clusters(rows,NOW),[])
 def test_urgent_official_alert_can_be_single_source(self):
  self.assertEqual(w.clusters([row('spa.gov.sa')],NOW)[0]['signal'],'official_alert')
  self.assertEqual(w.clusters([row('spa.gov.sa',title='Saudi ministry opens a new cultural exhibition')],NOW),[])
 def test_distinct_attack_locations_are_not_collapsed(self):
  self.assertFalse(w.same_event(TITLE,TITLE.replace('Riyadh','Jeddah')))
 def test_old_and_future_feed_items_are_not_trending(self):
  xml='''<rss><channel><item><title>Saudi authorities intercept Houthi missile near Riyadh airport</title><link>https://bbc.co.uk/news/old</link><pubDate>Mon, 02 Nov 2020 12:00:00 GMT</pubDate></item><item><title>Saudi authorities intercept Houthi missile near Riyadh airport</title><link>https://bbc.co.uk/news/future</link><pubDate>Mon, 02 Nov 2030 12:00:00 GMT</pubDate></item></channel></rss>'''
  class Response:
   def raise_for_status(self):pass
   def iter_content(self,size):yield xml.encode()
   def close(self):pass
  with patch.object(w.requests,'get',return_value=Response()):
   rows,status=w.read_feed(('https://bbc.co.uk/rss','world-news','bbc.co.uk'),NOW)
  self.assertEqual(status,'ok');self.assertEqual(rows,[])
 def test_unchanged_content_is_not_material(self):
  text='Original source evidence and information.'
  changed,h=w.material_change({'source_hash':w.digest(w.clean(text))},text)
  self.assertFalse(changed)

class TrendRunTests(unittest.TestCase):
 def test_no_signal_makes_no_ai_call(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(w,'STATE',Path(temp)/'state.json'),patch.object(w,'REPORT',Path(temp)/'report.json'),patch.object(w,'discover',return_value=([row()],{})),patch.object(w,'read_posts',return_value=[]),patch.object(n,'call_provider') as call:
   report=w.run(NOW)
  self.assertEqual(report['changed_ids'],[]);call.assert_not_called()
 def test_same_cached_signature_does_not_repeat_generation(self):
  with tempfile.TemporaryDirectory() as temp:
   state=Path(temp)/'state.json';key=w.digest(row()['url'])[:12]
   state.write_text(json.dumps({'events':{key:{'signature':w.signature(row()),'feed_updated':row()['published'],'last_seen':NOW}}}))
   with patch.object(w,'STATE',state),patch.object(w,'REPORT',Path(temp)/'report.json'),patch.object(w,'discover',return_value=(pair(),{})),patch.object(w,'read_posts',return_value=[]),patch.object(w,'generate') as generate:
    w.run(NOW)
   generate.assert_not_called()
 def test_provider_backoff_still_checks_sources_without_ai(self):
  with tempfile.TemporaryDirectory() as temp:
   state=Path(temp)/'state.json';state.write_text(json.dumps({'events':{},'provider_retry_after':NOW+3600}))
   with patch.object(w,'STATE',state),patch.object(w,'REPORT',Path(temp)/'report.json'),patch.object(w,'discover',return_value=(pair(),{})) as discover,patch.object(w,'read_posts',return_value=[]),patch.object(w,'generate') as generate:
    report=w.run(NOW)
   discover.assert_called_once();generate.assert_not_called();self.assertEqual(report['results'][0]['result'],'cooldown')

class UpdateIntegrityTests(unittest.TestCase):
 def old(self):return dict(id='abcdef123456',date='2026-11-01T12:00:00+00:00',category='world-news',source='https://bbc.co.uk/news/original',source_title=TITLE,en_title='Original stable English headline',hi_title='पुराना स्थायी हिन्दी शीर्षक',en_body='Original report.',hi_body='पुरानी खबर।')
 def evidence(self):return ' '.join('fact'+str(i) for i in range(90))
 def test_material_update_retains_url_id_and_publication_date(self):
  old=self.old();record={'source_hash':'old','tokens':[]}
  data={'en':{'title':'New English title with material facts','body':'Updated English report.'},'hi':{'title':'नई जानकारी सहित नया हिन्दी समाचार शीर्षक','body':'नई हिन्दी खबर।'}}
  with tempfile.TemporaryDirectory() as temp,patch.object(n,'POSTS',Path(temp)),patch.object(n,'source_text',return_value=self.evidence()),patch.object(n,'call_provider',return_value=(data,'gemini')),patch.object(n,'complete_body',side_effect=lambda body,lang:bool(body)):
   post,result=w.generate(w.clusters(pair(),NOW)[0],old,record,NOW)
   saved=json.loads((Path(temp)/(old['id']+'.json')).read_text())
  self.assertEqual(result,'updated')
  for key in ('id','date','en_title','hi_title','category'):self.assertEqual(saved[key],old[key])
  self.assertIn('updated_at',saved);self.assertEqual(saved['en_body'],'Updated English report.')
 def test_failed_update_never_overwrites_live_article(self):
  old=self.old()
  with tempfile.TemporaryDirectory() as temp,patch.object(n,'POSTS',Path(temp)),patch.object(n,'source_text',return_value=self.evidence()),patch.object(n,'call_provider',return_value=(None,'gemini')):
   path=Path(temp)/(old['id']+'.json');path.write_text(json.dumps(old));before=path.read_bytes()
   post,result=w.generate(w.clusters(pair(),NOW)[0],old,{'source_hash':'old','tokens':[]},NOW)
   self.assertEqual(path.read_bytes(),before)
  self.assertIsNone(post);self.assertEqual(result,'generation_incomplete')
 def test_editorial_no_change_does_not_refresh_article_date(self):
  old=self.old()
  with patch.object(n,'source_text',return_value=self.evidence()),patch.object(n,'call_provider',return_value=({'unchanged':True},'gemini')):
   post,result=w.generate(w.clusters(pair(),NOW)[0],old,{'source_hash':'old','tokens':[]},NOW)
  self.assertIsNone(post);self.assertEqual(result,'no_material_change');self.assertNotIn('updated_at',old)
 def test_source_history_prevents_regular_publisher_duplicates(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(n,'POSTS',Path(temp)):
   old=self.old();old['source_history']=[{'url':'https://bbc.co.uk/news/older','title':'Previous headline'}]
   (Path(temp)/'abcdef.json').write_text(json.dumps(old));index=n.published_story_index()
   self.assertTrue(n.duplicate_story('https://bbc.co.uk/news/older','Previous headline','world-news',index))
