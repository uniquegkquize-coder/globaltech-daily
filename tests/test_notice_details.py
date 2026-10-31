import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import notice_details as details
from official_notices import load_notices
from news_hub import official_notice_rows

class NoticeDetailsTests(unittest.TestCase):
    def test_clickable_links_escape_html(self):
        rendered=details.inline('[Apply now](https://ssc.gov.in/?a=1&b=2) <script>alert(1)</script>')
        self.assertIn('<a href="https://ssc.gov.in/?a=1&amp;b=2"',rendered)
        self.assertIn('Apply now</a>',rendered)
        self.assertNotIn('<script>',rendered)
        self.assertNotIn('<a ',details.inline('[bad](javascript:alert(1))'))
        self.assertIn('<a href="https://upsc.gov.in/notice.pdf"',details.inline('https://upsc.gov.in/notice.pdf'))

    def test_safe_facts_and_budget(self):
        fields=details.extract_facts('Last date of application: 30/11/2026\nApplication fee: Rs. 100\nCandidate name: Private Person\nRoll number 12345\nEligibility: degree from a recognized university')
        self.assertIn('fees',fields)
        wrapped=details.extract_facts('Examination is scheduled to be conducted from\n10/11/2026 to 12/11/2026')
        self.assertIn('10/11/2026',str(wrapped))
        self.assertNotIn('dates',details.extract_facts('Examination is scheduled to be conducted from'))
        self.assertIn('eligibility',fields)
        self.assertNotIn('Private Person',str(fields))
        self.assertLessEqual(sum(len(x.split()) for vals in fields.values() for x in vals),180)

    def test_internal_notice_pages_and_official_cta(self):
        record={'en_title':'Recruitment application notice','hi_title':'भर्ती आवेदन नोटिस','source':'https://ssc.gov.in/notice.pdf','category':'sarkari-naukri','date':'2026-01-01'}
        saved={}
        def write(path,content):saved[str(path)]=content
        def shell(lang,title,desc,url,body):return body
        with patch('official_notices.load_notices',return_value=[record]),patch.object(details,'details_cache',return_value={record['source']:{'fields':{'fees':['Application fee Rs.100']}}}):
            urls=details.render_notices(pathlib.Path('/tmp/output'),'https://example.com',shell,write)
        self.assertEqual(len(urls),2)
        self.assertTrue(all('/exam-notice/' in x for x in urls))
        self.assertIn('href="https://ssc.gov.in/notice.pdf"',saved['/tmp/output'+urls[0]+'index.html'])
        self.assertNotIn('applications are open',str(saved))
        self.assertIn('id="eligibility"',str(saved))

    def test_notice_listing_stays_on_site(self):
        record=load_notices()[0]
        with patch('news_hub.load_notices',return_value=[dict(record,date=__import__('datetime').date.today().isoformat())]):
            output=official_notice_rows(record['category'],'en')
        self.assertIn('/en/exam-notice/',output)
        self.assertNotIn('target="_blank"',output)

if __name__=='__main__':unittest.main()
