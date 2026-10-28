from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import urlparse, quote
import os, html, json, shutil, re, datetime as dt, math, textwrap, hashlib
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parents[1]; OUT=R/'dist'; SITE=os.getenv('SITE_URL','https://globaltech-daily.pages.dev').rstrip('/'); CONTACT='info@sellercalc.net'
shutil.rmtree(OUT,ignore_errors=True);OUT.mkdir(parents=True)
(OUT/'googled7fc3627b4add656.html').write_text('google-site-verification: googled7fc3627b4add656.html\n',encoding='utf-8')
def e(x):return html.escape(str(x or ''),quote=True)
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def title(p,lang):return p.get(lang+'_title') or p.get('en_title') or 'Technology news'
CATEGORIES={'technology':('Technology','टेक्नोलॉजी'),'government-schemes':('Government Schemes','सरकारी योजनाएँ'),'sarkari-naukri':('Sarkari Naukri','सरकारी नौकरी'),'private-vacancy':('Private Vacancies','प्राइवेट नौकरी'),'movies-entertainment':('Movies & Entertainment','फिल्में और मनोरंजन'),'world-news':('World News','विश्व समाचार'),'business':('Business','बिज़नेस'),'sports':('Sports','खेल'),'automobiles':('Automobiles','ऑटोमोबाइल'),'health-science':('Health & Science','स्वास्थ्य और विज्ञान'),'gaming':('Gaming','गेमिंग'),'environment':('Environment','पर्यावरण'),'travel':('Travel','यात्रा'),'education':('Education','शिक्षा'),'lifestyle':('Lifestyle','लाइफस्टाइल')}
def category(p):return p.get('category') if p.get('category') in CATEGORIES else 'technology'
def slug(p):return re.sub('[^a-f0-9]','',str(p.get('id','')))[:32]
def article_slug(p):
 base=title(p,'en').lower()
 base=re.sub(r'[^a-z0-9]+','-',base).strip('-')[:75].rstrip('-')
 return (base or 'news')+'-'+slug(p)[:10]
def article_path(p,lang):
 return f'/{lang}/news/{category(p)}/{article_slug(p)}/'

POSTS=[]
for f in sorted((R/'content/posts').glob('*.json')):
 try:
  p=json.loads(f.read_text(encoding='utf-8'))
  if slug(p) and str(p.get('source','')).startswith('https://') and len(p.get('en_body',''))>=150:POSTS.append(p)
 except (OSError,ValueError,TypeError):pass
POSTS.sort(key=lambda x:x.get('date',''),reverse=True)
TOOLS=[('ChatGPT','Writing, reasoning and coding','https://chatgpt.com/','Assistant'),('Gemini','Multimodal AI assistant','https://gemini.google.com/','Assistant'),('Claude','Writing and analysis','https://claude.ai/','Assistant'),('Perplexity','Research with linked sources','https://www.perplexity.ai/','Research'),('NotebookLM','Research from your own sources','https://notebooklm.google.com/','Research'),('Google AI Studio','Experiment with Gemini models','https://aistudio.google.com/','Developer'),('Hugging Face','Explore models and datasets','https://huggingface.co/','Developer'),('Canva','Visual content design','https://www.canva.com/','Design'),('GitHub Copilot','AI-assisted programming','https://github.com/features/copilot','Developer'),('Adobe Firefly','Creative generative AI','https://firefly.adobe.com/','Design')]
CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f8fc;color:#15213a;font:16px/1.7 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#0a6ab7}a:hover{text-decoration:underline}img{max-width:100%}.wrap{max-width:1200px;margin:auto;padding:0 24px}.top{background:#0a1429;color:#fff}.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:20px;min-height:76px;flex-wrap:wrap}.logo{font-size:25px;font-weight:900;letter-spacing:-.9px;color:white;text-decoration:none}.logo span{color:#5ce0dc}nav{display:flex;gap:17px;flex-wrap:wrap}nav a{color:#d9e6fb;text-decoration:none;font-size:14px;font-weight:650}.lead{padding:44px 0 28px}.eyebrow{color:#0b8a93;font-size:12px;font-weight:850;letter-spacing:.12em;text-transform:uppercase}h1{font-size:clamp(32px,4.4vw,58px);line-height:1.12;letter-spacing:-.04em;margin:12px 0 20px}h2{line-height:1.25;letter-spacing:-.02em}p{margin:0 0 1.15em}.muted{color:#5b6c83}.layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:34px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card,.panel,.article{background:#fff;border:1px solid #e0e8f1;border-radius:18px;overflow:hidden;box-shadow:0 8px 30px rgba(13,35,72,.04)}.card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.card .inner{padding:20px}.card h2{font-size:21px;margin:6px 0 12px}.card a{text-decoration:none;color:inherit}.card a:hover{color:#006db1}.date{color:#60718b;font-size:13px}.panel{padding:22px;margin-bottom:20px}.panel h2{font-size:18px;margin-top:0}.panel a{display:block;padding:10px 0;border-bottom:1px solid #e8edf5;text-decoration:none}.panel a:last-child{border:0}.article{padding:clamp(18px,4vw,54px);max-width:850px;margin:34px auto}.article h1{font-size:clamp(30px,4vw,48px)}.article .hero{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:12px;margin:12px 0 26px}.story{font-size:18px;line-height:1.85}.story h2{font-size:27px;margin:36px 0 12px}.story h3{font-size:22px;margin:28px 0 10px}.story ul{padding-left:26px}.story p{margin:0 0 1.25em}.summary{background:#eef8fa;border-left:4px solid #079aa3;padding:18px 22px;border-radius:8px;margin:22px 0}.summary strong{display:block;margin-bottom:8px}.source{border-top:1px solid #dfe8f0;margin-top:32px;padding-top:20px}.tools{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.tool{background:white;border:1px solid #e0e8f1;border-radius:16px;padding:22px}.tool h2{font-size:21px;margin:5px 0}.pill{display:inline-block;padding:3px 10px;border-radius:20px;background:#e2f7f7;color:#006a71;font-size:12px;font-weight:700}.tool a{font-weight:750}.footer{margin-top:65px;background:#0a1429;color:#c9d5e7;padding:36px 0}.footer a{color:#b5e8fa}.footer .wrap{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}.footerlinks{display:flex;gap:14px;flex-wrap:wrap}.reading{position:fixed;top:0;left:0;height:3px;background:#06aeb8;width:0;z-index:9}.related{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.related a{display:block;background:#f2f7fc;padding:15px;border-radius:10px;text-decoration:none;font-weight:650}.langswitch{font-size:14px}.notice{font-size:13px;color:#62718b}.sectiontitle{display:flex;justify-content:space-between;align-items:center;margin:24px 0 20px}@media(max-width:900px){.layout{grid-template-columns:1fr}.tools{grid-template-columns:repeat(2,minmax(0,1fr))}.side{display:none}}@media(max-width:600px){.wrap{padding:0 16px}.top .wrap{padding-top:15px;padding-bottom:15px}.logo{font-size:22px}nav{gap:12px}nav a{font-size:13px}.lead{padding-top:25px}.cards,.tools,.related{grid-template-columns:1fr}.article{border-radius:0;margin:12px auto;padding:20px 16px}.story{font-size:17px}.story h2{font-size:23px}.card .inner{padding:16px}}'''
CSS += '''.card{min-width:0}.card>a{display:block}.card img{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:contain;background:#10223b}.card .inner{padding:17px 19px}.card h2{font-size:19px;line-height:1.35;overflow-wrap:anywhere}.article{width:min(100% - 32px,900px);max-width:900px}.article .hero{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:contain;background:#10223b}.story{max-width:74ch;margin:auto}.story p{line-height:1.85}.story h2{margin-top:1.8em}.lead{padding-bottom:16px}@media(max-width:600px){.article{width:100%;margin:12px auto}.card .inner{padding:15px}.card h2{font-size:18px}}'''
CSS += '''.featured-tools{margin:54px 0 10px;padding:30px;border-radius:24px;background:linear-gradient(145deg,#e8f6fb,#f5f8ff);border:1px solid #d5e7f2}.featured-tools .sectiontitle{margin-top:0}.featured-tools .tool{box-shadow:0 6px 18px rgba(10,30,60,.05)}.featured-tools .tool h3{font-size:19px;margin:8px 0}.featured-grid{grid-template-columns:repeat(4,minmax(0,1fr))}@media(max-width:950px){.featured-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.featured-tools{margin:32px 0;padding:18px}.featured-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.featured-grid .tool{padding:13px}.featured-grid .tool h3{font-size:16px}.featured-grid .tool p{font-size:13px}.featured-grid .tool a{font-size:12px}}''';write(OUT/'style.css',CSS)
JS='''addEventListener('scroll',()=>{let d=document.documentElement;let m=d.scrollHeight-d.clientHeight;let b=document.querySelector('.reading');if(b)b.style.width=(m>0?100*d.scrollTop/m:0)+'%';},{passive:true});'''
JS += """document.addEventListener('click',async function(ev){const share=ev.target.closest('.native-share');if(share){const data={title:share.dataset.shareTitle,url:share.dataset.shareUrl};if(navigator.share){try{await navigator.share(data)}catch(err){if(err.name!=='AbortError')location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}else{location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}const copy=ev.target.closest('.copy-share');if(copy){try{await navigator.clipboard.writeText(copy.dataset.shareUrl);const old=copy.textContent;copy.textContent='✓ Copied';setTimeout(()=>copy.textContent=old,1800)}catch(err){prompt('Copy link:',copy.dataset.shareUrl)}}});"""
CSS += """.category-pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:30px 0 48px;flex-wrap:wrap}.category-pagination a{display:inline-block;background:#fff;border:1px solid #d9e5f0;border-radius:9px;padding:8px 13px;text-decoration:none}"""
CSS += """.breadcrumbs{font-size:13px;line-height:1.6;color:#5b6c83;margin-bottom:14px;overflow-wrap:anywhere}.breadcrumbs a{color:#12588b;text-decoration:none}.breadcrumbs span{color:#667085}"""
CSS += """.article-share{padding:15px 20px;margin:18px 0;border:1px solid #dce5f1;background:#f5f9ff;border-radius:14px}.article-share strong{display:block;margin-bottom:10px}.share-actions{display:flex;flex-wrap:wrap;gap:9px}.share-actions a,.share-actions button{font:600 14px/1.3 system-ui,sans-serif;display:inline-block;border:1px solid #bed2e7;background:white;color:#12588b;border-radius:9px;padding:10px 12px;text-decoration:none;cursor:pointer}.share-actions a:hover,.share-actions button:hover{background:#e5f2ff}"""
write(OUT/'style.css',CSS)
write(OUT/'site.js',JS)
def shell(lang,t,desc,url,body,extra=''):
 nav=[('Home','होम',''),('AI Tools','AI टूल्स','tools/'),('Schemes','सरकारी योजनाएँ','government-schemes/'),('Jobs','सरकारी नौकरी','sarkari-naukri/'),('Private Jobs','प्राइवेट नौकरी','private-vacancy/'),('Movies','फिल्में','movies-entertainment/'),('World','दुनिया','world-news/'),('Business','बिज़नेस','business/'),('Sports','खेल','sports/'),('Gaming','गेमिंग','gaming/'),('Environment','पर्यावरण','environment/'),('Travel','यात्रा','travel/'),('Education','शिक्षा','education/'),('Lifestyle','लाइफस्टाइल','lifestyle/'),('About','हमारे बारे में','about/'),('Editorial','संपादकीय नीति','editorial/'),('Contact','संपर्क','contact/')]
 links=''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in nav)
 return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="google-site-verification" content="IjjkuYPqG93dE2SwPvi0HJ258E5WwNGAhIu7LB9qQqE"><meta name="theme-color" content="#0a1429"><title>{e(t)}</title><meta name="description" content="{e(desc[:160])}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{e(url)}"><link rel="alternate" hreflang="en" href="{e(url.replace('/hi/','/en/'))}"><link rel="alternate" hreflang="hi" href="{e(url.replace('/en/','/hi/'))}"><link rel="stylesheet" href="/style.css">{extra}</head><body><div class="reading"></div><header class="top"><div class="wrap"><a class="logo" href="/{lang}/">GlobalTech <span>Daily</span></a><nav aria-label="Primary">{links}<a class="langswitch" href="/{'hi' if lang=='en' else 'en'}/">{'हिन्दी' if lang=='en' else 'English'}</a></nav></div></header><main>{body}</main><footer class="footer"><div class="wrap"><div><strong>GlobalTech Daily</strong><p>Independent AI-assisted technology explainers with source attribution.</p><a href="mailto:{CONTACT}">{CONTACT}</a></div><div class="footerlinks">{''.join(f'<a href="/{lang}/{s}/">{s.title()}</a>' for s in ['about','privacy','contact','editorial','corrections','affiliate','tools'])}</div></div></footer><script defer src="/site.js"></script></body></html>'''
def has_featured(p):
 return (R/'content'/'featured'/f'{slug(p)}.jpg').is_file()

def image_for(p):
 """Only publish genuine article-specific featured images; never generate empty placeholders."""
 if not has_featured(p):return
 s=slug(p);dest=OUT/'images'/f'{s}.jpg';dest.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(R/'content'/'featured'/f'{s}.jpg',dest)
def body_html(raw):
 parts=[];buf=[]
 def flush():
  if buf:parts.append('<p>'+e(' '.join(buf))+'</p>');buf.clear()
 for line in str(raw).splitlines():
  line=line.strip()
  if not line:flush();continue
  if line.startswith('### '):flush();parts.append('<h3>'+e(line[4:])+'</h3>')
  elif line.startswith('## '):flush();parts.append('<h2>'+e(line[3:])+'</h2>')
  elif line.startswith('- '):flush();parts.append('<p>• '+e(line[2:])+'</p>')
  else:buf.append(line)
 flush();return ''.join(parts)
def image_caption(p,lang):
 s=slug(p)
 metadata=R/'content'/'featured'/f'{s}.json'
 if metadata.is_file():
  try:
   info=json.loads(metadata.read_text(encoding='utf-8'))
   if info.get('kind') in ('licensed_source','publisher_source'):
    credit=str(info.get('attribution') or 'Original publisher')
    license_name=str(info.get('license') or 'Creative Commons')
    return (f'Image source: {credit} — rights not verified' if info.get('kind')=='publisher_source' and lang=='en' else f'चित्र स्रोत: {credit} — अधिकार सत्यापित नहीं' if info.get('kind')=='publisher_source' else f'Publisher image: {credit} — {license_name}' if lang=='en' else f'प्रकाशक की तस्वीर: {credit} — {license_name}')
  except (OSError,ValueError):pass
 return 'AI-generated conceptual illustration — not an event photograph.' if lang=='en' else 'AI से बनाई गई सांकेतिक तस्वीर — वास्तविक घटना की फोटो नहीं।'
def card(p,lang):
 s=slug(p);t=title(p,lang)
 picture=f'<img loading="lazy" src="/images/{s}.jpg" width="1280" height="720" alt="{e(t)} — article featured image">' if has_featured(p) else ''
 return f'<article class="card"><a href="{article_path(p,lang)}">{picture}<div class="inner"><span class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=="en" else 1])}</span><h2>{e(t)}</h2><div class="date">{e(p.get("date","")[:10])} · {e(urlparse(p.get("source","")).hostname or "Source")}</div></div></a></article>'

def limit_article_words(raw,limit=150):
 parts=re.findall(r'\\S+',str(raw or ''))
 if len(parts)<=limit:return str(raw or '')
 return ' '.join(parts[:limit]).rstrip(' ,;:')+'…'

for p in POSTS:image_for(p)
for p in POSTS:
 s=slug(p)
 for lang in ('en','hi'):
  t=title(p,lang);raw=limit_article_words(p.get(lang+'_body') or p.get('en_body',''));url=f'{SITE}{article_path(p,lang)}';desc=p.get(lang+'_meta') or re.sub(r'[#\n]+',' ',raw)[:155]
  related=[q for q in POSTS if slug(q)!=s][:4];related_html=''.join(f'<a href="{article_path(q,lang)}">{e(title(q,lang))}</a>' for q in related)
  schema={'@context':'https://schema.org','@type':'NewsArticle','headline':t,'articleSection':CATEGORIES[category(p)][0],'datePublished':p.get('date'),'dateModified':p.get('date'),'inLanguage':lang,'mainEntityOfPage':url,'image':([f'{SITE}/images/{s}.jpg'] if has_featured(p) else []),'author':{'@type':'Organization','name':'GlobalTech Daily Editorial Desk'},'publisher':{'@type':'Organization','name':'GlobalTech Daily','url':SITE},'isBasedOn':p['source']}
  if not has_featured(p):schema.pop('image',None)
  schema['breadcrumb']={'@type':'BreadcrumbList','itemListElement':[
   {'@type':'ListItem','position':1,'name':'Home' if lang=='en' else 'होम','item':f'{SITE}/{lang}/'},
   {'@type':'ListItem','position':2,'name':CATEGORIES[category(p)][0 if lang=='en' else 1],'item':f'{SITE}/{lang}/{category(p)}/'},
   {'@type':'ListItem','position':3,'name':t,'item':url}]}
  schema['description']=desc[:160]
  schema['url']=url
  schema_json=json.dumps(schema,ensure_ascii=False).replace('<',chr(92)+'u003c')
  og_image=f'<meta property="og:image" content="{SITE}/images/{s}.jpg">' if has_featured(p) else ''
  extra=f'<meta property="og:type" content="article"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="GlobalTech Daily"><meta property="og:locale" content="{"en_US" if lang=="en" else "hi_IN"}"><meta property="og:title" content="{e(t)}"><meta property="og:description" content="{e(desc[:160])}"><meta property="article:published_time" content="{e(p.get("date",""))}"><meta property="article:section" content="{e(CATEGORIES[category(p)][0])}">{og_image}<meta name="twitter:card" content="{"summary_large_image" if has_featured(p) else "summary"}"><meta name="twitter:title" content="{e(t)}"><meta name="twitter:description" content="{e(desc[:160])}"><script type="application/ld+json">{schema_json}</script>'
  sourcehost=urlparse(p['source']).hostname or 'original source'
  summary=e(p.get(lang+'_summary') or p.get('en_summary') or re.sub(r'[#\n]+',' ',raw)[:270])
  featured_html=(f'<img class="hero" src="/images/{s}.jpg" width="1280" height="720" fetchpriority="high" alt="AI-generated conceptual illustration for {e(t)}"><p class="notice">{e(image_caption(p,lang))}</p>' if has_featured(p) else '')
  share_text=('Share this article' if lang=='en' else 'यह खबर शेयर करें')
  copy_text=('Copy link' if lang=='en' else 'लिंक कॉपी करें')
  share_html=(f'<div class="article-share"><strong>{share_text}</strong><div class="share-actions">'
    f'<button type="button" class="native-share" data-share-url="{e(url)}" data-share-title="{e(t)}">↗ {share_text}</button>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://api.whatsapp.com/send?text={quote(t+" "+url)}">WhatsApp</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://www.facebook.com/sharer/sharer.php?u={quote(url,safe="")}">Facebook</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://t.me/share/url?url={quote(url,safe="")}&text={quote(t)}">Telegram</a>'
    f'<button type="button" class="copy-share" data-share-url="{e(url)}">{copy_text}</button></div></div>')
  content=f'''<div class="wrap"><article class="article"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/{lang}/">{'Home' if lang=='en' else 'होम'}</a> › <a href="/{lang}/{category(p)}/">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</a> › <span>{e(t)}</span></nav><div class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</div><h1>{e(t)}</h1><p class="date">{e(p.get('date','')[:10])} · GlobalTech Daily Editorial Desk · Source: {e(sourcehost)}</p>{featured_html}{share_html}<div class="summary"><strong>{'Key takeaways' if lang=='en' else 'मुख्य बातें'}</strong>{summary}</div><div class="story">{body_html(raw)}</div><div class="source"><strong>{'Read the original source' if lang=='en' else 'मूल स्रोत पढ़ें'}:</strong> <a href="{e(p['source'])}" rel="noopener noreferrer" target="_blank">{e(p.get('source_title') or sourcehost)}</a><p class="notice">{'AI-assisted reporting; source claims are attributed and have not been independently verified.' if lang=='en' else 'AI की सहायता से तैयार रिपोर्ट; मूल स्रोत के दावों की स्वतंत्र पुष्टि नहीं की गई है।'}</p></div><h2>{'More to read' if lang=='en' else 'और पढ़ें'}</h2><div class="related">{related_html}</div></article></div>'''
  write(OUT / article_path(p,lang).lstrip('/') / 'index.html',shell(lang,t,desc,url,content,extra))
for lang in ('en','hi'):
 h='Worldwide news, movies and technology explained' if lang=='en' else 'टेक्नोलॉजी की ताज़ा खबरें, आसान भाषा में'
 desc='Worldwide news, movies, entertainment, technology, business, sports and useful explainers.'
 latest=''.join(card(p,lang) for p in POSTS[:24]) or '<p>No articles yet. New verified-source explainers are being prepared.</p>'
 sidebar='<aside class="side"><div class="panel"><h2>Explore AI tools</h2>'+''.join(f'<a href="/{lang}/tools/">{e(x[0])} · {e(x[3])}</a>' for x in TOOLS[:6])+'</div><div class="panel"><h2>Our approach</h2><p>Read original sources. Check dates. Explain what matters. Corrections welcome.</p></div></aside>'
 featured=''.join(f'<article class="tool"><span class="pill">{e(cat)}</span><h3>{e(n)}</h3><p>{e(d)}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{ "Official website" if lang=="en" else "आधिकारिक वेबसाइट"} ↗</a></article>' for n,d,u,cat in TOOLS[:8])
 tools_home=f'<section class="featured-tools" aria-labelledby="featured-tools-heading"><div class="sectiontitle"><h2 id="featured-tools-heading">{"Explore AI Tools" if lang=="en" else "AI टूल्स खोजें"}</h2><a href="/{lang}/tools/">{"View all AI tools" if lang=="en" else "सभी AI टूल्स देखें"} →</a></div><p class="muted">{"Explore trusted official links for writing, research, coding and design." if lang=="en" else "लेखन, रिसर्च, कोडिंग और डिजाइन के लिए आधिकारिक AI टूल्स।"}</p><div class="tools featured-grid">{featured}</div></section>'
 home=f'<div class="wrap"><section class="lead"><div class="eyebrow">WORLDWIDE NEWS & EXPLAINERS</div><h1>{h}</h1><p class="muted">{desc}</p></section><div class="sectiontitle"><h2>{"Latest stories" if lang=="en" else "नई खबरें"}</h2><a href="/{lang}/tools/">AI Tools →</a></div><div class="layout"><div class="cards">{latest}</div>{sidebar}</div>{tools_home}</div>'
 write(OUT/lang/'index.html',shell(lang,h+' | GlobalTech Daily',desc,f'{SITE}/{lang}/',home))
 page_size=24
 total_pages=max(1,(len(POSTS)+page_size-1)//page_size)
 def page_nav(page):
  prev=(f'<a href="/{lang}/" rel="prev">← {"Previous" if lang=="en" else "पिछला"}</a>' if page==2 else f'<a href="/{lang}/page/{page-1}/" rel="prev">← {"Previous" if lang=="en" else "पिछला"}</a>') if page>1 else ''
  nxt=f'<a href="/{lang}/page/{page+1}/" rel="next">{"Next" if lang=="en" else "अगला"} →</a>' if page<total_pages else ''
  return f'<nav aria-label="Article pages" style="display:flex;justify-content:space-between;align-items:center;gap:16px;margin:28px 0 42px;font-size:1.1rem"><span>{prev}</span><span>{page} / {total_pages}</span><span>{nxt}</span></nav>'
 home=home.replace(f'<div class="cards">{latest}</div>',f'<div><div class="cards">{latest}</div>{page_nav(1)}</div>')
 write(OUT/lang/'index.html',shell(lang,h+' | GlobalTech Daily',desc,f'{SITE}/{lang}/',home))
 for page in range(2,total_pages+1):
  batch=''.join(card(p,lang) for p in POSTS[(page-1)*page_size:page*page_size])
  paged=f'<div class="wrap"><div class="sectiontitle"><h1>{"Latest stories" if lang=="en" else "नई खबरें"} — {page}</h1></div><div class="layout"><div><div class="cards">{batch}</div>{page_nav(page)}</div>{sidebar}</div></div>'
  write(OUT/lang/'page'/str(page)/'index.html',shell(lang,f'News page {page} | GlobalTech Daily',desc,f'{SITE}/{lang}/page/{page}/',paged))

 for cat,(en_label,hi_label) in CATEGORIES.items():
  selected=[p for p in POSTS if category(p)==cat]
  heading=en_label if lang=='en' else hi_label
  intro=('Source-linked reports and explainers. Verify official notices, dates and eligibility with the issuing authority.' if lang=='en' else 'स्रोत सहित समाचार और जानकारी। आधिकारिक नोटिस, तारीख और पात्रता संबंधित विभाग से जरूर जाँचें।')
  cat_pages=max(1,(len(selected)+23)//24)
  for cat_page in range(1,cat_pages+1):
   batch=selected[(cat_page-1)*24:cat_page*24]
   listing=''.join(card(p,lang) for p in batch) or ('<p>No published articles in this category yet.</p>' if lang=='en' else '<p>इस श्रेणी में अभी कोई प्रकाशित लेख नहीं है।</p>')
   prev_url=(f'/{lang}/{cat}/' if cat_page==2 else f'/{lang}/{cat}/page/{cat_page-1}/') if cat_page>1 else ''
   next_url=f'/{lang}/{cat}/page/{cat_page+1}/' if cat_page<cat_pages else ''
   prev_link=f'<a href="{prev_url}" rel="prev">← {"Previous" if lang=="en" else "पिछला"}</a>' if prev_url else ''
   next_link=f'<a href="{next_url}" rel="next">{"Next" if lang=="en" else "अगला"} →</a>' if next_url else ''
   pager=f'<nav class="category-pagination" aria-label="Category pages">{prev_link}<span>{cat_page} / {cat_pages}</span>{next_link}</nav>' if cat_pages>1 else ''
   catbody=f'<div class="wrap"><section class="lead"><h1>{e(heading)}{f" — {cat_page}" if cat_page>1 else ""}</h1><p class="muted">{e(intro)}</p></section><div class="cards">{listing}</div>{pager}</div>'
   cat_path=f'/{lang}/{cat}/' if cat_page==1 else f'/{lang}/{cat}/page/{cat_page}/'
   write(OUT / cat_path.lstrip('/') / 'index.html',shell(lang,heading+(f' — Page {cat_page}' if cat_page>1 else '')+' | GlobalTech Daily',intro,f'{SITE}{cat_path}',catbody))

 toolcards=''.join(f'<article class="tool"><span class="pill">{e(cat)}</span><h2>{e(n)}</h2><p>{e(d)}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">Official website ↗</a></article>' for n,d,u,cat in TOOLS)
 tools=f'<div class="wrap"><section class="lead"><div class="eyebrow">AI TOOLS DIRECTORY</div><h1>{"Explore useful AI tools" if lang=="en" else "काम के AI टूल्स खोजें"}</h1><p class="muted">Official links, brief descriptions and categories. Availability and pricing can change; verify on provider websites.</p></section><div class="tools">{toolcards}</div></div>'
 write(OUT/lang/'tools/index.html',shell(lang,'AI Tools Directory | GlobalTech Daily','Explore popular AI assistants, research, coding and design tools.',f'{SITE}/{lang}/tools/',tools))
 pages={
 'about':('About GlobalTech Daily','GlobalTech Daily is an independent bilingual technology publication focused on useful explainers and news. We use AI-assisted drafting, link to source materials, and welcome corrections. We do not claim to independently verify every publisher statement.'),
 'editorial':('Editorial Policy','Our articles are based on attributed source material. We prioritize official announcements, documentation and credible reporting. AI may assist drafting and translation. We prohibit fabricated quotes, unsupported claims, misleading headlines, and unattributed copying. When a claim cannot be confirmed, we label uncertainty or do not publish it. Readers can request corrections.'),
 'corrections':('Corrections Policy','Report factual errors, misleading headlines, inaccurate translations, or rights concerns to info@sellercalc.net with the article URL and supporting evidence. Substantive corrections should be reflected in the article with an updated date.'),
 'privacy':('Privacy Policy','This website serves static pages. Hosting providers may process technical logs and IP addresses. External websites have their own privacy policies. We do not operate user accounts or a newsletter. If analytics, advertising, or cookies are added, this notice must be updated before deployment. Privacy enquiries: info@sellercalc.net.'),
 'contact':('Contact GlobalTech Daily','For news tips, corrections, image rights requests, privacy matters or editorial feedback, email info@sellercalc.net. Do not include sensitive personal information.'),
 'affiliate':('Affiliate Disclosure','Our AI Tools directory currently contains informational links. If affiliate partnerships or paid placements are introduced, they will be clearly identified. We do not claim that editorial recommendations are paid placements.')}
 for s,(t,d) in pages.items():
  content=f'<div class="wrap"><article class="article"><div class="eyebrow">GLOBALTECH DAILY</div><h1>{e(t)}</h1><div class="story"><p>{e(d)}</p></div><p>Contact: <a href="mailto:{CONTACT}">{CONTACT}</a></p></article></div>'
  write(OUT/lang/s/'index.html',shell(lang,t,d,f'{SITE}/{lang}/{s}/',content))
write(OUT/'index.html','<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url=/en/"><link rel="canonical" href="'+SITE+'/en/"></head><body><a href="/en/">English</a></body></html>')
write(OUT/'robots.txt',f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/news-sitemap.xml\n')
urls=[f'/{lang}/{path}' for lang in ('en','hi') for path in ('','tools/','government-schemes/','sarkari-naukri/','private-vacancy/','movies-entertainment/','world-news/','business/','sports/','automobiles/','health-science/','gaming/','environment/','travel/','education/','lifestyle/','technology/','about/','editorial/','corrections/','privacy/','contact/','affiliate/')]+[f'/{lang}/page/{page}/' for lang in ('en','hi') for page in range(2,max(1,(len(POSTS)+23)//24)+1)]+[f'/{lang}/{cat}/page/{page}/' for lang in ('en','hi') for cat in CATEGORIES for page in range(2,max(1,(sum(1 for p in POSTS if category(p)==cat)+23)//24)+1)]+[article_path(p,lang) for p in POSTS for lang in ('en','hi')]
write(OUT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(SITE+u)+'</loc></url>' for u in urls)+'</urlset>')
recent=[]
for p in POSTS:
 try:
  if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(p['date'].replace('Z','+00:00'))).total_seconds()>172800:continue
 except (ValueError,KeyError,TypeError):continue
 for lang in ('en','hi'):
  recent.append('<url><loc>'+xml_escape(f'{SITE}{article_path(p,lang)}')+'</loc><news:news><news:publication><news:name>GlobalTech Daily</news:name><news:language>'+lang+'</news:language></news:publication><news:publication_date>'+e(p['date'])+'</news:publication_date><news:title>'+xml_escape(title(p,lang))+'</news:title></news:news></url>')
write(OUT/'news-sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'+''.join(recent)+'</urlset>')
# Preserve old article URLs as permanent redirects to canonical descriptive URLs.
redirects=[]
for p in POSTS:
 for lang in ('en','hi'):
  redirects.append(f'/{lang}/news/{slug(p)}/ {article_path(p,lang)} 301')
write(OUT/'_redirects','\n'.join(redirects)+'\n')
write(OUT/'_headers','/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/style.css\n  Cache-Control: public, max-age=3600\n/images/*\n  Cache-Control: public, max-age=86400\n')
print('Built',len(POSTS),'posts; AI Tools, bilingual pages, news sitemap and responsive layout')
