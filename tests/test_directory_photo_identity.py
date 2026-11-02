import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from image_rules import saved_photo_allowed
class PhotoContextTests(unittest.TestCase):
 def test_article_can_reuse_older_original_diagram(self):
  self.assertTrue(saved_photo_allowed({'kind':'publisher_source','source':'https://science.nasa.gov/image-article/apod-2026-october-25-dark-matter/','source_image':'https://assets.science.nasa.gov/apod/2021/october/DarkMatter.jpg'}))
 def test_article_can_use_previous_film_reference_photo(self):
  self.assertTrue(saved_photo_allowed({'kind':'publisher_source','source':'https://deadline.com/2026/10/smile-3-taps-director/','source_image':'https://deadline.com/2026/10/Smile-2.jpg'}))
 def test_product_profile_still_rejects_other_model(self):
  self.assertFalse(saved_photo_allowed({'kind':'publisher_source','source':'https://genesis.com/us/en/gv70/previous','source_image':'https://cdn.example/2026-gv60-prf.jpg'}))
if __name__=='__main__':unittest.main()
