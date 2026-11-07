"""Official housing/development authority discovery; no guessed district domains.

Catalogs expand the registry nationwide. GDA/GIDA are checked every pass;
other authorities rotate to keep the existing publisher's HTTP budget bounded.
"""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from authority_registry import REGIONAL_BOARDS, NATIONAL_CATALOGS, SCOPED_HOSTS

ROOT = Path(__file__).resolve().parents[1]
BOARD_EVIDENCE = {}
CATALOGS = (
    'https://www.awasbandhu.in/en/pages/authority',
    'https://igod.gov.in/sector/DBNsIHQBsvhI6u6Q3tju/organizations',
    'https://lsg.urban.rajasthan.gov.in/content/raj/udh/udh-department/en/DA-UIT.html',
)
# Website addresses linked by Awas Bandhu plus current official housing boards.
SEEDS = (
    'https://gdagkp.in/', 'https://gidagkp.in/',
    'https://upavp.in/', 'https://adaagra.org.in/', 'https://adaligarh.in/',
    'https://ayodhyada.in/', 'https://www.adaazamgarh.in/',
    'https://bbkdabaghpat.org/', 'https://www.bdabanda.in/',
    'https://www.bdainfo.org/', 'https://www.bdabasti.in/',
    'https://www.bdabulandshahar.in/', 'https://fsdafirozabad.com/',
    'https://gdaghaziabad.in/', 'https://hpdaonline.in/', 'https://jdaup.in/',
    'https://www.kdaindia.co.in/', 'https://kdakhurja.in/',
    'https://ldalucknow.in/', 'https://fa.mvdapms.com/',
    'https://www.mdameerut.in/', 'https://odaorai.com/',
    'https://pdaprayagraj.in/', 'https://rdaup.in/', 'https://rdarampur.com/',
    'https://sdasaharanpur.in/', 'https://usdaunnao.in/', 'https://vdavns.com/',
    'https://ksadakushinagar.in/', 'https://ssada.in/',
    'https://dda.gov.in/housing/housing-scheme',
    'https://dda.gov.in/whats-new', 'https://mhada.gov.in/en/lottery',
    'https://mhada.gov.in/en/latest-news',
    'https://cidco.maharashtra.gov.in/home/Marketing',
    'https://tnhb.tn.gov.in/all-notifications',
    'https://hbh.gov.in/e-Auction', 'https://hbh.gov.in/BookingForNewSchemes',
    'https://rhb.rajasthan.gov.in/',
)
AUTHORITY = re.compile(r'housing|development authority|improvement trust|industrial(?: areas?| infrastructure)? development|urban (?:development|affairs)|town(?: and country)? planning|real estate regulatory|आवास|विकास प्राधिकरण', re.I)
UPDATE = re.compile(r'\b(?:flats?|plots?|housing|allotment|auction|lottery|registration|tenders?|corrigendum|notification|public notice|press release|land acquisition|master plan|scheme|brochure|EOI|RFP|NIT)\b|फ्लैट|भूख[णं]्ड|भूखण्ड|भूखंड|आवास|पंजीकरण|निविदा|नीलामी|आवंटन|लाटरी|लॉटरी|अधिसूचना|संशोधन|सूचना|योजना|विज्ञप्ति', re.I)
TENDER = re.compile(r'\b(?:tender|corrigendum|EOI|RFP|NIT)\b|निविदा', re.I)
GENERIC = re.compile(r'^(?:home|view(?: all| more)?|click here|read more|news|news and events|tenders?|public notices?|registration|online registration|lottery results?|contact us|about us|login|schemes?|हिंदी|होम)$', re.I)

def public_url(value):
    p = urlparse(str(value))
    host = (p.hostname or '').lower()
    try:
        port = p.port
    except ValueError:
        return ''
    if p.scheme not in ('https', 'http') or not host or p.username or p.password or port not in (None, 80, 443):
        return ''
    if '.' not in host.removeprefix('www.') or host.endswith(('.local', '.localhost', '.internal')):
        return ''
    try:
        if not ipaddress.ip_address(host).is_global:
            return ''
    except ValueError:
        pass
    return urlunparse(p._replace(scheme='https', fragment=''))

def host(url):
    return (urlparse(url).hostname or '').lower().removeprefix('www.')

def cache_path(root=ROOT):
    return Path(root) / 'content/pending/_authority_sources.json'

def saved_registry(root=ROOT):
    try:
        cache = json.loads(cache_path(root).read_text(encoding='utf-8'))
        return cache if isinstance(cache, dict) else {}
    except (OSError, ValueError):
        return {}

def registry_urls(root=ROOT):
    regional = {u for urls in REGIONAL_BOARDS.values() for u in urls}
    return sorted(set(SEEDS) | regional | {u for u in saved_registry(root).get('urls', []) if isinstance(u, str) and public_url(u)})

def authority_url(url, root=ROOT):
    if not public_url(url) or host(url) not in {host(u) for u in registry_urls(root)}:
        return False
    scopes = SCOPED_HOSTS.get(host(url))
    return not scopes or any(urlparse(url).path.startswith(prefix) for prefix in scopes)

def catalog_urls(markup, base):
    """Only authority rows in a named official directory can add external hosts."""
    found = set()
    for a in BeautifulSoup(markup, 'html.parser').select('a[href]'):
        target = public_url(urljoin(base, a['href']))
        row = a.find_parent('tr') or a.find_parent('li') or a.parent
        text = ' '.join((a.get_text(' ', strip=True), a.get('title', ''), row.get_text(' ', strip=True)))
        # Awas Bandhu's authority table uses city names and a 'View' label.
        relevant = bool(AUTHORITY.search(text)) or (host(base) == 'awasbandhu.in' and row.name == 'tr')
        if target and relevant and host(target) != host(base):
            found.add(target)
    return sorted(found)

def catalog_links(markup, base):
    """Follow only links actually published by IGOD: regions, lists and pagination."""
    if host(base) != 'igod.gov.in':
        return []
    found = set()
    current = urlparse(base).path.removeprefix('/index.php')
    for a in BeautifulSoup(markup, 'html.parser').select('a[href]'):
        url = public_url(urljoin(base, a['href']))
        if not url or host(url) != 'igod.gov.in':
            continue
        path = urlparse(url).path.removeprefix('/index.php')
        row = a.find_parent('li') or a.find_parent('tr') or a.parent
        text = row.get_text(' ', strip=True)
        region = re.fullmatch(r'/sg/[A-Za-z]{2}/(?:categories|(?:E003|E011|E051)/organizations)/?', path)
        detail = path.startswith('/organization/') and AUTHORITY.search(text)
        pagination = path == current and url != base and (a.get('rel') or a.find_parent(class_=re.compile('pagin', re.I)) or re.fullmatch(r'\d+|next|»|›', a.get_text(strip=True), re.I))
        if region or detail or pagination:
            found.add(url)
    return sorted(found)

def refresh_catalogs(fetch, cache, root, now, budget=6):
    urls = set(registry_urls(root))
    known = set(CATALOGS) | set(NATIONAL_CATALOGS) | set(cache.get('catalog_urls', []))
    checks = dict(cache.get('catalog_checks', {}))
    due = [u for u in known if now - checks.get(u, {}).get('checked_at', 0) > (86400 if checks.get(u, {}).get('status') == 'ok' else 3600)]
    # Oldest/unseen first. A failing catalog advances rather than starving all
    # other states; its published sources remain available during the outage.
    due.sort(key=lambda u: (checks.get(u, {}).get('checked_at', 0), u not in CATALOGS, u))
    def read(catalog):
        status = 'unavailable'; added = 0
        discovered = []; links = []
        try:
            markup, final, _ = fetch(catalog, timeout=(3, 6), max_bytes=1_000_000)
            if markup and host(final) == host(catalog):
                discovered = catalog_urls(markup, final)
                added = len(discovered)
                links = catalog_links(markup, final)
                status = 'ok'
        except Exception as exc:
            print('AUTHORITY_CATALOG_UNAVAILABLE', host(catalog), type(exc).__name__, flush=True)
        return catalog, status, added, discovered, links
    with ThreadPoolExecutor(max_workers=3) as pool:
        for catalog, status, added, discovered, links in pool.map(read, due[:max(0, budget)]):
            urls.update(discovered)
            known.update(links)
            checks[catalog] = {'checked_at': now, 'status': status, 'discovered': added}
    return dict(cache, checked_at=now, urls=sorted(urls), catalog_urls=sorted(known), catalog_checks=checks)

def authority_boards(fetch, root=ROOT, now=None, limit=14, refresh=True):
    now = dt.datetime.now(dt.timezone.utc).timestamp() if now is None else now
    cache = saved_registry(root)
    if refresh:
        cache = refresh_catalogs(fetch, cache, root, now)
    urls = set(registry_urls(root)) | set(cache.get('urls', []))
    pinned = list(SEEDS[:2])[:max(0, limit)]
    rest = sorted(urls - set(pinned))
    count = min(max(0, limit - len(pinned)), len(rest))
    # Persist progress; wall-clock strides could permanently skip boards when
    # the scheduled interval and registry length shared a common divisor.
    start = int(cache.get('board_cursor', 0)) % max(1, len(rest))
    chosen = pinned + [rest[(start + i) % len(rest)] for i in range(count)]
    cache.update(urls=sorted(urls), board_cursor=(start + count) % max(1, len(rest)))
    path = cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2) + '\n', encoding='utf-8')
    print('AUTHORITY_SOURCE_REGISTRY', len(urls), 'boards;', len(chosen), 'selected', flush=True)
    return [(u, 'government-schemes', host(u)) for u in chosen]

def authority_category(title):
    if re.search(r'\b(?:recruitment|vacanc\w*|admit card|exam)\b|भर्ती|परीक्षा', title, re.I):
        return 'sarkari-naukri'
    return 'india-news' if TENDER.search(title) else 'government-schemes'

def save_board_evidence(root=ROOT):
    path = cache_path(root).with_name('_authority_notice_evidence.json')
    try:
        old = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = {}
    old.update(BOARD_EVIDENCE)
    if BOARD_EVIDENCE:
        old = dict(sorted(old.items(), key=lambda item: item[1].get('checked_at', 0), reverse=True)[:3000])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(old, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def board_evidence(url, root=ROOT):
    """An issuing authority's long public statement can support an unreadable scan.

    Short link titles never qualify as document evidence.
    """
    if not authority_url(url, root):
        return ''
    row = BOARD_EVIDENCE.get(url)
    if row is None:
        try:
            row = json.loads(cache_path(root).with_name('_authority_notice_evidence.json').read_text(encoding='utf-8')).get(url, {})
        except (OSError, ValueError):
            row = {}
    text = row.get('text', '')
    try:
        age = dt.datetime.now(dt.timezone.utc).timestamp() - float(row.get('checked_at', 0))
    except (ValueError, TypeError):
        return ''
    if age > 86400 or not 0 <= age or len(text) < 300 or len(text.split()) < 65:
        return ''
    return ('Official notice-board statement (PDF contents not verified). Board: '
            + row['board'] + '\n' + text)

def parse_authority_board(markup, base, limit=20):
    """Keep document query strings; generic menus and external login links are not news."""
    soup = BeautifulSoup(markup, 'html.parser')
    for node in soup.select('header,footer,nav,script,style,form'):
        node.decompose()
    rows = []; seen = set()
    for a in soup.select('a[href]')[:1500]:
        url = public_url(urljoin(base, a['href']))
        title = ' '.join(a.get_text(' ', strip=True).split())
        if GENERIC.fullmatch(title) or len(title) < 20:
            parent = a.find_parent(['li', 'tr', 'p'])
            title = ' '.join(parent.get_text(' ', strip=True).split()) if parent else title
        if not url or host(url) != host(base) or url == base or url in seen:
            continue
        if not 24 <= len(title) <= 1600 or GENERIC.fullmatch(title) or not UPDATE.search(title):
            continue
        if re.search(r'/(?:login|contact|about|privacy|search)(?:/|$)', urlparse(url).path, re.I):
            continue
        seen.add(url)
        BOARD_EVIDENCE[url] = {'board': base, 'text': title,
                               'checked_at': dt.datetime.now(dt.timezone.utc).timestamp()}
        rows.append((url, title[:210], authority_category(title), host(url)))
        if len(rows) >= limit:
            break
    return rows

def authority_stories(item, fetch):
    try:
        markup, final, _ = fetch(item[0], timeout=(4, 8), max_bytes=1_000_000)
        rows = parse_authority_board(markup, final) if host(final) == item[2] else []
        # Some homepages contain only generic links to their real notice boards.
        # Follow published same-host section URLs, never invent /news endpoints.
        if markup and host(final) == item[2] and len(rows) < 8:
            children = []
            for a in BeautifulSoup(markup, 'html.parser').select('a[href]')[:1000]:
                url = public_url(urljoin(final, a['href']))
                label = a.get_text(' ', strip=True)
                if not url or host(url) != item[2] or url == final or url in children:
                    continue
                if re.search(r'\.(?:pdf|jpg|jpeg|png|zip)$|/(?:login|contact|about|privacy)(?:/|$)', urlparse(url).path, re.I):
                    continue
                if len(label) <= 70 and re.search(r'notice|news|tender|press|scheme|auction|notification|circular|whats.?new|निविदा|सूचना|समाचार|योजना', label, re.I):
                    children.append(url)
                if len(children) == 2:
                    break
            for child in children:
                try:
                    child_html, child_final, _ = fetch(child, timeout=(3, 6), max_bytes=1_000_000)
                    if host(child_final) == item[2]:
                        rows.extend(parse_authority_board(child_html, child_final))
                except Exception as exc:
                    print('AUTHORITY_SECTION_UNAVAILABLE', item[2], type(exc).__name__, flush=True)
            rows = list({row[0]: row for row in rows}.values())[:20]
        print('AUTHORITY_BOARD', item[2], len(rows), 'candidates', flush=True)
        return rows
    except Exception as exc:
        print('AUTHORITY_BOARD_UNAVAILABLE', item[2], type(exc).__name__, flush=True)
        return []
