import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from seo_site import head, article_languages, category_description, write_site_sitemap, related_index
from news_sitemap import write_news_sitemap
from news_config import CATEGORIES

SITE='https://example.org'

class SiteSeoTests(unittest.TestCase):
    def test_article_social_image_and_url_are_not_overridden(self):
        extra='<meta property="og:image" content="https://example.org/photo.jpg"><meta property="og:url" content="https://example.org/en/news/a/">'
        result=head('en','A title','A summary',SITE+'/en/news/a/',extra,site=SITE)
        self.assertEqual(result.count('property="og:image"'),1)
        self.assertEqual(result.count('property="og:url"'),1)
        self.assertIn('photo.jpg',result)

    def test_publisher_identity_and_article_page_entity_are_linked(self):
        result=head('en','News','Summary',SITE+'/en/news/a/',site=SITE)
        self.assertIn('NewsMediaOrganization',result)
        self.assertIn(SITE+'/#publisher',result)
        self.assertIn(SITE+'/en/news/a/#webpage',result)
        self.assertNotIn('aggregateRating',result)

    def test_hindi_alternate_is_not_advertised_without_hindi(self):
        for body in ('English copy only','한국어 본문'):
            self.assertEqual(article_languages({'hi_body':body}),['en'])
        self.assertEqual(article_languages({'hi_body':'यह एक हिंदी समाचार लेख है।'}),['en','hi'])
        result=head('en','News','Summary',SITE+'/en/news/a/',site=SITE,alternates={'en':SITE+'/en/news/a/'})
        self.assertNotIn('hreflang="hi"',result)
        self.assertIn('hreflang="x-default"',result)

    def test_noindex_fallback_has_english_canonical(self):
        result=head('en','News','Summary',SITE+'/hi/news/a/',site=SITE,canonical=SITE+'/en/news/a/',robots='noindex,follow',alternates={'en':SITE+'/en/news/a/'})
        self.assertIn('rel="canonical" href="'+SITE+'/en/news/a/"',result)
        self.assertIn('content="noindex,follow"',result)

    def test_category_descriptions_are_distinct_and_paginated(self):
        for lang in ('en','hi'):
            descriptions=[category_description(k,names,lang) for k,names in CATEGORIES.items()]
            self.assertEqual(len(descriptions),len(set(descriptions)))
            self.assertNotEqual(category_description('technology',CATEGORIES['technology'],lang),category_description('technology',CATEGORIES['technology'],lang,2))

    def test_canonical_sitemap_excludes_fallbacks_redirects_and_missing_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            samples={
                'en/news/a/index.html':('<link rel="canonical" href="'+SITE+'/en/news/a/"><script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':[{'@type':'NewsArticle','datePublished':'2026-10-30T08:00:00+00:00','dateModified':'2026-11-01T08:00:00+00:00'}]})+'</script>'),
                'hi/news/a/index.html':'<meta name="robots" content="noindex,follow"><link rel="canonical" href="'+SITE+'/en/news/a/">',
                'en/courses/pharmacy/index.html':'<link rel="canonical" href="'+SITE+'/en/courses/pharmacy/">',
                'en/news/old/index.html':'<meta http-equiv="refresh" content="0;url=/en/news/a/"><link rel="canonical" href="'+SITE+'/en/news/a/">',
                'en/empty/index.html':'<meta name="robots" content="noindex,follow"><link rel="canonical" href="'+SITE+'/en/empty/">'}
            for name,tags in samples.items():
                path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('<html><head>'+tags+'</head><body></body></html>')
            self.assertEqual(write_site_sitemap(out,SITE,[*samples,'en/missing/index.html']),2)
            root=ET.parse(out/'sitemap.xml').getroot();ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
            self.assertEqual({x.text for x in root.findall('s:url/s:loc',ns)},{SITE+'/en/news/a/',SITE+'/en/courses/pharmacy/'})
            self.assertEqual(root.find('s:url[s:loc="'+SITE+'/en/news/a/"]/s:lastmod',ns).text,'2026-11-01T08:00:00+00:00')

    def test_news_sitemap_only_lists_real_translations(self):
        now=dt.datetime(2026,11,3,tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            write_news_sitemap(out,SITE,[{'date':now.isoformat(),'hi_body':'English duplicated'}],lambda p,lang:'/'+lang+'/article/',lambda p,lang:'Title',now,languages=article_languages)
            self.assertNotIn('/hi/article/',(out/'news-sitemap.xml').read_text())

    def test_related_coverage_prefers_shared_subject_over_unrelated_desk_story(self):
        posts=[{'id':'roman','category':'science','en_title':'NASA Roman telescope opens pixel adoption','date':'2026-10-30'},
               {'id':'same','category':'science','en_title':'New medical study examines knee pain','date':'2026-11-02'},
               {'id':'relevant','category':'space','en_title':'NASA Roman telescope camera captures first images','date':'2026-10-28'}]
        self.assertEqual(related_index(posts)['roman'][0]['id'],'relevant')
        posts[0]['related_post_ids']=['same']
        self.assertEqual(related_index(posts)['roman'][0]['id'],'same')

if __name__=='__main__':unittest.main()
