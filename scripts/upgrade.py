from pathlib import Path
p=Path(__file__).with_name('collect.py');s=p.read_text()
s=s.replace('import requests, feedparser','import requests, feedparser\nfrom bs4 import BeautifulSoup')
s=s.replace("'gemini-3.5-flash-lite,gemini-3.5-flash,gemini-3.8-flash,gemini-2.5-flash-lite'", "'gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.5-flash,gemini-3.6-flash,gemini-3.8-flash'")
s=s.replace("'robotics', 'computer-use', 'live', 'native'", "'robotics', 'computer-use', 'live', 'native', 'transcribe', 'translate', 'video', 'omni'")
s=s.replace("MAX_MODELS_PER_ARTICLE = max(1, min(30, int(os.getenv('MAX_MODELS_PER_ARTICLE', '12'))))", "MAX_MODELS_PER_ARTICLE = max(1, min(100, int(os.getenv('MAX_MODELS_PER_ARTICLE', '30'))))")
s=s.replace("        ordered.extend(m for m in sorted(set(discovered), key=priority) if m not in ordered)", "        ordered.extend(m for m in sorted(set(discovered), key=priority) if m not in ordered and 'pro' not in m.lower())\n        # Pro models can be enabled explicitly with ALLOW_PAID_MODELS=true.\n        if os.getenv('ALLOW_PAID_MODELS', 'false').lower() == 'true':\n            ordered.extend(m for m in sorted(set(discovered)) if m not in ordered)")
s=s.replace("    prompt = f'''", "    prompt = f'''")
s=s.replace('Use ONLY facts in the supplied official source excerpt.', 'Use ONLY facts in the supplied official source article. Explain context and implications only when supported. Structure each language body with 3-5 informative sections using headings on separate lines prefixed ##. Include a useful factual opening and key takeaways. Never fabricate quotes, dates, availability, prices, or benchmarks.')
s=s.replace('aim for 350-650 words in English if source permits, otherwise shorter', 'aim for 500-900 words in English if the full source contains enough facts, otherwise shorter')
s=s.replace('SOURCE EXCERPT: {excerpt[:6000]}', 'SOURCE ARTICLE TEXT: {excerpt[:16000]}')
s=s.replace("'maxOutputTokens': 5000", "'maxOutputTokens': 8000")
s=s.replace("            excerpt = clean(entry.get('summary', '') or entry.get('description', ''))", "            excerpt = clean(entry.get('summary', '') or entry.get('description', ''))\n            article_text, image_url = fetch_source(url)\n            if len(article_text) > len(excerpt): excerpt = article_text")
s=s.replace("            article.update(id=post_id, source=url, date=dt.datetime.now(UTC).isoformat(), source_title=clean(entry.get('title')))", "            article.update(id=post_id, source=url, date=dt.datetime.now(UTC).isoformat(), source_title=clean(entry.get('title')), source_image=image_url)")
marker='def main():'
fn='''def fetch_source(url):
    """Extract official article text; external images are not reused without license."""
    try:
        response = requests.get(url, timeout=(8, 22), headers={'User-Agent': 'Mozilla/5.0 (compatible; GlobalTechDaily/1.0)'})
        response.raise_for_status()
        if 'html' not in response.headers.get('Content-Type', 'text/html'): return '', ''
        soup = BeautifulSoup(response.text[:1500000], 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'form']): tag.decompose()
        main = soup.find('article') or soup.find('main') or soup
        chunks = [clean(t.get_text(' ', strip=True)) for t in main.find_all(['h2', 'h3', 'p', 'li'])]
        text = '\\n'.join(t for t in chunks if len(t) > 35)
        return text[:18000], ''
    except (requests.RequestException, ValueError) as exc:
        print('Source extraction unavailable:', type(exc).__name__, flush=True)
        return '', ''

'''
s=s.replace(marker,fn+marker)
p.write_text(s)
