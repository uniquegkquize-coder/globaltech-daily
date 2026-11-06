from pathlib import Path
from link_resources import render as render_link_resources
from article_layout import render as render_article, guide_body, excerpt, CSS as ARTICLE_CSS
from news_sitemap import write_news_sitemap, is_news_article
from seo_text import description as seo_description
from seo_site import head as seo_head, article_languages, iso_date, json_ld, category_description, write_site_sitemap, related_index, ROBOTS
from redirect_assets import write_redirects
from site_ui import MENU_CSS, label
from news_config import CATEGORIES, memberships
from news_hub import HUB_CSS, HUB_JS, render_hubs, recent_priority, news_sort, matches_category, official_notice_rows
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import urlparse, quote
import os, html, json, shutil, re, datetime as dt, math, textwrap, hashlib, functools
from PIL import Image, ImageDraw, ImageFont
from expanded_hubs import CSS as GLOBAL_CSS, JS as GLOBAL_JS, render_expanded_hubs, article_note
from notice_details import CSS as EXAM_CSS, inline as linked_inline, article_panel, render_notices, notice_path, details_cache
from official_notices import load_notices
from directories import CSS as DIRECTORY_CSS, JS as DIRECTORY_JS, render as render_directories
R=Path(__file__).resolve().parents[1]; OUT=R/'dist'; SITE='https://globewiredaily.org'.rstrip('/'); CONTACT='contact@globewiredaily.org'
OUT.mkdir(parents=True,exist_ok=True)
# Remove only obsolete build-generated HTML redirect stubs. Never remove article pages.
# The redirect generator recreates every currently required stub later in this build.
def clean_generated_redirect_stubs():
 count=0
 for p in OUT.rglob('index.html'):
  try:
   if p.stat().st_size > 2048: continue
   body=p.read_text(encoding='utf-8')
   if '<title>Article moved</title>' not in body or '<meta http-equiv="refresh"' not in body: continue
   p.unlink()
   count+=1
  except (OSError, UnicodeError): continue
 print('CLEAN_GENERATED_REDIRECT_STUBS',count)
clean_generated_redirect_stubs()

(OUT/'d9e47b8c32a16f5098c7d6e5b4a3210f.txt').write_text('d9e47b8c32a16f5098c7d6e5b4a3210f\n',encoding='utf-8')
GENERATED_HTML=set()
(OUT/'googled7fc3627b4add656.html').write_text('google-site-verification: googled7fc3627b4add656.html\n',encoding='utf-8')
def e(x):return html.escape(str(x or ''),quote=True)
def write(p,s):
 if p.name=='index.html':GENERATED_HTML.add(p.relative_to(OUT).as_posix())
 p.parent.mkdir(parents=True,exist_ok=True)
 data=s.encode('utf-8')
 if p.is_file() and p.read_bytes()==data:return
 p.write_bytes(data)
def title(p,lang):
 raw=str(p.get(lang+'_seo_title') or p.get(lang+'_title') or p.get('en_title') or 'Technology news')
 if p.get('directory_name') and p.get('content_type')=='evergreen_directory_guide' and not p.get(lang+'_seo_title'):
  suffix={'phones':('Specifications & buying guide','स्पेसिफिकेशन और खरीद गाइड'),'cars':('Specifications, variants & buying guide','स्पेसिफिकेशन, वेरिएंट और खरीद गाइड'),'bikes':('Specifications & buying guide','स्पेसिफिकेशन और खरीद गाइड'),'colleges':('Courses, fees & admission guide','कोर्स, फीस और एडमिशन गाइड')}.get(p.get('directory_kind'))
  if suffix:raw=p['directory_name']+': '+suffix[lang=='hi']
 return re.sub(r'\s*[—–-]\s*article featured image\s*$', '', raw, flags=re.I).strip()
TOOLS=[('ChatGPT','Writing, reasoning and coding','https://chatgpt.com/','Assistant'),('Gemini','Multimodal AI assistant','https://gemini.google.com/','Assistant'),('Claude','Writing and analysis','https://claude.ai/','Assistant'),('Perplexity','Research with linked sources','https://www.perplexity.ai/','Research'),('NotebookLM','Research from your own sources','https://notebooklm.google.com/','Research'),('Google AI Studio','Experiment with Gemini models','https://aistudio.google.com/','Developer'),('Hugging Face','Explore models and datasets','https://huggingface.co/','Developer'),('Canva','Visual content design','https://www.canva.com/','Design'),('GitHub Copilot','AI-assisted programming','https://github.com/features/copilot','Developer'),('Adobe Firefly','Creative generative AI','https://firefly.adobe.com/','Design')]
def category(p):return p.get('category') if p.get('category') in CATEGORIES else 'technology'
def slug(p):return re.sub('[^a-f0-9]','',str(p.get('id','')))[:32]
def article_slug(p):
 base=str(p.get('url_title') or p.get('en_title') or 'news').lower()
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
# Collapse repeat imports of the same source (RSS tracking parameters are ignored).
# Keep the article with the most substantive body, retaining every old URL.
DUPLICATE_POSTS=[]
_unique={}
for _post in sorted(POSTS,key=lambda p:(len(p.get('en_body','')),p.get('date','')),reverse=True):
 _u=urlparse(_post['source'])
 _key=(_u.netloc.lower().removeprefix('www.'),_u.path.rstrip('/'))
 _headline=re.sub(r'[^a-z0-9]+',' ',str(_post.get('en_title','')).lower()).strip()
 _existing=_unique.get(('source',_key)) or _unique.get(('headline',_headline))
 if _existing:
  DUPLICATE_POSTS.append((_post,_existing))
 else:
  _unique[('source',_key)]=_post
  _unique[('headline',_headline)]=_post
POSTS=list({p['id']:p for p in _unique.values()}.values())
POSTS.sort(key=news_sort)
TOOLS=[('ChatGPT','Writing, reasoning and coding','https://chatgpt.com/','Assistant'),('Gemini','Multimodal AI assistant','https://gemini.google.com/','Assistant'),('Claude','Writing and analysis','https://claude.ai/','Assistant'),('Perplexity','Research with linked sources','https://www.perplexity.ai/','Research'),('NotebookLM','Research from your own sources','https://notebooklm.google.com/','Research'),('Google AI Studio','Experiment with Gemini models','https://aistudio.google.com/','Developer'),('Hugging Face','Explore models and datasets','https://huggingface.co/','Developer'),('Canva','Visual content design','https://www.canva.com/','Design'),('GitHub Copilot','AI-assisted programming','https://github.com/features/copilot','Developer'),('Adobe Firefly','Creative generative AI','https://firefly.adobe.com/','Design')]
CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f8fc;color:#15213a;font:16px/1.7 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#0a6ab7}a:hover{text-decoration:underline}img{max-width:100%}.wrap{max-width:1200px;margin:auto;padding:0 24px}.top{background:#0a1429;color:#fff}.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:20px;min-height:76px;flex-wrap:wrap}.logo{font-size:25px;font-weight:900;letter-spacing:-.9px;color:white;text-decoration:none}.logo span{color:#5ce0dc}nav{display:flex;gap:17px;flex-wrap:wrap}nav a{color:#d9e6fb;text-decoration:none;font-size:14px;font-weight:650}.lead{padding:44px 0 28px}.eyebrow{color:#0b8a93;font-size:12px;font-weight:850;letter-spacing:.12em;text-transform:uppercase}h1{font-size:clamp(32px,4.4vw,58px);line-height:1.12;letter-spacing:-.04em;margin:12px 0 20px}h2{line-height:1.25;letter-spacing:-.02em}p{margin:0 0 1.15em}.muted{color:#5b6c83}.layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:34px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card,.panel,.article{background:#fff;border:1px solid #e0e8f1;border-radius:18px;overflow:hidden;box-shadow:0 8px 30px rgba(13,35,72,.04)}.card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.card .inner{padding:20px}.card h2{font-size:21px;margin:6px 0 12px}.card a{text-decoration:none;color:inherit}.card a:hover{color:#006db1}.date{color:#60718b;font-size:13px}.panel{padding:22px;margin-bottom:20px}.panel h2{font-size:18px;margin-top:0}.panel a{display:block;padding:10px 0;border-bottom:1px solid #e8edf5;text-decoration:none}.panel a:last-child{border:0}.article{padding:clamp(18px,4vw,54px);max-width:850px;margin:34px auto}.article h1{font-size:clamp(30px,4vw,48px)}.article .hero{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:12px;margin:12px 0 26px}.story{font-size:18px;line-height:1.85}.story h2{font-size:27px;margin:36px 0 12px}.story h3{font-size:22px;margin:28px 0 10px}.story ul{padding-left:26px}.story p{margin:0 0 1.25em}.summary{background:#eef8fa;border-left:4px solid #079aa3;padding:18px 22px;border-radius:8px;margin:22px 0}.summary strong{display:block;margin-bottom:8px}.source{border-top:1px solid #dfe8f0;margin-top:32px;padding-top:20px}.tools{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.tool{background:white;border:1px solid #e0e8f1;border-radius:16px;padding:22px}.tool h2{font-size:21px;margin:5px 0}.pill{display:inline-block;padding:3px 10px;border-radius:20px;background:#e2f7f7;color:#006a71;font-size:12px;font-weight:700}.tool a{font-weight:750}.footer{margin-top:65px;background:#0a1429;color:#c9d5e7;padding:36px 0}.footer a{color:#b5e8fa}.footer .wrap{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}.footerlinks{display:flex;gap:14px;flex-wrap:wrap}.reading{position:fixed;top:0;left:0;height:3px;background:#06aeb8;width:0;z-index:9}.related{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.related a{display:block;background:#f2f7fc;padding:15px;border-radius:10px;text-decoration:none;font-weight:650}.langswitch{font-size:14px}.notice{font-size:13px;color:#62718b}.sectiontitle{display:flex;justify-content:space-between;align-items:center;margin:24px 0 20px}@media(max-width:900px){.layout{grid-template-columns:1fr}.tools{grid-template-columns:repeat(2,minmax(0,1fr))}.side{display:none}}@media(max-width:600px){.wrap{padding:0 16px}.top .wrap{padding-top:15px;padding-bottom:15px}.logo{font-size:22px}nav{gap:12px}nav a{font-size:13px}.lead{padding-top:25px}.cards,.tools,.related{grid-template-columns:1fr}.article{border-radius:0;margin:12px auto;padding:20px 16px}.story{font-size:17px}.story h2{font-size:23px}.card .inner{padding:16px}}'''
CSS += '''.card{min-width:0}.card>a{display:block}.card img{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:contain;background:#10223b}.card .inner{padding:17px 19px}.card h2{font-size:19px;line-height:1.35;overflow-wrap:anywhere}.article{width:min(100% - 32px,900px);max-width:900px}.article .hero{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:contain;background:#10223b}.story{max-width:74ch;margin:auto}.story p{line-height:1.85}.story h2{margin-top:1.8em}.lead{padding-bottom:16px}@media(max-width:600px){.article{width:100%;margin:12px auto}.card .inner{padding:15px}.card h2{font-size:18px}}'''
CSS += '''.featured-tools{margin:54px 0 10px;padding:30px;border-radius:24px;background:linear-gradient(145deg,#e8f6fb,#f5f8ff);border:1px solid #d5e7f2}.featured-tools .sectiontitle{margin-top:0}.featured-tools .tool{box-shadow:0 6px 18px rgba(10,30,60,.05)}.featured-tools .tool h3{font-size:19px;margin:8px 0}.featured-grid{grid-template-columns:repeat(4,minmax(0,1fr))}@media(max-width:950px){.featured-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.featured-tools{margin:32px 0;padding:18px}.featured-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.featured-grid .tool{padding:13px}.featured-grid .tool h3{font-size:16px}.featured-grid .tool p{font-size:13px}.featured-grid .tool a{font-size:12px}}''';CSS += """.trending-news .trending-list{display:grid!important;grid-template-columns:minmax(0,1fr)!important;gap:12px!important}.trending-news .trending-list>a{display:flex!important;align-items:center!important;gap:14px!important;padding:12px!important;background:#f3f7fc!important;border:1px solid #e1e9f2!important;border-radius:12px!important;text-decoration:none!important;color:#15213a!important;min-width:0!important}.trending-news .trending-list>a>img{display:block!important;width:112px!important;height:74px!important;max-width:112px!important;flex:0 0 112px!important;object-fit:cover!important;border-radius:8px!important}.trending-news .trending-list>a>span{display:block!important;flex:1!important;min-width:0!important;overflow-wrap:anywhere!important;font-weight:650!important;line-height:1.45!important}@media(max-width:560px){.trending-news .trending-list>a>img{width:86px!important;max-width:86px!important;height:62px!important;flex-basis:86px!important}}"""
CSS += """/* Compact, accessible responsive navigation and tighter homepage rhythm. */
.top .wrap{max-width:1320px;min-height:70px;gap:12px;padding-top:12px;padding-bottom:12px}
.top nav{gap:8px 16px;align-items:center}
.top nav a{white-space:nowrap;font-size:13px}
.logo{white-space:nowrap;font-size:23px}
.lead{padding-top:30px;padding-bottom:8px}
.lead h1{font-size:clamp(31px,3.8vw,50px);max-width:1000px;margin-bottom:12px}
.lead + .sectiontitle{margin-top:12px}
@media(min-width:1000px){.top .wrap{display:grid;grid-template-columns:auto minmax(0,1fr)}.top nav{justify-content:flex-end}}
@media(max-width:999px){.top .wrap{display:block}.top nav{margin-top:10px;display:flex;flex-wrap:nowrap;overflow-x:auto;scrollbar-width:thin;padding-bottom:6px}.top nav a{flex:none}.lead{padding-top:24px}}
@media(max-width:600px){.top .wrap{padding-top:11px;padding-bottom:7px}.logo{font-size:21px}.lead h1{font-size:clamp(29px,7vw,39px)}}
"""
CSS += """.focus-news{margin-top:34px}.focus-news .cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.focus-news .card{min-width:0}@media(max-width:850px){.focus-news .cards{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:540px){.focus-news .cards{grid-template-columns:1fr}}"""
CSS += """/* Robust mobile More menu: viewport-fixed panel avoids clipped scroll containers. */
@media(max-width:999px){
 .top nav{overflow:visible!important}
 .top .wrap{overflow:visible!important}
 .top .nav-more{position:static!important;flex:0 0 auto!important;width:auto!important}
 .top .nav-more summary{display:inline-flex!important;align-items:center;color:#fff!important;cursor:pointer;padding:8px 12px!important}
 .top .nav-more[open] .nav-more-list{
  display:grid!important;position:fixed!important;z-index:99999!important;
  top:110px!important;left:12px!important;right:12px!important;
  width:auto!important;max-width:none!important;max-height:calc(100dvh - 125px)!important;
  overflow-y:auto!important;overscroll-behavior:contain;
  grid-template-columns:repeat(2,minmax(0,1fr))!important;
  background:#0d1d36!important;border:2px solid #5ce0dc!important;
  box-shadow:0 16px 45px rgba(0,0,0,.5)!important;
  border-radius:14px!important;padding:12px!important;
 }
 .top .nav-more:not([open]) .nav-more-list{display:none!important}
 .top .nav-more-list a{color:#fff!important;background:#172c4a!important;border-radius:8px;margin:3px;padding:12px 8px!important;white-space:normal!important;line-height:1.4}
}
"""
CSS += """/* Category menu is OUTSIDE the scrolling nav, so it cannot be clipped. */
.top .wrap{overflow:visible!important}
.category-menu{position:relative;z-index:200}
.category-menu .nav-more{position:relative!important;width:auto!important;flex:none!important}
.category-menu summary{display:block;cursor:pointer;color:#eaf4ff!important;font-weight:700;padding:9px 13px;border:1px solid #45627f;border-radius:9px;list-style:none}
.category-menu summary::-webkit-details-marker{display:none}
.category-menu .nav-more-list{display:none!important}
.category-menu .nav-more[open] .nav-more-list{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;position:absolute!important;right:0!important;left:auto!important;top:100%!important;width:min(400px,92vw)!important;max-height:65vh!important;overflow-y:auto!important;background:#10243e!important;border:1px solid #4e7697!important;box-shadow:0 12px 30px #0006!important;z-index:9999!important;padding:10px!important}
.category-menu .nav-more-list a{display:block;color:#fff!important;background:#1d3655!important;border-radius:7px;margin:3px;padding:10px!important;white-space:normal!important}
@media(max-width:999px){
 .top .wrap{display:flex!important;flex-wrap:wrap!important;align-items:center}
 .top nav{flex:1 1 100%;order:3;overflow-x:auto!important;overflow-y:hidden!important;flex-wrap:nowrap!important}
 .category-menu{order:2;margin-left:auto}
 .category-menu .nav-more[open] .nav-more-list{position:absolute!important;right:0!important;top:100%!important;left:auto!important;width:min(340px,90vw)!important;max-height:70vh!important}
}
"""
write(OUT/'style.css',CSS + MENU_CSS + HUB_CSS + GLOBAL_CSS + EXAM_CSS)
JS='''addEventListener('scroll',()=>{let d=document.documentElement;let m=d.scrollHeight-d.clientHeight;let b=document.querySelector('.reading');if(b)b.style.width=(m>0?100*d.scrollTop/m:0)+'%';},{passive:true});'''
JS += """document.addEventListener('click',async function(ev){const share=ev.target.closest('.native-share');if(share){const data={title:share.dataset.shareTitle,url:share.dataset.shareUrl};if(navigator.share){try{await navigator.share(data)}catch(err){if(err.name!=='AbortError')location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}else{location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}const copy=ev.target.closest('.copy-share');if(copy){try{await navigator.clipboard.writeText(copy.dataset.shareUrl);const old=copy.textContent;copy.textContent='✓ Copied';setTimeout(()=>copy.textContent=old,1800)}catch(err){prompt('Copy link:',copy.dataset.shareUrl)}}});"""
CSS += """.category-pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:30px 0 48px;flex-wrap:wrap}.category-pagination a{display:inline-block;background:#fff;border:1px solid #d9e5f0;border-radius:9px;padding:8px 13px;text-decoration:none}"""
CSS += """.skip-link{position:absolute;left:12px;top:-100px;z-index:999999;background:white;color:#123;padding:10px}.skip-link:focus{top:10px}.topic-directory{columns:3;column-gap:30px}.topic-directory li{break-inside:avoid;margin:0 0 12px}@media(max-width:700px){.topic-directory{columns:2}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}"""
CSS += """.breadcrumbs{font-size:13px;line-height:1.6;color:#5b6c83;margin-bottom:14px;overflow-wrap:anywhere}.breadcrumbs a{color:#12588b;text-decoration:none}.breadcrumbs span{color:#667085}"""
CSS += """.article-tags{margin:26px 0;padding:16px 0;border-top:1px solid #e5ebf3;border-bottom:1px solid #e5ebf3}.article-tags strong{display:block;font-size:14px;margin-bottom:10px}.tag-list{display:flex;gap:8px;flex-wrap:wrap}.tag{font-size:12px;padding:5px 11px;background:#eef4fa;color:#24496a;border:1px solid #dce7f2;border-radius:100px}.related .related-card{padding:0;overflow:hidden;background:#f2f7fc}.related-card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.related-card span:not(.related-placeholder){display:block;padding:12px;font-size:14px;line-height:1.5}.related-placeholder{display:flex;align-items:center;justify-content:center;min-height:120px;background:#e4edf7;color:#49617a;font-size:12px}.trending-news{margin-top:32px;border-top:1px solid #dfe7ef;padding-top:20px}.trending-list{display:grid;gap:12px}.trending-list a{display:flex;align-items:center;gap:14px;background:#f7f9fc;padding:10px;border-radius:10px;text-decoration:none;font-weight:650;line-height:1.5}.trending-list img{width:100px;height:68px;object-fit:cover;border-radius:7px;flex-shrink:0}@media(max-width:560px){.related{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.related-card span:not(.related-placeholder){font-size:12px;padding:9px}.trending-list img{width:82px;height:58px}}"""
CSS += """.article{max-width:850px;margin:28px auto 50px;padding:clamp(20px,4vw,42px);line-height:1.85}.article h1{font-size:clamp(30px,4vw,46px);line-height:1.2}.article .story{font-size:17px;line-height:1.9}.article .story h2{margin:30px 0 12px;font-size:26px}.article .story h3{margin:24px 0 10px;font-size:21px}.article .story p{margin-bottom:20px}.article .hero{width:100%;height:auto;border-radius:12px}.author-about{margin:32px 0;padding:22px;background:#f5f8fc;border:1px solid #e0e8f1;border-radius:14px}.author-about h2{margin:0 0 8px;font-size:20px}@media(max-width:600px){.article{margin:14px auto 28px;padding:18px}.article .story{font-size:16px;line-height:1.8}.article .story h2{font-size:22px}}"""
CSS += """.card h2,.related-card span,.trending-list span{overflow:visible;text-overflow:clip;white-space:normal;overflow-wrap:anywhere;-webkit-line-clamp:unset;line-clamp:unset}.card,.card .inner{height:auto}.card a:focus-visible{outline:3px solid #0b8a93;outline-offset:3px}@media(max-width:600px){.card h2{font-size:17px;line-height:1.45}}"""
CSS += """.top nav{display:flex;align-items:center;flex-wrap:wrap;gap:10px}.nav-more{position:relative;z-index:50}.nav-more summary{cursor:pointer;list-style:none;padding:8px 12px;font-weight:650}.nav-more summary::-webkit-details-marker{display:none}.nav-more-list{position:absolute;right:0;top:100%;width:min(290px,85vw);max-height:70vh;overflow:auto;background:white;border:1px solid #dce5f1;box-shadow:0 12px 30px #0002;border-radius:12px;padding:8px;display:grid;z-index:60}.nav-more-list a{display:block;padding:9px 12px;color:#13263e}.card h2{display:block!important;-webkit-line-clamp:unset!important;line-clamp:unset!important;max-height:none!important;overflow:visible!important}.card .inner{height:auto!important;min-height:0!important}@media(max-width:600px){.nav-more-list{right:0}}"""
CSS += """/* Final mobile dropdown override: placed AFTER the default white popup rules. */
@media(max-width:999px){
 .top nav{overflow:visible!important;flex-wrap:wrap!important}
 .top .wrap{overflow:visible!important}
 .nav-more{position:static!important;flex:0 0 100%;width:100%}
 .nav-more summary{color:#e7f2ff!important;padding:8px 0}
 .nav-more-list{position:static!important;right:auto!important;top:auto!important;width:100%!important;max-height:none!important;overflow:visible!important;display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));background:#14233d!important;border:1px solid #354967!important;box-shadow:none!important;margin:5px 0 10px}
 .nav-more-list a{color:#e7f2ff!important;white-space:normal!important}
 .nav-more:not([open]) .nav-more-list{display:none!important}
}
"""
CSS += """.article-share{padding:15px 20px;margin:18px 0;border:1px solid #dce5f1;background:#f5f9ff;border-radius:14px}.article-share strong{display:block;margin-bottom:10px}.share-actions{display:flex;flex-wrap:wrap;gap:9px}.share-actions a,.share-actions button{font:600 14px/1.3 system-ui,sans-serif;display:inline-block;border:1px solid #bed2e7;background:white;color:#12588b;border-radius:9px;padding:10px 12px;text-decoration:none;cursor:pointer}.share-actions a:hover,.share-actions button:hover{background:#e5f2ff}"""
CSS += """/* Robust mobile More menu: viewport-fixed panel avoids clipped scroll containers. */
@media(max-width:999px){
 .top nav{overflow:visible!important}
 .top .wrap{overflow:visible!important}
 .top .nav-more{position:static!important;flex:0 0 auto!important;width:auto!important}
 .top .nav-more summary{display:inline-flex!important;align-items:center;color:#fff!important;cursor:pointer;padding:8px 12px!important}
 .top .nav-more[open] .nav-more-list{
  display:grid!important;position:fixed!important;z-index:99999!important;
  top:110px!important;left:12px!important;right:12px!important;
  width:auto!important;max-width:none!important;max-height:calc(100dvh - 125px)!important;
  overflow-y:auto!important;overscroll-behavior:contain;
  grid-template-columns:repeat(2,minmax(0,1fr))!important;
  background:#0d1d36!important;border:2px solid #5ce0dc!important;
  box-shadow:0 16px 45px rgba(0,0,0,.5)!important;
  border-radius:14px!important;padding:12px!important;
 }
 .top .nav-more:not([open]) .nav-more-list{display:none!important}
 .top .nav-more-list a{color:#fff!important;background:#172c4a!important;border-radius:8px;margin:3px;padding:12px 8px!important;white-space:normal!important;line-height:1.4}
}
"""
CSS += """/* Category menu is OUTSIDE the scrolling nav, so it cannot be clipped. */
.top .wrap{overflow:visible!important}
.category-menu{position:relative;z-index:200}
.category-menu .nav-more{position:relative!important;width:auto!important;flex:none!important}
.category-menu summary{display:block;cursor:pointer;color:#eaf4ff!important;font-weight:700;padding:9px 13px;border:1px solid #45627f;border-radius:9px;list-style:none}
.category-menu summary::-webkit-details-marker{display:none}
.category-menu .nav-more-list{display:none!important}
.category-menu .nav-more[open] .nav-more-list{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;position:absolute!important;right:0!important;left:auto!important;top:100%!important;width:min(400px,92vw)!important;max-height:65vh!important;overflow-y:auto!important;background:#10243e!important;border:1px solid #4e7697!important;box-shadow:0 12px 30px #0006!important;z-index:9999!important;padding:10px!important}
.category-menu .nav-more-list a{display:block;color:#fff!important;background:#1d3655!important;border-radius:7px;margin:3px;padding:10px!important;white-space:normal!important}
@media(max-width:999px){
 .top .wrap{display:flex!important;flex-wrap:wrap!important;align-items:center}
 .top nav{flex:1 1 100%;order:3;overflow-x:auto!important;overflow-y:hidden!important;flex-wrap:nowrap!important}
 .category-menu{order:2;margin-left:auto}
 .category-menu .nav-more[open] .nav-more-list{position:absolute!important;right:0!important;top:100%!important;left:auto!important;width:min(340px,90vw)!important;max-height:70vh!important}
}
"""
write(OUT/'style.css',CSS + MENU_CSS + HUB_CSS + GLOBAL_CSS + EXAM_CSS)
write(OUT/'site.js',JS + HUB_JS + GLOBAL_JS)
def shell(lang,t,desc,url,body,extra='',*,alternate_urls=None,canonical_url=None,robots=ROBOTS,document_lang=None):
 desc=seo_description(desc,body,t)
 page_title=t if 'GlobeWire Daily' in t else t+' | GlobeWire Daily'
 meta=seo_head(document_lang or lang,page_title,desc,url,extra,site=SITE,alternates=alternate_urls,canonical=canonical_url,robots=robots)
 target_lang='hi' if lang=='en' else 'en'
 switch_url=(alternate_urls.get(target_lang) if alternate_urls is not None else url.replace('/en/','/hi/',1) if lang=='en' else url.replace('/hi/','/en/',1)) or f'{SITE}/{target_lang}/'
 switch_label=('हिन्दी' if lang=='en' else 'English')
 if alternate_urls is not None and target_lang not in alternate_urls:switch_label+=' Home'
 nav=[('Home','होम',''),('Latest News','ताज़ा खबरें','all-news/'),('Global Topics','वैश्विक विषय','global-topics/'),('Jobs & Exams','नौकरी और परीक्षा','jobs-exams/'),('Tech & AI','टेक और AI','technology/'),('Entertainment','मनोरंजन','movies-entertainment/'),('Jobs & Schemes','नौकरी और योजनाएँ','sarkari-naukri/')]
 links=''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in nav)
 more=[('All Latest News','सभी ताज़ा खबरें','all-news/'),('Jobs & Exam Hub','नौकरी और परीक्षा हब','jobs-exams/'),('Launches & Specs','लॉन्च और स्पेक्स','launches/'),('Freebies & Discounts','फ्रीबीज़ और डिस्काउंट','freebies-deals/'),('Study Abroad Guide','विदेश में पढ़ाई','study-abroad-guide/'),('Jobs Archive','पुराने नोटिस','jobs-archive/'),('AI Tools','AI टूल्स','tools/'),('College Finder','कॉलेज खोजें','colleges/'),('Course Explorer','कोर्स खोजें','courses/'),('Car Explorer','कार खोजें','cars/'),('Phone Explorer','फोन खोजें','phones/'),('Bike Explorer','बाइक खोजें','bikes/')]+[(en,hi,cat+'/') for cat,(en,hi) in CATEGORIES.items()]+[('About','हमारे बारे में','about/'),('Contact','संपर्क','contact/')]
 more_html='<details class="nav-more"><summary>'+('More' if lang=='en' else 'और देखें')+'</summary><div class="nav-more-list">'+''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in more)+'</div></details>'
 return f'''<!doctype html><html lang="{document_lang or lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="google-site-verification" content="IjjkuYPqG93dE2SwPvi0HJ258E5WwNGAhIu7LB9qQqE"><meta name="theme-color" content="#0a1429"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1849673109734274" crossorigin="anonymous"></script>{meta}<script async src="https://www.googletagmanager.com/gtag/js?id=G-MFZZNMZCWJ"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","G-MFZZNMZCWJ");</script><meta name="generator" content="GlobeWire SEO v2"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta name="color-scheme" content="light"><link rel="stylesheet" href="/style.css?v={hashlib.sha256((CSS+MENU_CSS+HUB_CSS+GLOBAL_CSS+EXAM_CSS+DIRECTORY_CSS+ARTICLE_CSS).encode()).hexdigest()[:12]}"></head><body><a class="skip-link" href="#main-content">{'Skip to content' if lang=='en' else 'मुख्य सामग्री पर जाएँ'}</a><div class="reading"></div><header class="top"><div class="wrap"><a class="logo" href="/{lang}/">GlobeWire <span>Daily</span></a><nav aria-label="Primary">{links}<a class="langswitch" href="{e(switch_url)}" hreflang="{target_lang}">{switch_label}</a></nav><div class="category-menu">{more_html}</div></div></header><main id="main-content">{body}</main><footer class="footer"><div class="wrap"><div><strong>GlobeWire Daily</strong><p>{label("Independent bilingual news and explainers, with clear sourcing, corrections and transparent editorial standards.",lang)}</p><a href="mailto:{CONTACT}">{CONTACT}</a></div><div class="footerlinks">{''.join(f'<a href="/{lang}/{s}/">{label(s.title(),lang)}</a>' for s in ['about','privacy','contact','editorial','corrections','affiliate','tools','resources','site-map'])}</div></div></footer><script defer src="/site.js?v={hashlib.sha256((JS+HUB_JS+GLOBAL_JS+DIRECTORY_JS).encode()).hexdigest()[:12]}"></script></body></html>'''
def adsterra_slot(position, lang):
    label = 'विज्ञापन' if lang == 'hi' else 'Advertisement'
    fallback = ''
    if position == 'title':
        invitation = 'GlobeWire Daily पर विज्ञापन दें' if lang == 'hi' else 'Advertise on GlobeWire Daily'
        fallback = (
            '<div style="max-width:728px;margin:12px auto;padding:8px 12px;'
            'border:1px solid #dce5f1;border-radius:8px;background:#f5f8fc">'
            f'<small>{label}</small><br><a href="/{lang}/contact/">{invitation}</a></div>'
        )
    return f'<div data-adsterra-slot="{position}" aria-label="{label}" style="text-align:center;overflow:hidden">{fallback}</div>'


def article_ad_scripts():
    return r'''
<script>
(() => {
  if (navigator.globalPrivacyControl) return;

  function mount(slot) {
    if (slot.querySelector('iframe')) return;
    const available = slot.clientWidth;
    const [width, height, key] = slot.dataset.adsterraSlot === "inline"
      ? [300, 250, "52835a675f1767f1a04f1936910f50fc"]
      : available >= 728
        ? [728, 90, "ea1d474556632d121d26679ad3ab397a"]
        : [320, 50, "d5df9465701fdd4db6592b1b19550468"];
    if (available < width) return;

    const frame = document.createElement("iframe");
    frame.title = slot.getAttribute("aria-label");
    frame.width = width;
    frame.height = height;
    frame.loading = "lazy";
    frame.style.cssText = "display:block;border:0;margin:12px auto;max-width:100%";
    // Adsterra uses document.cookie in its supplied loader and needs a real origin.
    frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox");
    const options = JSON.stringify({key, format: "iframe", height, width, params: {}});
    // Keep document.write and per-banner options in this frame.
    frame.srcdoc = '<body style="margin:0;overflow:hidden"><script>window.atOptions=' + options
      + ';<' + '/script><script src="https://bicea.org/22/' + key + '"><' + '/script></body>';
    slot.replaceChildren(frame);
  }

  fetch("/cdn-cgi/trace", {cache: "no-store", credentials: "omit"})
    .then(response => response.ok ? response.text() : "")
    .then(trace => {
      if (!/^loc=IN\r?$/m.test(trace)) return;

      let adsterraDisabled = false;
      try { adsterraDisabled = sessionStorage.getItem("globewire-adsterra") === "no"; } catch {}
      if (!adsterraDisabled) {
        document.querySelectorAll("[data-adsterra-slot]").forEach(mount);
      }

      window.infolinks_pid = 3449361;
      window.infolinks_wsid = 0;
      const tag = document.createElement("script");
      tag.src = "https://resources.infolinks.com/js/infolinks_main.js";
      tag.async = true;
      document.body.appendChild(tag);
    })
    .catch(() => {});
})();
</script>'''


@functools.lru_cache(maxsize=None)
def image_digest(ident):
 try:return hashlib.sha256((OUT/'images'/f'{ident}.jpg').read_bytes()).hexdigest()[:12]
 except OSError:return '0'
def image_version(p):return image_digest(slug(p))
@functools.lru_cache(maxsize=None)
def featured_info(ident):
 try:return json.loads((R/'content'/'featured'/f'{ident}.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):return {}
def image_alt(p,lang):
 info=featured_info(slug(p))
 from image_rules import saved_photo_allowed
 if not saved_photo_allowed(info,R) or not (R/'content'/'featured'/f'{slug(p)}.jpg').is_file():return title(p,lang)
 return str(info.get(lang+'_alt') or info.get('alt') or title(p,lang))

def has_featured(p):
 # Existing licensed/credited images always take priority.
 return (R/'content'/'featured'/f'{slug(p)}.jpg').is_file() or (OUT/'images'/f'{slug(p)}.jpg').is_file()

def image_for(p):
 """Keep existing photos; generate clearly labeled original editorial artwork only when missing."""
 s=slug(p);dest=OUT/'images'/f'{s}.jpg';dest.parent.mkdir(parents=True,exist_ok=True)
 existing=R/'content'/'featured'/f'{s}.jpg'
 metadata=R/'content'/'featured'/f'{s}.json'
 use_original=existing.is_file()
 if use_original and metadata.is_file():
  try:
   # Do not publish generic Commons substitutes or publisher social-sharing logos.
   info=json.loads(metadata.read_text(encoding='utf-8'))
   source_path=urlparse(str(info.get('source_image') or info.get('image_url') or '')).path
   generic=bool(re.search(r'(?i)(?:/assets/images/share/|/(?:app-store|appstore|social-share|share-banner|og-default)(?:[._/-]|$))',source_path))
   from image_rules import saved_photo_allowed
   use_original=saved_photo_allowed(info,R) and info.get('kind') in ('licensed_source','licensed_photo','publisher_source','source_original','manual_original') and not generic
  except (ValueError,OSError,TypeError):
   use_original=False
 if use_original:
  shutil.copy2(existing,dest)
  return
 # If a previously selected photo is removed (for irrelevant subject or rights),
 # overwrite its old dist JPEG with a clearly labeled editorial illustration.
 # Never leave a misleading cached photo after the source image was removed.
 canvas=Image.new('RGB',(1280,720),(12,28,55))
 draw=ImageDraw.Draw(canvas)
 draw.rectangle((0,0,1280,16),fill=(29,199,196))
 draw.ellipse((930,80,1430,580),outline=(35,91,117),width=18)
 draw.ellipse((1000,145,1350,495),outline=(35,91,117),width=12)
 try:
  font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
  heading_font=ImageFont.truetype(font_path,54)
  small_font=ImageFont.truetype(font_path,29)
 except OSError:
  heading_font=ImageFont.load_default()
  small_font=ImageFont.load_default()
 category_name=CATEGORIES[category(p)][0].upper()
 draw.text((75,65),'GLOBEWIRE DAILY',font=small_font,fill=(85,227,221))
 draw.text((75,120),category_name,font=small_font,fill=(195,211,231))
 headline=title(p,'en')
 lines=textwrap.wrap(headline,width=34)[:4]
 for index,line in enumerate(lines):
  draw.text((75,230+index*78),line,font=heading_font,fill=(255,255,255))
 draw.rectangle((75,610,610,660),fill=(20,66,92))
 draw.text((90,616),'EDITORIAL ILLUSTRATION',font=small_font,fill=(224,239,247))
 canvas.save(dest,'JPEG',quality=88,optimize=True)
@functools.lru_cache(maxsize=None)
def image_dimensions(ident):
 try:
  with Image.open(OUT/'images'/f'{ident}.jpg') as image:return image.size
 except (OSError,ValueError):return (1280,720)

def body_html(raw):
 return render_article(raw)[0]
def image_caption(p,lang):
 s=slug(p)
 metadata=R/'content'/'featured'/f'{s}.json'
 if metadata.is_file():
  try:
   info=json.loads(metadata.read_text(encoding='utf-8'))
   from urllib.parse import urlparse
   import re
   path=urlparse(str(info.get('source_image') or info.get('image_url') or '')).path
   generic=bool(re.search(r'(?i)(?:/assets/images/share/|/(?:app-store|appstore|social-share|share-banner|og-default)(?:[._/-]|$))',path))
   from image_rules import saved_photo_allowed
   if generic or not saved_photo_allowed(info,R) or not (R/'content'/'featured'/f'{s}.jpg').is_file():
    return 'Original GlobeWire Daily editorial illustration — source photograph unavailable.' if lang=='en' else 'GlobeWire Daily का सांकेतिक चित्र — स्रोत फोटो उपलब्ध नहीं।'
   if info.get('kind') in ('licensed_source','publisher_source','licensed_photo'):
    credit=str(info.get('attribution') or 'Original publisher')
    license_name=str(info.get('license_name') or info.get('license') or '').strip()
    suffix=f' — {license_name}' if license_name else ''
    return (f'Image: {credit}{suffix}' if lang=='en' else f'चित्र: {credit}{suffix}')
   if info.get('kind')=='ai_generated':
    return 'AI-generated editorial illustration — not an event photograph.' if lang=='en' else 'AI से बनी सांकेतिक तस्वीर — घटना की वास्तविक फोटो नहीं।'
  except (OSError,ValueError):pass
 if not metadata.is_file():
  if (R/'content'/'featured'/f'{s}.jpg').is_file():
   return 'Featured image; source information not supplied.' if lang=='en' else 'फीचर्ड चित्र; स्रोत की जानकारी उपलब्ध नहीं है।'
  return 'Original GlobeWire Daily editorial illustration — not an event photograph.' if lang=='en' else 'GlobeWire Daily की मूल सांकेतिक तस्वीर — घटना की वास्तविक फोटो नहीं।'
 return 'Featured image; provenance not specified.' if lang=='en' else 'फीचर्ड चित्र; स्रोत निर्दिष्ट नहीं है।'
def image_caption_html(p,lang):
 # Photographer, photo-source page, reuse terms and crop disclosure follow the
 # photo. Every user-controlled value is escaped before inserting into HTML.
 caption=e(image_caption(p,lang))
 metadata=R/'content'/'featured'/f'{slug(p)}.json'
 if not metadata.is_file():return caption
 try:
  info=json.loads(metadata.read_text(encoding='utf-8'))
  if 'illustration' in caption.lower() or 'सांकेतिक' in caption:return caption
  links=[]
  if info.get('rights_status')=='source_rights_unverified':
   links.append('Source image rights not independently verified' if lang=='en' else 'स्रोत चित्र के उपयोग अधिकार स्वतंत्र रूप से सत्यापित नहीं')
  source_url=str(info.get('source_image') or info.get('image_url') or '')
  if source_url.startswith('https://'):
   links.append('<a target="_blank" rel="noopener noreferrer" href="'+e(source_url)+'">'+('Photo source' if lang=='en' else 'चित्र स्रोत')+'</a>')
  license_url=str(info.get('license') or '')
  if license_url.startswith('https://'):
   links.append('<a target="_blank" rel="noopener noreferrer" href="'+e(license_url)+'">'+('License terms' if lang=='en' else 'लाइसेंस शर्तें')+'</a>')
  if info.get('modifications'):
   links.append(e(str(info['modifications'])))
  elif info.get('kind')=='publisher_source':
   links.append('Cropped to 16:9; original source image' if lang=='en' else 'स्रोत चित्र 16:9 अनुपात में काटा गया')
  elif info.get('kind')=='licensed_photo':
   links.append('Cropped to 16:9; representative photograph' if lang=='en' else '16:9 में काटी गई प्रतिनिधि फोटो')
  return caption+(' · '+' · '.join(links) if links else '')
 except (OSError,ValueError,TypeError):return caption

def card(p,lang):
 s=slug(p);t=title(p,lang)
 picture=f'<img loading="lazy" src="/images/{s}.jpg?v={image_version(p)}" width="1280" height="720" alt="{e(t)}">' if has_featured(p) else ''
 return f'<article class="card"><a href="{article_path(p,lang)}">{picture}<div class="inner"><span class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=="en" else 1])}</span><h2>{e(t)}</h2><div class="date">{e(p.get("date","")[:10])}</div></div></a></article>'

AUTHOR_HANDLES={'technology':'tech-desk','business':'business-desk','world-news':'world-desk','sports':'sports-desk','health-science':'science-desk','government-schemes':'public-services-desk','sarkari-naukri':'careers-desk','private-vacancy':'careers-desk','movies-entertainment':'entertainment-desk','automobiles':'auto-desk','gaming':'gaming-desk','environment':'climate-desk','travel':'travel-desk','education':'education-desk','lifestyle':'lifestyle-desk'}
def author_handle(p):return AUTHOR_HANDLES.get(category(p),'editorial-desk')
def author_name(p):return 'GlobeWire Daily '+author_handle(p).replace('-',' ').title()
def updated_notice(p,lang):
 if not p.get('updated_at') or p.get('updated_at')==p.get('date'):return ''
 return '<p class="date">'+('Updated: ' if lang=='en' else 'अपडेट: ')+'<time datetime="'+e(p['updated_at'])+'">'+e(display_date(p['updated_at']))+'</time></p>'

def article_keywords(p,lang):
 raw=p.get(lang+'_keywords') or p.get('en_keywords') or []
 if isinstance(raw,str):
  # Older drafts stringified keyword arrays as Python literals.
  if raw.strip().startswith('['):
   try:
    import ast
    raw=ast.literal_eval(raw)
   except (ValueError,SyntaxError):raw=re.split(r'[,;|]',raw)
  else:raw=re.split(r'[,;|]',raw)
 if not isinstance(raw,list):raw=[]
 terms=[str(x).strip() for x in raw if str(x).strip()]
 terms.extend([title(p,lang),CATEGORIES[category(p)][0 if lang=='en' else 1],'GlobeWire Daily'])
 seen=set();result=[]
 for term in terms:
  key=term.casefold()
  if key not in seen and len(term)<=100:
   seen.add(key);result.append(term)
 return result[:12]
_trending_rank_cache=None
def trending_posts(exclude=None,limit=6):
 """Editorial trending proxy: recent articles with topical keyword overlap.
 No fabricated traffic, view counts or real-time search popularity."""
 global _trending_rank_cache
 if _trending_rank_cache is not None:
  return [p for p in _trending_rank_cache if exclude is None or slug(p)!=slug(exclude)][:limit]
 now=dt.datetime.now(dt.timezone.utc)
 pool=[]
 for p in POSTS:
  try:
   published=dt.datetime.fromisoformat(str(p.get('date','')).replace('Z','+00:00'))
   if published.tzinfo is None:published=published.replace(tzinfo=dt.timezone.utc)
   age=max(0,(now-published).total_seconds()/3600)
  except (ValueError,TypeError):age=9999
  terms=set(re.findall(r'[a-z]{4,}',str(p.get('en_title','')).lower()))
  overlaps=sum(bool(terms & set(re.findall(r'[a-z]{4,}',str(q.get('en_title','')).lower()))) for q in POSTS[:50] if slug(q)!=slug(p))
  score=(max(0,168-age)/24)+min(overlaps,5)*0.7
  pool.append((score,p))
 pool.sort(key=lambda x:x[0],reverse=True)
 _trending_rank_cache=[p for _,p in pool]
 return [p for p in _trending_rank_cache if exclude is None or slug(p)!=slug(exclude)][:limit]

def trending_section(lang,exclude=None):
 selected=trending_posts(exclude,6)
 if not selected:return ''
 heading='Trending on GlobeWire Daily' if lang=='en' else 'GlobeWire Daily पर चर्चित खबरें'
 note='Selected from recent coverage and related topics; not live search rankings.' if lang=='en' else 'हालिया खबरों और संबंधित विषयों पर आधारित चयन; लाइव सर्च रैंकिंग नहीं।'
 return '<section class="trending-news trending-feature"><h2>'+heading+'</h2><p class="muted">'+note+'</p><div class="trending-list">'+''.join('<a href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="120" height="80" src="/images/{slug(q)}.jpg?v={image_version(q)}" alt="">' if has_featured(q) else '<span class="related-placeholder">News</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in selected)+'</div></section>'

def display_date(value):
 try:
  stamp=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
  if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=dt.timezone.utc)
  return stamp.astimezone(dt.timezone(dt.timedelta(hours=5,minutes=30))).strftime('%d %b %Y, %I:%M %p IST')
 except (ValueError,TypeError):return str(value or '')[:10]

def limit_article_words(raw,limit=10000):
 parts=re.findall(r'\S+',str(raw or ''))
 if len(parts)<=limit:return str(raw or '')
 return ' '.join(parts[:limit]).rstrip(' ,;:')+'…'

RELATED_POSTS=related_index(POSTS)
logo=Image.new('RGB',(512,512),(10,20,41));draw=ImageDraw.Draw(logo)
draw.ellipse((40,40,472,472),outline=(92,224,220),width=12)
draw.text((140,205),'GW',fill='white',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',100) if Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf').exists() else ImageFont.load_default(size=100))
logo.save(OUT/'publisher-logo.png')
social=Image.new('RGB',(1200,630),(10,20,41));draw=ImageDraw.Draw(social)
font_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
font=ImageFont.truetype(str(font_path),68) if font_path.exists() else ImageFont.load_default(size=68)
small=ImageFont.truetype(str(font_path),30) if font_path.exists() else ImageFont.load_default(size=30)
draw.text((65,170),'GlobeWire Daily',fill='white',font=font);draw.text((70,295),'News, context and useful explainers',fill=(92,224,220),font=small);draw.text((70,500),'globewiredaily.org',fill='white',font=small)
social.save(OUT/'social-card.jpg','JPEG',quality=85,optimize=True)
for p in POSTS:image_for(p)
for p in POSTS:
 s=slug(p)
 for lang in ('en','hi'):
  available=article_languages(p);fallback=lang not in available;content_lang='en' if fallback else lang
  t=title(p,content_lang);raw=limit_article_words(p.get(content_lang+'_body') or p.get('en_body',''));url=f'{SITE}{article_path(p,lang)}';desc=seo_description(p.get(content_lang+'_meta'),raw,t)
  if p.get('content_type')=='evergreen_directory_guide':raw=guide_body(raw)
  story_html,toc_html,reading_minutes=render_article(raw,content_lang)
  canonical_url=f'{SITE}{article_path(p,"en")}' if fallback else url
  alternate_urls={code:SITE+article_path(p,code) for code in available}
  schema={'@context':'https://schema.org','@type':'NewsArticle' if is_news_article(p) else 'Article','headline':t,'articleSection':CATEGORIES[category(p)][0],'datePublished':p.get('date'),'dateModified':p.get('updated_at') or p.get('date'),'inLanguage':lang,'mainEntityOfPage':url,'image':([f'{SITE}/images/{s}.jpg?v={image_version(p)}'] if has_featured(p) else []),'author':{'@type':'Organization','name':author_name(p),'url':f'{SITE}/{lang}/author/{author_handle(p)}/'},'publisher':{'@type':'Organization','name':'GlobeWire Daily','url':SITE},'isBasedOn':p['source']}
  if not has_featured(p):schema.pop('image',None)
  schema['breadcrumb']={'@type':'BreadcrumbList','itemListElement':[
   {'@type':'ListItem','position':1,'name':'Home' if lang=='en' else 'होम','item':f'{SITE}/{lang}/'},
   {'@type':'ListItem','position':2,'name':CATEGORIES[category(p)][0 if lang=='en' else 1],'item':f'{SITE}/{lang}/{category(p)}/'},
   {'@type':'ListItem','position':3,'name':t,'item':url}]}
  schema['keywords']=article_keywords(p,lang)
  schema['description']=desc[:160]
  schema['url']=url
  crumbs=schema.pop('breadcrumb')
  schema['@id']=canonical_url+'#article';schema['url']=canonical_url
  schema['mainEntityOfPage']={'@id':canonical_url+'#webpage'}
  schema['inLanguage']=content_lang;schema['articleSection']=CATEGORIES[category(p)][content_lang=='hi']
  schema['publisher']={'@id':SITE+'/#publisher'}
  for field in ('datePublished','dateModified'):
   stamp=iso_date(schema.get(field))
   if stamp:schema[field]=stamp
   else:schema.pop(field,None)
  schema_json=json.dumps({'@context':'https://schema.org','@graph':[schema,crumbs]},ensure_ascii=False).replace('<',chr(92)+'u003c')
  extra_keywords='<meta name="keywords" content="'+e(', '.join(article_keywords(p,lang)))+'">'
  image_width,image_height=image_dimensions(s)
  og_image=f'<meta property="og:image" content="{SITE}/images/{s}.jpg?v={image_version(p)}"><meta property="og:image:width" content="{image_width}"><meta property="og:image:height" content="{image_height}"><meta property="og:image:alt" content="{e(image_alt(p,lang))}"><meta name="twitter:image" content="{SITE}/images/{s}.jpg?v={image_version(p)}">' if has_featured(p) else ''
  extra=f'<meta property="og:type" content="article"><meta property="og:url" content="{e(canonical_url)}"><meta property="og:site_name" content="GlobeWire Daily"><meta property="og:locale" content="{"en_US" if lang=="en" else "hi_IN"}"><meta property="og:title" content="{e(t)}"><meta property="og:description" content="{e(desc[:160])}"><meta property="article:published_time" content="{e(p.get("date",""))}"><meta property="article:section" content="{e(CATEGORIES[category(p)][0])}">{og_image}<meta name="twitter:card" content="{"summary_large_image" if has_featured(p) else "summary"}"><meta name="twitter:title" content="{e(t)}"><meta name="twitter:description" content="{e(desc[:160])}"><script type="application/ld+json">{schema_json}</script>'
  extra=extra_keywords+extra
  if schema.get("dateModified"):extra+='<meta property="article:modified_time" content="'+e(schema["dateModified"])+'">'
  sourcehost=urlparse(p['source']).hostname or 'original source'
  summary=e(excerpt(raw,p.get(content_lang+'_summary') or ''))
  featured_html=(f'<img class="hero" src="/images/{s}.jpg?v={image_version(p)}" width="{image_width}" height="{image_height}" fetchpriority="high" alt="{e(image_alt(p,lang))}"><p class="notice">{image_caption_html(p,lang)}</p>' if has_featured(p) else '')
  share_text=('Share this article' if lang=='en' else 'यह खबर शेयर करें')
  copy_text=('Copy link' if lang=='en' else 'लिंक कॉपी करें')
  share_html=(f'<div class="article-share"><strong>{share_text}</strong><div class="share-actions">'
    f'<button type="button" class="native-share" data-share-url="{e(url)}" data-share-title="{e(t)}">↗ {share_text}</button>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://api.whatsapp.com/send?text={quote(t+" "+url)}">WhatsApp</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://www.facebook.com/sharer/sharer.php?u={quote(url,safe="")}">Facebook</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://t.me/share/url?url={quote(url,safe="")}&text={quote(t)}">Telegram</a>'
    f'<button type="button" class="copy-share" data-share-url="{e(url)}">{copy_text}</button></div></div>')
  related=RELATED_POSTS.get(p['id'],[])
  related_html=''.join('<a class="related-card" href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="320" height="180" src="/images/{slug(q)}.jpg?v={image_version(q)}" alt="{e(title(q,lang))}">' if has_featured(q) else '<span class="related-placeholder" aria-hidden="true">GlobeWire Daily</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in related)
  keyword_html='<section class="article-tags"><strong>'+('Topics' if lang=='en' else 'संबंधित विषय')+'</strong><div class="tag-list">'+''.join('<span class="tag">'+e(term)+'</span>' for term in article_keywords(p,lang)[:7])+'</div></section>'
  context_html='<aside class="context-links"><strong>'+('Explore this topic' if lang=='en' else 'इस विषय पर और पढ़ें')+'</strong><a href="/'+lang+'/'+category(p)+'/">'+e(CATEGORIES[category(p)][0 if lang=='en' else 1])+'</a>'
  if p.get('directory_kind') in ('phones','cars','bikes','colleges') and p.get('directory_name'):
   from directories import entry_slug
   kind=p['directory_kind'];name=p['directory_name']
   context_html+='<a href="/'+lang+'/'+kind+'/'+entry_slug(name)+'/">'+e(name)+(' — full directory profile' if lang=='en' else ' — डायरेक्टरी में पूरा विवरण')+'</a>'
  context_html+=''.join('<a href="'+article_path(q,lang)+'">'+e(title(q,lang))+'</a>' for q in related[:2])+'</aside>'
  # Offer relevant next steps at a section boundary without interrupting prose.
  boundaries=list(re.finditer(r'<h2 id=',story_html))
  split=boundaries[2].start() if len(boundaries)>2 else len(story_html)
  show_ads=not fallback and is_news_article(p)
  story_html=story_html[:split]+context_html+story_html[split:]
  if show_ads:
   if len(boundaries)<=2:
    paragraphs=[m.end() for m in re.finditer(r"<blockquote>.*?</blockquote>|(</p>)",story_html,re.S) if m[1]]
    if len(paragraphs)>1:split=paragraphs[(len(paragraphs)-1)//2]
   if len(boundaries)>2 or len(paragraphs)>1:
    story_html=story_html[:split]+adsterra_slot("inline",lang)+story_html[split:]
  title_ad=adsterra_slot("title",lang) if show_ads else ""
  reading_html='<p class="reading-meta">'+(f'{reading_minutes} min read' if content_lang=='en' else f'{reading_minutes} मिनट में पढ़ें')+'</p>'
  guide_notice=('<p class="guide-context">'+('Reference guide • Source-listed details may cover multiple variants. Check the exact model and market before buying.' if content_lang=='en' else 'संदर्भ गाइड • स्रोत में कई वेरिएंट का विवरण हो सकता है। खरीदने से पहले सही मॉडल और बाजार की जानकारी जाँचें।')+'</p>') if p.get('directory_kind') in ('phones','cars','bikes') else ''
  trending_html=trending_section(lang,p)
  content=f'''<div class="wrap"><article class="article readable-article" data-article-layout="v3"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/{lang}/">{'Home' if lang=='en' else 'होम'}</a> › <a href="/{lang}/{category(p)}/">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</a> › <span>{e(t)}</span></nav><div class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</div><h1>{e(t)}</h1>{title_ad}<p class="date"><time datetime="{e(p.get('date',''))}">{e(display_date(p.get('date','')))}</time> · <a href="/{lang}/author/{author_handle(p)}/">{e(author_name(p))}</a> · Source: {e(sourcehost)}</p>{reading_html}{updated_notice(p,lang)}<div class="summary"><strong>{'Key takeaways' if lang=='en' else 'मुख्य बातें'}</strong>{summary}</div>{featured_html}{guide_notice}{article_note(p,lang)}{article_panel(p,lang)}{toc_html}<div class="story">{story_html}</div>{share_html}{keyword_html}<div class="source"><strong>{'Read the original source' if lang=='en' else 'मूल स्रोत पढ़ें'}:</strong> <a href="{e(p['source'])}" rel="noopener noreferrer" target="_blank">{e(p.get('source_title') or sourcehost)}</a><p class="notice">{'AI-assisted reporting; source claims are attributed and have not been independently verified.' if lang=='en' else 'AI की सहायता से तैयार रिपोर्ट; मूल स्रोत के दावों की स्वतंत्र पुष्टि नहीं की गई है।'}</p></div><section class="author-about"><h2>{'About the author' if lang=='en' else 'लेखक के बारे में'}</h2><p><a href="/{lang}/author/{author_handle(p)}/">{e(author_name(p))}</a> — {'AI-assisted news based on attributed published sources.' if lang=='en' else 'प्रकाशित स्रोतों पर आधारित AI-सहायता प्राप्त खबरें।'}</p></section><h2>{'More to read' if lang=='en' else 'और पढ़ें'}</h2><div class="related">{related_html}</div>{trending_html}</article></div>'''
  page=shell(lang,t,desc,url,content,extra,alternate_urls=alternate_urls,canonical_url=canonical_url,robots='noindex,follow,max-image-preview:large' if fallback else ROBOTS,document_lang=content_lang)
  if show_ads:
   page=page.removesuffix('</body></html>')+article_ad_scripts()+'</body></html>'
  write(OUT / article_path(p,lang).lstrip('/') / 'index.html',page)
for lang in ('en','hi'):
 h='Worldwide news, movies and technology explained' if lang=='en' else 'दुनियाभर की ताज़ा खबरें, आसान हिंदी में'
 desc=label('Worldwide news, movies, entertainment, technology, business, sports and useful explainers.',lang)
 latest=''.join(card(p,lang) for p in POSTS[:24]) or '<p>No articles yet. New verified-source explainers are being prepared.</p>'
 focus_posts=[p for p in POSTS if category(p) in ('technology','automobiles')][:6]
 focus_html='<section class="focus-news"><div class="sectiontitle"><h2>'+('Technology & Automobiles' if lang=='en' else 'टेक्नोलॉजी और ऑटोमोबाइल')+'</h2><a href="/'+lang+'/technology/">'+('More technology news' if lang=='en' else 'और टेक खबरें')+' →</a></div><div class="cards">'+''.join(card(p,lang) for p in focus_posts)+'</div></section>' if focus_posts else ''
 sidebar='<aside class="side"><div class="panel"><h2>'+label('Explore AI tools',lang)+'</h2>'+''.join(f'<a href="/{lang}/tools/">{e(x[0])} · {e(label(x[3],lang))}</a>' for x in TOOLS[:6])+'</div><div class="panel"><h2>'+label('Our approach',lang)+'</h2><p>'+label('Read original sources. Check dates. Explain what matters. Corrections welcome.',lang)+'</p></div></aside>'
 featured=''.join(f'<article class="tool"><span class="pill">{e(label(cat,lang))}</span><h3>{e(n)}</h3><p>{e(label(d,lang))}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{ "Official website" if lang=="en" else "आधिकारिक वेबसाइट"} ↗</a></article>' for n,d,u,cat in TOOLS[:8])
 tools_home=f'<section class="featured-tools" aria-labelledby="featured-tools-heading"><div class="sectiontitle"><h2 id="featured-tools-heading">{"Explore AI Tools" if lang=="en" else "AI टूल्स खोजें"}</h2><a href="/{lang}/tools/">{"View all AI tools" if lang=="en" else "सभी AI टूल्स देखें"} →</a></div><p class="muted">{"Explore trusted official links for writing, research, coding and design." if lang=="en" else "लेखन, रिसर्च, कोडिंग और डिजाइन के लिए आधिकारिक AI टूल्स।"}</p><div class="tools featured-grid">{featured}</div></section>'
 priority_links=''.join('<a href="'+article_path(q,lang)+'">'+e(title(q,lang))+'</a>' for q in recent_priority(POSTS))
 priority_home='<section class="hub-home"><div class="sectiontitle"><h2>'+('Priority updates' if lang=='en' else 'जरूरी अपडेट')+'</h2><a href="/'+lang+'/all-news/">'+('All latest news →' if lang=='en' else 'सभी ताज़ा खबरें →')+'</a></div><p class="muted">'+('Selected from the last 48 hours by freshness and editorial topic priority.' if lang=='en' else 'पिछले 48 घंटों की खबरों में से ताज़गी और उपयोगिता के आधार पर चयन।')+'</p><div class="hub-announcement">'+priority_links+'</div><div class="hub-topics"><a href="/'+lang+'/jobs-exams/">'+('Jobs & Exam Hub' if lang=='en' else 'नौकरी और परीक्षा हब')+'</a><a href="/'+lang+'/telecom/">Jio · Airtel · Vi · BSNL</a></div></section>'
 home=f'<div class="wrap"><section class="lead"><div class="eyebrow">{label("WORLDWIDE NEWS & EXPLAINERS",lang)}</div><h1>{h}</h1><p class="muted">{desc}</p></section><div class="sectiontitle"><h2>{"Latest stories" if lang=="en" else "नई खबरें"}</h2><a href="/{lang}/tools/">{"AI Tools" if lang=="en" else "AI टूल्स"} →</a></div><div class="layout"><div class="cards">{latest}</div>{sidebar}</div>{priority_home}{focus_html}{trending_section(lang)}{tools_home}</div>'
 write(OUT/lang/'index.html',shell(lang,h+' | GlobeWire Daily',desc,f'{SITE}/{lang}/',home))
 page_size=24
 total_pages=max(1,(len(POSTS)+page_size-1)//page_size)
 def page_nav(page):
  prev=(f'<a href="/{lang}/" rel="prev">← {"Previous" if lang=="en" else "पिछला"}</a>' if page==2 else f'<a href="/{lang}/page/{page-1}/" rel="prev">← {"Previous" if lang=="en" else "पिछला"}</a>') if page>1 else ''
  nxt=f'<a href="/{lang}/page/{page+1}/" rel="next">{"Next" if lang=="en" else "अगला"} →</a>' if page<total_pages else ''
  return f'<nav aria-label="Article pages" style="display:flex;justify-content:space-between;align-items:center;gap:16px;margin:28px 0 42px;font-size:1.1rem"><span>{prev}</span><span>{page} / {total_pages}</span><span>{nxt}</span></nav>'
 home=home.replace(f'<div class="cards">{latest}</div>',f'<div><div class="cards">{latest}</div>{page_nav(1)}</div>')
 write(OUT/lang/'index.html',shell(lang,h+' | GlobeWire Daily',desc,f'{SITE}/{lang}/',home))
 for page in range(2,total_pages+1):
  batch=''.join(card(p,lang) for p in POSTS[(page-1)*page_size:page*page_size])
  paged=f'<div class="wrap"><div class="sectiontitle"><h1>{"Latest stories" if lang=="en" else "नई खबरें"} — {page}</h1></div><div class="layout"><div><div class="cards">{batch}</div>{page_nav(page)}</div>{sidebar}</div></div>'
  write(OUT/lang/'page'/str(page)/'index.html',shell(lang,f'News page {page} | GlobeWire Daily',desc,f'{SITE}/{lang}/page/{page}/',paged))

 for cat,(en_label,hi_label) in CATEGORIES.items():
  selected=[p for p in POSTS if matches_category(p,cat)]
  heading=en_label if lang=='en' else hi_label
  intro=category_description(cat,CATEGORIES[cat],lang)
  cat_pages=max(1,(len(selected)+23)//24)
  for cat_page in range(1,cat_pages+1):
   batch=selected[(cat_page-1)*24:cat_page*24]
   listing=''.join(card(p,lang) for p in batch) or ('<p>No published articles in this category yet.</p>' if lang=='en' else '<p>इस श्रेणी में अभी कोई प्रकाशित लेख नहीं है।</p>')
   prev_url=(f'/{lang}/{cat}/' if cat_page==2 else f'/{lang}/{cat}/page/{cat_page-1}/') if cat_page>1 else ''
   next_url=f'/{lang}/{cat}/page/{cat_page+1}/' if cat_page<cat_pages else ''
   prev_link=f'<a href="{prev_url}" rel="prev">← {"Previous" if lang=="en" else "पिछला"}</a>' if prev_url else ''
   next_link=f'<a href="{next_url}" rel="next">{"Next" if lang=="en" else "अगला"} →</a>' if next_url else ''
   pager=f'<nav class="category-pagination" aria-label="Category pages">{prev_link}<span>{cat_page} / {cat_pages}</span>{next_link}</nav>' if cat_pages>1 else ''
   telecom_links=('<div class="hub-topics"><a href="https://www.jio.com/about/news-media/" target="_blank" rel="noopener noreferrer">Jio ↗</a><a href="https://www.airtel.in/press-release/" target="_blank" rel="noopener noreferrer">Airtel ↗</a><a href="https://www.myvi.in/media/press-releases" target="_blank" rel="noopener noreferrer">Vi ↗</a><a href="https://wsc.cdr.bsnl.co.in/viewAllPlans" target="_blank" rel="noopener noreferrer">BSNL plans ↗</a><a href="https://trai.gov.in/notifications/press-release" target="_blank" rel="noopener noreferrer">TRAI ↗</a></div>' if cat=='telecom' else '')
   notices_html=official_notice_rows(cat,lang)
   notices_html=('<section class="hub-section"><ul>'+notices_html+'</ul></section>' if notices_html else '')
   catbody=f'<div class="wrap"><section class="lead"><h1>{e(heading)}{f" — {cat_page}" if cat_page>1 else ""}</h1><p class="muted">{e(intro)}</p>{telecom_links}</section>{notices_html}<div class="cards">{listing}</div>{pager}</div>'
   cat_path=f'/{lang}/{cat}/' if cat_page==1 else f'/{lang}/{cat}/page/{cat_page}/'
   write(OUT / cat_path.lstrip('/') / 'index.html',shell(lang,heading+(f' — Page {cat_page}' if cat_page>1 else '')+' | GlobeWire Daily',category_description(cat,CATEGORIES[cat],lang,cat_page),f'{SITE}{cat_path}',catbody,robots=ROBOTS if selected or notices_html else 'noindex,follow,max-image-preview:large'))

 toolcards=''.join(f'<article class="tool"><span class="pill">{e(label(cat,lang))}</span><h2>{e(n)}</h2><p>{e(label(d,lang))}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">Official website ↗</a></article>' for n,d,u,cat in TOOLS)
 tools=f'<div class="wrap"><section class="lead"><div class="eyebrow">AI TOOLS DIRECTORY</div><h1>{"Explore useful AI tools" if lang=="en" else "काम के AI टूल्स खोजें"}</h1><p class="muted">Official links, brief descriptions and categories. Availability and pricing can change; verify on provider websites.</p></section><div class="tools">{toolcards}</div></div>'
 write(OUT/lang/'tools/index.html',shell(lang,'AI Tools Directory | GlobeWire Daily','Explore popular AI assistants, research, coding and design tools.',f'{SITE}/{lang}/tools/',tools))
 pages={
 'about':('About GlobeWire Daily','GlobeWire Daily is an independent bilingual technology publication focused on useful explainers and news. We use AI-assisted drafting and translation, link to source materials, and welcome corrections. We do not claim to independently verify every publisher statement.'),
 'editorial':('Editorial Policy','Our articles are based on attributed source material. We prioritize official announcements, documentation and credible reporting. AI may assist drafting and translation. We require useful source-supported context, practical implications, clear distinctions between confirmed facts and uncertainty, and transparent attribution. We prohibit fabricated quotes, unsupported claims, misleading headlines, and unattributed copying. When a claim cannot be confirmed, we label uncertainty or do not publish it. Readers can request corrections.'),
 'corrections':('Corrections Policy','Report factual errors, misleading headlines, inaccurate translations, or rights concerns to contact@globewiredaily.org with the article URL and supporting evidence. Substantive corrections should be reflected in the article with an updated date.'),
 'privacy':('Privacy Policy','GlobeWire Daily publishes static news and informational pages. Hosting providers may process IP addresses, device information and technical request logs for security and delivery. We use Google AdSense advertising technology, which may use cookies or similar identifiers to serve and measure ads, subject to applicable consent requirements and Google policies. You can learn how Google uses data from partner sites at https://policies.google.com/technologies/partner-sites and manage Google ad preferences at https://myadcenter.google.com/. On news articles, Adsterra and Infolinks ads may load automatically for visitors whose connection is identified as being in India. These providers may use cookies or similar technologies to serve and measure ads. Third-party websites linked from our articles have separate privacy practices. We do not operate reader accounts or a newsletter. For privacy or data requests, contact contact@globewiredaily.org.'),
 'contact':('Contact GlobeWire Daily','For news tips, corrections, image rights requests, privacy matters or editorial feedback, email contact@globewiredaily.org. Do not include sensitive personal information.'),
 'affiliate':('Affiliate Disclosure','Our AI Tools directory currently contains informational links. If affiliate partnerships or paid placements are introduced, they will be clearly identified. We do not claim that editorial recommendations are paid placements.')}
 for s,(t,d) in pages.items():
  content=f'<div class="wrap"><article class="article"><div class="eyebrow">GLOBEWIRE DAILY</div><h1>{e(t)}</h1><div class="story"><p>{e(label(d,lang))}</p></div><p>Contact: <a href="mailto:{CONTACT}">{CONTACT}</a></p></article></div>'
  write(OUT/lang/s/'index.html',shell(lang,t,d,f'{SITE}/{lang}/{s}/',content))
for lang in ('en','hi'):
 author_url=f'{SITE}/{lang}/author/editorial-desk/'
 author_body='<div class="wrap"><article class="article"><h1>GlobeWire Daily Editorial Desk</h1><p>AI-assisted reporting based on attributed sources. No individual journalist is claimed.</p><p><a href="/'+lang+'/editorial/">Editorial policy</a> · <a href="mailto:'+CONTACT+'">Contact</a></p></article><h2>Recent articles</h2><div class="cards">'+''.join(card(p,lang) for p in POSTS[:24])+'</div></div>'
 write(OUT/lang/'author'/'editorial-desk'/'index.html',shell(lang,'GlobeWire Daily Editorial Desk','Source-attributed news reporting',author_url,author_body))
for lang in ('en','hi'):
 for handle in sorted(set(AUTHOR_HANDLES.values())):
  author_url=f'{SITE}/{lang}/author/{handle}/'
  author_title='GlobeWire Daily '+handle.replace('-',' ').title()
  matching=[p for p in POSTS if author_handle(p)==handle]
  author_body='<div class="wrap"><section class="lead"><h1>'+e(author_title)+'</h1><p>Topic-focused editorial desk of GlobeWire Daily. AI-assisted articles use attributed published sources; no individual reporter or independent verification is implied.</p><p><a href="/'+lang+'/editorial/">Editorial policy</a></p></section><div class="cards">'+''.join(card(p,lang) for p in matching[:24])+'</div></div>'
  write(OUT/lang/'author'/handle/'index.html',shell(lang,author_title,author_title+' — AI-assisted source-attributed reporting',author_url,author_body))
# Bare domain forwards readers to the canonical English homepage.
# Keep the published news, category links and the Hindi language switch under /en/ and /hi/.
write(OUT/'index.html','<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url=/en/"><link rel="canonical" href="'+SITE+'/en/"></head><body><a href="/en/">English</a></body></html>')
write(OUT/'favicon.svg','''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0a1429"/><circle cx="32" cy="32" r="23" fill="none" stroke="#5ce0dc" stroke-width="2"/><path d="M9 32h46M32 9c-12 12-12 34 0 46M32 9c12 12 12 34 0 46" fill="none" stroke="#5ce0dc" stroke-width="1.5"/><text x="32" y="40" text-anchor="middle" fill="white" font-family="Arial,sans-serif" font-size="21" font-weight="bold">GW</text></svg>''')
# A real 404 document prevents Pages from serving the homepage with HTTP 200 for unknown URLs.
missing='<div class="wrap"><article class="article"><h1>Page not found / पेज नहीं मिला</h1><p>The requested page is unavailable. Check the address or browse the current news categories.</p><p>यह पेज उपलब्ध नहीं है। पता जाँचें या खबरों की श्रेणियाँ देखें।</p><p><a href="/en/">English home</a> · <a href="/hi/">हिंदी होम</a> · <a href="/en/site-map/">Explore topics</a></p></article></div>'
write(OUT/'404.html',shell('en','Page not found | GlobeWire Daily','The requested page was not found.',SITE+'/404.html',missing,alternate_urls={},robots='noindex,follow'))
write(OUT/'robots.txt',f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/news-sitemap.xml\n')
urls=[f'/{lang}/{path}' for lang in ('en','hi') for path in ('','colleges/','courses/','cars/','phones/','bikes/','global-topics/','launches/','freebies-deals/','study-abroad-guide/','jobs-archive/','all-news/','jobs-exams/','author/editorial-desk/','tools/','government-schemes/','sarkari-naukri/','private-vacancy/','movies-entertainment/','world-news/','business/','sports/','automobiles/','health-science/','gaming/','environment/','travel/','education/','lifestyle/','technology/','about/','editorial/','corrections/','privacy/','contact/','affiliate/')]+[f'/{lang}/page/{page}/' for lang in ('en','hi') for page in range(2,max(1,(len(POSTS)+23)//24)+1)]+[f'/{lang}/{cat}/page/{page}/' for lang in ('en','hi') for cat in CATEGORIES for page in range(2,max(1,(sum(1 for p in POSTS if matches_category(p,cat))+23)//24)+1)]+[f'/{lang}/author/{handle}/' for lang in ('en','hi') for handle in sorted(set(AUTHOR_HANDLES.values()))]+[article_path(p,lang) for p in POSTS for lang in ('en','hi')]
notice_cache=details_cache()
urls += [notice_path(n,lang) for n in load_notices() if notice_cache.get(n['source'],{}).get('fields') for lang in ('en','hi')]
urls=list(dict.fromkeys(urls+[f'/{lang}/{cat}/' for lang in ('en','hi') for cat in CATEGORIES]))
write(OUT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(SITE+u)+'</loc></url>' for u in urls)+'</urlset>')
write_news_sitemap(OUT,SITE,POSTS,article_path,title,languages=article_languages)
# Preserve old article URLs as permanent redirects to canonical descriptive URLs.
redirects=['/ /en/ 301']
for p in POSTS:
 for lang in ('en','hi'):
  redirects.append(f'/{lang}/news/{slug(p)}/ {article_path(p,lang)} 301')
for old,canonical in DUPLICATE_POSTS:
 for lang in ('en','hi'):
  oldpath=article_path(old,lang)
  redirects.append(f'{oldpath} {article_path(canonical,lang)} 301')
  redirects.append(f'/{lang}/news/{slug(old)}/ {article_path(canonical,lang)} 301')
  olddir=OUT/oldpath.lstrip('/')
  if olddir.is_dir():shutil.rmtree(olddir)
print('SEO_REDIRECTS',write_redirects(OUT,redirects,write,SITE))
write(OUT/'ads.txt','google.com, pub-1849673109734274, DIRECT, f08c47fec0942fa0\n')
write(OUT/'_headers','/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/\n  Cache-Control: public, max-age=0, must-revalidate\n/*/\n  Cache-Control: public, max-age=0, must-revalidate\n/style.css\n  Cache-Control: public, max-age=3600\n/site.js\n  Cache-Control: public, max-age=3600\n/images/*\n  Cache-Control: public, max-age=86400\n/seo-audit.json\n  X-Robots-Tag: noindex\n/deployment.json\n  X-Robots-Tag: noindex\n')
print('Built',len(POSTS),'posts; AI Tools, bilingual pages, news sitemap and responsive layout')

render_hubs(OUT,SITE,POSTS,shell,article_path,title,write)

render_expanded_hubs(OUT,SITE,POSTS,shell,article_path,title,write)

render_notices(OUT,SITE,shell,write)
render_directories(OUT,SITE,shell,write)
render_link_resources(OUT,SITE,POSTS,shell,article_path,title,write)
write(OUT/'style.css',CSS+MENU_CSS+HUB_CSS+GLOBAL_CSS+EXAM_CSS+DIRECTORY_CSS+ARTICLE_CSS)
write(OUT/'site.js',JS+HUB_JS+GLOBAL_JS+DIRECTORY_JS)

# Let production checks distinguish a stale status badge from a stale deployment.
from image_rules import pipeline_fingerprint
write(OUT/'deployment.json',json.dumps({'image_pipeline':pipeline_fingerprint(R),'posts':len(POSTS),'seo_pipeline':'v2'},sort_keys=True)+'\n')

# Reconcile the sitemap after every page family has rendered, including courses and directory profiles.
for lang in ('en','hi'):
 heading='Explore GlobeWire Daily' if lang=='en' else 'GlobeWire Daily की सभी श्रेणियाँ'
 links=''.join('<li><a href="/'+lang+'/'+key+'/">'+e(names[lang=='hi'])+'</a></li>' for key,names in CATEGORIES.items())
 extras=[('resources','Reference resources','संदर्भ और तुलना'),('all-news','Latest news','ताज़ा खबरें'),('jobs-exams','Jobs and exams','नौकरी और परीक्षा'),('colleges','Colleges','कॉलेज'),('courses','Courses','कोर्स'),('cars','Cars','कारें'),('phones','Phones','फोन'),('bikes','Bikes','बाइक'),('tools','AI tools','AI टूल्स')]
 links+=''.join('<li><a href="/'+lang+'/'+key+'/">'+e(hi if lang=='hi' else en)+'</a></li>' for key,en,hi in extras)
 body='<div class="wrap"><section class="lead"><h1>'+heading+'</h1><p>'+('Browse news categories, reference directories and useful tools.' if lang=='en' else 'खबरों की श्रेणियाँ, संदर्भ डायरेक्टरी और उपयोगी टूल्स देखें।')+'</p></section><ul class="topic-directory">'+links+'</ul></div>'
 write(OUT/lang/'site-map/index.html',shell(lang,heading,'News topics and reference directories' if lang=='en' else 'खबरों के विषय और उपयोगी डायरेक्टरी',SITE+'/'+lang+'/site-map/',body))
count=write_site_sitemap(OUT,SITE,GENERATED_HTML)
write(OUT/'seo-audit.json',json.dumps({'version':'v2','canonical_indexable_pages':count,'article_records':len(POSTS),'translated_hindi_articles':sum('hi' in article_languages(p) for p in POSTS)},sort_keys=True)+'\n')
print('SEO_SITEMAP',count,'generated indexable self-canonical pages')

# Cloudflare Pages capacity diagnostics: preserve every article and asset.
from collections import Counter
asset_files=[p for p in OUT.rglob('*') if p.is_file()]
asset_counts=Counter(p.suffix.lower() or '[no extension]' for p in asset_files)
section_counts=Counter(p.relative_to(OUT).parts[0] for p in asset_files)
redirect_stub_count=0
for p in asset_files:
 if p.name!='index.html' or p.stat().st_size>2048: continue
 try:
  if '<title>Article moved</title>' in p.read_text(encoding='utf-8'):
   redirect_stub_count+=1
 except (OSError, UnicodeError): pass
print('CLOUDFLARE_ASSET_COUNT',len(asset_files),'BY_TYPE',dict(asset_counts))
# Show the sections responsible for growth; never prune published articles.
asset_sections=Counter('/'.join(p.relative_to(OUT).parts[:2]) for p in asset_files)
print('CLOUDFLARE_ASSET_SECTIONS',dict(asset_sections.most_common(30)))
print('PUBLISHED_ARTICLES_PRESERVED',len(POSTS),'DUPLICATE_REDIRECTS',len(DUPLICATE_POSTS))
print('CLOUDFLARE_ASSET_SECTIONS',dict(section_counts),'REDIRECT_STUBS',redirect_stub_count)
print('ARTICLE_SOURCE_JSON_COUNT',len(list((R/'content/posts').glob('*.json'))),'PUBLISHED_POSTS',len(POSTS))
if len(asset_files)>19000:
 raise RuntimeError(f'Cloudflare Pages output has {len(asset_files)} files; safe threshold is 19000. No article or image has been deleted; use the section diagnostics to plan a safe migration.')
