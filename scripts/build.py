from pathlib import Path
from datetime import datetime
import html
import json
import os
import shutil
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
SITE = os.getenv('SITE_URL', 'https://globaltech-daily.pages.dev').rstrip('/')
OUT.mkdir(parents=True, exist_ok=True)
shutil.rmtree(OUT)
OUT.mkdir(parents=True)


def esc(value):
    return html.escape(str(value or ''), quote=True)


def page(title, description, body, canonical, lang='en', alternate=None):
    alt = '' if not alternate else f'<link rel="alternate" hreflang="{"hi" if lang == "en" else "en"}" href="{esc(alternate)}">'
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(description[:160])}"><link rel="canonical" href="{esc(canonical)}">{alt}<link rel="stylesheet" href="/style.css"></head><body><header><a class="brand" href="/{lang}/">GlobalTech Daily</a><nav><a href="/en/">English</a><a href="/hi/">हिन्दी</a><a href="/en/about/">About</a><a href="/en/tools/">Tools</a></nav></header><main>{body}</main><footer>AI-assisted technology briefs based on official publisher announcements. Not independently fact-checked. <a href="/en/privacy/">Privacy</a> · <a href="/en/affiliate/">Affiliate disclosure</a></footer></body></html>'''


posts = []
for file in (ROOT / 'content' / 'posts').glob('*.json'):
    try:
        item = json.loads(file.read_text(encoding='utf-8'))
        if all(item.get(k) for k in ('id', 'source', 'en_title', 'hi_title', 'en_body', 'hi_body')) and str(item['id']).isalnum() and urlparse(item['source']).scheme == 'https':
            posts.append(item)
    except (OSError, ValueError, TypeError):
        print('Skipped invalid article:', file.name)
posts.sort(key=lambda p: str(p.get('date', '')), reverse=True)
urls = []
for lang in ('en', 'hi'):
    links = []
    for post in posts:
        slug = post['id']
        title = post[f'{lang}_title']
        body = post[f'{lang}_body']
        path = f'/{lang}/news/{slug}/'
        alternate = f'{SITE}/{"hi" if lang == "en" else "en"}/news/{slug}/'
        article_html = ''.join(f'<p>{esc(paragraph)}</p>' for paragraph in body.split('\n') if paragraph.strip())
        date = esc(str(post.get('date', ''))[:10])
        content = f'<article><h1>{esc(title)}</h1><p class="meta">{date} · AI-assisted, source-attributed report</p>{article_html}<p class="source">Original source: <a href="{esc(post["source"])}" rel="noopener noreferrer">Read publisher announcement</a></p><p class="note">This summary has not been independently fact-checked.</p></article>'
        target = OUT / lang / 'news' / slug
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(page(title + ' | GlobalTech Daily', body[:155], content, SITE + path, lang, alternate), encoding='utf-8')
        links.append(f'<a class="story" href="{path}"><h2>{esc(title)}</h2><span>{date}</span></a>')
        urls.append(path)
    intro = 'Latest technology updates from official sources' if lang == 'en' else 'आधिकारिक स्रोतों से नवीनतम तकनीकी अपडेट'
    content = f'<section class="hero"><h1>GlobalTech Daily</h1><p>{intro}</p></section><section>{"".join(links) if links else "<p>No articles published yet. Check back soon.</p>"}</section>'
    target = OUT / lang
    target.mkdir(exist_ok=True)
    path = f'/{lang}/'
    (target / 'index.html').write_text(page('GlobalTech Daily | Technology News', intro, content, SITE + path, lang, SITE + ('/hi/' if lang == 'en' else '/en/')), encoding='utf-8')
    urls.append(path)

(OUT / 'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/en/"><link rel="canonical" href="/en/"></head><body><a href="/en/">Visit GlobalTech Daily</a></body></html>', encoding='utf-8')
(OUT / 'style.css').write_text('''*{box-sizing:border-box}body{margin:0;background:#0c1525;color:#edf3ff;font:17px/1.7 system-ui,-apple-system,sans-serif}a{color:#8dc8ff}header,main,footer{max-width:1000px;margin:auto;padding:20px}header{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;border-bottom:1px solid #314158}nav{display:flex;gap:16px;flex-wrap:wrap}.brand{font-weight:800;font-size:23px;text-decoration:none;color:white}.hero{padding:24px 0}h1{font-size:clamp(28px,5vw,42px);line-height:1.25}h2{font-size:21px}.story{display:block;text-decoration:none;background:#172740;border:1px solid #2b4262;border-radius:12px;padding:16px 22px;margin:14px 0}.story h2{margin:0 0 5px}.story span,.meta,.note,footer{color:#bac8dc;font-size:14px}article{background:#172740;padding:clamp(18px,4vw,34px);border-radius:14px}article p{white-space:pre-wrap}.source{border-top:1px solid #334962;padding-top:16px}footer{border-top:1px solid #314158;margin-top:30px}''', encoding='utf-8')
(OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n', encoding='utf-8')
(OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{xml_escape(SITE + path)}</loc></url>' for path in urls) + '</urlset>', encoding='utf-8')
static_pages = {
    'about': ('About GlobalTech Daily', 'We publish AI-assisted summaries of technology announcements from official sources. These are not independently verified reports. Editorial corrections and contact information should be added by the site owner.'),
    'privacy': ('Privacy Policy', 'This website owner must publish a complete privacy policy describing analytics, advertising, cookies and contact details before enabling such services.'),
    'affiliate': ('Affiliate Disclosure', 'Some links may be affiliate links. If you purchase through them, the publisher may receive a commission. Sponsored and affiliate content should be clearly identified.'),
    'tools': ('Technology Tools', 'Tools and product recommendations will be added here after editorial review.'),
}
for slug, (title, description) in static_pages.items():
    target = OUT / 'en' / slug
    target.mkdir(parents=True, exist_ok=True)
    (target / 'index.html').write_text(page(title, description, f'<h1>{esc(title)}</h1><p>{esc(description)}</p>', f'{SITE}/en/{slug}/'), encoding='utf-8')
print(f'Built {len(posts)} posts; {len(urls)} indexed language URLs', flush=True)
