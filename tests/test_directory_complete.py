import json,sys,unittest,tempfile,hashlib
from unittest.mock import patch
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import directory_facts as f
import directories as d
import directory_photos as photos
import image_rules as rules
import research_directory_sources as r
import publish_directory_guides as p
FIX=Path(__file__).parent/'fixtures/directory'
class CompleteDirectoryTests(unittest.TestCase):
 def test_nullable_profile_locations_render(self):
  entry={'country':'Malawi','region':None,'city':None,'courses':[{'course':'BBA'},{'course':'MBA'}]}
  with tempfile.TemporaryDirectory() as tmp,patch.object(d,'DATA',{'colleges':[]}),patch.object(d,'external_records',return_value=[]),patch.object(d,'detailed_profiles',return_value={'colleges':{'Test University':entry}}):
   out=Path(tmp)
   def write(path,body):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
   d.render(out,'https://example.com',lambda lang,title,desc,url,body:'<head></head>'+body,write)
   self.assertTrue((out/'en/colleges/test-university/index.html').exists())
 def test_plus_model_urls_do_not_overwrite_base(self):
  self.assertNotEqual(d.entry_slug('Samsung Galaxy S24'),d.entry_slug('Samsung Galaxy S24+'))
 def test_profile_original_is_reused_by_existing_guide(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(photos.images,'IMAGES',Path(tmp)),patch.object(photos,'guide_images',return_value={('colleges','test university'):'guide'}):
   folder=Path(tmp);(folder/'profile.jpg').write_bytes(b'photo')
   (folder/'profile.json').write_text(json.dumps({'kind':'publisher_source','source_image':'https://official.example/campus.jpg'}))
   photos.sync_guide_photo('colleges','Test University','profile')
   self.assertEqual((folder/'guide.jpg').read_bytes(),b'photo')
   self.assertEqual(json.loads((folder/'guide.json').read_text())['post_id'],'guide')
 def test_reviewed_direct_photo_keeps_original_source(self):
  entry={'source_image_url':'https://cdn.example/model.jpg','image_source_url':'https://manufacturer.example/model','manufacturer':'Maker'}
  with patch.object(photos.images,'save_source_photo',return_value=True) as save:
   self.assertTrue(photos.pinned_photo(entry,'profile','Phone'))
   self.assertEqual(save.call_args.args[1:4],('https://cdn.example/model.jpg','https://manufacturer.example/model',''))
 def test_pinned_photo_rejects_unsafe_urls(self):
  with patch.object(photos.images,'save_source_photo') as save:
   self.assertFalse(photos.pinned_photo({'source_image_url':'javascript:alert(1)','official_url':'https://example.com'},'id','Phone'))
   save.assert_not_called()
 def test_gv60_navigation_photo_rejected_for_gv70(self):
  self.assertFalse(rules.directory_photo_matches('Genesis GV70',{'url':'https://cdn.example/2026-gv60-prf-awd.jpg','label':'','origin':'article'}))
  self.assertTrue(rules.directory_photo_matches('Genesis GV70',{'url':'https://cdn.example/2026-gv70-25t-advanced.jpg','label':'','origin':'article'}))
 def test_opaque_body_navigation_images_need_identity(self):
  self.assertFalse(rules.directory_photo_matches('Genesis GV70',{'url':'https://cdn.example/hash.png','label':'','origin':'article'}))
  self.assertTrue(rules.directory_photo_matches('Vivo X Fold 5',{'url':'https://cdn.example/hash.png','label':'','origin':'social'}))
 def test_existing_wrong_model_photo_cannot_be_reused(self):
  self.assertFalse(rules.saved_photo_allowed({'kind':'publisher_source','source':'https://genesis.example/us/en/gv70/previous','source_image':'https://cdn.example/2026-gv60-prf.jpg'}))
 def test_rejected_stable_photo_is_not_mislabeled_as_illustration(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(f,'ROOT',Path(tmp)),patch.object(f,'guide_images',return_value={}):
   root=Path(tmp);ident=hashlib.sha256(b'directory:cars:Genesis GV70').hexdigest()[:24]
   folder=root/'content/featured';folder.mkdir(parents=True);out=root/'dist';(out/'images').mkdir(parents=True)
   (folder/(ident+'.jpg')).write_bytes(b'wrong photo');(out/'images'/(ident+'.jpg')).write_bytes(b'wrong photo')
   (folder/(ident+'.json')).write_text(json.dumps({'kind':'publisher_source','source':'https://genesis.example/gv70/previous','source_image':'https://cdn.example/gv60.jpg'}))
   self.assertIsNone(f.photo('cars','Genesis GV70',out))
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
  output=f.structured_html({'fee_schedule':{'basis':'2026 annual','tuition':[{'category':'Reserved','amount':1000}]},'regulatory_history':[{'programme':'BBA','status':'withdrawn'}]},'en')
  for term in ('2026 annual','Reserved','1000','withdrawn'):self.assertIn(term,output)
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
