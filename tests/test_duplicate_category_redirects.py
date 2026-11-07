"""A category repair plus duplicate collapse must not strand published URLs."""
import ast
from pathlib import Path
import re
import shutil
import tempfile
import unittest


class DuplicateCategoryRedirectTests(unittest.TestCase):
    def redirect_lines(self, previous):
        source=(Path(__file__).resolve().parents[1]/'scripts/build.py').read_text()
        tree=ast.parse(source)
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'category','slug','article_slug','article_path'}]
        old={'id':'ec6f5799b859','category':'sports','previous_categories':previous,
             'en_title':'Kadeena Cox Shatters World Record to Secure Gold at Para-Cycling Track World Championships'}
        canonical={'id':'d9e27b4c748b','category':'sports',
                   'en_title':'Kadeena Cox Sets World Record to Win Gold at Para Cycling Track World Championships'}
        block=source[source.index("redirects=['/ /en/ 301']"):source.index("print('SEO_REDIRECTS'")]
        with tempfile.TemporaryDirectory() as directory:
            scope=dict(CATEGORIES={'sports':None,'cricket':None,'world-news':None},re=re,shutil=shutil,
                       OUT=Path(directory),POSTS=[canonical],DUPLICATE_POSTS=[(old,canonical)])
            exec(compile(ast.Module(body=functions,type_ignores=[]),'<paths>','exec'),scope)
            exec(compile(block,'<redirect-build>','exec'),scope)
            return scope['redirects'],scope['article_path'](canonical,'en'),scope['article_path'](canonical,'hi')

    def test_exact_two_urls_which_blocked_oracle_deployment(self):
        rows,en,hi=self.redirect_lines(['cricket'])
        slug='kadeena-cox-shatters-world-record-to-secure-gold-at-para-cycling-track-worl-ec6f5799b8'
        self.assertIn(f'/en/news/cricket/{slug}/ {en} 301',rows)
        self.assertIn(f'/hi/news/cricket/{slug}/ {hi} 301',rows)

    def test_multiple_former_categories_redirect_directly_to_winner(self):
        rows,en,hi=self.redirect_lines(['cricket','world-news'])
        for lang,target in [('en',en),('hi',hi)]:
            for category in ('cricket','world-news'):
                matches=[r for r in rows if r.startswith(f'/{lang}/news/{category}/')]
                self.assertEqual(len(matches),1)
                self.assertTrue(matches[0].endswith(f' {target} 301'))
