"""Shared, conservative identities for publisher URLs and news headlines."""
from functools import lru_cache
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

STOPWORDS = set('the and for with from this that after over into says said news latest update updates today india indian a an of to in on at is are as by has have breaking world video videos live watch exclusive'.split())

@lru_cache(maxsize=8192)
def canonical_lead_key(url):
    if not url:
        return ''
    parsed = urlsplit(str(url))
    host = parsed.netloc.lower().removeprefix('www.')
    # BBC uses the same article identifiers on its domestic and global domains.
    if host == 'm.gsmarena.com':
        host = 'gsmarena.com'
    if host == 'bbc.co.uk':
        host = 'bbc.com'
    path = re.sub(r'/amp/?$', '', parsed.path).rstrip('/')
    query = sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                   if not (k.lower().startswith('utm_') or k.lower() in
                           {'fbclid', 'gclid', 'at_medium', 'at_campaign'}))
    # Keep document identity parameters (id, article, page, etc.).
    return urlunsplit(('https', host, path, urlencode(query), ''))

def headline_key(value):
    text = unicodedata.normalize('NFKC', str(value or '')).casefold()
    return ' '.join(re.findall(r'[^\W_]+', text, flags=re.UNICODE))

@lru_cache(maxsize=16384)
def story_tokens(value):
    return frozenset(w for w in headline_key(value).split() if len(w) > 2 and w not in STOPWORDS)

def same_story(a, b):
    x, y = story_tokens(a), story_tokens(b)
    if min(len(x), len(y)) < 4 or min(len(x), len(y)) / max(len(x), len(y)) < .7:
        return False
    # Scores, model names, years and counts can distinguish real new stories.
    if set(re.findall(r'\d+', str(a))) != set(re.findall(r'\d+', str(b))):
        return False
    # A scheduled hearing and its eventual ruling are separate developments.
    pending = r'\b(?:to hear|will hear|hearing scheduled|set to hear)\b'
    decision = r'\b(?:orders?|ordered|rules?|ruled|surrender|verdict|revokes?|revoked)\b'
    if ((re.search(pending, str(a), re.I) and re.search(decision, str(b), re.I)) or
        (re.search(pending, str(b), re.I) and re.search(decision, str(a), re.I))):
        return False
    common = len(x & y)
    return common >= 4 and (common / min(len(x), len(y)) >= .86 or common / len(x | y) >= .72)

def collapse_posts(posts):
    """Keep source records intact; return canonical posts and redirect pairs."""
    sources, headlines, keep, duplicates = {}, {}, [], []
    for post in sorted(posts, key=lambda p: (len(p.get('en_body', '')), p.get('date', '')), reverse=True):
        source = canonical_lead_key(post.get('source', ''))
        headline = headline_key(post.get('en_title', ''))
        existing = sources.get(source) if source else None
        existing = existing or (headlines.get(headline) if headline else None)
        if existing:
            duplicates.append((post, existing))
        else:
            keep.append(post)
            if source:
                sources[source] = post
            if headline:
                headlines[headline] = post
    return keep, duplicates
