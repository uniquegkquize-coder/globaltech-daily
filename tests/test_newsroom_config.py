"""Offline checks for the scheduled newsroom configuration (no API calls)."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COLLECT = ROOT / "scripts" / "collect.py"
WORKFLOW = ROOT / ".github" / "workflows" / "news-auto.yml"

class NewsroomConfigTests(unittest.TestCase):
    def test_python_compiles(self):
        for path in (ROOT / "scripts").glob("*.py"):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"))

    def test_category_count_and_gaming(self):
        tree = ast.parse(COLLECT.read_text(encoding="utf-8"))
        feeds = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "FEEDS" for t in node.targets))
        categories = {row[1] for row in feeds}
        self.assertEqual(len(categories), 14)
        self.assertIn("gaming", categories)
        self.assertTrue(any("ign.com" in row[0] for row in feeds))

    def test_recruitment_source_guard(self):
        code = COLLECT.read_text(encoding='utf-8')
        self.assertIn('OFFICIAL_JOB_DOMAINS', code)
        self.assertIn("if cat=='sarkari-naukri'", code)
        self.assertIn('Skipping recruitment story without an official government source', code)

    def test_category_routing(self):
        code = COLLECT.read_text(encoding='utf-8')
        self.assertIn("if default not in ('sarkari-naukri','government-schemes'): return default", code)
        self.assertIn('groups[actual_cat].append((url,title,actual_cat,domain))', code)

    def test_workflow_targets(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("POSTS_PER_RUN: '14'", workflow)
        self.assertIn("MAX_AI_CALLS_PER_RUN: '60'", workflow)
        self.assertIn("AI_PROVIDER_ORDER: gemini,groq,openrouter", workflow)
        self.assertIn("python -u scripts/build.py", workflow)

if __name__ == "__main__":
    unittest.main()
