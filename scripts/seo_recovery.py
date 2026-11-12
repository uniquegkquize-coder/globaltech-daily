"""Read-only production and Search Console audits for GlobeWire Daily."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from audit_built_seo import SITE, audit_page, read_sitemaps
from editorial_quality import normalize_post
from news_config import CATEGORIES, route_category
from story_identity import collapse_posts

PROPERTY = 'sc-domain:globewiredaily.org'
HOMES = [SITE + '/en/', SITE + '/hi/']
API = 'https://searchconsole.googleapis.com'
BATCH = 24


def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                   encoding='utf-8')
    tmp.replace(path)


def crawl(url):
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=Retry(
            total=2, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods={'GET'}, respect_retry_after_header=False)))
        return session.get(url, timeout=(6, 15), allow_redirects=False,
                           headers={'User-Agent': 'GlobeWireDaily SEO audit'})


def live_audit(state, slot):
    def read(path):
        response = crawl(SITE + path)
        if response.status_code != 200:
            raise ValueError(f'{path}: HTTP {response.status_code}')
        return response.content

    urls, news, errors = read_sitemaps(read, SITE)
    articles = sorted(u for u in urls if len(urlsplit(u).path.split('/')) == 6
                      and '/news/' in u)
    cursor = state.get('sample_start') if state.get('slot') == slot else state.get('cursor')
    start = (cursor if cursor is not None else slot * BATCH) % max(len(articles), 1)
    batch = (articles + articles)[start:start + min(BATCH, len(articles))]
    # Include the counterpart of each sampled article when it is indexable.
    counterparts = {u.replace('/en/', '/hi/', 1) if '/en/news/' in u
                    else u.replace('/hi/', '/en/', 1) for u in batch}
    sample = sorted(set(HOMES + batch) | (counterparts & urls))

    for path in ('/en/', '/hi/?seo-audit=1', urlsplit(batch[0]).path if batch else '/en/'):
        response = crawl('https://www.globewiredaily.org' + path)
        if response.status_code not in (301, 308) or response.headers.get('Location') != SITE + path:
            errors.append(f'www redirect failed for {path}: HTTP {response.status_code}')
    root = crawl(SITE + '/')
    if root.status_code not in (301, 308) or root.headers.get('Location') not in ('/en/', HOMES[0]):
        errors.append(f'Root redirect failed: HTTP {root.status_code}')
    robots = read('/robots.txt').decode('utf-8')
    for url in (SITE + '/sitemap.xml', SITE + '/news-sitemap.xml'):
        if f'Sitemap: {url}' not in robots.splitlines():
            errors.append(f'Sitemap missing from robots.txt: {url}')
    rules = RobotFileParser()
    rules.parse(robots.splitlines())
    for url in sample:
        if not rules.can_fetch('Googlebot', url):
            errors.append(f'Blocked for Googlebot: {url}')
    unknown = crawl(SITE + '/en/seo-recovery-missing-91bfa2d8/')
    if unknown.status_code != 404:
        errors.append(f'Missing page returns HTTP {unknown.status_code}')

    def check(url):
        try:
            response = crawl(url)
            if response.status_code != 200:
                return [f'{url}: HTTP {response.status_code}'], None
            page_errors, alternates = audit_page(url, response.text, urls)
            if 'noindex' in response.headers.get('X-Robots-Tag', '').lower():
                page_errors.append(f'Noindex HTTP header: {url}')
            return page_errors, alternates
        except requests.RequestException as exc:
            return [f'{url}: {type(exc).__name__}'], None

    with ThreadPoolExecutor(max_workers=6) as pool:
        findings = dict(zip(sample, pool.map(check, sample)))
    for url, (page_errors, alternates) in findings.items():
        errors.extend(page_errors)
        lang = urlsplit(url).path.split('/')[1]
        for target in set((alternates or {}).values()):
            if target in findings and findings[target][1] is not None and findings[target][1].get(lang) != url:
                errors.append(f'Non-reciprocal hreflang: {url} -> {target}')
    if articles:
        state.update(slot=slot, sample_start=start, cursor=(start + len(batch)) % len(articles))
    return {'sample': sample, 'sitemap_urls': len(urls), 'news_urls': len(news),
            'errors': errors, 'sample_start': start}


def story_audit(posts_dir):
    posts, categories, invalid = [], [], []
    for path in sorted(posts_dir.glob('*.json')):
        try:
            post = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(post, dict) or not post.get('id'):
                raise ValueError('Missing article ID')
            if not isinstance(post.get('en_body'), str) or len(post['en_body']) < 150:
                raise ValueError('Missing or short English article')
            if not str(post.get('source', '')).startswith('https://'):
                raise ValueError('Missing HTTPS source')
            normalized = normalize_post(post)
        except (OSError, ValueError, TypeError) as exc:
            invalid.append({'file': path.name, 'reason': str(exc)})
            continue
        posts.append(normalized)
        old, new = post.get('category'), normalized.get('category')
        if old != new or old not in CATEGORIES:
            categories.append({'id': post['id'], 'from': old, 'to': new, 'signal': 'editorial routing'})
        elif old in ('sports', 'cricket'):
            subject = route_category(post.get('en_title', ''), old)
            if subject not in ('sports', 'cricket'):
                categories.append({'id': post['id'], 'from': old, 'to': subject,
                                   'signal': 'headline conflicts with sports source'})
    _, duplicates = collapse_posts(posts)
    return {'valid_records': len(posts), 'invalid_records': invalid,
            'duplicate_candidates': [{'id': old['id'], 'canonical_id': keep['id']}
                                     for old, keep in duplicates],
            'category_candidates': categories}


def ctr_candidates(rows):
    candidates = []
    for row in rows:
        query, page = row['keys']
        url = urlsplit(page)
        if url.hostname not in ('globewiredaily.org', 'www.globewiredaily.org'):
            continue
        if len(url.path.split('/')) != 6 or not url.path.startswith(('/en/news/', '/hi/news/')):
            continue
        if 'globewire' in query.casefold() or row['impressions'] < 50 or not 1 <= row['position'] <= 20:
            continue
        # Triage thresholds are fractions, grouped by average search position.
        position = row['position']
        floor = 0.03 if position <= 3 else 0.01 if position <= 10 else 0.003
        if row['ctr'] < floor:
            candidates.append({**row, 'canonical_candidate': SITE + url.path,
                               'ctr_floor': floor,
                               'priority': round(row['impressions'] * (floor - row['ctr']), 3)})
    return sorted(candidates, key=lambda r: (-r['priority'], r['keys']))[:100]


def gsc_audit(credentials, end, sample):
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2.service_account import Credentials

    auth = Credentials.from_service_account_info(
        json.loads(credentials), scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    endpoint = f'{API}/webmasters/v3/sites/{quote(PROPERTY, safe="")}/searchAnalytics/query'
    start = end - timedelta(days=27)
    window = {'startDate': start.isoformat(), 'endDate': end.isoformat(),
              'type': 'web', 'dataState': 'final'}
    with AuthorizedSession(auth) as session:
        def request(url, data):
            response = session.post(url, json=data, timeout=(6, 20))
            response.raise_for_status()
            return response.json()

        series = request(endpoint, {**window, 'dimensions': ['date']}).get('rows', [])
        rows = []
        limit = 2500
        for offset in range(0, 10000, limit):
            page = request(endpoint, {**window, 'dimensions': ['query', 'page'],
                                      'rowLimit': limit, 'startRow': offset}).get('rows', [])
            rows.extend(page)
            if len(page) < limit:
                break
        inspections = {}
        for url in HOMES + [u for lang in ('en', 'hi') for u in
                            [next((x for x in sample if x.startswith(SITE + f'/{lang}/news/')), None)]
                            if u]:
            payload = request(f'{API}/v1/urlInspection/index:inspect',
                              {'siteUrl': PROPERTY, 'inspectionUrl': url})
            inspections[url] = payload['inspectionResult']['indexStatusResult']
    def totals(last_day):
        first_day = last_day - timedelta(days=6)
        days = [row for row in series if first_day.isoformat() <= row['keys'][0] <= last_day.isoformat()]
        clicks = sum(row['clicks'] for row in days)
        impressions = sum(row['impressions'] for row in days)
        return {'start': first_day.isoformat(), 'end': last_day.isoformat(),
                'clicks': clicks, 'impressions': impressions,
                'ctr': clicks / impressions if impressions else None,
                'position': sum(row['position'] * row['impressions'] for row in days) / impressions
                if impressions else None}

    return {'status': 'ok', 'window': window, 'daily': series, 'inspections': inspections,
            'latest_week': totals(end), 'prior_week': totals(end - timedelta(days=7)),
            'ctr_candidates': ctr_candidates(rows), 'rows_scanned': len(rows),
            'scan_cap_reached': len(rows) == 10000}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--posts', type=Path, default=Path('content/posts'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output / 'checkpoint.json'
    state = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    now = datetime.now(ZoneInfo('America/Los_Angeles'))
    end = (now - timedelta(days=3)).date()
    try:
        live = live_audit(state, int(now.timestamp()) // 21600)
    except (requests.RequestException, ValueError) as exc:
        live = {'errors': [str(exc)], 'sample': []}
    stories = story_audit(args.posts)
    credentials = os.environ.get('SEO_GSC_SERVICE_ACCOUNT_JSON')
    report_key = os.environ.get('SEO_GSC_REPORT_KEY')
    gsc_status = 'Search Console credentials are absent'
    private_report = args.output / 'search-console.json.fernet'
    private_report.unlink(missing_ok=True)
    if credentials:
        from cryptography.fernet import Fernet
        from google.auth.exceptions import GoogleAuthError

        if not report_key:
            gsc_status = 'error: Search Console report encryption key is absent'
        else:
            try:
                cipher = Fernet(report_key.encode('ascii'))
                gsc = gsc_audit(credentials, end, live['sample'])
                private_report.write_bytes(cipher.encrypt(json.dumps(gsc, ensure_ascii=False).encode()))
                gsc_status = 'encrypted report generated'
            except (requests.RequestException, ValueError, KeyError, GoogleAuthError) as exc:
                gsc_status = 'error: ' + type(exc).__name__
    write_json(checkpoint, state)
    write_json(args.output / 'audit.json', {'live': live, 'stories': stories,
                                           'search_console': gsc_status})
    public_summary = {key: value for key, value in live.items() if key not in ('sample', 'errors')}
    print(json.dumps({'live': {**public_summary, 'sample_size': len(live['sample']),
                              'errors': live['errors'][:15]},
                      'stories': {key: len(value) if isinstance(value, list) else value
                                  for key, value in stories.items()},
                      'search_console': gsc_status}, ensure_ascii=False))
    return bool(live['errors'] or gsc_status.startswith('error:') or not stories['valid_records'])


if __name__ == '__main__':
    raise SystemExit(main())
