import ast,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from seo_text import description
class DescriptionTests(unittest.TestCase):
 def test_metadata_object_uses_description_not_provenance(self):
  self.assertEqual(description({'description':'Source-based news summary.','author':'News desk'}),'Source-based news summary.')
 def test_legacy_python_dictionary_is_recovered(self):
  self.assertEqual(description("{'description': 'Ranking methodology explained.', 'date': '2026-11-02'}"),'Ranking methodology explained.')
 def test_provenance_dictionary_falls_back_to_actual_intro(self):
  self.assertEqual(description("{'source_url': 'https://example.com', 'author': 'Desk'}",'## Overview\n\nUniversity rankings compare teaching and graduate outcomes.'),'University rankings compare teaching and graduate outcomes.')
 def test_hindi_remains_hindi(self):
  self.assertEqual(description({'date':'2026-11-02'},'## जानकारी\n\nविश्वविद्यालय की रैंकिंग कैसे बनती है, जानें।'),'विश्वविद्यालय की रैंकिंग कैसे बनती है, जानें।')
 def test_malformed_serialized_metadata_cannot_leak(self):
  self.assertEqual(description("{'source_url': broken",'An actual article introduction.'),'An actual article introduction.')
 def test_markup_and_raw_urls_are_removed(self):
  self.assertEqual(description('<b>NASA</b> opens [pixel signup](https://example.com) &amp; certificate details. https://example.com'),'NASA opens pixel signup & certificate details.')
 def test_short_valid_meta_is_preserved(self):
  self.assertEqual(description('Valid original summary.'),'Valid original summary.')
 def test_long_description_ends_on_word_boundary(self):
  v=description('A useful source-grounded summary. '*20)
  self.assertLessEqual(len(v),160);self.assertTrue(v.endswith('…'));self.assertNotIn('source_url',v)
 def test_existing_complete_draft_is_normalized_before_publication(self):
  source=(Path(__file__).resolve().parents[1]/'scripts/collect.py').read_text()
  self.assertIn("article[lang+'_meta']=seo_description",source)
 def test_root_has_permanent_redirect_and_fallback(self):
  source=(Path(__file__).resolve().parents[1]/'scripts/build.py').read_text()
  self.assertIn("redirects=['/ /en/ 301']",source)
  self.assertIn('http-equiv="refresh" content="0;url=/en/"',source)
if __name__=='__main__':unittest.main()
