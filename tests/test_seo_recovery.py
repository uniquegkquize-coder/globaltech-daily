import json
from xml.sax.saxutils import escape
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_built_seo import SITE, audit, audit_page, read_sitemaps
from seo_recovery import ctr_candidates, story_audit
from seo_site import head


class SeoRecoveryTests(unittest.TestCase):
    def test_fallback_has_no_language_alternates(self):
        en = SITE + '/en/news/technology/example/'
        hi = SITE + '/hi/news/technology/example/'
        tags = head('en', 'Example', 'Summary', hi, site=SITE,
                    alternates={'en': en}, canonical=en, robots='noindex,follow')
        self.assertIn(f'rel="canonical" href="{en}"', tags)
        self.assertNotIn('hreflang', tags)

    def test_audit_flags_nonindexable_alternate_target(self):
        en = SITE + '/en/news/technology/example/'
        tags = head('en', 'Example', 'Summary', en, site=SITE)
        errors, _ = audit_page(en, f'<html lang="en"><head>{tags}</head></html>', {en})
        self.assertEqual(len(errors), 1)
        self.assertIn('Invalid hreflang hi', errors[0])

    def test_audit_follows_news_shards_and_checks_membership(self):
        en = SITE + '/en/news/technology/example/'
        hi = SITE + '/hi/news/technology/example/'
        ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        sitemap = f'<urlset xmlns="{ns}"><url><loc>{en}</loc></url></urlset>'
        index = f'<sitemapindex xmlns="{ns}"><sitemap><loc>{SITE}/news-sitemap-1.xml</loc></sitemap></sitemapindex>'
        shard = f"""<urlset xmlns="{ns}" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
          <url><loc>{hi}</loc><news:news><news:publication><news:language>hi</news:language></news:publication>
          <news:publication_date>2026-11-12T15:00:00Z</news:publication_date><news:title>शीर्षक</news:title>
          </news:news></url></urlset>"""
        files = {'/sitemap.xml': sitemap, '/news-sitemap.xml': index, '/news-sitemap-1.xml': shard}
        canonical, news, errors = read_sitemaps(files.__getitem__, SITE)
        self.assertEqual((canonical, news), ({en}, {hi}))
        self.assertEqual(errors, ['News URL absent from canonical sitemap: ' + hi])

    def test_verify_built_site_checks_origin_redirects_and_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / 'rendered'
            (out / 'en').mkdir(parents=True)
            url = SITE + '/en/'
            tags = head('en', 'Example', 'Summary', url, site=SITE, alternates={'en': url})
            (out / 'en/index.html').write_text(
                f'<html lang="en"><head>{tags}</head><main id="main-content"><h1>Example</h1></main></html>')
            ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
            (out / 'sitemap.xml').write_text(f'<urlset xmlns="{ns}"><url><loc>{escape(url)}</loc></url></urlset>')
            (out / 'news-sitemap.xml').write_text(f'<urlset xmlns="{ns}"></urlset>')
            (out / '_redirects').write_text('/ /en/ 301\n')
            (out / '404.html').write_text('<meta name="robots" content="noindex">')
            (root / 'redirects.json').write_text(json.dumps({'/old/': ['/en/', '301']}))
            inventory = root / 'inventory.json'
            inventory.write_text(json.dumps({'urls': ['/en/', '/old/', '/legacy/']}))
            self.assertFalse(audit(out, inventory=inventory)['ok'])
            legacy = ['dist/legacy/index.html']
            result = audit(out, inventory=inventory, legacy_files=legacy)
            self.assertTrue(result['ok'])
            self.assertEqual(result['legacy_inventory_paths'], ['/legacy/'])
            (root / 'redirects.json').write_text(json.dumps({'/old/': ['/missing/', '301']}))
            self.assertFalse(audit(out, inventory=inventory, legacy_files=legacy)['ok'])

    def test_ctr_triage_accepts_both_languages_and_collates_legacy_host(self):
        hi = '/hi/news/technology/example/'
        sample = {'keys': ['खोज', 'https://www.globewiredaily.org' + hi],
                  'impressions': 320, 'clicks': 0, 'ctr': 0, 'position': 7}
        branded = {**sample, 'keys': ['GlobeWire Daily', SITE + hi]}
        low_volume = {**sample, 'impressions': 25}
        strong_ctr = {**sample, 'ctr': 0.02}
        result = ctr_candidates([branded, sample, low_volume, strong_ctr])
        self.assertEqual([row['canonical_candidate'] for row in result], [SITE + hi])

    def test_story_audit_reports_duplicates_and_misrouting_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            posts = Path(directory)
            title = 'Anant Singh wins Bihar assembly election in Mokama'
            record = {'id': 'aaa1', 'en_title': title, 'en_body': 'Report body ' * 20,
                      'category': 'sports', 'source': 'https://example.com/news/1'}
            original = json.dumps(record)
            first = posts / 'aaa1.json'
            first.write_text(original)
            (posts / 'bbb2.json').write_text(json.dumps({**record, 'id': 'bbb2'}))
            result = story_audit(posts)
            self.assertEqual(result['valid_records'], 2)
            self.assertEqual(result['duplicate_candidates'], [{'id': 'bbb2', 'canonical_id': 'aaa1'}])
            self.assertEqual(len(result['category_candidates']), 2)
            self.assertEqual(first.read_text(), original)
