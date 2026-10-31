import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from news_config import classify, CATEGORIES
from official_notices import parse_board, official_url, notice_date
from expanded_hubs import article_note

class ExpansionTests(unittest.TestCase):
    def test_scoped_classification(self):
        self.assertEqual(classify('Galaxy mobile phone launch price specifications','technology'),'mobile-launches')
        self.assertNotEqual(classify('Company share price reaches record high','business'),'car-launches')
        self.assertEqual(classify('India cricket team ICC World Cup','sports'),'cricket')
        self.assertEqual(classify('Final result of recruitment examination','sarkari-naukri'),'results')
        self.assertNotEqual(classify('Nvidia quarterly results','technology'),'results')
        self.assertEqual(len(CATEGORIES),48)
        self.assertNotEqual(classify("Neil Simon's Rumors revival cast",'movies-entertainment'),'entertainment-rumours')

    def test_official_document_index(self):
        html='''<ul><li>30/10/2026 <a href="/docs/result.pdf">Final result of civil services recruitment examination</a></li>
        <li><a href="https://example.com/fake.pdf">Recruitment application for civil services examination</a></li>
        <li><a href="/results">Recruitment examination results navigation menu</a></li>
        <li><a href="/docs/application.pdf">Application deadline for recruitment examination</a></li></ul>'''
        rows=parse_board(html,'https://upsc.gov.in/')
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['date'],'2026-10-30')
        self.assertIsNone(rows[1]['date'])
        self.assertFalse(official_url('https://upsc.gov.in.fake.example/notice.pdf'))
        self.assertFalse(official_url('http://upsc.gov.in/notice.pdf'))
        self.assertIsNone(notice_date('31/02/2026'))

    def test_article_disclosures(self):
        self.assertIn('unconfirmed',article_note({'category':'entertainment-rumours','en_title':'Actor casting rumour'},'en').lower())
        self.assertTrue(article_note({'category':'freebies','en_title':'Free game offer'},'en'))
        self.assertEqual(article_note({'category':'cricket','en_title':'Match result'},'en'),'')

if __name__=='__main__':unittest.main()
