import os, sys, json, hashlib, datetime as dt, pathlib, re, time, html
import requests, feedparser
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS = ROOT / 'content' / 'posts'
POSTS.mkdir(parents=True, exist_ok=True)
FEEDS = ['https://blog.cloudflare.com/rss/', 'https://blog.google/rss/']
PREFERRED_MODELS = [m.strip() for m in os.getenv('GEMINI_MODELS', 'gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.5-flash,gemini-3.6-flash,gemini-3.8-flash').split(',') if m.strip()]
MAX_MODELS_PER_ARTICLE = max(1, min(200, int(os.getenv('MAX_MODELS_PER_ARTICLE', '100'))))
MODEL_CACHE = None

def discover_models(api_key):
    global MODEL_CACHE
    if MODEL_CACHE is not None:
        return MODEL_CACHE
    discovered = []
    url = 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000'
    try:
        for _ in range(5):
            response = requests.get(url, headers={'x-goog-api-key': api_key}, timeout=(10, 25))
            response.raise_for_status()
            result = response.json()
            for item in result.get('models', []):
                name = item.get('name', '').removeprefix('models/')
                methods = item.get('supportedGenerationMethods', [])
                # Only text-oriented Gemini generation models. No image, audio, TTS, embedding, or experimental tools.
                if ('generateContent' in methods and name.startswith('gemini-')
                        and not any(x in name.lower() for x in ('image', 'tts', 'audio', 'embedding', 'robotics', 'computer-use', 'live', 'native', 'transcribe', 'translate', 'video', 'omni'))):
                    discovered.append(name)
            token = result.get('nextPageToken')
            if not token:
                break
            url = 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000&pageToken=' + requests.utils.quote(token)
        # Prefer lower-cost Flash/Lite families, then other compatible models.
        def priority(name):
            return (0 if 'flash-lite' in name else 1 if 'flash' in name else 2, name)
        ordered = [m for m in PREFERRED_MODELS if m in discovered]
        ordered.extend(m for m in sorted(set(discovered), key=priority) if m not in ordered )
        # All compatible text models are discoverable. A free-tier project may reject some.
        # No request is made to a model unless earlier models fail.
        MODEL_CACHE = ordered
        print('Discovered compatible models:', len(ordered), flush=True)
    except (requests.RequestException, ValueError) as exc:
        print('Model discovery failed:', type(exc).__name__, str(exc)[:180], flush=True)
        # Do not blindly probe models when discovery or authentication fails.
        MODEL_CACHE = []
    return MODEL_CACHE

LIMIT = int(os.getenv('DAILY_LIMIT', '11'))
UTC = dt.timezone.utc

def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(value or '')))).strip()

def today_count():
    day = dt.datetime.now(UTC).date().isoformat()
    total = 0
    for path in POSTS.glob('*.json'):
        try:
            if json.loads(path.read_text(encoding='utf-8')).get('date', '')[:10] == day:
                total += 1
        except (ValueError, OSError):
            pass
    return total

def generate(api_key, title, excerpt, source):
    prompt = f'''You are a careful bilingual technology news editor. Use ONLY facts in the supplied official source article. Explain context and implications only when supported. Structure each language body with 4-6 informative sections using headings on separate lines prefixed ##. Include what happened, key details, why it matters, availability or limitations if sourced, and practical implications if supported. Include a useful factual opening and key takeaways. Never fabricate quotes, dates, availability, prices, or benchmarks. No speculation, invented facts, fabricated quotations or unsourced claims. Attribute source claims clearly. If the excerpt does not contain enough verifiable information for an informative article, return {{}}. Do NOT pad length. Return JSON with these string fields: en_title, hi_title, en_body, hi_body, en_meta, hi_meta, en_keywords, hi_keywords. Bodies must be plain text with paragraphs separated by blank lines, factual and detailed when supported; prefer a substantive 500-900 word English explanation when the source contains enough distinct verified facts; do not repeat, invent, or pad. If facts are limited, write a shorter accurate article. Hindi should communicate equivalent facts. Titles should be clear and descriptive, not clickbait. Meta descriptions 120-160 characters when feasible. Keywords should be comma-separated relevant phrases, not spam. Never say you independently fact-checked. SOURCE URL: {source}\nSOURCE TITLE: {title}\nSOURCE ARTICLE TEXT: {excerpt[:16000]}'''
    payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 8192}}
    models = discover_models(api_key)
    if not models:
        print('No compatible models discovered; check API key/project.', flush=True)
        return None
    for model in models[:MAX_MODELS_PER_ARTICLE]:
        print('Trying Gemini model:', model, flush=True)
        try:
            resp = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', headers={'x-goog-api-key': api_key}, json=payload, timeout=(10, 65))
            if not resp.ok:
                print('Model HTTP', resp.status_code, resp.text[:200], flush=True)
                if resp.status_code == 429 and 'quota' in resp.text.lower():
                    print('Quota limit reached; stopping this article to avoid waste', flush=True)
                    return None
                if resp.status_code in (401, 403):
                    print('Authentication/billing restriction; stopping attempts', flush=True)
                    return None
                continue
            raw = resp.json()['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(raw)
            required = ('en_title', 'hi_title', 'en_body', 'hi_body')
            if not isinstance(data, dict) or any(not isinstance(data.get(k), str) or len(data[k].strip()) < 30 for k in required):
                print('Incomplete article; skipping', flush=True)
                continue
            print('Gemini model succeeded:', model, flush=True)
            return data
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            print('Model failed:', type(exc).__name__, str(exc)[:150], flush=True)
    return None

def fetch_source(url):
    """Extract official article text; external images are not reused without license."""
    try:
        response = requests.get(url, timeout=(8, 22), headers={'User-Agent': 'Mozilla/5.0 (compatible; GlobalTechDaily/1.0)'})
        response.raise_for_status()
        if 'html' not in response.headers.get('Content-Type', 'text/html'): return '', ''
        soup = BeautifulSoup(response.text[:1500000], 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'form']): tag.decompose()
        main = soup.find('article') or soup.find('main') or soup
        chunks = [clean(t.get_text(' ', strip=True)) for t in main.find_all(['h2', 'h3', 'p', 'li'])]
        text = '\n'.join(t for t in chunks if len(t) > 35)
        return text[:18000], ''
    except (requests.RequestException, ValueError) as exc:
        print('Source extraction unavailable:', type(exc).__name__, flush=True)
        return '', ''

def main():
    if os.getenv('AUTO_POST', 'false').lower() != 'true':
        print('AUTO_POST disabled'); return 0
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        print('GEMINI_API_KEY missing'); return 1
    remaining = max(0, LIMIT - today_count())
    print('Remaining daily allowance:', remaining, flush=True)
    if remaining == 0: return 0
    created = 0
    for feed in FEEDS:
        try:
            response = requests.get(feed, timeout=25, headers={'User-Agent': 'GlobalTechDailyBot/1.0'})
            response.raise_for_status()
            entries = feedparser.parse(response.content).entries
            print('Feed', feed, 'entries:', len(entries), flush=True)
        except requests.RequestException as exc:
            print('RSS unavailable:', str(exc)[:160]); continue
        for entry in entries[:30]:
            if created >= remaining: break
            url = entry.get('link', '').strip()
            if not url.startswith('https://'): continue
            post_id = hashlib.sha256(url.encode()).hexdigest()[:12]
            path = POSTS / (post_id + '.json')
            if path.exists(): continue
            pub = entry.get('published_parsed') or entry.get('updated_parsed')
            if not pub: continue
            age = (dt.datetime.now(UTC).date() - dt.date(*pub[:3])).days
            if not 0 <= age <= 7: continue
            excerpt = clean(entry.get('summary', '') or entry.get('description', ''))
            article_text, image_url = fetch_source(url)
            if len(article_text) > len(excerpt): excerpt = article_text
            if len(excerpt) < 160: continue
            print('Processing:', clean(entry.get('title'))[:90], flush=True)
            article = generate(api_key, clean(entry.get('title')), excerpt, url)
            if not article: continue
            article.update(id=post_id, source=url, date=dt.datetime.now(UTC).isoformat(), source_title=clean(entry.get('title')), source_image=image_url)
            path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding='utf-8')
            created += 1
            print('Saved article', created, post_id, flush=True)
            time.sleep(2)
        if created >= remaining: break
    print('Published', created, flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())
