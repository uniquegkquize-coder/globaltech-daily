import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import authority_sources as a
import collect
from official_notices import official_url


class AuthoritySourcesTests(unittest.TestCase):
    def tearDown(self):
        a.BOARD_EVIDENCE.clear()

    def test_board_keeps_query_and_avoids_menus(self):
        markup = '''<nav><a href="/registration">Online Registration</a></nav>
        <a href="/Document?id=12&amp;type=notice">Kushmi Enclave flat registration extended to 13 November 2026</a>
        <a href="/Document?id=13&amp;type=notice">Corrigendum to tender for township road construction works</a>
        <a href="/Document?id=12&amp;type=notice">Duplicate flat registration extension notice</a>
        <a href="https://evil.example/flat.pdf">New housing scheme registration notification</a>
        <a href="/contact">Contact us for flats registration and tenders</a>'''
        rows = a.parse_authority_board(markup, 'https://gdagkp.in/')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], 'https://gdagkp.in/Document?id=12&type=notice')
        self.assertEqual([r[2] for r in rows], ['government-schemes', 'india-news'])

    def test_generic_download_label_uses_notice_row(self):
        markup = '<li>Residential plots lottery registration deadline extended to 30 November 2026 <a href="/docs/12.pdf">Click Here</a></li>'
        self.assertIn('Residential plots', a.parse_authority_board(markup, 'https://gdagkp.in/')[0][1])

    def test_official_non_government_suffix_and_spoof(self):
        self.assertTrue(official_url('https://www.gdagkp.in/Content/Images/12.pdf'))
        self.assertFalse(a.authority_url('https://gdagkp.in.evil.example/12.pdf'))
        for url in ('https://127.0.0.1/x', 'https://www.mvdamirzapur/', 'https://x.in:bad/', 'https://user:pass@gdagkp.in/x'):
            self.assertFalse(a.public_url(url))

    def test_property_sports_city_and_tender_routing(self):
        self.assertEqual(collect.category_for_url('Rapti Nagar Sports City plot allotment lottery registration opens', 'sports', 'https://gdagkp.in/docs/12.pdf'), 'government-schemes')
        self.assertEqual(collect.category_for_url('Tender notification for road maintenance', 'government-schemes', 'https://gdagkp.in/docs/12.pdf'), 'india-news')

    def test_catalog_only_promotes_authority_rows(self):
        markup = '<table><tr><td>Gorakhpur</td><td><a href="http://www.gdagkp.in/">View</a></td></tr></table><footer><a href="https://vendor.example">Vendor</a></footer>'
        self.assertEqual(a.catalog_urls(markup, a.CATALOGS[0]), ['https://www.gdagkp.in/'])
        nationwide = '<li>Hyderabad Metropolitan Development Authority <a href="https://www.hmda.gov.in/">Website</a></li><li><a href="https://vendor.example">Contact</a></li>'
        self.assertEqual(a.catalog_urls(nationwide, a.CATALOGS[1]), ['https://www.hmda.gov.in/'])

    def test_rotation_pins_gorakhpur_and_retains_failed_catalogs(self):
        def unavailable(*args, **kwargs):
            raise TimeoutError()
        with tempfile.TemporaryDirectory() as root:
            first = a.authority_boards(unavailable, root, now=1000000, limit=5)
            second = a.authority_boards(unavailable, root, now=1003600, limit=5, refresh=False)
            self.assertEqual([r[0] for r in first[:2]], list(a.SEEDS[:2]))
            self.assertEqual(len(first), 5)
            self.assertNotEqual(first[2:], second[2:])
            self.assertGreaterEqual(len(a.registry_urls(root)), len(a.SEEDS))

    def test_unreadable_pdf_requires_substantial_recent_board_statement(self):
        url = 'https://gdagkp.in/notice/12.pdf'
        a.parse_authority_board('<a href="/notice/12.pdf">New flat registration notice available here</a>', 'https://gdagkp.in/')
        self.assertEqual(a.board_evidence(url), '')
        statement = ' '.join(['Residential plot registration deadline 30 November 2026.'] * 12)
        a.parse_authority_board('<a href="/notice/12.pdf">' + statement + '</a>', 'https://gdagkp.in/')
        with tempfile.TemporaryDirectory() as root:
            a.save_board_evidence(root)
            a.BOARD_EVIDENCE.clear()
            self.assertIn(statement, a.board_evidence(url, root))
            with patch.object(a.dt, 'datetime') as clock:
                clock.now.return_value.timestamp.return_value = 9999999999
                self.assertEqual(a.board_evidence(url, root), '')

    def test_prompt_covers_deadlines_and_emd_without_invention(self):
        prompt = collect.article_prompt('hi', 'Flat registration', 'https://gdagkp.in/notice/12.pdf', 'Official details', 'government-schemes')
        self.assertIn('EMD/security deposit', prompt)
        self.assertIn('Do not describe an expired or undated notice as registration open', prompt)


if __name__ == '__main__':
    unittest.main()
