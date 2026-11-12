import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from seo_recovery_audit import audit, gsc_opportunities

class SeoRecoveryTests(unittest.TestCase):
    def test_detects_bad_canonical_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            page = root / "en" / "news" / "technology" / "story" / "index.html"
            page.parent.mkdir(parents=True)
            content = '<html><head><title>Story</title><link rel="canonical" href="https://wrong.example/"></head><body></body></html>'
            page.write_text(content)
            (root / "sitemap.xml").write_text('<urlset/>')
            (root / "news-sitemap.xml").write_text('<urlset/>')
            result = audit(root)
            self.assertIn("canonical", [x["issue"] for x in result["issues"]])
            self.assertEqual(page.read_text(), content)
    def test_optional_gsc_export(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "pages.csv"
            f.write_text("Top pages,Clicks,Impressions\\nhttps://globewiredaily.org/en/news/a/,2,500\\n")
            result = gsc_opportunities(f)
            self.assertEqual(result[0]["impressions"], 500)

if __name__ == "__main__":
    unittest.main()
