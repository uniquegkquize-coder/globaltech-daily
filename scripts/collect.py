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
FEEDS = [
    'https://blog.cloudflare.com/rss/',
    'https://blog.google/rss/',
]
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
DAILY_LIMIT = 10
UTC = dt.timezone.utc


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(value or '')))).strip()


def count_today():
    today = dt.datetime.now(UTC).date().isoformat()
    count = 0
    for file in POSTS.glob('*.json'):
        try:
            item = json.loads(file.read_text(encoding='utf-8'))
            if str(item.get('date', ''))[:10] == today:
                count += 1
        except (OSError, ValueError, TypeError):
            continue
    return count


def make_article(api_key, title, summary, link):
    prompt = (
        'You are writing a short, original bilingual technology news brief from an OFFICIAL '
        'publisher excerpt, not an independently verified report. Use ONLY the supplied title '
        'and excerpt. Attribute factual claims to the publisher. Do not invent details, quotes, '
        'figures, dates, product capabilities or external verification. If information is '
        'insufficient, return {}. Return JSON with exactly en_title, hi_title, en_body, hi_body. '
        'Both titles should be concise. Each body should contain 100-900 characters of readable '
        'plain text, not HTML. English and Hindi should convey the same facts.\n'
        f'SOURCE URL: {link}\nTITLE: {title}\nEXCERPT: {summary[:1400]}'
    )
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 2400},
    }
    for attempt in range(2):
        try:
            response = requests.post(
                API_URL,
                headers={'x-goog-api-key': api_key},
                json=payload,
                timeout=(15, 120),
            )
            if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                print(f'Gemini HTTP {response.status_code}; retrying once', flush=True)
                time.sleep(8)
                continue
            if not response.ok:
                print(f'Gemini HTTP {response.status_code}: {response.text[:600]}', flush=True)
                return None, True
            result = response.json()
            parts = result['candidates'][0]['content']['parts']
            raw = ''.join(part.get('text', '') for part in parts)
            article = json.loads(raw)
            fields = ('en_title', 'hi_title', 'en_body', 'hi_body')
            if not isinstance(article, dict) or not all(
                isinstance(article.get(k), str) and len(article[k].strip()) >= (100 if k.endswith('body') else 8)
                for k in fields
            ):
                print('Skipped: Gemini returned incomplete article', flush=True)
                return None, False
            return {k: article[k].strip() for k in fields}, False
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            print(f'Gemini error: {type(exc).__name__}: {str(exc)[:300]}', flush=True)
            if attempt == 0:
                time.sleep(8)
                continue
            return None, True
    return None, True


def main():
    print('GlobalTech Daily collector started', flush=True)
    if os.getenv('AUTO_POST', 'false').strip().lower() != 'true':
