import os, sys, json, hashlib, datetime as dt, pathlib, re, time, html
import requests, feedparser
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS = ROOT / 'content' / 'posts'
POSTS.mkdir(parents=True, exist_ok=True)
# Curated public/official feeds; a feed is only a discovery mechanism, not proof.
FEED_SOURCES = [
 ('https://blog.google/rss/', 'technology'),
 ('https://blog.cloudflare.com/rss/', 'technology'),
 ('https://www.cisa.gov/cybersecurity-advisories/all.xml', 'technology'),
 ('https://www.nasa.gov/feed/', 'technology'),
]
FEEDS = FEED_SOURCES
SCHEME_WORDS = ('scheme','yojana','subsidy','beneficiary','welfare','pension','pm-kisan','scholarship','आवास','योजना','सब्सिडी','पेंशन')
JOB_WORDS = ('recruitment','vacancy','notification','application','exam','admit card','results','upsc','ssc','rrb','भर्ती','रिक्ति','परीक्षा','नौकरी')
def categorize(headline, default):
    t = headline.lower()
    if any(w in t for w in JOB_WORDS): return 'sarkari-naukri'
    if any(w in t for w in SCHEME_WORDS): return 'government-schemes'
    return default

PREFERRED_MODELS = [m.strip() for m in os.getenv('GEMINI_MODELS', 'gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.5-flash,gemini-3.6-flash,gemini-3.8-flash').split(',') if m.strip()]
MAX_MODELS_PER_ARTICLE = max(0, min(2, int(os.getenv('MAX_MODELS_PER_ARTICLE', '1'))))
MAX_AI_CALLS_PER_RUN = max(0, min(8, int(os.getenv('MAX_AI_CALLS_PER_RUN', '2'))))
AI_CALLS = 0
QUOTA_EXHAUSTED = set()
MAX_SOURCE_CANDIDATES = max(1, min(30, int(os.getenv('MAX_SOURCE_CANDIDATES', '8'))))
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

MIN_WORDS = max(300, int(os.getenv('MIN_ARTICLE_WORDS', '1200')))
LIMIT = int(os.getenv('DAILY_LIMIT', '10'))
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

def valid_article(data):
    return (isinstance(data, dict)
            and all(isinstance(data.get(k), str) and len(data[k].split()) >= MIN_WORDS for k in ('en_body', 'hi_body'))
            and all(isinstance(data.get(k), str) and len(data[k].strip()) >= 30 for k in ('en_title', 'hi_title')))

def alternate_provider(prompt):
    """Optional fallback. Free model availability and quotas are provider-controlled."""
    global AI_CALLS
    router_key = os.getenv('OPENROUTER_API_KEY', '').strip()
    groq_key = os.getenv('GROQ_API_KEY', '').strip()
    poll_key = os.getenv('POLLINATIONS_API_KEY', '').strip()
    providers = []
    if groq_key:
        providers.append(('Groq', 'https://api.groq.com/openai/v1/chat/completions',
                          {'Authorization': 'Bearer ' + groq_key},
                          os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')))
    if router_key:
        providers.append(('OpenRouter', 'https://openrouter.ai/api/v1/chat/completions',
                          {'Authorization': 'Bearer ' + router_key},
                          os.getenv('OPENROUTER_MODEL', 'openrouter/free')))
    # Pollinations text API can require a key; do not pretend anonymous access is guaranteed.
    if poll_key:
        providers.append(('Pollinations', 'https://gen.pollinations.ai/v1/chat/completions',
                          {'Authorization': 'Bearer ' + poll_key},
                          os.getenv('POLLINATIONS_MODEL', 'openai')))
    for name, endpoint, headers, model in providers:
        if AI_CALLS >= MAX_AI_CALLS_PER_RUN: break
        if name in QUOTA_EXHAUSTED: continue
        AI_CALLS += 1
        try:
            response = requests.post(endpoint, headers=headers,
                json={'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                      'response_format': {'type': 'json_object'}, 'max_tokens': 8500},
                timeout=(10, 100))
            if not response.ok:
                print(name, 'HTTP', response.status_code, response.text[:120], flush=True)
                if response.status_code in (401, 402, 403, 429): QUOTA_EXHAUSTED.add(name)
                continue
            content = response.json()['choices'][0]['message']['content']
            data = json.loads(content)
            if valid_article(data):
                print(name, 'model succeeded:', model, flush=True)
                return data
            print(name, 'response below minimum or invalid', flush=True)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            print(name, 'failed:', type(exc).__name__, str(exc)[:140], flush=True)
    return None

def generate(api_key, title, excerpt, source, category):
    prompt = f'''You are an experienced bilingual editor. Produce an original, carefully attributed, helpful, detailed public-information article based ONLY on the verified supplied source text. Category: {category}. Source URL: {source}. Headline: {title}. Source material: {excerpt[:24000]}.
Return ONLY JSON fields en_title, hi_title, en_body, hi_body, en_meta, hi_meta, en_keywords, hi_keywords. Write in English and Hindi, independently natural, with ## section headings and actionable but accurate explanations. Each language article MUST contain at least {MIN_WORDS} words of distinct, source-supported information. Never invent dates, eligibility, salaries, deadlines, vacancy counts, links, quotes, tests, prices, application procedures, or results. Do not repeat or pad to reach length. If the source lacks enough verified detail for {MIN_WORDS} substantive words in BOTH languages, return {{}} instead of publishing. Explicitly distinguish confirmed facts from unknowns; link to original source. For government jobs, avoid implying an official notice exists unless the source provides one; never invent application links. No plagiarized passages.'''
    global AI_CALLS
    payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 9000}}
    models = discover_models(api_key) if api_key and 'Gemini' not in QUOTA_EXHAUSTED and MAX_MODELS_PER_ARTICLE else []
    if not models:
        print('No Gemini models available; trying configured alternatives.', flush=True)
        return alternate_provider(prompt)
    for model in models[:MAX_MODELS_PER_ARTICLE]:
        if AI_CALLS >= MAX_AI_CALLS_PER_RUN: break
        AI_CALLS += 1
        print('Trying Gemini model:', model, flush=True)
        try:
            resp = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', headers={'x-goog-api-key': api_key}, json=payload, timeout=(10, 65))
            if not resp.ok:
                print('Model HTTP', resp.status_code, resp.text[:200], flush=True)
                if resp.status_code == 429 and 'quota' in resp.text.lower():
                    print('Quota limit reached; stopping this article to avoid waste', flush=True)
                    QUOTA_EXHAUSTED.add('Gemini')
                    return alternate_provider(prompt)
                if resp.status_code in (401, 403):
                    print('Authentication/billing restriction; stopping attempts', flush=True)
                    QUOTA_EXHAUSTED.add('Gemini')
                    return alternate_provider(prompt)
                continue
            raw = resp.json()['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(raw)
            required = ('en_title', 'hi_title', 'en_body', 'hi_body')
            if not isinstance(data, dict) or any(not isinstance(data.get(k), str) or len(data[k].strip().split()) < MIN_WORDS for k in required if k.endswith('_body')) or any(not isinstance(data.get(k), str) or len(data[k].strip()) < 30 for k in ('en_title','hi_title')):
                print(f'Under {MIN_WORDS} words in one or both languages; not publishing', flush=True)
                continue
            print('Gemini model succeeded:', model, flush=True)
            return data
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            print('Model failed:', type(exc).__name__, str(exc)[:150], flush=True)
    return alternate_provider(prompt)

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
    if not any(os.getenv(k, '').strip() for k in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'OPENROUTER_API_KEY', 'POLLINATIONS_API_KEY')):
        print('No provider API key configured'); return 1
    remaining = max(0, LIMIT - today_count())
    print('Remaining daily allowance:', remaining, flush=True)
    if remaining == 0: return 0
    created = 0
    candidates = 0
    for feed, default_category in FEEDS:
        try:
            response = requests.get(feed, timeout=25, headers={'User-Agent': 'GlobalTechDailyBot/1.0'})
            response.raise_for_status()
            entries = feedparser.parse(response.content).entries
            print('Feed', feed, 'entries:', len(entries), flush=True)
        except requests.RequestException as exc:
            print('RSS unavailable:', str(exc)[:160]); continue
        for entry in entries[:30]:
            if created >= remaining or AI_CALLS >= MAX_AI_CALLS_PER_RUN or candidates >= MAX_SOURCE_CANDIDATES: break
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
            candidates += 1
            print('Processing:', clean(entry.get('title'))[:90], flush=True)
            category = categorize(clean(entry.get('title')), default_category)
            article = generate(api_key, clean(entry.get('title')), excerpt, url, category)
            if not article: continue
            article.update(id=post_id, source=url, date=dt.datetime.now(UTC).isoformat(), source_title=clean(entry.get('title')), source_image=image_url, category=category, image_kind='conceptual')
            path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding='utf-8')
            created += 1
            print('Saved article', created, post_id, flush=True)
            time.sleep(2)
        if created >= remaining or AI_CALLS >= MAX_AI_CALLS_PER_RUN or candidates >= MAX_SOURCE_CANDIDATES: break
    print('AI requests used this run:', AI_CALLS, 'of', MAX_AI_CALLS_PER_RUN, flush=True)
    print('Published', created, flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())
