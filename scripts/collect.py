import sys
import os
import json
import hashlib
def generate(title, summary, source):
    prompt = (
        'You are writing an attributed short technology announcement digest, not independent reporting. '
        'Use ONLY the supplied title and summary. Do not invent facts, quotes, figures, or availability. '
        'If details are inadequate, return {}. Avoid clickbait. '
        'Return JSON object with strings: en_title, hi_title, en_body, hi_body. '
        'Titles should be informative and each body 80-160 words, with source attribution. '
        'The Hindi version must faithfully reflect the English version. '
        f'Official source: {source}\nTitle: {title}\nSummary: {summary[:1000]}'
    )
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 1800},
    }
    for attempt in range(2):
        try:
            response = requests.post(
                url, headers={'x-goog-api-key': os.environ['GEMINI_API_KEY']},
                json=payload, timeout=(15, 120)
            )
            if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                print(f'Transient Gemini HTTP {response.status_code}; retrying once', flush=True)
                time.sleep(8)
                continue
            if not response.ok:
                print('Gemini HTTP', response.status_code, response.text[:600], flush=True)
                return None, True
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(content)
            fields = ('en_title', 'hi_title', 'en_body', 'hi_body')
            if not isinstance(data, dict) or not all(isinstance(data.get(k), str) and len(data[k].strip()) >= (10 if 'title' in k else 80) for k in fields):
                print('Model returned incomplete content; skipped', flush=True)
                return None, False
            return {k: data[k].strip() for k in fields}, False
        except (requests.Timeout, requests.ConnectionError) as error:
            print(f'Gemini network issue ({type(error).__name__}), attempt {attempt+1}', flush=True)
            if attempt == 0:
                time.sleep(8)
                continue
            return None, True
        except (ValueError, KeyError, IndexError, TypeError) as error:
            print(f'Invalid Gemini response: {type(error).__name__}', flush=True)
            return None, True
    return None, True


def main():
    if os.getenv('AUTO_POST', 'false').lower() != 'true':
        print('AUTO_POST is off; no articles generated')
        return 0
    if not os.getenv('GEMINI_API_KEY'):
        print('ERROR: GEMINI_API_KEY is missing')
        return 1
    POSTS.mkdir(parents=True, exist_ok=True)
    remaining = max(0, MAX_DAILY - today_count())
    if remaining == 0:
        print('Daily limit reached (10 articles)')
        return 0
    count = 0
    api_failed = False
    for feed in FEEDS:
        if count >= remaining:
            break
        try:
            entries = get_entries(feed)
        except (requests.RequestException, ValueError) as error:
            print(f'Feed unavailable: {feed} ({type(error).__name__})', flush=True)
            continue
        for entry in entries[:20]:
            if count >= remaining:
                break
            link = str(entry.get('link', '')).strip()
            title = clean(entry.get('title', ''))
            summary = clean(entry.get('summary', ''))
            if not link.startswith('https://') or not title or len(summary) < 150 or not recent(entry):
                continue
            key = hashlib.sha256(link.encode('utf-8')).hexdigest()[:12]
            target = POSTS / f'{key}.json'
            if target.exists():
                continue
            result, failed = generate(title, summary, link)
            api_failed = api_failed or failed
            if result is None:
                if failed:
                    print('Stopping after Gemini failure to conserve quota', flush=True)
                    break
                continue
            result.update(id=key, source=link, date=dt.datetime.now(dt.timezone.utc).isoformat(),
                          content_type='official-source-summary', independently_verified=False)
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            count += 1
            print('Created article', key, flush=True)
            time.sleep(2)
        if api_failed:
            break
    print(f'Published {count} (daily total {today_count()}/{MAX_DAILY})', flush=True)
    return 1 if api_failed else 0


if __name__ == '__main__':
    sys.exit(main())
