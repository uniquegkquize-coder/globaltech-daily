import datetime as dt
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from scripts.news_config import classify, memberships, lead_priority, CATEGORIES, EXTRA_FEEDS
from scripts.news_hub import news_sort, recent_priority, render_hubs, exam_bucket

class NewsPriorityTests(unittest.TestCase):
 def test_topics_and_preserved_primary_category(self):
  self.assertEqual(len(CATEGORIES),48)
  self.assertEqual(classify('Airtel announces new broadband plan','technology'),'telecom')
  self.assertEqual(classify('SSC CGL exam result declared','sarkari-naukri'),'results')
  self.assertEqual(classify('NVIDIA quarterly results','business'),'business')
  self.assertEqual(classify('SSC admit card download','sarkari-naukri'),'admit-cards')
  self.assertEqual(classify('SSC answer key released','sarkari-naukri'),'answer-keys')
  post={'category':'technology','en_title':'Airtel recharge update'}
  self.assertEqual(memberships(post),{'technology','telecom'})
  self.assertEqual(post['category'],'technology')
 def test_actual_freshness_beats_topic_weight(self):
  now=dt.datetime(2026,10,31,12,tzinfo=dt.timezone.utc)
  popular=('https://a.test','Popular','telecom','a.test')
  other=('https://b.test','New development','travel','b.test')
  self.assertLess(lead_priority(other,(now-dt.timedelta(hours=1)).isoformat(),now.timestamp()),lead_priority(popular,(now-dt.timedelta(days=2)).isoformat(),now.timestamp()))
  self.assertGreater(lead_priority(popular,None,now.timestamp()),lead_priority(other,(now-dt.timedelta(hours=1)).isoformat(),now.timestamp()))
 def test_newest_first_and_no_old_priority_items(self):
  old={'id':'a','category':'telecom','date':'2026-10-30T10:00:00+00:00','source_published_at':'2026-10-27T10:00:00+00:00'}
  new={'id':'b','category':'travel','date':'2026-10-31T10:00:00+00:00'}
  self.assertEqual(sorted([old,new],key=news_sort),[new,old])
  now=dt.datetime(2026,10,31,12,tzinfo=dt.timezone.utc).timestamp()
  self.assertEqual(recent_priority([old,new],now=now),[new])
 def test_discovery_covers_every_added_topic(self):
  base={'technology','government-schemes','sarkari-naukri','private-vacancy','movies-entertainment','world-news','business','sports','automobiles','health-science','gaming','environment','travel','education','lifestyle'}
  self.assertEqual(set(CATEGORIES)-base,{c for _,c,_ in EXTRA_FEEDS}-base)
  self.assertTrue(any(d=='myvi.in' for _,_,d in EXTRA_FEEDS))

 def test_jobs_hub_excludes_non_vacancy_reports(self):
  self.assertIsNone(exam_bucket({'category':'sarkari-naukri','en_title':'October holiday update: offices closed'}))
  self.assertEqual(exam_bucket({'category':'sarkari-naukri','en_title':'SSC recruitment applications open'}),'sarkari-naukri')
