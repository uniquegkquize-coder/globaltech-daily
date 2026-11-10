import ast
import hashlib
import html
from pathlib import Path
import unittest

from scripts.advertising import head_ads, footer_ads


class AdvertisingRemovalTests(unittest.TestCase):
    def test_legacy_adsterra_tags_are_disabled(self):
        self.assertEqual(head_ads(), '')
        self.assertEqual(footer_ads(), '')

    def test_common_shell_contains_no_adsterra(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'scripts/build.py').read_text())
        shell = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'shell')
        namespace = dict(ROBOTS='index,follow', SITE='https://globewiredaily.org',
                         CONTACT='contact@example.test', CATEGORIES={}, e=html.escape,
                         hashlib=hashlib, seo_description=lambda *a: 'description',
                         seo_head=lambda *a, **kw: '', label=lambda text, lang: text)
        for name in ('CSS','MENU_CSS','HUB_CSS','GLOBAL_CSS','EXAM_CSS','DIRECTORY_CSS','ARTICLE_CSS','JS','HUB_JS','GLOBAL_JS','DIRECTORY_JS'):
            namespace[name] = ''
        exec(compile(ast.Module(body=[shell], type_ignores=[]), '<shell>', 'exec'), namespace)
        for language, path in [('en','/en/'), ('hi','/hi/phones/'), ('en','/en/news/business/example/')]:
            with self.subTest(path=path):
                page = namespace['shell'](language, 'Test', 'Test', 'https://globewiredaily.org'+path, '<p>Page</p>')
                self.assertNotIn('profitableratecpmnetwork.com', page)
                self.assertNotIn('data-adsterra-', page)
                self.assertNotIn('bicea.org/22/', page)
                self.assertIn('</head>', page)
                self.assertIn('</body>', page)

    def test_article_loader_keeps_infolinks_without_adsterra(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts/build.py').read_text()
        tree = ast.parse(source)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'article_ad_scripts')
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<article-ads>', 'exec'), namespace)
        markup = namespace['article_ad_scripts']()
        self.assertIn('infolinks_main.js', markup)
        self.assertNotIn('profitableratecpmnetwork.com', markup)
        self.assertNotIn('bicea.org/22/', markup)
        self.assertNotIn('atOptions', markup)

    def test_no_adsterra_loader_or_slots_in_build_source(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts/build.py').read_text()
        for forbidden in ('adsterra_slot(', 'head_ads()', 'footer_ads()'):
            self.assertNotIn(forbidden, source)
