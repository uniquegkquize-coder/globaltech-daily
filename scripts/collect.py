import os
import sys
import json
import hashlib
import datetime as dt
import pathlib
import re
import time
import html

import requests
import feedparser

ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS = ROOT / 'content' / 'posts'
POSTS.mkdir(parents=True, exist_ok=True)
FEEDS = [
    'https://blog.cloudflare.com/rss/',
    'https://blog.google/rss/',
]
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
DAILY_LIMIT = 10
UTC = dt.timezone.utc


def clean(value):
    value = re.sub(r'<[^>]+>', ' ', str(value or ''))
    return re.sub(r'\s+', ' ', html.unescape(value)).strip()


def today_count():
    today = dt.datetime.now(UTC).date()
    count = 0
    for path in POSTS.glob('*.json'):
        try:
            item = json.loads(path.read_text(encoding='utf-8'))
            date_text = str(item.get('date', ''))[:10]
            if dt.date.fromisoformat(date_text) == today:
                count += 1
        except (ValueError, OSError, TypeError, json.JSONDecodeError):
            continue
    return count


def generate(key, title, summary, link):
    prompt = (
        'Create a factual bilingual news brief based ONLY on the official source excerpt below. '
        'Do not claim to have independently verified the story. Do not invent details, quotes, '
        'dates, prices, or claims. Clearly attribute all factual claims to the publisher. '
        'If the excerpt lacks sufficient detail, return an empty JSON object {}. '
        'Return a JSON object with exactly these four string keys: '
        'en_title, hi_title, en_body, hi_body. Each title should be 15-140 characters; '
        'each body 100-1200 characters, in readable paragraphs. Do not use HTML.\n'
        f'SOURCE: {link}\nTITLE: {title}\nEXCERPT: {summary[:1200]}'
    )
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 1600},
    }
    response = None
    for attempt in range(2):
        try:
            response = requests.post(
                API_URL,
                headers={'x-goog-api-key': key},
                json=payload,
                timeout=(15, 120),
            )
            if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                print(f'Gemini HTTP {response.status_code}; retrying once', flush=True)
                time.sleep(8)
                continue
            if not response.ok:
                print(f'Gemini HTTP {response.status_code}: {response.text[:700]}', flush=True)
                return None, True
            data = response.json()
            raw = data['candidates'][0]['content']['parts'][0]['text']
            article = json.loads(raw)
            fields = ('en_title', 'hi_title', 'en_body', 'hi_body')
            if not isinstance(article, dict) or any(
                not isinstance(article.get(field), str) or len(article[field].strip()) < 15
                for field in fields
            ):
                print('Skipped: insufficient Gemini output', flush=True)
                return None, False
            if len(article['en_body']) < 100 or len(article['hi_body']) < 100:
                print('Skipped: article too short', flush=True)
                return None, False
            return {field: article[field].strip() for field in fields}, False
        except (requests.RequestException, KeyError, IndexError, ValueError, TypeError) as exc:
            print(f'Gemini request error: {type(exc).__name__}: {str(exc)[:300]}', flush=True)
            if attempt == 0:
                time.sleep(8)
                continue
            return None, True
