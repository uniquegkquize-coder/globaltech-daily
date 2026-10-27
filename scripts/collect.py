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
FEEDS = ['https://blog.cloudflare.com/rss/', 'https://blog.google/rss/']
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
DAILY_LIMIT = 10
UTC = dt.timezone.utc


def clean(value):
    value = re.sub(r'<[^>]+>', ' ', str(value or ''))
    return re.sub(r'\s+', ' ', html.unescape(value)).strip()


def today_count():
    today = dt.datetime.now(UTC).date().isoformat()
    count = 0
    for path in POSTS.glob('*.json'):
        try:
            item = json.loads(path.read_text(encoding='utf-8'))
            if str(item.get('date', ''))[:10] == today:
                count += 1
        except (ValueError, OSError, TypeError):
            continue
    return count


def generate(key, title, summary, link):
    prompt = (
        'Write a short, original bilingual technology announcement brief based ONLY on '
        'the official-source excerpt. Do not invent facts, prices, quotations, or dates. '
        'Attribute claims to the publisher; do not claim independent verification. '
        'If insufficient information, return {}. Return JSON with exactly four string '
        'fields: en_title, hi_title, en_body, hi_body. Each body must be 100-1200 '
        'characters; use readable plain text, no HTML.\n'
        f'SOURCE: {link}\nTITLE: {title}\nEXCERPT: {summary[:1200]}'
    )
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 1800},
    }
    for attempt in range(2):
        try:
            response = requests.post(API_URL, headers={'x-goog-api-key': key},
                                     json=payload, timeout=(15, 120))
            if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                print(f'Gemini HTTP {response.status_code}; retrying once', flush=True)
                time.sleep(8)
                continue
            if not response.ok:
                print(f'Gemini HTTP {response.status_code}: {response.text[:500]}', flush=True)
                return None, True
            data = response.json()
            raw = data['candidates'][0]['content']['parts'][0]['text']
            article = json.loads(raw)
            fields = ('en_title', 'hi_title', 'en_body', 'hi_body')
            if not isinstance(article, dict) or any(
                not isinstance(article.get(field), str) or len(article[field].strip()) < 15
                for field in fields
            ):
                print('Skipped: incomplete article', flush=True)
                return None, False
            if len(article['en_body']) < 100 or len(article['hi_body']) < 100:
                print('Skipped: article too short', flush=True)
                return None, False
            return {field: article[field].strip() for field in fields}, False
        except (requests.RequestException, KeyError, IndexError, ValueError, TypeError) as exc:
            print(f'Gemini request error: {type(exc).__name__}: {str(exc)[:250]}', flush=True)
            if attempt == 0:
                time.sleep(8)
                continue
            return None, True
    return None, True


def main():
    if os.getenv('AUTO_POST', 'false').lower() != 'true':
        print('AUTO_POST is off; no news generated', flush=True)
        return 0
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        print('ERROR: GEMINI_API_KEY missing', flush=True)
