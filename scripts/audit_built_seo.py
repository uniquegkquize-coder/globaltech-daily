"""Check every canonical sitemap URL against the built site, without network requests."""
import argparse
from datetime import datetime
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse,unquote
import xml.etree.ElementTree as ET

from seo_site import iso_date

SITE = 'https://globewiredaily.org'
SITEMAP = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
NEWS = '{http://www.google.com/schemas/sitemap-news/0.9}'


def read_sitemaps(read, site):
    errors, url_sets = [], []
    for name in ('/sitemap.xml', '/news-sitemap.xml'):
        is_news = name.startswith('/news-')
        urls = set()
        seen = set()
        def visit(path):
            if path in seen:
                errors.append(f'Duplicate sitemap reference: {path}')
                return
            seen.add(path)
            try:
                data = read(path)
                if len(data) > 50 * 1024 * 1024:
                    errors.append(f'Sitemap exceeds 50 MiB: {path}')
                root = ET.fromstring(data)
            except (OSError, ValueError, ET.ParseError) as exc:
                errors.append(f'Cannot read sitemap {path}: {exc}')
                return
            if root.tag == SITEMAP + 'sitemapindex' and path == name:
                children = root.findall(SITEMAP + 'sitemap/' + SITEMAP + 'loc')
                if not children or len(children) > 50000:
                    errors.append(f'Invalid sitemap index length: {path}')
                for loc in children:
                    url = loc.text or ''
                    if re.fullmatch(re.escape(site) + r'/[a-z0-9-]+\.xml', url):
                        visit(url.removeprefix(site))
                    else:
                        errors.append(f'Invalid child sitemap URL: {url}')
                return
            if root.tag != SITEMAP + 'urlset':
                errors.append(f'Invalid sitemap root: {path}')
                return
            rows = root.findall(SITEMAP + 'url')
            if len(rows) > (1000 if is_news else 50000):
                errors.append(f'Too many URLs in {path}: {len(rows)}')
            for row in rows:
                url = row.findtext(SITEMAP + 'loc', '')
                parsed = urlparse(url)
                if not url.startswith(site + '/') or not parsed.path.startswith(('/en/', '/hi/')) or parsed.query or parsed.fragment:
                    errors.append(f'Invalid sitemap URL: {url}')
                    continue
                if url in urls:
                    errors.append(f'Duplicate sitemap URL: {url}')
                urls.add(url)
                if is_news:
                    news = row.find(NEWS + 'news')
                    if (news is None or not news.findtext(NEWS + 'title')
                            or not iso_date(news.findtext(NEWS + 'publication_date'))
                            or news.findtext(NEWS + 'publication/' + NEWS + 'language') != parsed.path.split('/')[1]):
                        errors.append(f'Invalid news entry: {url}')
        visit(name)
        url_sets.append(urls)
    urls, news_urls = url_sets
    if not urls:
        errors.append('Empty canonical sitemap')
    errors.extend(f'News URL absent from canonical sitemap: {url}' for url in sorted(news_urls - urls))
    return urls, news_urls, errors


def audit_page(url, source, urls):
    errors = []
    head = source.split('</head>', 1)[0]
    canonical = re.findall(r'<link rel="canonical" href="([^"]*)"', head)
    if list(map(html.unescape, canonical)) != [url]:
        errors.append('Canonical mismatch: ' + url)
    robots = re.search(r'<meta name="robots" content="([^"]*)"', head)
    if not robots or 'noindex' in robots[1].lower():
        errors.append('Nonindexable sitemap target: ' + url)
    for label, pattern in [('title', r'<title>\s*[^<]+</title>'),
                           ('description', r'<meta name="description" content="[^"]+">')]:
        if len(re.findall(pattern, head)) != 1:
            errors.append(f'Missing/duplicate {label}: {url}')
    lang = urlparse(url).path.split('/')[1]
    if not re.search(r'<html\s+lang="' + lang + r'"', source):
        errors.append('HTML language mismatch: ' + url)
    alternates = {}
    for code, link in re.findall(r'<link rel="alternate" hreflang="([^"]*)" href="([^"]*)"', head):
        link = html.unescape(link)
        if code in alternates or code not in ('en', 'hi', 'x-default') or link not in urls:
            errors.append(f'Invalid hreflang {code}: {url} -> {link}')
        if code in ('en', 'hi') and not urlparse(link).path.startswith('/' + code + '/'):
            errors.append(f'Hreflang language mismatch {code}: {url} -> {link}')
        alternates[code] = link
    peer_lang = 'hi' if lang == 'en' else 'en'
    peer = url.replace(f'/{lang}/', f'/{peer_lang}/', 1)
    if ('/news/' in url or url.endswith(f'/{lang}/')) and peer in urls and alternates.get(peer_lang) != peer:
        errors.append(f'Missing bilingual hreflang: {url} -> {peer}')
    if alternates and (alternates.get(lang) != url or alternates.get('x-default') != alternates.get('en', url)):
        errors.append('Hreflang self or default mismatch: ' + url)

    nodes = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', head, re.S):
        try:
            value = json.loads(raw)
            nodes.extend(value.get('@graph', [value]))
        except (ValueError, AttributeError, TypeError):
            errors.append('Invalid JSON-LD: ' + url)
    articles = [n for n in nodes if n.get('@type') in ('NewsArticle', 'Article')]
    if 'data-article-layout="v3"' in source:
        if len(articles) != 1:
            errors.append('Missing/duplicate Article schema: ' + url)
        crumbs = [n.get('itemListElement', []) for n in nodes if n.get('@type') == 'BreadcrumbList']
        if (len(crumbs) != 1 or len(crumbs[0]) < 3 or crumbs[0][-1].get('item') != url
                or [item.get('position') for item in crumbs[0]] != list(range(1, len(crumbs[0]) + 1))):
            errors.append('Invalid article breadcrumb: ' + url)
    for row in articles:
        published = iso_date(row.get('datePublished'))
        modified = iso_date(row.get('dateModified'))
        if (row.get('url') != url or row.get('inLanguage') != lang or not row.get('headline')
                or 'breadcrumb' in row or not row.get('author', {}).get('name')
                or row.get('mainEntityOfPage', {}).get('@id') != url + '#webpage'):
            errors.append('Invalid article schema identity: ' + url)
        if row.get('@type') == 'NewsArticle' and not published:
            errors.append('Missing NewsArticle publication date: ' + url)
        if published and modified and datetime.fromisoformat(modified) < datetime.fromisoformat(published):
            errors.append('Article modified before publication: ' + url)
    return errors, alternates


def audit(out, site=SITE, inventory=None, legacy_files=()):
    out = Path(out)
    urls, news_urls, errors = read_sitemaps(lambda name: (out/name.lstrip('/')).read_bytes(), site)
    checked = article_count = alternates = 0
    hreflang = {}
    missing=out/'404.html'
    if not missing.is_file() or 'noindex' not in missing.read_text(encoding='utf-8').split('</head>',1)[0]:errors.append('Missing noindex 404 document')
    static_rows = [line.split() for line in (out/'_redirects').read_text().splitlines()
                   if line.strip() and not line.lstrip().startswith('#')]
    dynamic = sum('*' in row[0] or ':' in row[0] for row in static_rows)
    if dynamic > 100 or len(static_rows) - dynamic > 2000:
        errors.append('Cloudflare Pages redirect budget exceeded')
    redirect_rows = {source: [target, code] for source, target, code in static_rows}
    origin_redirects = out.parent / 'redirects.json'
    if origin_redirects.is_file():
        redirect_rows.update(json.loads(origin_redirects.read_text()))
    redirects = set(redirect_rows)
    existence={}
    def exists(path):
        path=unquote(path)
        if path not in existence:
            target=out/path.lstrip('/')
            existence[path]=path in redirects or target.is_file() or (target/'index.html').is_file()
        return existence[path]
    for source, (target, code) in redirect_rows.items():
        if (source == target or target in redirects or code not in ('301', '308')
                or not target.startswith('/') or target.startswith('//') or not exists(target)):
            errors.append(f'Invalid permanent redirect: {source} -> {target} ({code})')
        if site + source in urls:
            errors.append(f'Redirect is indexable in sitemap: {source}')
    legacy_inventory_paths = []
    if inventory:
        legacy_files = set(legacy_files)
        for route in json.loads(Path(inventory).read_text())['urls']:
            if exists(route):
                continue
            legacy_path = 'dist/' + unquote(route).lstrip('/')
            if legacy_path in legacy_files or legacy_path + 'index.html' in legacy_files:
                legacy_inventory_paths.append(route)
            else:
                errors.append(f'Missing published URL: {route}')
    for url in sorted(urls):
        path = unquote(urlparse(url).path)
        target = out / path.lstrip('/') / 'index.html'
        if not target.is_file():
            errors.append('Missing sitemap target: ' + url)
            continue
        source = target.read_text(encoding='utf-8')
        page_errors, hreflang[url] = audit_page(url, source, urls)
        errors.extend(page_errors)
        alternates += len(hreflang[url])
        article_count += 'data-article-layout="v3"' in source
        if len(re.findall(r'<h1(?:\s|>)',source))!=1:errors.append('H1 count: '+url)
        if source.count('id="main-content"')!=1:errors.append('Missing/duplicate main landmark: '+url)
        if 'data-article-layout="v3"' in source:
            ids=re.findall(r'\bid="([^"]+)"',source)
            if len(ids)!=len(set(ids)):errors.append('Duplicate reading anchor: '+url)
            toc=re.search(r'<nav class="article-toc".*?</nav>',source,re.S)
            if toc:
                for anchor in re.findall(r'href="#([^"]+)"',toc[0]):
                    if html.unescape(anchor) not in ids:errors.append('Broken reading anchor: '+url)
        for raw in re.findall(r'(?:href|src)="([^"#]+)"',source):
            link=html.unescape(raw);parts=urlparse(link)
            if parts.netloc and parts.netloc!=urlparse(site).netloc:continue
            if parts.scheme not in ('','https','http') or not parts.path.startswith('/'):continue
            if not exists(parts.path):errors.append('Broken internal URL '+parts.path+' from '+url)
        checked+=1
    for url, links in hreflang.items():
        lang = urlparse(url).path.split('/')[1]
        for target in set(links.values()):
            if target in hreflang and hreflang[target].get(lang) != url:
                errors.append(f'Non-reciprocal hreflang: {url} -> {target}')
    errors = list(dict.fromkeys(errors))
    return {'checked_pages': checked, 'article_pages': article_count,
            'alternate_links': alternates, 'news_urls': len(news_urls),
            'server_redirects': len(redirect_rows), 'legacy_inventory_paths': legacy_inventory_paths,
            'errors': errors, 'ok': not errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, nargs='?', default=Path('dist'))
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--legacy-files', type=Path, help='Tracked files from git ls-tree for the legacy dist layer')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    legacy_files = args.legacy_files.read_text().splitlines() if args.legacy_files else ()
    result = audit(args.output, inventory=args.inventory, legacy_files=legacy_files)
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({**result, 'errors': result['errors'][:15]}, ensure_ascii=False))
    raise SystemExit(not result['ok'])
