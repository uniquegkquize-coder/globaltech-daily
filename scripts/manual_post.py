"""Validate a GlobeWire editor submission and prepare the existing article format."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
from urllib.parse import urlsplit

from editorial_quality import normalize_post
from news_config import CATEGORIES
from story_identity import canonical_lead_key, same_story

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://globewiredaily.org'


def text_field(data, name, minimum=0, maximum=250):
    value = data.get(name, '')
    if not isinstance(value, str):
        raise ValueError(f'{name} must be text.')
    value = value.strip()
    forbidden = ('profitableratecpmnetwork.com', 'data-adsterra-', 'bicea.org/22/', 'window.atoptions')
    if any(marker in value.lower() for marker in forbidden):
        raise ValueError(f'Remove blocked ad markup from {name}.')
    if not minimum <= len(value) <= maximum:
        raise ValueError(f'{name} needs {minimum}–{maximum} characters.')
    return value


def https_url(value):
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('Use a full HTTPS URL without credentials.')
    if any(char.isspace() or char in '\\"<>' for char in value):
        raise ValueError('The URL contains an invalid character.')
    return value


def title_key(value):
    return ' '.join(''.join(
        char if unicodedata.category(char)[0] in 'LMN' else ' '
        for char in unicodedata.normalize('NFKC', value).casefold()
    ).split())


def prepare(data, now):
    if not isinstance(data, dict):
        raise ValueError('Paste the submission copied from the GlobeWire editor.')
    post = {'manual_post': True, 'date': now.isoformat()}
    category = text_field(data, 'category', 1)
    if category not in CATEGORIES:
        raise ValueError('Choose a GlobeWire category.')
    post['category'] = category
    post['en_title'] = text_field(data, 'en_title', 5, 180)
    post['en_body'] = text_field(data, 'en_body', 150, 24000)
    post['en_meta'] = text_field(data, 'en_meta', maximum=160)
    post['hi_title'] = text_field(data, 'hi_title', maximum=180)
    post['hi_body'] = text_field(data, 'hi_body', maximum=24000)
    post['hi_meta'] = text_field(data, 'hi_meta', maximum=160)
    if any(post[key] for key in ('hi_title', 'hi_body', 'hi_meta')):
        if len(post['hi_title']) < 5 or len(post['hi_body']) < 150 or not all(
            re.search(r'[\u0900-\u097f]', post[key]) for key in ('hi_title', 'hi_body')
        ):
            raise ValueError('Enter both a Hindi headline and at least 150 characters of Hindi text.')
    source = text_field(data, 'source', maximum=2000)
    post['url_title'] = post['en_title']
    if source:
        post['source'] = https_url(source)
        post['source_title'] = text_field(data, 'source_title', maximum=180) or post['en_title']
        identity = canonical_lead_key(source)
    else:
        post['original_reporting'] = True
        identity = 'globewire-original:' + title_key(post['en_title'])
    post['id'] = hashlib.sha256(identity.encode()).hexdigest()[:12]
    post = normalize_post(post)
    article_slug = re.sub(r'[^a-z0-9]+', '-', post['url_title'].lower()).strip('-')[:75].rstrip('-')
    paths = {
        lang: f'/{lang}/news/{post["category"]}/{article_slug or "news"}-{post["id"][:10]}/'
        for lang in ('en', 'hi') if lang == 'en' or post['hi_body']
    }
    if not source:
        post['source'] = SITE + paths['en']
        post['source_title'] = post['en_title']
    photo = {
        'url': text_field(data, 'image_url', maximum=2000),
        'credit': text_field(data, 'image_credit', maximum=150),
        'license': text_field(data, 'image_license', maximum=250),
    }
    if any(photo.values()):
        if not all(photo.values()):
            raise ValueError('A photo needs an HTTPS image link, credit and reuse terms.')
        https_url(photo['url'])
    fingerprint = {key: value for key, value in post.items() if key != 'date'}
    fingerprint['photo'] = photo
    post['manual_submission'] = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return post, paths, photo


def check_existing(folder, post):
    headlines = [post[key] for key in ('en_title', 'hi_title', 'source_title') if post.get(key)]
    keys = {title_key(title) for title in headlines}
    keys.discard('')
    source = canonical_lead_key(post['source'])
    existing = folder / f'{post["id"]}.json'
    for path in sorted(folder.glob('*.json'), key=lambda path: path != existing):
        try:
            old = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(old, dict):
            continue
        if old.get('manual_submission') == post['manual_submission']:
            return True
        old_titles = [old.get(key) for key in ('en_title', 'hi_title', 'source_title')]
        old_urls = [old.get('source')]
        for previous in old.get('source_history') or []:
            if isinstance(previous, dict):
                old_urls.append(previous.get('url'))
                old_titles.append(previous.get('title'))
        if (
            path.stem == post['id']
            or any(source == canonical_lead_key(url) for url in old_urls if url)
            or any(title_key(title) in keys or any(same_story(title, new) for new in headlines)
                   for title in old_titles if isinstance(title, str) and title)
        ):
            raise ValueError(f'Duplicate of an existing post ({path.stem}). Open {SITE}/en/news/{path.stem}/')
    return False


def run(submission, check):
    post, paths, photo = prepare(submission, dt.datetime.now(dt.timezone.utc))
    folder = ROOT / 'content/posts'
    already_saved = check_existing(folder, post)
    if not check and not already_saved:
        path = folder / f'{post["id"]}.json'
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(post, indent=2, ensure_ascii=False) + '\n')
        if photo['url']:
            try:
                subprocess.run(
                    [sys.executable, str(ROOT / 'scripts/import_image.py'), post['id'],
                     photo['url'], post['source'], photo['license'], photo['credit']],
                    check=True, timeout=45, capture_output=True,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                path.unlink(missing_ok=True)
                for suffix in ('.jpg', '.json'):
                    (ROOT / 'content/featured' / (post['id'] + suffix)).unlink(missing_ok=True)
                raise ValueError('Photo import failed. Use a direct JPEG/PNG/WebP link at least 1200 px wide, or clear the photo fields for an illustration.') from None
    result = {'id': post['id'], 'already_saved': already_saved,
              'urls': {lang: SITE + path for lang, path in paths.items()}}
    print(json.dumps(result, ensure_ascii=False))
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        heading = 'Already saved' if already_saved else ('Checks passed' if check else 'Article saved to main')
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write(f'## {heading}\n\n')
            if not check or already_saved:
                stream.write('Article links become available after the Oracle deployment.\n\n')
            for lang, url in result['urls'].items():
                stream.write(f'- [{lang.upper()}]({url})\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('submission', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        run(json.loads(args.submission.read_text(encoding='utf-8')), args.check)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(summary, 'a', encoding='utf-8') as stream:
                stream.write(f'## Submission stopped\n\n{exc}\n')
        sys.exit(1)
