"""Bounded public-page fetch: ordinary HTTP first, optional JS rendering second.

Does not solve CAPTCHAs, bypass authentication, evade access controls or use proxies.
"""
import os
import threading
import requests

BROWSER_LIMIT=threading.BoundedSemaphore(2)
BROWSER_ATTEMPTS=int(os.getenv("BROWSER_ATTEMPTS_PER_RUN","8"))
_attempts=0
_lock=threading.Lock()

def fetch_public_html(url, session=None, timeout=(5,12), max_bytes=2000000):
    global _attempts
    client=session or requests
    try:
        response=client.get(url,timeout=timeout,headers={
            "User-Agent":"GlobalTechDaily/1.0 (+https://globewiredaily.org)",
            "Accept":"text/html,application/xhtml+xml",
        })
        response.raise_for_status()
        if "html" in response.headers.get("Content-Type","").lower() and len(response.text.encode("utf-8"))<=max_bytes:
            return response.text,response.url,"http"
        return "",response.url,"non-html"
    except requests.HTTPError as exc:
        code=getattr(exc.response,"status_code",None)
        if code in (401,403,407,429,451):
            return "",url,"access-denied-"+str(code)
    except requests.RequestException:
        pass
    if os.getenv("ENABLE_PUBLIC_BROWSER_FALLBACK","0")!="1":
        return "",url,"http-failed"
    with _lock:
        if _attempts>=BROWSER_ATTEMPTS:return "",url,"browser-budget-exhausted"
        _attempts+=1
    with BROWSER_LIMIT:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    page=browser.new_page()
                    response=page.goto(url,wait_until="domcontentloaded",timeout=16000)
                    if response and response.status in (401,403,407,429,451):
                        return "",url,"access-denied-"+str(response.status)
                    page.wait_for_timeout(700)
                    final=page.url
                    html=page.content()
                    if len(html.encode("utf-8"))>max_bytes:return "",final,"oversized"
                    if any(s in html.lower() for s in ("verify you are human","captcha challenge","cf-challenge")):
                        return "",final,"challenge"
                    return html,final,"browser"
                finally:browser.close()
        except Exception as exc:
            return "",url,"browser-failed-"+type(exc).__name__
