from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import urlparse
import os, html, json, shutil, re, datetime as dt, math, textwrap, hashlib
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parents[1]; OUT=R/'dist'; SITE=os.getenv('SITE_URL','https://globaltech-daily.pages.dev').rstrip('/'); CONTACT='info@sellercalc.net'
shutil.rmtree(OUT,ignore_errors=True);OUT.mkdir(parents=True)
def e(x):return html.escape(str(x or ''),quote=True)
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def title(p,lang):return p.get(lang+'_title') or p.get('en_title') or 'Technology news'
def slug(p):return re.sub('[^a-f0-9]','',str(p.get('id','')))[:32]
POSTS=[]
for f in sorted((R/'content/posts').glob('*.json')):
 try:
  p=json.loads(f.read_text(encoding='utf-8'))
  if slug(p) and str(p.get('source','')).startswith('https://') and len(p.get('en_body',''))>=150:POSTS.append(p)
 except (OSError,ValueError,TypeError):pass
POSTS.sort(key=lambda x:x.get('date',''),reverse=True)
TOOLS=[('ChatGPT','Writing, reasoning and coding','https://chatgpt.com/','Assistant'),('Gemini','Multimodal AI assistant','https://gemini.google.com/','Assistant'),('Claude','Writing and analysis','https://claude.ai/','Assistant'),('Perplexity','Research with linked sources','https://www.perplexity.ai/','Research'),('NotebookLM','Research from your own sources','https://notebooklm.google.com/','Research'),('Google AI Studio','Experiment with Gemini models','https://aistudio.google.com/','Developer'),('Hugging Face','Explore models and datasets','https://huggingface.co/','Developer'),('Canva','Visual content design','https://www.canva.com/','Design'),('GitHub Copilot','AI-assisted programming','https://github.com/features/copilot','Developer'),('Adobe Firefly','Creative generative AI','https://firefly.adobe.com/','Design')]
CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f8fc;color:#15213a;font:16px/1.7 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#0a6ab7}a:hover{text-decoration:underline}img{max-width:100%}.wrap{max-width:1200px;margin:auto;padding:0 24px}.top{background:#0a1429;color:#fff}.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:20px;min-height:76px;flex-wrap:wrap}.logo{font-size:25px;font-weight:900;letter-spacing:-.9px;color:white;text-decoration:none}.logo span{color:#5ce0dc}nav{display:flex;gap:17px;flex-wrap:wrap}nav a{color:#d9e6fb;text-decoration:none;font-size:14px;font-weight:650}.lead{padding:44px 0 28px}.eyebrow{color:#0b8a93;font-size:12px;font-weight:850;letter-spacing:.12em;text-transform:uppercase}h1{font-size:clamp(32px,4.4vw,58px);line-height:1.12;letter-spacing:-.04em;margin:12px 0 20px}h2{line-height:1.25;letter-spacing:-.02em}p{margin:0 0 1.15em}.muted{color:#5b6c83}.layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:34px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card,.panel,.article{background:#fff;border:1px solid #e0e8f1;border-radius:18px;overflow:hidden;box-shadow:0 8px 30px rgba(13,35,72,.04)}.card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.card .inner{padding:20px}.card h2{font-size:21px;margin:6px 0 12px}.card a{text-decoration:none;color:inherit}.card a:hover{color:#006db1}.date{color:#60718b;font-size:13px}.panel{padding:22px;margin-bottom:20px}.panel h2{font-size:18px;margin-top:0}.panel a{display:block;padding:10px 0;border-bottom:1px solid #e8edf5;text-decoration:none}.panel a:last-child{border:0}.article{padding:clamp(18px,4vw,54px);max-width:850px;margin:34px auto}.article h1{font-size:clamp(30px,4vw,48px)}.article .hero{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:12px;margin:12px 0 26px}.story{font-size:18px;line-height:1.85}.story h2{font-size:27px;margin:36px 0 12px}.story h3{font-size:22px;margin:28px 0 10px}.story ul{padding-left:26px}.story p{margin:0 0 1.25em}.summary{background:#eef8fa;border-left:4px solid #079aa3;padding:18px 22px;border-radius:8px;margin:22px 0}.summary strong{display:block;margin-bottom:8px}.source{border-top:1px solid #dfe8f0;margin-top:32px;padding-top:20px}.tools{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.tool{background:white;border:1px solid #e0e8f1;border-radius:16px;padding:22px}.tool h2{font-size:21px;margin:5px 0}.pill{display:inline-block;padding:3px 10px;border-radius:20px;background:#e2f7f7;color:#006a71;font-size:12px;font-weight:700}.tool a{font-weight:750}.footer{margin-top:65px;background:#0a1429;color:#c9d5e7;padding:36px 0}.footer a{color:#b5e8fa}.footer .wrap{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}.footerlinks{display:flex;gap:14px;flex-wrap:wrap}.reading{position:fixed;top:0;left:0;height:3px;background:#06aeb8;width:0;z-index:9}.related{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.related a{display:block;background:#f2f7fc;padding:15px;border-radius:10px;text-decoration:none;font-weight:650}.langswitch{font-size:14px}.notice{font-size:13px;color:#62718b}.sectiontitle{display:flex;justify-content:space-between;align-items:center;margin:24px 0 20px}@media(max-width:900px){.layout{grid-template-columns:1fr}.tools{grid-template-columns:repeat(2,minmax(0,1fr))}.side{display:none}}@media(max-width:600px){.wrap{padding:0 16px}.top .wrap{padding-top:15px;padding-bottom:15px}.logo{font-size:22px}nav{gap:12px}nav a{font-size:13px}.lead{padding-top:25px}.cards,.tools,.related{grid-template-columns:1fr}.article{border-radius:0;margin:12px auto;padding:20px 16px}.story{font-size:17px}.story h2{font-size:23px}.card .inner{padding:16px}}'''
CSS += '''.featured-tools{margin:54px 0 10px;padding:30px;border-radius:24px;background:linear-gradient(145deg,#e8f6fb,#f5f8ff);border:1px solid #d5e7f2}.featured-tools .sectiontitle{margin-top:0}.featured-tools .tool{box-shadow:0 6px 18px rgba(10,30,60,.05)}.featured-tools .tool h3{font-size:19px;margin:8px 0}.featured-grid{grid-template-columns:repeat(4,minmax(0,1fr))}@media(max-width:950px){.featured-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.featured-tools{margin:32px 0;padding:18px}.featured-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.featured-grid .tool{padding:13px}.featured-grid .tool h3{font-size:16px}.featured-grid .tool p{font-size:13px}.featured-grid .tool a{font-size:12px}}''';write(OUT/'style.css',CSS)
JS='''addEventListener('scroll',()=>{let d=document.documentElement;let m=d.scrollHeight-d.clientHeight;let b=document.querySelector('.reading');if(b)b.style.width=(m>0?100*d.scrollTop/m:0)+'%';},{passive:true});'''
write(OUT/'site.js',JS)
def shell(lang,t,desc,url,body,extra=''):
 nav=[('Home','होम',''),('AI Tools','AI टूल्स','tools/'),('About','हमारे बारे में','about/'),('Editorial','संपादकीय नीति','editorial/'),('Contact','संपर्क','contact/')]
 links=''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in nav)
 return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0a1429"><title>{e(t)}</title><meta name="description" content="{e(desc[:160])}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{e(url)}"><link rel="alternate" hreflang="en" href="{e(url.replace('/hi/','/en/'))}"><link rel="alternate" hreflang="hi" href="{e(url.replace('/en/','/hi/'))}"><link rel="stylesheet" href="/style.css">{extra}</head><body><div class="reading"></div><header class="top"><div class="wrap"><a class="logo" href="/{lang}/">GlobalTech <span>Daily</span></a><nav aria-label="Primary">{links}<a class="langswitch" href="/{'hi' if lang=='en' else 'en'}/">{'हिन्दी' if lang=='en' else 'English'}</a></nav></div></header><main>{body}</main><footer class="footer"><div class="wrap"><div><strong>GlobalTech Daily</strong><p>Independent AI-assisted technology explainers with source attribution.</p><a href="mailto:{CONTACT}">{CONTACT}</a></div><div class="footerlinks">{''.join(f'<a href="/{lang}/{s}/">{s.title()}</a>' for s in ['about','privacy','contact','editorial','corrections','affiliate','tools'])}</div></div></footer><script defer src="/site.js"></script></body></html>'''
def image_for(p):
 """Create distinctive topic-led editorial art; never imply it is an event photograph."""
 s=slug(p); dest=OUT/'images'/f'{s}.jpg'; dest.parent.mkdir(parents=True,exist_ok=True)
 topic=' '.join(str(p.get(k,'')) for k in ('en_title','en_keywords','source_title')).lower()
 topics=[
  ('SECURITY','CYBERSECURITY',('security','vulnerability','waf','certificate','cryptograph','attack','exposure','breach','phishing','zero-day','compliance','isms','php','encryption')),
  ('CHIP','SEMICONDUCTORS',('chip','semiconductor','gpu','processor','nvidia','silicon','cpu')),
  ('DEVICE','DEVICES',('phone','iphone','pixel','android','smartphone','laptop','macbook','device','wearable')),
  ('ROBOT','ROBOTICS',('robot','automation','humanoid','drone')),
  ('CLOUD','CLOUD & WEB',('cloud infrastructure','cloud service','server','hosting','web','network','typescript','rust','cache','api','kv','edge','storefront')),
  ('SCIENCE','RESEARCH',('research','university','stanford','science','brain','learning','education','study')),
  ('AI','ARTIFICIAL INTELLIGENCE',('ai','gemini','chatgpt','openai','llm','model','machine learning','agent')),
  ('COMMERCE','DIGITAL BUSINESS',('commerce','marketing','retail','shopping','payment','advertising'))]
 # Priority uses article-specific signals; general company words do not override precise topics.
 cat,label='TECH','TECHNOLOGY'
 for name,tag,words in topics:
  if any(w in topic for w in words):cat,label=name,tag;break
 seed=int(hashlib.sha256((p.get('source_title','')+s).encode()).hexdigest()[:8],16)
 palettes={'SECURITY':('#071e33','#0c465b','#4ef3ce'),'CHIP':('#101733','#293b8a','#b5a4ff'),'DEVICE':('#11263d','#2463a0','#ffbd77'),'ROBOT':('#172036','#36678b','#ffd06c'),'CLOUD':('#092c37','#155f7b','#70d5ff'),'SCIENCE':('#132640','#425d8b','#b1e879'),'AI':('#201a40','#6249a3','#a9f4fc'),'COMMERCE':('#24213b','#75549a','#ffb77c'),'TECH':('#15233b','#255b81','#82e8d4')}
 bg,mid,accent=palettes[cat]; im=Image.new('RGB',(1280,720),bg);d=ImageDraw.Draw(im)
 # Atmospheric layered background, kept away from headline-free art.
 d.ellipse((650,-380,1450,420),fill=mid)
 d.ellipse((835,-210,1470,430),outline=accent,width=3)
 for i in range(8):
  x=65+i*160;d.line((x,570,x+260,705),fill=mid,width=2)
 # Large illustrative focal element on the right.
 cx,cy=880,325
 if cat=='SECURITY':
  d.polygon([(cx,cy-205),(cx+172,cy-135),(cx+152,cy+95),(cx,cy+215),(cx-152,cy+95),(cx-172,cy-135)],fill='#16495b',outline=accent,width=12)
  d.arc((cx-70,cy-75,cx+70,cy+65),185,355,fill='#ffffff',width=16)
  d.rounded_rectangle((cx-86,cy-15,cx+86,cy+105),radius=18,fill=accent)
  d.ellipse((cx-12,cy+28,cx+12,cy+52),fill=bg);d.rectangle((cx-5,cy+49,cx+5,cy+79),fill=bg)
 elif cat=='CHIP':
  d.rounded_rectangle((cx-175,cy-175,cx+175,cy+175),radius=35,fill='#27386b',outline=accent,width=10)
  d.rounded_rectangle((cx-100,cy-100,cx+100,cy+100),radius=20,outline='#ffffff',width=7)
  for off in range(-130,131,65):
   d.line((cx+off,cy-175,cx+off,cy-220),fill=accent,width=9);d.line((cx+off,cy+175,cx+off,cy+220),fill=accent,width=9)
   d.line((cx-175,cy+off,cx-220,cy+off),fill=accent,width=9);d.line((cx+175,cy+off,cx+220,cy+off),fill=accent,width=9)
 elif cat=='DEVICE':
  d.rounded_rectangle((cx-128,cy-230,cx+128,cy+230),radius=38,fill='#06182c',outline=accent,width=12)
  d.rounded_rectangle((cx-104,cy-194,cx+104,cy+180),radius=16,fill='#255e91')
  d.ellipse((cx-75,cy-125,cx+75,cy+25),outline='#ffffff',width=10)
  d.line((cx-60,cy+92,cx+60,cy+92),fill=accent,width=10)
 elif cat=='ROBOT':
  d.rounded_rectangle((cx-175,cy-145,cx+175,cy+165),radius=75,fill='#34526b',outline=accent,width=12)
  d.ellipse((cx-112,cy-32,cx-45,cy+35),fill=accent);d.ellipse((cx+45,cy-32,cx+112,cy+35),fill=accent)
  d.arc((cx-90,cy-5,cx+90,cy+100),15,165,fill='#ffffff',width=10)
  d.line((cx,cy-145,cx,cy-205),fill=accent,width=12);d.ellipse((cx-20,cy-225,cx+20,cy-185),fill=accent)
 elif cat=='CLOUD':
  d.ellipse((cx-160,cy-65,cx+15,cy+110),fill=accent)
  d.ellipse((cx-45,cy-160,cx+180,cy+95),fill=accent)
  d.rounded_rectangle((cx-190,cy-30,cx+210,cy+125),radius=60,fill=accent)
  for k in range(3):
   yy=cy+180+k*45;d.line((cx-150,yy,cx+145,yy),fill='#d9f8ff',width=9)
 elif cat=='SCIENCE':
  for r in (80,140,205):d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=accent,width=5)
  for dx,dy in ((-185,0),(185,0),(0,-185),(0,185),(120,120),(-120,-120)):
   d.line((cx,cy,cx+dx,cy+dy),fill='#c6e4f0',width=6);d.ellipse((cx+dx-16,cy+dy-16,cx+dx+16,cy+dy+16),fill=accent)
  d.ellipse((cx-35,cy-35,cx+35,cy+35),fill='#ffffff')
 elif cat=='AI':
  for x,y in ((-145,-110),(0,-190),(145,-110),(-145,110),(0,190),(145,110)):
   d.line((cx,cy,cx+x,cy+y),fill=accent,width=10);d.ellipse((cx+x-24,cy+y-24,cx+x+24,cy+y+24),fill='#ffffff')
  d.rounded_rectangle((cx-110,cy-110,cx+110,cy+110),radius=50,fill='#423e8c',outline=accent,width=12)
  d.ellipse((cx-42,cy-42,cx+42,cy+42),fill=accent)
 else:
  for i,h in enumerate((130,210,160,285)):
   x=cx-170+i*110;d.rounded_rectangle((x,cy+160-h,x+70,cy+160),radius=10,fill=accent if i%2 else '#e6f8ff')
  d.line((cx-220,cy+175,cx+245,cy+175),fill='#ffffff',width=8)
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf';normal='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
 if Path(font).exists(): f=ImageFont.truetype(font,58);small=ImageFont.truetype(normal,25);tagfont=ImageFont.truetype(font,24)
 else:f=small=tagfont=ImageFont.load_default()
 d.rounded_rectangle((70,85,360,141),radius=14,fill=accent)
 d.text((92,100),'GLOBALTECH DAILY',font=tagfont,fill=bg)
 # Short, readable category label, not a duplicate of the full headline.
 words=label.split();lines=[];line=''
 for word in words:
  candidate=(line+' '+word).strip()
  if d.textbbox((0,0),candidate,font=f)[2]>525 and line:lines.append(line);line=word
  else:line=candidate
 if line:lines.append(line)
 for i,line in enumerate(lines[:3]):d.text((75,250+i*79),line,font=f,fill='#ffffff')
 d.line((75,565,550,565),fill=accent,width=9)
 d.text((75,590),'Original editorial illustration',font=small,fill='#cbd9eb')
 im.save(dest,'JPEG',quality=87,optimize=True)
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
def card(p,lang):
 s=slug(p);t=title(p,lang);return f'<article class="card"><a href="/{lang}/news/{s}/"><img loading="lazy" src="/images/{s}.jpg" width="1280" height="720" alt="Original editorial illustration for {e(t)}"><div class="inner"><span class="eyebrow">TECH NEWS</span><h2>{e(t)}</h2><div class="date">{e(p.get("date","")[:10])} · {e(urlparse(p.get("source","")).hostname or "Source")}</div></div></a></article>'
for p in POSTS:image_for(p)
for p in POSTS:
 s=slug(p)
 for lang in ('en','hi'):
  t=title(p,lang);raw=p.get(lang+'_body') or p.get('en_body','');url=f'{SITE}/{lang}/news/{s}/';desc=p.get(lang+'_meta') or re.sub(r'[#\n]+',' ',raw)[:155]
  related=[q for q in POSTS if slug(q)!=s][:4];related_html=''.join(f'<a href="/{lang}/news/{slug(q)}/">{e(title(q,lang))}</a>' for q in related)
  schema={'@context':'https://schema.org','@type':'NewsArticle','headline':t,'datePublished':p.get('date'),'dateModified':p.get('date'),'inLanguage':lang,'mainEntityOfPage':url,'image':[f'{SITE}/images/{s}.jpg'],'author':{'@type':'Organization','name':'GlobalTech Daily Editorial Desk'},'publisher':{'@type':'Organization','name':'GlobalTech Daily'},'isBasedOn':p['source']}
  extra=f'<meta property="og:type" content="article"><meta property="og:title" content="{e(t)}"><meta property="og:description" content="{e(desc)}"><meta property="og:image" content="{SITE}/images/{s}.jpg"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace('<', chr(92) + 'u003c')}</script>'
  sourcehost=urlparse(p['source']).hostname or 'original source'
  summary=e(p.get(lang+'_summary') or p.get('en_summary') or re.sub(r'[#\n]+',' ',raw)[:270])
  content=f'''<div class="wrap"><article class="article"><div class="eyebrow">TECHNOLOGY / EXPLAINED</div><h1>{e(t)}</h1><p class="date">{e(p.get('date','')[:10])} · GlobalTech Daily Editorial Desk · Source: {e(sourcehost)}</p><img class="hero" src="/images/{s}.jpg" width="1280" height="720" fetchpriority="high" alt="Original editorial illustration for {e(t)}"><div class="summary"><strong>{'Key takeaways' if lang=='en' else 'मुख्य बातें'}</strong>{summary}</div><div class="story">{body_html(raw)}</div><div class="source"><strong>{'Read the original source' if lang=='en' else 'मूल स्रोत पढ़ें'}:</strong> <a href="{e(p['source'])}" rel="noopener noreferrer" target="_blank">{e(p.get('source_title') or sourcehost)}</a><p class="notice">{'AI-assisted reporting; source claims are attributed and have not been independently verified.' if lang=='en' else 'AI की सहायता से तैयार रिपोर्ट; मूल स्रोत के दावों की स्वतंत्र पुष्टि नहीं की गई है।'}</p></div><h2>{'More to read' if lang=='en' else 'और पढ़ें'}</h2><div class="related">{related_html}</div></article></div>'''
  write(OUT/lang/'news'/s/'index.html',shell(lang,t,desc,url,content,extra))
for lang in ('en','hi'):
 h='Latest technology news, explained' if lang=='en' else 'टेक्नोलॉजी की ताज़ा खबरें, आसान भाषा में'
 desc='Source-attributed technology news, practical AI tools and useful explainers.'
 latest=''.join(card(p,lang) for p in POSTS[:24]) or '<p>No articles yet. New verified-source explainers are being prepared.</p>'
 sidebar='<aside class="side"><div class="panel"><h2>Explore AI tools</h2>'+''.join(f'<a href="/{lang}/tools/">{e(x[0])} · {e(x[3])}</a>' for x in TOOLS[:6])+'</div><div class="panel"><h2>Our approach</h2><p>Read original sources. Check dates. Explain what matters. Corrections welcome.</p></div></aside>'
 featured=''.join(f'<article class="tool"><span class="pill">{e(cat)}</span><h3>{e(n)}</h3><p>{e(d)}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{ "Official website" if lang=="en" else "आधिकारिक वेबसाइट"} ↗</a></article>' for n,d,u,cat in TOOLS[:8])
 tools_home=f'<section class="featured-tools" aria-labelledby="featured-tools-heading"><div class="sectiontitle"><h2 id="featured-tools-heading">{"Explore AI Tools" if lang=="en" else "AI टूल्स खोजें"}</h2><a href="/{lang}/tools/">{"View all AI tools" if lang=="en" else "सभी AI टूल्स देखें"} →</a></div><p class="muted">{"Explore trusted official links for writing, research, coding and design." if lang=="en" else "लेखन, रिसर्च, कोडिंग और डिजाइन के लिए आधिकारिक AI टूल्स।"}</p><div class="tools featured-grid">{featured}</div></section>'
 home=f'<div class="wrap"><section class="lead"><div class="eyebrow">INDEPENDENT TECH EXPLAINERS</div><h1>{h}</h1><p class="muted">{desc}</p></section><div class="sectiontitle"><h2>{"Latest stories" if lang=="en" else "नई खबरें"}</h2><a href="/{lang}/tools/">AI Tools →</a></div><div class="layout"><div class="cards">{latest}</div>{sidebar}</div>{tools_home}</div>'
 write(OUT/lang/'index.html',shell(lang,h+' | GlobalTech Daily',desc,f'{SITE}/{lang}/',home))
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
urls=[f'/{lang}/{path}' for lang in ('en','hi') for path in ('','tools/','about/','editorial/','corrections/','privacy/','contact/','affiliate/')]+[f'/{lang}/news/{slug(p)}/' for p in POSTS for lang in ('en','hi')]
write(OUT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(SITE+u)+'</loc></url>' for u in urls)+'</urlset>')
recent=[]
for p in POSTS:
 try:
  if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(p['date'].replace('Z','+00:00'))).total_seconds()>172800:continue
 except (ValueError,KeyError,TypeError):continue
 for lang in ('en','hi'):
  recent.append('<url><loc>'+xml_escape(f'{SITE}/{lang}/news/{slug(p)}/')+'</loc><news:news><news:publication><news:name>GlobalTech Daily</news:name><news:language>'+lang+'</news:language></news:publication><news:publication_date>'+e(p['date'])+'</news:publication_date><news:title>'+xml_escape(title(p,lang))+'</news:title></news:news></url>')
write(OUT/'news-sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'+''.join(recent)+'</urlset>')
write(OUT/'_headers','/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/style.css\n  Cache-Control: public, max-age=3600\n/images/*\n  Cache-Control: public, max-age=86400\n')
print('Built',len(POSTS),'posts; AI Tools, bilingual pages, news sitemap and responsive layout')
