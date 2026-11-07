import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bs4 import BeautifulSoup
import research_directory_sources as research
import publish_directory_guides as publisher
from directory_refresh import refresh_sources, protect_reviewed, merge_rows


class DirectoryRefreshTests(unittest.TestCase):
    def test_official_store_can_omit_brand_but_not_change_model_number(self):
        html='<title>X Fold5 16GB+512GB Titanium Grey</title><table><tr><td>Price</td><td>INR 149999</td></tr><tr><td>RAM</td><td>16 GB</td></tr></table>'
        record={'manufacturer':'vivo','official_url':'https://www.vivo.com/in/products/param/x-fold5'}
        with patch.object(research,'fetch_public_html',return_value=(html,'https://shop.vivo.com/in/product/10316','browser')):
            facts=research.enrich('phones','Vivo X Fold 5',record,Mock(),'https://shop.vivo.com/in/product/10316')
        self.assertEqual(facts['price'],'INR 149999')
        with patch.object(research,'fetch_public_html',return_value=(html.replace('Fold5','Fold50'),'https://shop.vivo.com/in/product/10316','browser')):
            self.assertEqual(research.enrich('phones','Vivo X Fold 5',record,Mock(),'https://shop.vivo.com/in/product/10316'),{})

    def test_recheck_prices_and_each_course_not_only_static_pdf(self):
        entry = {'official_url': 'https://college.example/', 'source_url': 'https://college.example/brochure.pdf',
                 'field_sources': {'fees': {'url': 'https://college.example/fees'}},
                 'courses': [{'source_url': 'https://college.example/pharmacy'}]}
        self.assertEqual(refresh_sources('colleges', entry),
                         ['https://college.example/fees', 'https://college.example/pharmacy', 'https://college.example/'])

    def test_reviewed_prices_refresh_with_evidence_static_specs_stay(self):
        old = {'reviewed_fields': ['price', 'fees', 'courses', 'battery']}
        additions = {'price': 'INR 90000', 'battery': 'incorrect marketing copy',
                     'field_sources': {'price': {'url': 'https://maker.example/model'}, 'battery': {'url': 'https://maker.example/model'}}}
        protect_reviewed(old, additions)
        self.assertEqual(additions['price'], 'INR 90000')
        self.assertNotIn('battery', additions)
        self.assertNotIn('battery', additions['field_sources'])
        self.assertNotIn('price', protect_reviewed(old, {'price': 'unsourced'}))

    def test_price_change_replaces_same_row_preserves_other_courses(self):
        old = [{'course': 'BPharm', 'fees': 'INR 150000', 'source_url': 'https://college.example/p'},
               {'course': 'MBA', 'fees': 'INR 200000', 'source_url': 'https://college.example/m'}]
        new = [{'course': 'BPharm', 'fees': 'INR 180000', 'source_url': 'https://college.example/p'}]
        result = merge_rows(old, new)
        self.assertEqual(len(result), 2)
        by_course={r['course']:r for r in result}
        self.assertEqual(by_course['BPharm']['fees'], 'INR 180000')
        self.assertEqual(by_course['MBA'], old[1])
        self.assertEqual(merge_rows(result, new), result)

    def test_offer_currency_and_availability_are_not_lost(self):
        html = '''<title>Example Phone</title><script type="application/ld+json">
        {"@type":"Product","name":"Example Phone","offers":{"@type":"Offer",
        "price":"25999","priceCurrency":"INR","availability":"https://schema.org/OutOfStock"}}</script>'''
        with patch.object(research, 'fetch_public_html', return_value=(html, 'https://shop.example/phone', 'browser')):
            entry = research.enrich('phones', 'Example Phone', {}, Mock(), 'https://shop.example/phone')
        self.assertEqual(entry['price'], 'INR 25999')
        self.assertIn('OutOfStock', entry['availability'])
        self.assertEqual(entry['field_sources']['price']['url'], 'https://shop.example/phone')

    def test_course_page_with_institution_identity_and_singular_fee(self):
        html = '''<title>Bachelor of Pharmacy</title><h1>BPharm</h1><p>Example University</p>
        <table><tr><td>Annual Fee</td><td>INR 180000</td></tr><tr><td>Duration</td><td>4 years</td></tr></table>'''
        with patch.object(research, 'fetch_public_html', return_value=(html, 'https://college.example/pharmacy', 'browser')):
            entry = research.enrich('colleges', 'Example University', {'official_url': 'https://college.example/'}, Mock(), 'https://college.example/pharmacy')
        self.assertEqual(entry['fees'], 'INR 180000')

    def test_complete_specs_do_not_block_separate_price_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'content').mkdir()
            source = 'https://maker.example/specs'
            price = 'https://shop.example/phone'
            old = {'display': '6 inches', 'processor': 'CPU', 'ram': '8GB', 'storage': '128GB', 'battery': '5000mAh',
                   'official_url': source, 'source_url': source, 'price': 'INR 30000',
                   'reviewed_fields': ['price','battery'], 'field_sources': {'price': {'url': price}}}
            target = root / 'content/directory-details.json'
            target.write_text(json.dumps({'phones': {'Example Phone': old}}))
            records = root / 'content/directory-records.json'
            records.write_text('{}')
            def enrich(kind, name, base, session, url=None):
                if url == price:
                    return {'price': 'INR 25999', 'field_sources': {'price': {'url': price, 'retrieved_at': '2026-11-07'}}}
                return {'battery': '5000mAh', 'field_sources': {'battery': {'url': source}}}
            with patch.object(research, 'ROOT', root), patch.object(research, 'TARGET', target), patch.object(research, 'RECORDS', records), patch.object(research, 'enrich', side_effect=enrich), patch.object(research, 'discover', return_value=[]):
                research.main()
            updated = json.loads(target.read_text())['phones']['Example Phone']
            self.assertEqual(updated['price'], 'INR 25999')
            self.assertEqual(updated['battery'], old['battery'])

    def test_all_changed_published_guides_update_without_ten_item_backlog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts = root / 'content/posts'
            posts.mkdir(parents=True)
            details = {'phones': {f'Phone {i}': {'battery': '5000mAh', 'display': '6 inches', 'price': 'INR 20000', 'source_url': f'https://maker.example/phone-{i}'} for i in range(12)}}
            (root / 'content/directory-details.json').write_text(json.dumps(details))
            for name, entry in details['phones'].items():
                ident, post = publisher.article('phones', name, entry, entry['source_url'])
                post['directory_fingerprint'] = 'old'
                post['date'] = '2026-01-01'
                (posts / (ident + '.json')).write_text(json.dumps(post))
            with patch.object(publisher, 'ROOT', root), patch.object(publisher, 'POSTS', posts):
                publisher.main()
            status = json.loads((root / 'content/directory-guide-status.json').read_text())
            self.assertEqual(status['updated'], 12)
            self.assertTrue(all(json.loads(path.read_text())['date'] == '2026-01-01' for path in posts.glob('*.json')))
