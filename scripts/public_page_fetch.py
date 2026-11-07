"""Bounded public HTTP/JS fetches. Never retry access restrictions in a browser."""
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlparse
import requests

BROWSER_LIMIT = threading.BoundedSemaphore(2)
BROWSER_ATTEMPTS = int(os.getenv('BROWSER_ATTEMPTS_PER_RUN', '8'))
_attempts = 0
_lock = threading.Lock()
CACHE = Path(os.getenv('PUBLIC_FETCH_CACHE', '/tmp/globewire-public-cache'))
DENIED = (401, 403, 407, 429, 451)

def restricted(html):
    return bool(re.search(r'verify you are human|captcha challenge|cf-challenge|access denied|subscribe to (?:continue|read)', html[:200000], re.I))

def needs_render(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    if soup.select_one('table,dl'):
        return False
    for node in soup.select('script,style,noscript'): node.decompose()
    return len(soup.get_text(' ', strip=True)) < 700

def fetch_public_html(url, session=None, timeout=(5,12), max_bytes=2000000, render=False):
    global _attempts
    if urlparse(url).scheme not in ('https', 'http') or not urlparse(url).hostname:
        return '', url, 'invalid-url'
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / (hashlib.sha256((url+str(render)).encode()).hexdigest()+'.json')
    try:
        saved = json.loads(cache.read_text())
        retry_shell=bool(saved['html']) and os.getenv('ENABLE_PUBLIC_BROWSER_FALLBACK','0')=='1' and needs_render(saved['html']) and 'browser' not in saved['method']
        if not retry_shell and time.time()-saved['time'] < (21600 if saved['html'] else 3600):
            return saved['html'], saved['url'], 'cached-'+saved['method']
    except (OSError, ValueError, KeyError): pass
    def done(html, final, method):
        cache.write_text(json.dumps(dict(html=html,url=final,method=method,time=time.time())))
        return html, final, method
    client = session or requests
    html = ''; final = url; failure = 'http-failed'
    for attempt in range(2):
        try:
            response = client.get(url, timeout=timeout, stream=True, headers={
                'User-Agent':'GlobeWireDaily/1.0 (+https://globewiredaily.org)',
                'Accept':'text/html,application/xhtml+xml,application/xml,text/xml'})
            final = response.url
            if response.status_code in DENIED:
                response.close()
                return done('',final,'access-denied-'+str(response.status_code))
            if response.status_code >= 500:
                response.close(); failure='http-'+str(response.status_code)
                if attempt == 0: time.sleep(.3); continue
                break
            response.raise_for_status()
            content_type = response.headers.get('Content-Type',response.headers.get('content-type','')).lower()
            raw=bytearray()
            for chunk in response.iter_content(65536):
                raw.extend(chunk)
                if len(raw)>max_bytes:
                    response.close(); return done('',final,'oversized')
            response.close()
            if not any(x in content_type for x in ('html','xml','text/')):
                return done('',final,'non-html')
            html=raw.decode(response.encoding or 'utf-8',errors='replace')
            if restricted(html): return done('',final,'challenge-or-restricted')
            if not render and not needs_render(html): return done(html,final,'http')
            break
        except requests.HTTPError as exc:
            return done('',final,'http-'+str(exc.response.status_code))
        except requests.RequestException as exc:
            failure=type(exc).__name__
    if os.getenv('ENABLE_PUBLIC_BROWSER_FALLBACK','0') != '1':
        return done(html,final,'http' if html else failure)
    with _lock:
        if _attempts >= BROWSER_ATTEMPTS: return done(html,final,'browser-budget-exhausted')
        _attempts += 1
    with BROWSER_LIMIT:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
                try:
                    page=browser.new_page()
                    response=page.goto(url,wait_until='domcontentloaded',timeout=20000)
                    if response and response.status in DENIED:
                        return done('',page.url,'access-denied-'+str(response.status))
                    if render:
                        try:
                            page.wait_for_function("document.body && document.body.innerText.length > 700", timeout=6000)
                        except Exception:pass
                    else:page.wait_for_timeout(1200)
                    rendered=page.content()
                    if restricted(rendered): return done('',page.url,'challenge-or-restricted')
                    if len(rendered.encode())>max_bytes: return done('',page.url,'oversized')
                    return done(rendered,page.url,'browser')
                finally: browser.close()
        except Exception as exc:
            return done(html,final,'browser-failed-'+type(exc).__name__)
