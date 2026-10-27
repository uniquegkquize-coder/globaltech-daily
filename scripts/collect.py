import os, sys, json, hashlib, datetime as dt, pathlib, re, time, html
import requests, feedparser
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS = ROOT / 'content' / 'posts'
POSTS.mkdir(parents=True, exist_ok=True)
FEEDS = ['https://blog.cloudflare.com/rss/', 'https://blog.google/rss/']
MODELS = [m.strip() for m in os.getenv('GEMINI_MODELS', 'gemini-3.5-flash-lite,gemini-3.5-flash,gemini-3.8-flash,gemini-2.5-flash-lite').split(',') if m.strip()]
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

def generate(api_key, title, excerpt, source):
    prompt = f'''You are a careful bilingual technology news editor. Use ONLY facts in the supplied official source excerpt. No speculation, invented facts, fabricated quotations or unsourced claims. Attribute source claims clearly. If the excerpt does not contain enough verifiable information for an informative article, return {{}}. Do NOT pad length. Return JSON with these string fields: en_title, hi_title, en_body, hi_body, en_meta, hi_meta, en_keywords, hi_keywords. Bodies must be plain text with paragraphs separated by blank lines, factual and detailed when supported; aim for 350-650 words in English if source permits, otherwise shorter. Hindi should communicate equivalent facts. Titles should be clear and descriptive, not clickbait. Meta descriptions 120-160 characters when feasible. Keywords should be comma-separated relevant phrases, not spam. Never say you independently fact-checked. SOURCE URL: {source}\nSOURCE TITLE: {title}\nSOURCE EXCERPT: {excerpt[:6000]}'''
    payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 5000}}
    for model in MODELS[:4]:
        print('Trying Gemini model:', model, flush=True)
        try:
            resp = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', headers={'x-goog-api-key': api_key}, json=payload, timeout=(10, 65))
            if not resp.ok:
                print('Model HTTP', resp.status_code, resp.text[:200], flush=True)
                if resp.status_code in (400, 401, 403):
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
            if len(excerpt) < 160: continue
            print('Processing:', clean(entry.get('title'))[:90], flush=True)
            article = generate(api_key, clean(entry.get('title')), excerpt, url)
            if not article: continue
            article.update(id=post_id, source=url, date=dt.datetime.now(UTC).isoformat(), source_title=clean(entry.get('title')))
            path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding='utf-8')
            created += 1
            print('Saved article', created, post_id, flush=True)
            time.sleep(2)
        if created >= remaining: break
    print('Published', created, flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())
