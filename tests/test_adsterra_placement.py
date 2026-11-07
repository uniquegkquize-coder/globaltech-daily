import ast
import hashlib
import html
import json
from pathlib import Path
import unittest

from scripts.advertising import POPUNDER_URL, SOCIAL_BAR_URL, head_ads, footer_ads


class AdsterraPlacementTests(unittest.TestCase):
    def test_native_tags_keep_original_urls_and_privacy_control(self):
        for markup, source in [(head_ads(), POPUNDER_URL), (footer_ads(), SOCIAL_BAR_URL)]:
            self.assertIn('!navigator.globalPrivacyControl', markup)
            literal = markup.split('document.write(', 1)[1].split(');', 1)[0]
            self.assertEqual(json.loads(literal), '<script src="' + source + '"></script>')
            self.assertEqual(markup.count('</script>'), 1)
            self.assertNotIn('async', markup)

    def test_common_shell_places_each_format_once_on_every_page(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'scripts/build.py').read_text())
        shell = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'shell')
        namespace = dict(ROBOTS='index,follow', SITE='https://globewiredaily.org', CONTACT='contact@example.test',
                         CATEGORIES={}, head_ads=head_ads, footer_ads=footer_ads, e=html.escape,
                         hashlib=hashlib, seo_description=lambda *a: 'description', seo_head=lambda *a, **kw: '', label=lambda text, lang: text)
        for name in ('CSS','MENU_CSS','HUB_CSS','GLOBAL_CSS','EXAM_CSS','DIRECTORY_CSS','ARTICLE_CSS','JS','HUB_JS','GLOBAL_JS','DIRECTORY_JS'):
            namespace[name] = ''
        exec(compile(ast.Module(body=[shell], type_ignores=[]), '<shell>', 'exec'), namespace)
        for language, path in [('en','/en/'), ('hi','/hi/phones/'), ('en','/en/news/business/example/')]:
            with self.subTest(path=path):
                page = namespace['shell'](language, 'Test', 'Test', 'https://globewiredaily.org'+path, '<p>Page</p>')
                self.assertEqual(page.count(POPUNDER_URL), 1)
                self.assertEqual(page.count(SOCIAL_BAR_URL), 1)
                self.assertLess(page.index(POPUNDER_URL), page.index('</head>'))
                self.assertGreater(page.index(SOCIAL_BAR_URL), page.index('<body>'))
                self.assertLess(page.index(SOCIAL_BAR_URL), page.index('</body>'))

    def test_article_loader_does_not_duplicate_sitewide_formats(self):
        source=(Path(__file__).resolve().parents[1] / 'scripts/build.py').read_text()
        tree=ast.parse(source)
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='article_ad_scripts')
        namespace={}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<article-ads>','exec'),namespace)
        markup=namespace['article_ad_scripts']()
        self.assertNotIn('profitableratecpmnetwork.com',markup)
        self.assertIn('infolinks_main.js',markup)
        self.assertIn('52835a675f1767f1a04f1936910f50fc',markup)
