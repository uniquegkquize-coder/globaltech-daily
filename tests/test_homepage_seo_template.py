"""Regression checks for live homepage title and accessible trending thumbnails."""
import ast
import html
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

SOURCE = (Path(__file__).resolve().parents[1] / 'scripts' / 'build.py').read_text(encoding='utf-8')
TREE = ast.parse(SOURCE)


class HomepageSeoTemplateTests(unittest.TestCase):
    def test_english_homepage_title_stays_concise_and_hindi_unchanged(self):
        candidates = [
            node for node in ast.walk(TREE)
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'h' for t in node.targets)
            and isinstance(node.value, ast.IfExp)
        ]
        self.assertEqual(len(candidates), 1)
        expr = compile(ast.Expression(body=candidates[0].value), '<homepage-title>', 'eval')
        english = eval(expr, {'lang': 'en'})
        hindi = eval(expr, {'lang': 'hi'})
        self.assertEqual(english, 'World News, Tech & Entertainment')
        self.assertEqual(hindi, 'दुनियाभर की ताज़ा खबरें, आसान हिंदी में')
        self.assertLessEqual(len(english + ' | GlobeWire Daily'), 60)

    def test_trending_thumbnail_has_descriptive_alt_and_single_link_label(self):
        method = next(
            n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef)
            and n.name == 'trending_section'
        )
        namespace = {
            'trending_posts': lambda exclude, limit: [{'id': 'sample'}],
            'article_path': lambda q, lang: f'/{lang}/news/sample/',
            'has_featured': lambda q: True,
            'slug': lambda q: 'sample',
            'image_version': lambda q: '123',
            'image_alt': lambda q, lang: 'Original photo & illustration',
            'title': lambda q, lang: 'News title <special>',
            'e': lambda value: html.escape(str(value), quote=True),
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<trending>', 'exec'), namespace)
        for lang in ('en', 'hi'):
            with self.subTest(lang=lang):
                markup = namespace['trending_section'](lang)
                soup = BeautifulSoup(markup, 'html.parser')
                anchor = soup.select_one('.trending-list a')
                photo = anchor.img
                self.assertEqual(anchor['aria-label'], 'News title <special>')
                self.assertEqual(photo['alt'], 'Original photo & illustration')
                self.assertEqual(anchor['href'], f'/{lang}/news/sample/')
                self.assertEqual(anchor.span.text, 'News title <special>')


if __name__ == '__main__':
    unittest.main()
