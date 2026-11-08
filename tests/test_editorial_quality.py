import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from editorial_quality import normalize_post, aligned_hindi_title
from article_layout import excerpt
from story_identity import same_story, collapse_posts
from news_config import route_category
from news_hub import recent_priority
from repair_categories import repair
import directories as d

class EditorialQualityTests(unittest.TestCase):
 def test_future_launch_translation_stays_future(self):
  en='Vinfast VF5 Electric SUV to Launch in India'
  self.assertEqual(aligned_hindi_title(en,'VF5 भारत में लॉन्च – कीमत'), 'VF5 भारत में लॉन्च की तैयारी – कीमत')
  for hi in ['VF5 भारत में लॉन्च हो सकती है','VF5 भारत में लॉन्च की तैयारी','VF5 की संभावित कीमत']:
   self.assertEqual(aligned_hindi_title(en,hi),hi)
  self.assertEqual(aligned_hindi_title('VF5 launched in India','VF5 भारत में लॉन्च'),'VF5 भारत में लॉन्च')
 def test_bike_routes_stable_and_old_url_category_retained(self):
  post={'id':'bike','category':'car-launches','en_title':'KTM 200 Duke vs Bajaj Pulsar NS200: Price and Features'}
  updated=normalize_post(post)
  self.assertEqual(updated['category'],'automobiles')
  self.assertEqual(updated['previous_categories'],['car-launches'])
  self.assertEqual(normalize_post(updated),updated)
  self.assertEqual(post['category'],'car-launches')
  self.assertEqual(route_category('Mountain bike cycling race','sports'),'sports')
 def test_repair_writes_title_even_when_category_is_unchanged(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'a.json';path.write_text(json.dumps({'id':'a','category':'car-launches','en_title':'VF5 SUV to launch in India','hi_title':'VF5 भारत में लॉन्च – कीमत'}))
   self.assertEqual(len(repair(tmp,True)),1)
   self.assertIn('लॉन्च की तैयारी',json.loads(path.read_text())['hi_title'])
   self.assertEqual(repair(tmp,True),[])
 def test_bullet_only_summary_and_invalid_provided_summary(self):
  self.assertEqual(excerpt('## Overview\n- India won the opening three matches.'),'India won the opening three matches.')
  self.assertEqual(excerpt('## Overview\n\nUseful sourced information for readers.','--- All data above is a disclaimer.'),'Useful sourced information for readers.')
  self.assertEqual(excerpt('## Heading\n\n| A | B |\n|---|---|'),'')
 def test_reworded_buyout_offer_but_not_new_results(self):
  a='Microsoft Offers Voluntary Buyouts to 60,000 Workers Amid Massive AI Infrastructure Spend'
  b='Microsoft Reportedly Offers Buyouts to 60,000 Employees Amid AI Shift'
  self.assertTrue(same_story(a,b))
  for other in ['Microsoft reports 20,000 employees accepted the buyout','Amazon offers buyouts to 60,000 employees','Microsoft offers buyouts to 30,000 employees']:
   self.assertFalse(same_story(a,other))
  posts=[{'id':'a','source':'https://a.example/story','en_title':a},{'id':'b','source':'https://b.example/story','en_title':b}]
  self.assertEqual(len(collapse_posts(posts)[0]),2) # existing articles stay intact
 def test_reference_guide_not_in_priority_news(self):
  records=[{'id':'guide','date':'2026-11-08T02:00:00+00:00','content_type':'evergreen_directory_guide','category':'gadgets'}]
  self.assertEqual(recent_priority(records,now=1794106800),[])
 def test_directory_pagination_preserves_every_profile_and_global_index(self):
  records={'phones':{f'Phone {i}':{'country':'India' if i%2 else 'Japan','battery':'5000 mAh','ram':'8GB','os':'Android','official_url':'https://maker.example'} for i in range(103)}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(d,'DATA',{'phones':[]}),patch.object(d,'detailed_profiles',return_value=records),patch.object(d,'external_records',return_value=[]):
   out=Path(tmp)
   def write(path,body):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
   def shell(lang,title,desc,url,body):return '<html><head><title>'+title+'</title><link rel="canonical" href="'+url+'"></head><body>'+body+'</body></html>'
   d.render(out,'https://example.com',shell,write)
   for lang in ('en','hi'):
    seen=[]
    for page in (1,2,3):
     path=out/d.listing_path(lang,'phones',page).lstrip('/')/'index.html';soup=BeautifulSoup(path.read_text(),'html.parser')
     seen += [a['href'] for a in soup.select('.directory-card h2 a')]
     self.assertLessEqual(len(soup.select('[data-item]')),48)
     self.assertEqual(soup.select_one('link[rel="canonical"]')['href'],'https://example.com'+d.listing_path(lang,'phones',page))
     self.assertTrue(soup.select_one('[data-directory-index]'))
    self.assertEqual(len(seen),103);self.assertEqual(len(set(seen)),103)
    self.assertEqual(len(json.loads((out/lang/'phones/search.json').read_text())),103)
    self.assertEqual(len(list((out/lang/'phones').glob('phone-*/index.html'))),103)
    self.assertNotIn('Fees, eligibility, placement',(out/lang/'phones/index.html').read_text())

if __name__=='__main__':unittest.main()
