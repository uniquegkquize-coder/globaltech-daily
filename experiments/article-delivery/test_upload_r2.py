import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("upload_r2.py")
spec = importlib.util.spec_from_file_location("upload_r2", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class UploadManifestTests(unittest.TestCase):
    def test_only_canonical_article_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = [
                "en/news/sports/test-123/index.html",
                "hi/news/technology/test-456/index.html",
                "en/news/old-legacy/index.html",
                "en/index.html",
            ]
            for path in paths:
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("<html><body>Test</body></html>")
            found = [key for key, _ in module.articles(root)]
            self.assertEqual(found, paths[:2])
    def test_empty_dist_has_no_articles(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list(module.articles(Path(tmp))), [])

if __name__ == "__main__":
    unittest.main()
