"""Check every canonical sitemap URL against the built site, without network requests."""
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse,unquote
import xml.etree.ElementTree as ET

def audit(out,site='https://globewiredaily.org'):
    out=Path(out);ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls=[x.text for x in ET.parse(out/'sitemap.xml').getroot().findall('s:url/s:loc',ns)]
    errors=[];checked=0;article_count=0;alternates=0
    if len(urls)!=len(set(urls)):errors.append('Duplicate canonical sitemap URLs')
    if len(urls)>50000:errors.append('Normal sitemap exceeds 50,000 URLs')
    redirects={line.split()[0] for line in (out/'_redirects').read_text().splitlines() if line.strip() and not line.startswith('#')}
    existence={}
    def exists(path):
        path=unquote(path)
        if path not in existence:
            target=out/path.lstrip('/')
            existence[path]=path in redirects or target.is_file() or (target/'index.html').is_file()
        return existence[path]
    for url in urls:
        path=urlparse(url).path;target=out/path.lstrip('/')/'index.html'
        if not target.is_file():errors.append('Missing sitemap target: '+url);continue
        source=target.read_text(encoding='utf-8');head=source.split('</head>',1)[0]
        canonical=re.findall(r'<link rel="canonical" href="([^"]*)"',head)
        if canonical!=[url]:errors.append('Canonical mismatch: '+url)
        robots=re.search(r'<meta name="robots" content="([^"]*)"',head)
        if not robots or 'noindex' in robots[1]:errors.append('Nonindexable sitemap target: '+url)
        if len(re.findall(r'<title>.*?</title>',head,re.S))!=1:errors.append('Missing/duplicate title: '+url)
        if len(re.findall(r'<meta name="description"',head))!=1:errors.append('Missing/duplicate description: '+url)
        if len(re.findall(r'<h1(?:\s|>)',source))!=1:errors.append('H1 count: '+url)
        if source.count('id="main-content"')!=1:errors.append('Missing/duplicate main landmark: '+url)
        for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',head,re.S):
            try:
                value=json.loads(raw)
                for row in value.get('@graph',[value]):
                    if row.get('@type') in ('NewsArticle','Article'):
                        article_count+=1
                        if 'breadcrumb' in row:errors.append('Breadcrumb nested under Article: '+url)
            except ValueError:errors.append('Invalid JSON-LD: '+url)
        for code,link in re.findall(r'<link rel="alternate" hreflang="([^"]*)" href="([^"]*)"',head):
            if link.startswith(site) and not exists(urlparse(html.unescape(link)).path):errors.append('Missing alternate '+code+': '+url)
            alternates+=1
        for raw in re.findall(r'(?:href|src)="([^"#]+)"',source):
            link=html.unescape(raw);parts=urlparse(link)
            if parts.netloc and parts.netloc!=urlparse(site).netloc:continue
            if parts.scheme not in ('','https','http') or not parts.path.startswith('/'):continue
            if not exists(parts.path):errors.append('Broken internal URL '+parts.path+' from '+url)
        checked+=1
    errors=list(dict.fromkeys(errors))
    return {'checked_pages':checked,'article_pages':article_count,'alternate_links':alternates,'errors':errors,'ok':not errors}

if __name__=='__main__':
    result=audit(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'dist')
    print(json.dumps({**result,'errors':result['errors'][:15]},ensure_ascii=False))
    raise SystemExit(0 if result['ok'] else 1)
