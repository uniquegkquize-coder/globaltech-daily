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
        print('AUTO_POST is OFF; no automatic articles', flush=True)
        return 0
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        print('ERROR: GEMINI_API_KEY is missing', flush=True)
        return 1
    POSTS.mkdir(parents=True, exist_ok=True)
    existing = count_today()
    remaining = max(0, DAILY_LIMIT - existing)
    print(f'Existing today: {existing}; remaining daily allowance: {remaining}', flush=True)
    if not remaining:
        print('Published 0 (daily limit reached)', flush=True)
        return 0

    published = 0
    api_failed = False
    candidates = 0
    today = dt.datetime.now(UTC).date()
    for url in FEEDS:
        if published >= remaining or api_failed:
            break
        try:
            feed_response = requests.get(url, timeout=(10, 25), headers={'User-Agent': 'GlobalTechDaily/1.0 (RSS reader)'})
            feed_response.raise_for_status()
            entries = feedparser.parse(feed_response.content).entries
            print(f'Feed {url}: {len(entries)} entries', flush=True)
        except requests.RequestException as exc:
            print(f'Feed error {url}: {str(exc)[:200]}', flush=True)
            continue
        for entry in entries[:30]:
            if published >= remaining or api_failed:
                break
            link = str(entry.get('link', '')).strip()
            title = clean(entry.get('title', ''))
            if not link.startswith('https://') or not title:
                continue
            post_id = hashlib.sha256(link.encode('utf-8')).hexdigest()[:12]
            file = POSTS / f'{post_id}.json'
            if file.exists():
                continue
            published_date = entry.get('published_parsed') or entry.get('updated_parsed')
            if not published_date:
                continue
            try:
                age = (today - dt.date(*published_date[:3])).days
            except (TypeError, ValueError):
                continue
            if not 0 <= age <= 3:
                continue
            summary = clean(entry.get('summary', '') or entry.get('description', ''))
            if len(summary) < 150:
                continue
            candidates += 1
            print(f'Processing: {title[:90]}', flush=True)
            article, failed = make_article(api_key, title, summary, link)
            if failed:
                api_failed = True
                break
            if not article:
                continue
            article.update(id=post_id, source=link, date=dt.datetime.now(UTC).isoformat())
            file.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding='utf-8')
            published += 1
            print(f'Saved article {published}: {post_id}', flush=True)
            time.sleep(2)
    print(f'Eligible candidates checked: {candidates}', flush=True)
    print(f'Published {published}', flush=True)
    if api_failed:
        print('ERROR: Gemini API failed; investigate messages above', flush=True)
        return 1
    if not candidates:
        print('No recent eligible RSS items; this is not an API error', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
