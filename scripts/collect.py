import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import time

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / 'content' / 'posts'
FEEDS = ('https://blog.cloudflare.com/rss/', 'https://blog.google/rss/')
PREFERRED_MODELS = tuple(x.strip() for x in os.getenv(
    'GEMINI_MODELS',
    'gemini-3.8-flash,gemini-3.5-flash-lite,gemini-3.5-flash,gemini-2.5-flash-lite'
).split(',') if x.strip())
API_BASE = 'https://generativelanguage.googleapis.com/v1beta'
MAX_MODELS_PER_ARTICLE = 3

UTC = dt.timezone.utc
DAILY_LIMIT = 10


def clean(text):
    text = re.sub(r'<[^>]*>', ' ', str(text or ''))
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def count_today():
    today = dt.datetime.now(UTC).date()
    count = 0
    for file in POSTS.glob('*.json'):
        try:
            record = json.loads(file.read_text(encoding='utf-8'))
            if dt.date.fromisoformat(str(record.get('date', ''))[:10]) == today:
                count += 1
        except (OSError, ValueError, TypeError):
            continue
    return count


def available_models(api_key):
    """Use model listing to avoid trying IDs unavailable to this API key."""
    try:
        response = requests.get(
            f'{API_BASE}/models',
            headers={'x-goog-api-key': api_key},
            timeout=(10, 20),
        )
        response.raise_for_status()
        return {
            item.get('name', '').removeprefix('models/')
            for item in response.json().get('models', [])
            if 'generateContent' in item.get('supportedGenerationMethods', [])
        }
    except (requests.RequestException, ValueError) as exc:
        print(f'Model listing unavailable: {type(exc).__name__}: {str(exc)[:180]}', flush=True)
        return None


def generate(api_key, title, excerpt, url, models):
    prompt = (
        'Write an original, cautious bilingual brief about an official technology announcement. '
        'Use ONLY the following source title and excerpt. Attribute all claims to the publisher. '
        'Do not invent facts or claim independent verification. If details are insufficient, return {}. '
        'Return JSON with string fields en_title, hi_title, en_body, hi_body. '
        'Each title should be short, each body 100-1000 characters. No HTML.\n'
        f'SOURCE URL: {url}\nTITLE: {title}\nEXCERPT: {excerpt[:1200]}'
    )
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 2200},
    }
    fields = ('en_title', 'hi_title', 'en_body', 'hi_body')
    for model in models[:MAX_MODELS_PER_ARTICLE]:
        print(f'Trying Gemini model: {model}', flush=True)
        try:
            response = requests.post(
                f'{API_BASE}/models/{model}:generateContent',
                headers={'x-goog-api-key': api_key},
                json=payload,
                timeout=(10, 55),
            )
            if response.status_code == 429:
                print(f'Gemini {model}: 429 quota/rate limit. Stopping to protect quota.', flush=True)
                return None, True
            if response.status_code in (400, 401, 403):
                print(f'Gemini {model}: HTTP {response.status_code}: {response.text[:350]}', flush=True)
                return None, True
            if response.status_code in (404, 500, 502, 503, 504):
                print(f'Gemini {model}: HTTP {response.status_code}; trying fallback', flush=True)
                continue
            response.raise_for_status()
            result = response.json()
            parts = result['candidates'][0]['content']['parts']
            raw = ''.join(part.get('text', '') for part in parts)
            article = json.loads(raw)
            if not isinstance(article, dict) or any(
                not isinstance(article.get(field), str) or len(article[field].strip()) < 15
                for field in fields
            ):
                print(f'Gemini {model}: incomplete article; trying fallback', flush=True)
                continue
            if len(article['en_body'].strip()) < 100 or len(article['hi_body'].strip()) < 100:
                print(f'Gemini {model}: article too short; trying fallback', flush=True)
                continue
            print(f'Gemini model succeeded: {model}', flush=True)
            return {field: article[field].strip() for field in fields}, False
        except requests.Timeout:
            print(f'Gemini {model}: timeout; trying fallback', flush=True)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            print(f'Gemini {model}: {type(exc).__name__}: {str(exc)[:200]}', flush=True)
    print('All attempted Gemini models failed', flush=True)
    return None, True


def main():
    print('GlobalTech Daily collector started', flush=True)
    if os.getenv('AUTO_POST', 'false').strip().lower() != 'true':
        print('AUTO_POST is OFF', flush=True)
        return 0
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        print('ERROR: GEMINI_API_KEY is missing', flush=True)
        return 1

    available = available_models(api_key)
    models = [m for m in PREFERRED_MODELS if available is None or m in available]
    if not models:
        print('ERROR: No configured text models are listed for this API key', flush=True)
        return 1
    print('Fallback order: ' + ', '.join(models[:MAX_MODELS_PER_ARTICLE]), flush=True)
    POSTS.mkdir(parents=True, exist_ok=True)
    remaining = max(0, DAILY_LIMIT - count_today())
    print(f'Remaining daily allowance: {remaining}', flush=True)
    if remaining == 0:
        print('Published 0 (daily limit reached)', flush=True)
        return 0

    published = 0
    candidates = 0
    api_failed = False
    seen = set()
    today = dt.datetime.now(UTC).date()

    for feed_url in FEEDS:
        if published >= remaining or api_failed:
            break
        try:
            response = requests.get(feed_url, timeout=(10, 25), headers={'User-Agent': 'GlobalTechDailyBot/1.0'})
            response.raise_for_status()
            entries = feedparser.parse(response.content).entries
            print(f'Feed {feed_url}: {len(entries)} entries', flush=True)
        except requests.RequestException as exc:
            print(f'Feed error: {type(exc).__name__}: {str(exc)[:200]}', flush=True)
            continue

        for entry in entries[:30]:
            if published >= remaining or api_failed:
                break
            link = entry.get('link', '').strip()
            if not link or link in seen:
                continue
            seen.add(link)
            post_id = hashlib.sha256(link.encode('utf-8')).hexdigest()[:12]
            destination = POSTS / f'{post_id}.json'
            if destination.exists():
                continue
            stamp = entry.get('published_parsed') or entry.get('updated_parsed')
            if not stamp:
                continue
            try:
                age = (today - dt.date(*stamp[:3])).days
            except (TypeError, ValueError):
                continue
            if age < 0 or age > 3:
                continue
            title = clean(entry.get('title', ''))
            excerpt = clean(entry.get('summary', '') or entry.get('description', ''))
            if len(title) < 12 or len(excerpt) < 150:
                continue
            candidates += 1
            print(f'Processing: {title[:90]}', flush=True)
            article, failed = generate(api_key, title, excerpt, link, models)
            if failed:
                api_failed = True
                break
            if not article:
                continue
            article.update({'id': post_id, 'source': link, 'date': dt.datetime.now(UTC).isoformat()})
            destination.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding='utf-8')
            published += 1
            print(f'Saved article {published}: {post_id}', flush=True)
            time.sleep(2)

    print(f'Eligible candidates checked: {candidates}', flush=True)
    print(f'Published {published}', flush=True)
    if api_failed:
        print('ERROR: Gemini API request failed', flush=True)
        return 1
    if candidates == 0:
        print('No eligible recent RSS entries found', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
