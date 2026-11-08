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
        from scripts.news_config import CATEGORIES, EXTRA_FEEDS
        categories = {row[1] for row in feeds+EXTRA_FEEDS}
        self.assertEqual(categories,set(CATEGORIES))
        self.assertEqual(len(categories), 48)
        self.assertIn('private-vacancy', categories)
        self.assertIn("gaming", categories)
        self.assertTrue(any("ign.com" in row[0] for row in feeds))

    def test_recruitment_source_guard(self):
        code = COLLECT.read_text(encoding='utf-8')
        self.assertIn('OFFICIAL_JOB_DOMAINS', code)
        self.assertIn("if cat=='sarkari-naukri'", code)
        self.assertIn('Skipping recruitment story from unapproved source', code)
        self.assertIn("REGIONAL_PORTALS['sarkari-naukri']", code)

    def test_category_routing(self):
        code = COLLECT.read_text(encoding='utf-8')
        self.assertIn("if default not in ('sarkari-naukri','government-schemes'): return default", code)
        self.assertIn('groups[actual_cat].append((url,title,actual_cat,domain))', code)

    def test_provider_and_incomplete_story_fallback(self):
        code = COLLECT.read_text(encoding="utf-8")
        self.assertIn("GEMINI_MODELS", code)
        self.assertIn("gemini-2.5-flash-lite", code)
        self.assertIn("UNAVAILABLE_MODELS.add((provider,model))", code)
        self.assertIn("if not complete_body(state.get(lang+'_body',''),lang):", code)
        self.assertIn("blocked_until", code)
        self.assertIn("for story in (() if bulk_pending else candidates()):", code)
        self.assertIn("while time.monotonic()<deadline and published<remaining and CALLS<MAX_CALLS:", code)

    def test_root_redirects_to_canonical_english_homepage(self):
        build = (ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
        self.assertIn('http-equiv="refresh" content="0;url=/en/"', build)
        self.assertIn("Cache-Control: public, max-age=0, must-revalidate", build)

    def test_workflow_targets(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "cron: '7 */2 * * *'",
            "default: '200'",
            "MIN_POSTS_PER_CATEGORY: '2'",
            "MAX_AI_CALLS_PER_RUN: '100'",
            "AI_PROVIDER_ORDER: gemini,groq,openrouter",
            "MAX_MODELS_PER_ARTICLE: '5'",
            "MAX_LICENSED_PHOTOS_PER_RUN: '200'",
            "python -u scripts/generate_images.py",
            "python -u scripts/publish_news_batch.py",
            "git rebase -X theirs origin/main",
        )
        for target in required:
            self.assertIn(target, workflow)
        for obsolete in ("scripts/build.py", "sleep 300"):
            self.assertNotIn(obsolete, workflow)

    def test_optional_r2_delivery_workflow(self):
        if not (ROOT / ".github/workflows/delivery-release.yml").is_file():
            self.skipTest("R2 delivery workflow is not installed")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("cron: '7 */2 * * *'", workflow)
        self.assertIn("default: '200'", workflow)
        self.assertIn("MIN_POSTS_PER_CATEGORY: '2'", workflow)
        self.assertIn("MAX_AI_CALLS_PER_RUN: '100'", workflow)
        self.assertIn("AI_PROVIDER_ORDER: gemini,groq,openrouter", workflow)
        self.assertIn("MAX_MODELS_PER_ARTICLE: '5'", workflow)
        self.assertIn("MAX_LICENSED_PHOTOS_PER_RUN: '200'", workflow)
        self.assertIn("python -u scripts/generate_images.py", workflow)
        self.assertNotIn("scripts/build.py", workflow)
        delivery=(ROOT/'.github/workflows/delivery-release.yml').read_text()
        self.assertIn("python scripts/build.py --render-only",delivery)
        self.assertIn("python scripts/r2_sync.py --upload",delivery)
        self.assertIn("git rebase -X theirs origin/main", workflow)
        self.assertNotIn("sleep 300", workflow)

    def test_saved_drafts_are_prioritized_in_both_languages(self):
        code = COLLECT.read_text(encoding="utf-8")
        # Publish-ready bilingual drafts (e.g. trending-queue drafts) and
        # single-language drafts both get the first AI slots; a draft that is
        # complete in either language must never be skipped here.
        self.assertIn("if not (ready_en or ready_hi or requested):continue", code)
        self.assertNotIn("if ready_en==ready_hi:continue", code)
        self.assertIn("single_language_ids=", code)
        self.assertIn("Recovering missing language from saved source-grounded draft", code)
        self.assertIn("Prioritizing missing English for saved Hindi draft", code)
        self.assertIn("Prioritizing missing Hindi for saved English draft", code)

if __name__ == "__main__":
    unittest.main()
