import json,sys,unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import directory_facts as f
import research_directory_sources as r
import publish_directory_guides as p
FIX=Path(__file__).parent/'fixtures/directory'
class CompleteDirectoryTests(unittest.TestCase):
 def test_base_model_excludes_xtec_led(self):
  soup=BeautifulSoup((FIX/'hero-model-sections.html').read_text(),'html.parser')
  rows=f.embedded_model_rows(f.model_scope(soup,'https://hero.example/splendor-plus.html'))
  self.assertEqual(next(x['value'] for x in rows if x['label']=='Head Lamp'),'12V 35 /35W Halogen Bulb MFR')
  self.assertTrue(any(x['label']=='Overall Width (mm)' for x in rows))
 def test_regular_and_lateral_fees_stay_separate(self):
  soup=BeautifulSoup('<h1>BPharm</h1>'+(FIX/'parul-programme-tabs.html').read_text(),'html.parser')
  rows=f.programme_cards(soup)
  self.assertEqual([x['duration'] for x in rows],['4 years','3 years'])
  self.assertEqual(rows[0]['fee'],'1,80,000/- Per Annum')
  self.assertNotIn('tuition-note',rows[0]['eligibility criteria'])
 def test_variant_columns_preserved(self):
  soup=BeautifulSoup('<h2>Engines</h2><table><tr><th>Engine</th><th>Diesel</th><th>Petrol</th></tr><tr><td>Power</td><td>100 kW</td><td>110 kW</td></tr></table>','html.parser')
  self.assertEqual(f.source_tables(soup)[0]['rows'][1],['Power','100 kW','110 kW'])
 def test_all_dimensions_preserved(self):
  soup=BeautifulSoup('<table><tr><td>Length</td><td>3985 mm</td></tr><tr><td>Width</td><td>1820 mm</td></tr><tr><td>Height</td><td>1844 mm</td></tr></table>','html.parser')
  self.assertEqual(len(f.specification_rows(soup)),3)
 def test_framework_pairs(self):
  soup=BeautifulSoup('<script type="application/json">{"specs":[{"label":"Battery","value":"6000 mAh"}]}</script>','html.parser')
  self.assertEqual(f.framework_pairs(soup)['battery'],'6000 mAh')
 def test_structured_fees_and_regulatory_history_visible(self):
  output=f.structured_html({'fee_schedule':{'basis':'2026 annual','tuition':'USD 1000'},'regulatory_history':[{'programme':'BBA','status':'withdrawn'}]},'en')
  for term in ('2026 annual','USD 1000','withdrawn'):self.assertIn(term,output)
 def test_table_escapes_and_links(self):
  output=f.table_html('Fees',[{'course':'<script>','source_url':'https://official.example/fees'}])
  self.assertNotIn('<script>',output);self.assertIn('&lt;script&gt;',output);self.assertIn('href="https://official.example/fees"',output)
 def test_schema_escapes_script_and_image_is_absolute(self):
  output=f.schema('phones','</script>',{},'https://example.com/en/phones/model/',{'src':'/images/photo.jpg'})
  value=json.loads(output.removeprefix('<script type="application/ld+json">').removesuffix('</script>'))
  self.assertEqual(value['image'],'https://example.com/images/photo.jpg');self.assertNotIn('</script></script>',output)
 def test_sparse_entries_not_meaningful(self):
  self.assertFalse(f.meaningful({'name':'Phone','country':'India','source_url':'https://example.com'}))
 def test_courses_are_meaningful(self):self.assertTrue(f.meaningful({'courses':[{'course':'BBA'},{'course':'MBA'}]}))
 def test_car_specs_without_price_are_meaningful(self):
  self.assertTrue(f.meaningful({'engine':'2L','transmission':'6AT','dimensions':'4000 mm'}))
 def test_safe_url_rejects_script_and_credentials(self):
  self.assertFalse(f.safe_url('javascript:alert(1)'));self.assertFalse(f.safe_url('https://user:password@example.com'))
 def test_label_retains_unit_matching(self):self.assertEqual(f.label('Battery Capacity (mAh)'),'batterycapacity')
 def test_timestamp_does_not_change_fingerprint(self):
  a={'battery':'6000 mAh','field_sources':{'battery':{'retrieved_at':'one'}},'checked_at':'one'}
  b={'battery':'6000 mAh','field_sources':{'battery':{'retrieved_at':'two'}},'checked_at':'two'}
  self.assertEqual(p.fingerprint(a),p.fingerprint(b))
if __name__=='__main__':unittest.main()
