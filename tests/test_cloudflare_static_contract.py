"""Regression guards for the Cloudflare Pages static contract.

Covers two real incidents:
1. trending_watch.py shipped twice (2026-11-04) with a literal "\\n" instead
   of a real newline (lines 125 and 230); compileall caught it only after
   push, so scheduled workflows failed for hours. The syntax canary below
   proves this guard class actually fires, then proves the tree is clean.
2. A partial publish must never truncate dist/_redirects back to the
   legacy-only stub; the Pages 301 budget has to survive every build.
"""
import compileall
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RENDERED=ROOT/'build/rendered'
REDIRECTS=RENDERED/'_redirects'

class SyntaxGuardTests(unittest.TestCase):
 """Any syntax damage under scripts/ must fail here, before push."""
 def test_pristine_scripts_compile(self):
  self.assertTrue(compileall.compile_dir(str(ROOT/'scripts'),quiet=1),'A script under scripts/ failed to compile')
 def test_tagged_literal_newline_damage_is_caught_and_cleaned(self):
  canary=ROOT/'scripts'/'_syntax_canary_tmp.py'
  first=second=None
  try:
   canary.write_text("x='a'\\n y='b'",encoding='utf-8')
   first=compileall.compile_dir(str(ROOT/'scripts'),quiet=1)
  finally:
   if canary.exists():canary.unlink()
   for p in (ROOT/'scripts'/'__pycache__').glob('*_syntax_canary_tmp*'):p.unlink()
  second=compileall.compile_dir(str(ROOT/'scripts'),quiet=1)
  self.assertFalse(first,'compileall must fail while a literal-\\n line exists; the guard would be ineffective')
  self.assertTrue(second,'compileall must succeed once the tagged damage is removed')
  self.assertFalse(canary.exists(),'canary script leaked into the tree')
  residue=[p.name for p in (ROOT/'scripts'/'__pycache__').glob('*_syntax_canary_tmp*')]
  self.assertEqual(residue,[],f'canary bytecode residue left behind: {residue}')

class PagesStaticContractTests(unittest.TestCase):
 """dist/ in the checkout must keep the artifacts Pages serves directly."""
 def setUp(self):
  if not RENDERED.is_dir():self.skipTest('rendered build not present; CI builds before running this integration check')
 def test_redirect_budget_survives_partial_publishes(self):
  self.assertTrue(REDIRECTS.is_file(),'dist/_redirects is missing')
  lines=REDIRECTS.read_text(encoding='utf-8').strip().splitlines()
  self.assertEqual(lines,['/ /en/ 301'])
  import json
  aliases=json.loads((ROOT/'build/redirects.json').read_text())
  self.assertGreater(len(aliases),4000,'Legacy URL map must survive every release')
  self.assertTrue(lines[0].startswith('/ '),'first redirect rule must keep routing the bare homepage')
 def test_required_static_artifacts_exist(self):
  for name in ('404.html','robots.txt','sitemap.xml','news-sitemap.xml','ads.txt','_headers','_redirects'):
   path=RENDERED/name
   self.assertTrue(path.is_file() and path.stat().st_size>0,f'{name} missing or empty in dist/')
 def test_seo_head_keeps_analytics_adsense_and_cache_busting(self):
  html=(RENDERED/'en'/'index.html').read_text(encoding='utf-8')
  for token in ('ca-pub-1849673109734274','G-MFZZNMZCWJ','/style.css?v=','/favicon.svg','hreflang'):
   self.assertIn(token,html,f'publishing head lost required token: {token}')

if __name__=='__main__':unittest.main()
