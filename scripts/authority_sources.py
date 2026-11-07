"""Official housing/development authority discovery; no guessed district domains.

Catalogs expand the registry nationwide. GDA/GIDA are checked every pass;
other authorities rotate to keep the existing publisher's HTTP budget bounded.
"""
import datetime as dt
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup

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
AUTHORITY = re.compile(r'housing|development authority|improvement trust|industrial development|आवास|विकास प्राधिकरण', re.I)
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
    return sorted(set(SEEDS) | {u for u in saved_registry(root).get('urls', []) if isinstance(u, str) and public_url(u)})

def authority_url(url, root=ROOT):
    return bool(public_url(url)) and host(url) in {host(u) for u in registry_urls(root)}

def catalog_urls(markup, base):
    """Only authority rows in a named official directory can add external hosts."""
    found = set()
    for a in BeautifulSoup(markup, 'html.parser').select('a[href]'):
        target = public_url(urljoin(base, a['href']))
        row = a.find_parent('tr') or a.find_parent('li') or a.parent
        text = row.get_text(' ', strip=True)
        # Awas Bandhu's authority table uses city names and a 'View' label.
        relevant = bool(AUTHORITY.search(text)) or (host(base) == 'awasbandhu.in' and row.name == 'tr')
        if target and relevant and host(target) != host(base):
            found.add(target)
    return sorted(found)

def authority_boards(fetch, root=ROOT, now=None, limit=14, refresh=True):
    now = dt.datetime.now(dt.timezone.utc).timestamp() if now is None else now
    cache = saved_registry(root)
    urls = set(registry_urls(root))
    try:
        checked = float(cache.get('checked_at', 0))
    except (ValueError, TypeError):
        checked = 0
    if refresh and now - checked > 86400:
        for catalog in CATALOGS:
            try:
                markup, final, _ = fetch(catalog, timeout=(3, 6), max_bytes=1_000_000)
                if host(final) == host(catalog):
                    urls.update(catalog_urls(markup, catalog))
            except Exception as exc:
                print('AUTHORITY_CATALOG_UNAVAILABLE', host(catalog), type(exc).__name__, flush=True)
        path = cache_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'checked_at': now, 'urls': sorted(urls)}, indent=2) + '\n', encoding='utf-8')
    pinned = list(SEEDS[:2])[:max(0, limit)]
    rest = sorted(urls - set(pinned))
    count = min(max(0, limit - len(pinned)), len(rest))
    start = (int(now // 3600) * max(1, count)) % max(1, len(rest))
    chosen = pinned + [rest[(start + i) % len(rest)] for i in range(count)]
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
        print('AUTHORITY_BOARD', item[2], len(rows), 'candidates', flush=True)
        return rows
    except Exception as exc:
        print('AUTHORITY_BOARD_UNAVAILABLE', item[2], type(exc).__name__, flush=True)
        return []
