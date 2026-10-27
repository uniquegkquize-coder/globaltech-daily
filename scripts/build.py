from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
import os, html, json, shutil, re
from PIL import Image, ImageDraw, ImageFont
CONTACT = 'info@sellercalc.net'
R = Path(__file__).resolve().parents[1]
OUT = R / 'dist'
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
SITE = os.getenv('SITE_URL', 'https://globaltech-daily.pages.dev').rstrip('/')
POSTS = []
for f in (R / 'content' / 'posts').glob('*.json'):
    try:
        p = json.loads(f.read_text(encoding='utf-8'))
        if p.get('id') and p.get('source'):
            POSTS.append(p)
    except (ValueError, OSError):
        pass
POSTS.sort(key=lambda p: p.get('date', ''), reverse=True)

def e(s): return html.escape(str(s or ''), quote=True)
def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
def cover(title):
    # Self-created decorative SVG; not a licensed photo or a 1200px raster Discover image.
    safe = e(re.sub(r'[^\w\s\-.,]', '', title)[:75])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675"><rect width="1200" height="675" fill="#0b1730"/><circle cx="1050" cy="100" r="260" fill="#1761ab" opacity=".35"/><rect x="65" y="80" width="420" height="12" fill="#4ec6e8"/><text x="65" y="155" fill="#4ec6e8" font-family="Arial,sans-serif" font-size="45" font-weight="bold">GLOBALTECH DAILY</text><foreignObject x="65" y="210" width="1060" height="340"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial,sans-serif;font-size:65px;line-height:1.2;font-weight:700;color:white;overflow-wrap:break-word">{safe}</div></foreignObject><text x="65" y="620" fill="#a7c9e6" font-family="Arial,sans-serif" font-size="30">TECHNOLOGY NEWS • SOURCE-ATTRIBUTED</text></svg>'''

def raster_cover(slug, title):
    image = Image.new('RGB', (1280, 720), '#0b1730')
    draw = ImageDraw.Draw(image)
    draw.ellipse((870,-230,1520,420), fill='#173a72')
    draw.rounded_rectangle((68,70,310,124), radius=14, fill='#18b8d4')
    fonts = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf']
    font_path = next((f for f in fonts if Path(f).exists()), None)
    big = ImageFont.truetype(font_path, 55) if font_path else ImageFont.load_default()
    small = ImageFont.truetype(font_path, 26) if font_path else ImageFont.load_default()
    draw.text((85,82), 'TECH NEWS', fill='#06162a', font=small)
    words = title.split(); lines=[]; current=''
    for word in words:
        test=(current+' '+word).strip()
        if draw.textbbox((0,0),test,font=big)[2] > 1110 and current:
            lines.append(current);current=word
        else: current=test
    if current: lines.append(current)
    for i,line in enumerate(lines[:5]): draw.text((72,175+i*83),line,fill='#ffffff',font=big)
    draw.text((72,635),'GLOBALTECH DAILY  •  TECHNOLOGY EXPLAINED',fill='#93dce9',font=small)
    dest=OUT/'images'/f'{slug}.jpg';dest.parent.mkdir(parents=True,exist_ok=True)
    image.save(dest, 'JPEG', quality=88, optimize=True)

def paragraphs_html(body):
    chunks=re.split(r'\n\s*\n|(?=^## )', body.strip(), flags=re.M)
    result=[]
    for chunk in chunks:
        chunk=chunk.strip()
        if not chunk: continue
        if chunk.startswith('## '):
            lines=chunk.splitlines();result.append('<h2>'+e(lines[0][3:])+'</h2>')
            if len(lines)>1: result.append('<p>'+e(' '.join(lines[1:]))+'</p>')
        else: result.append('<p>'+e(chunk)+'</p>')
    return ''.join(result)

def shell(lang, title, description, canonical, body, extra=''):
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{e(canonical)}"><link rel="stylesheet" href="/style.css">{extra}</head><body><header><a class="brand" href="/{lang}/">GlobalTech Daily</a><nav><a href="/en/">English</a> · <a href="/hi/">हिन्दी</a> · <a href="/{lang}/about/">About</a> · <a href="/{lang}/privacy/">Privacy</a> · <a href="/{lang}/contact/">Contact</a> · <a href="/{lang}/editorial/">Editorial</a></nav></header><main>{body}</main><footer>AI-assisted reporting based on attributed source announcements. <a href="/{lang}/affiliate/">Affiliate disclosure</a> · <a href="mailto:{CONTACT}">{CONTACT}</a></footer></body></html>'''

for p in POSTS:
    slug = re.sub('[^a-f0-9]', '', str(p['id']))[:32]
    if not slug: continue
    title_for_cover = p.get('en_title', p.get('source_title', 'Technology News'))
    raster_cover(slug, title_for_cover)
    for lang in ('en', 'hi'):
        title = p.get(lang + '_title') or p.get('en_title') or 'Technology News'
        body = p.get(lang + '_body') or p.get('en_body') or ''
        meta = p.get(lang + '_meta') or (str(body)[:155])
        keywords = p.get(lang + '_keywords', '')
        canonical = f'{SITE}/{lang}/news/{slug}/'
        alternate = 'hi' if lang == 'en' else 'en'
        date = p.get('date', '')
        paragraphs = paragraphs_html(body)
        if not paragraphs: paragraphs = '<p>Details are being updated.</p>'
        schema = {'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': title, 'datePublished': date, 'dateModified': date, 'inLanguage': lang, 'mainEntityOfPage': canonical, 'image': [f'{SITE}/images/{slug}.jpg'], 'publisher': {'@type': 'Organization', 'name': 'GlobalTech Daily'}, 'isBasedOn': p['source']}
        schema_json = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
        extra = f'<meta name="keywords" content="{e(keywords)}"><meta property="og:type" content="article"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(meta)}"><meta property="og:image" content="{SITE}/images/{slug}.jpg"><meta name="robots" content="max-image-preview:large"><link rel="alternate" hreflang="{alternate}" href="{SITE}/{alternate}/news/{slug}/"><script type="application/ld+json">{schema_json}</script>'
        content = f'<article><div class="tag">TECHNOLOGY</div><h1>{e(title)}</h1><p class="date">{e(date[:10])} · AI-assisted, source-attributed report</p><img class="hero" src="/images/{slug}.jpg" width="1200" height="675" alt="GlobalTech Daily illustration for {e(title)}"><div class="story">{paragraphs}</div><p class="source">Original source: <a href="{e(p["source"])}" rel="noopener noreferrer">{e(p.get("source_title") or "Official announcement")}</a></p><p class="notice">This article summarizes a publisher announcement. It has not been independently fact-checked.</p></article>'
        write(OUT / lang / 'news' / slug / 'index.html', shell(lang, title, meta, canonical, content, extra))
for lang in ('en', 'hi'):
    links = []
    for p in POSTS:
        slug = re.sub('[^a-f0-9]', '', str(p['id']))[:32]
        if not slug: continue
        title = p.get(lang + '_title') or p.get('en_title') or 'Technology News'
        links.append(f'<a class="item" href="/{lang}/news/{slug}/"><img src="/images/{slug}.jpg" loading="lazy" alt="" width="240" height="135"><div><h2>{e(title)}</h2><small>{e(p.get("date", "")[:10])}</small></div></a>')
    heading = 'Latest Technology News' if lang == 'en' else 'ताज़ा टेक्नोलॉजी समाचार'
    content = f'<h1>{heading}</h1><p>AI-assisted summaries with links to original publisher announcements.</p>' + (''.join(links) if links else '<p>No articles published yet.</p>')
    write(OUT / lang / 'index.html', shell(lang, heading + ' | GlobalTech Daily', heading, f'{SITE}/{lang}/', content))
    for slug, heading, text in [('about', 'About GlobalTech Daily', 'GlobalTech Daily is an independent technology news summary website. We publish bilingual, AI-assisted explainers based on attributed public announcements. We do not claim independent verification of publisher statements. For corrections email info@sellercalc.net.'), ('privacy', 'Privacy Policy', 'We publish static pages. Hosting and external links may involve technical logs or third-party data processing. We do not currently claim to operate an email newsletter or account system. For privacy enquiries email info@sellercalc.net. Update this policy before enabling analytics, advertising, cookies or contact forms.'), ('affiliate', 'Affiliate Disclosure', 'If we add affiliate links, we will label them clearly and may earn a commission at no extra cost to you. Editorial coverage is not paid placement unless specifically disclosed.'), ('contact', 'Contact and Corrections', 'For corrections, copyright requests, privacy enquiries or editorial feedback email info@sellercalc.net. Do not submit sensitive personal information.'), ('editorial', 'Editorial Policy', 'Articles are AI-assisted summaries of publicly available publisher announcements. Sources are linked. We aim for accuracy and do not invent quotes or claim independent verification. Corrections should be made promptly after review. Contact info@sellercalc.net.'), ('tools', 'Technology Tools', 'Technology guides and tools will be added after editorial review.')]:
        write(OUT / lang / slug / 'index.html', shell(lang, heading, text, f'{SITE}/{lang}/{slug}/', f'<h1>{heading}</h1><p>{text}</p>'))
write(OUT / 'index.html', '<!doctype html><html><head><meta http-equiv="refresh" content="0;url=/en/"></head><body><a href="/en/">English</a></body></html>')
write(OUT / 'style.css', 'body{font:18px/1.7 system-ui,sans-serif;background:#0c1628;color:#eaf1ff;max-width:960px;margin:auto;padding:20px}a{color:#8dd9ff}header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:18px 0;border-bottom:1px solid #35415c}.brand{font-size:25px;font-weight:800;text-decoration:none}main{min-height:65vh}h1{line-height:1.2;font-size:clamp(30px,5vw,46px)}h2{font-size:22px;line-height:1.3;margin:0}.item{display:flex;gap:20px;padding:20px 0;border-bottom:1px solid #35415c;text-decoration:none}.item img{width:180px;height:auto;object-fit:cover;border-radius:10px}.hero{width:100%;height:auto;border-radius:14px}.story{font-size:19px;line-height:1.85}.story p{margin:1.2em 0}.tag{color:#6cdbff;font-weight:bold}.date,.notice,small,footer{color:#b4bfd2}.source,.notice{border-top:1px solid #35415c;padding-top:18px}footer{margin-top:50px;border-top:1px solid #35415c;padding:22px 0}@media(max-width:550px){.item img{width:115px}.item{gap:12px}}')
write(OUT / 'robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
urls = ['/en/', '/hi/'] + [f'/{lang}/news/{p["id"]}/' for p in POSTS for lang in ('en', 'hi')]
write(OUT / 'sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + xml_escape(SITE + u) + '</loc></url>' for u in urls) + '</urlset>')
print('Built', len(POSTS), 'posts')
