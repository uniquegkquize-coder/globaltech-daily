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
from urllib.parse import quote, urlsplit

from editorial_quality import normalize_post
from news_config import CATEGORIES, route_category
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


def infer_category(post):
    """Prefer a headline match, then a source section or the opening text."""
    fallback = 'india-news'
    for language in ('en', 'hi'):
        topic = route_category(post[language + '_title'], fallback)
        if topic != fallback:
            return topic
    topic = route_category(post['en_title'], fallback, post.get('source', ''))
    if topic != fallback:
        return topic
    for language in ('en', 'hi'):
        opening = next(
            (line.strip() for line in post[language + '_body'].splitlines()
             if line.strip() and not line.lstrip().startswith(('#', '-', '*', '>'))),
            '',
        )
        topic = route_category(opening[:400], fallback)
        if topic != fallback:
            return topic
    return fallback


def submission_hash(post, photo):
    fingerprint = {key: value for key, value in post.items()
                   if key not in ('date', 'manual_category_mode')}
    fingerprint['photo'] = photo
    return hashlib.sha256(json.dumps(fingerprint, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prepare(data, now):
    if not isinstance(data, dict):
        raise ValueError('Paste the submission copied from the GlobeWire editor.')
    post = {'manual_post': True, 'date': now.isoformat()}
    category = text_field(data, 'category')
    if category and category not in CATEGORIES:
        raise ValueError('Choose a valid GlobeWire category or leave it blank for automatic selection.')
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
    post['category'] = category or infer_category(post)
    post['manual_category_mode'] = 'selected' if category else 'automatic'
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
    upload = text_field(data, 'image_upload', maximum=180)
    if upload and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._ -]*\.(?:jpe?g|png|webp)', upload, re.I):
        raise ValueError('Enter the uploaded JPG, PNG or WebP filename, including its extension.')
    if upload and photo['url']:
        raise ValueError('Fill either image_upload or image_url.')
    if any(photo.values()) or upload:
        if not ((photo['url'] or upload) and photo['credit'] and photo['license']):
            raise ValueError('A photo needs an upload or HTTPS link, plus credit and reuse terms.')
    if photo['url']:
        https_url(photo['url'])
    post['manual_submission'] = submission_hash(post, photo)
    if upload:
        photo['upload'] = upload
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


def import_linked_photo(post, photo):
    subprocess.run(
        [sys.executable, str(ROOT / 'scripts/import_image.py'), post['id'],
         photo['url'], post['source'], photo['license'], photo['credit']],
        check=True, timeout=45, capture_output=True,
    )
    metadata_path = ROOT / 'content/featured' / (post['id'] + '.json')
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata.update(source_image=photo['url'], license_name=photo['license'])
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_upload(name):
    path = ROOT / 'content/manual-uploads' / name
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Upload {name} to content/manual-uploads on main first.')
    with path.open('rb') as stream:
        content = stream.read(15_000_001)
    if len(content) > 15_000_000:
        raise ValueError('Photo must be at most 15 MB.')
    return content


def run(submission, check):
    post, paths, photo = prepare(submission, dt.datetime.now(dt.timezone.utc))
    folder = ROOT / 'content/posts'
    upload = photo.get('upload')
    if upload:
        from import_image import prepare_image, save_featured

        uploaded_bytes = read_upload(upload)
        uploaded_sha = hashlib.sha256(uploaded_bytes).hexdigest()
        post['manual_submission'] = hashlib.sha256(
            (post['manual_submission'] + upload + uploaded_sha).encode()
        ).hexdigest()
        if check:
            try:
                prepare_image(uploaded_bytes, minimum_width=1, formats=['JPEG', 'PNG', 'WEBP'])
            except OSError as exc:
                raise ValueError('The upload could not be opened as JPG, PNG or WebP.') from exc
    already_saved = check_existing(folder, post)
    if not check and not already_saved:
        path = folder / f'{post["id"]}.json'
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(post, indent=2, ensure_ascii=False) + '\n')
        if photo['url'] or upload:
            try:
                if upload:
                    url = 'https://github.com/uniquegkquize-coder/globaltech-daily/blob/main/content/manual-uploads/' + quote(upload)
                    save_featured(ROOT, post, uploaded_bytes, 'licensed_source',
                                  photo['credit'], photo['license'], post['source'], url, uploaded=True)
                else:
                    import_linked_photo(post, photo)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                path.unlink(missing_ok=True)
                for suffix in ('.jpg', '.json'):
                    (ROOT / 'content/featured' / (post['id'] + suffix)).unlink(missing_ok=True)
                raise ValueError('Photo import failed. Check the uploaded file or direct photo link.') from exc
    result = {'id': post['id'], 'already_saved': already_saved, 'category': post['category'],
              'urls': {lang: SITE + path for lang, path in paths.items()}}
    print(json.dumps(result, ensure_ascii=False))
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        heading = 'Already saved' if already_saved else ('Checks passed' if check else 'Article saved to main')
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write(f'## {heading}\n\n')
            stream.write(f'Category: **{CATEGORIES[post["category"]][0]}** (`{post["category"]}`)\n\n')
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
