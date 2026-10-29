from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import urlparse, quote
import os, html, json, shutil, re, datetime as dt, math, textwrap, hashlib
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parents[1]; OUT=R/'dist'; SITE='https://globewiredaily.org'.rstrip('/'); CONTACT='contact@globewiredaily.org'
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'googled7fc3627b4add656.html').write_text('google-site-verification: googled7fc3627b4add656.html\n',encoding='utf-8')
def e(x):return html.escape(str(x or ''),quote=True)
def write(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 data=s.encode('utf-8')
 if p.is_file() and p.read_bytes()==data:return
 p.write_bytes(data)
def title(p,lang):
 raw=str(p.get(lang+'_title') or p.get('en_title') or 'Technology news')
 return re.sub(r'\\s*[—–-]\\s*article featured image\\s*$', '', raw, flags=re.I).strip()
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
write(OUT/'style.css',CSS)
JS='''addEventListener('scroll',()=>{let d=document.documentElement;let m=d.scrollHeight-d.clientHeight;let b=document.querySelector('.reading');if(b)b.style.width=(m>0?100*d.scrollTop/m:0)+'%';},{passive:true});'''
JS += """document.addEventListener('click',async function(ev){const share=ev.target.closest('.native-share');if(share){const data={title:share.dataset.shareTitle,url:share.dataset.shareUrl};if(navigator.share){try{await navigator.share(data)}catch(err){if(err.name!=='AbortError')location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}else{location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}const copy=ev.target.closest('.copy-share');if(copy){try{await navigator.clipboard.writeText(copy.dataset.shareUrl);const old=copy.textContent;copy.textContent='✓ Copied';setTimeout(()=>copy.textContent=old,1800)}catch(err){prompt('Copy link:',copy.dataset.shareUrl)}}});"""
CSS += """.category-pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:30px 0 48px;flex-wrap:wrap}.category-pagination a{display:inline-block;background:#fff;border:1px solid #d9e5f0;border-radius:9px;padding:8px 13px;text-decoration:none}"""
CSS += """.breadcrumbs{font-size:13px;line-height:1.6;color:#5b6c83;margin-bottom:14px;overflow-wrap:anywhere}.breadcrumbs a{color:#12588b;text-decoration:none}.breadcrumbs span{color:#667085}"""
CSS += """.article-tags{margin:26px 0;padding:16px 0;border-top:1px solid #e5ebf3;border-bottom:1px solid #e5ebf3}.article-tags strong{display:block;font-size:14px;margin-bottom:10px}.tag-list{display:flex;gap:8px;flex-wrap:wrap}.tag{font-size:12px;padding:5px 11px;background:#eef4fa;color:#24496a;border:1px solid #dce7f2;border-radius:100px}.related .related-card{padding:0;overflow:hidden;background:#f2f7fc}.related-card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.related-card span:not(.related-placeholder){display:block;padding:12px;font-size:14px;line-height:1.5}.related-placeholder{display:flex;align-items:center;justify-content:center;min-height:120px;background:#e4edf7;color:#49617a;font-size:12px}.trending-news{margin-top:32px;border-top:1px solid #dfe7ef;padding-top:20px}.trending-list{display:grid;gap:12px}.trending-list a{display:flex;align-items:center;gap:14px;background:#f7f9fc;padding:10px;border-radius:10px;text-decoration:none;font-weight:650;line-height:1.5}.trending-list img{width:100px;height:68px;object-fit:cover;border-radius:7px;flex-shrink:0}@media(max-width:560px){.related{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.related-card span:not(.related-placeholder){font-size:12px;padding:9px}.trending-list img{width:82px;height:58px}}"""
CSS += """.article{max-width:850px;margin:28px auto 50px;padding:clamp(20px,4vw,42px);line-height:1.85}.article h1{font-size:clamp(30px,4vw,46px);line-height:1.2}.article .story{font-size:17px;line-height:1.9}.article .story h2{margin:30px 0 12px;font-size:26px}.article .story h3{margin:24px 0 10px;font-size:21px}.article .story p{margin-bottom:20px}.article .hero{width:100%;height:auto;border-radius:12px}.author-about{margin:32px 0;padding:22px;background:#f5f8fc;border:1px solid #e0e8f1;border-radius:14px}.author-about h2{margin:0 0 8px;font-size:20px}@media(max-width:600px){.article{margin:14px auto 28px;padding:18px}.article .story{font-size:16px;line-height:1.8}.article .story h2{font-size:22px}}"""
CSS += """.card h2,.related-card span,.trending-list span{overflow:visible;text-overflow:clip;white-space:normal;overflow-wrap:anywhere;-webkit-line-clamp:unset;line-clamp:unset}.card,.card .inner{height:auto}.card a:focus-visible{outline:3px solid #0b8a93;outline-offset:3px}@media(max-width:600px){.card h2{font-size:17px;line-height:1.45}}"""
CSS += """.featured-figure{margin:18px 0 24px}.image-credit{font-size:12px;color:#68778a;margin-top:6px}.card h2{word-break:normal;overflow-wrap:break-word}"""
CSS += """/* Mobile menu must not be clipped by the horizontally scrolling nav.
   Keep dropdown in normal document flow and match the dark header. */
@media(max-width:999px){
 .top nav{overflow:visible!important;flex-wrap:wrap!important;align-items:center;gap:6px 12px;padding-bottom:4px}
 .top nav a{white-space:nowrap}
 .nav-more{position:static;flex-basis:100%;width:100%}
 .nav-more summary{display:inline-flex;align-items:center;color:#d9e6fb;padding:6px 0}
 .nav-more-list{position:static!important;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));width:100%;max-height:none;overflow:visible;background:#14233d;border:1px solid #354967;box-shadow:none;margin:4px 0 10px;padding:8px;border-radius:10px}
 .nav-more-list a{white-space:normal!important;color:#e7f2ff!important;font-size:13px;line-height:1.4;padding:10px 8px}
 .nav-more-list a:hover,.nav-more-list a:focus-visible{background:#263b5b;border-radius:6px}
 .nav-more:not([open]) .nav-more-list{display:none}
}
"""
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
write(OUT/'style.css',CSS)
write(OUT/'site.js',JS)
def shell(lang,t,desc,url,body,extra=''):
 nav=[('Home','होम',''),('Tech & AI','टेक और AI','technology/'),('Entertainment','मनोरंजन','movies-entertainment/'),('Jobs & Schemes','नौकरी और योजनाएँ','sarkari-naukri/')]
 links=''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in nav)
 more=[('AI Tools','AI टूल्स','tools/'),('Government Schemes','सरकारी योजनाएँ','government-schemes/'),('Private Jobs','प्राइवेट नौकरी','private-vacancy/'),('World','दुनिया','world-news/'),('Business','बिज़नेस','business/'),('Sports','खेल','sports/'),('Gaming','गेमिंग','gaming/'),('Automobiles','ऑटोमोबाइल','automobiles/'),('Health & Science','स्वास्थ्य और विज्ञान','health-science/'),('Environment','पर्यावरण','environment/'),('Travel','यात्रा','travel/'),('Education','शिक्षा','education/'),('Lifestyle','लाइफस्टाइल','lifestyle/'),('About','हमारे बारे में','about/'),('Editorial','संपादकीय नीति','editorial/'),('Contact','संपर्क','contact/')]
 more_html='<details class="nav-more"><summary>'+('More' if lang=='en' else 'और देखें')+'</summary><div class="nav-more-list">'+''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in more)+'</div></details>'
 return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="google-site-verification" content="IjjkuYPqG93dE2SwPvi0HJ258E5WwNGAhIu7LB9qQqE"><meta name="theme-color" content="#0a1429"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1849673109734274" crossorigin="anonymous"></script><title>{e(t)}</title><meta name="description" content="{e(desc[:160])}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{e(url)}"><link rel="alternate" hreflang="en" href="{e(url.replace('/hi/','/en/'))}"><link rel="alternate" hreflang="hi" href="{e(url.replace('/en/','/hi/'))}"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta name="color-scheme" content="light"><link rel="stylesheet" href="/style.css">{extra}</head><body><div class="reading"></div><header class="top"><div class="wrap"><a class="logo" href="/{lang}/">GlobeWire <span>Daily</span></a><nav aria-label="Primary">{links}<a class="langswitch" href="/{'hi' if lang=='en' else 'en'}/">{'हिन्दी' if lang=='en' else 'English'}</a></nav><div class="category-menu">{more_html}</div></div></header><main>{body}</main><footer class="footer"><div class="wrap"><div><strong>GlobeWire Daily</strong><p>Independent bilingual news and explainers, with clear sourcing, corrections and transparent editorial standards.</p><a href="mailto:{CONTACT}">{CONTACT}</a></div><div class="footerlinks">{''.join(f'<a href="/{lang}/{s}/">{s.title()}</a>' for s in ['about','privacy','contact','editorial','corrections','affiliate','tools'])}</div></div></footer><script defer src="/site.js"></script></body></html>'''
def has_featured(p):
 # Existing licensed/credited images always take priority.
 return (R/'content'/'featured'/f'{slug(p)}.jpg').is_file() or (OUT/'images'/f'{slug(p)}.jpg').is_file()

def image_for(p):
 """Keep existing photos; generate clearly labeled original editorial artwork only when missing."""
 s=slug(p);dest=OUT/'images'/f'{s}.jpg';dest.parent.mkdir(parents=True,exist_ok=True)
 existing=R/'content'/'featured'/f'{s}.jpg'
 if existing.is_file():
  shutil.copy2(existing,dest)
  return
 # No third-party photos are scraped or reused without documented rights.
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
def body_html(raw):
 # Render the small, supported Markdown subset without exposing formatting tokens.
 def inline(value):
  safe=e(value)
  safe=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',safe)
  safe=re.sub(r'(^|[^*])\*([^*\n]+)\*(?!\*)',r'\1<em>\2</em>',safe)
  return safe
 parts=[];buf=[];items=[]
 def flush():
  if buf:parts.append('<p>'+inline(' '.join(buf))+'</p>');buf.clear()
 def flush_items():
  if items:parts.append('<ul>'+''.join('<li>'+inline(item)+'</li>' for item in items)+'</ul>');items.clear()
 for line in str(raw).splitlines():
  line=line.strip()
  if not line:flush();flush_items();continue
  if line.startswith('### '):
   flush();flush_items();parts.append('<h3>'+inline(line[4:])+'</h3>')
  elif line.startswith('## '):
   flush();flush_items();parts.append('<h2>'+inline(line[3:])+'</h2>')
  elif re.match(r'^(?:[-*] |\d+\. )',line):
   flush();items.append(re.sub(r'^(?:[-*] |\d+\. )','',line))
  else:flush_items();buf.append(line)
 flush();flush_items();return ''.join(parts)
def image_caption(p,lang):
 s=slug(p)
 metadata=R/'content'/'featured'/f'{s}.json'
 if metadata.is_file():
  try:
   info=json.loads(metadata.read_text(encoding='utf-8'))
   if info.get('kind') in ('licensed_source','publisher_source'):
    credit=str(info.get('attribution') or 'Original publisher')
    license_name=str(info.get('license') or 'Creative Commons')
    return (f'Image: {credit} — {license_name}' if lang=='en' else f'चित्र: {credit} — {license_name}')
  except (OSError,ValueError):pass
 if not metadata.is_file():
  if (R/'content'/'featured'/f'{s}.jpg').is_file():
   return 'Featured image; source information not supplied.' if lang=='en' else 'फीचर्ड चित्र; स्रोत की जानकारी उपलब्ध नहीं है।'
  return 'Original GlobeWire Daily editorial illustration — not an event photograph.' if lang=='en' else 'GlobeWire Daily की मूल सांकेतिक तस्वीर — घटना की वास्तविक फोटो नहीं।'
 return 'Featured image; provenance not specified.' if lang=='en' else 'फीचर्ड चित्र; स्रोत निर्दिष्ट नहीं है।'
def card(p,lang):
 s=slug(p);t=title(p,lang)
 picture=f'<img loading="lazy" src="/images/{s}.jpg" width="1280" height="720" alt="{e(t)}">' if has_featured(p) else ''
 return f'<article class="card"><a href="{article_path(p,lang)}">{picture}<div class="inner"><span class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=="en" else 1])}</span><h2>{e(t)}</h2><div class="date">{e(p.get("date","")[:10])}</div></div></a></article>'

AUTHOR_HANDLES={'technology':'tech-desk','business':'business-desk','world-news':'world-desk','sports':'sports-desk','health-science':'science-desk','government-schemes':'public-services-desk','sarkari-naukri':'careers-desk','private-vacancy':'careers-desk','movies-entertainment':'entertainment-desk','automobiles':'auto-desk','gaming':'gaming-desk','environment':'climate-desk','travel':'travel-desk','education':'education-desk','lifestyle':'lifestyle-desk'}
def author_handle(p):return AUTHOR_HANDLES.get(category(p),'editorial-desk')
def author_name(p):return 'GlobeWire Daily '+author_handle(p).replace('-',' ').title()
def article_keywords(p,lang):
 raw=p.get(lang+'_keywords') or p.get('en_keywords') or []
 if isinstance(raw,str):raw=re.split(r'[,;|]',raw)
 if not isinstance(raw,list):raw=[]
 terms=[str(x).strip() for x in raw if str(x).strip()]
 terms.extend([title(p,lang),CATEGORIES[category(p)][0 if lang=='en' else 1],'GlobeWire Daily'])
 seen=set();result=[]
 for term in terms:
  key=term.casefold()
  if key not in seen and len(term)<=100:
   seen.add(key);result.append(term)
 return result[:12]
def trending_posts(exclude=None,limit=6):
 """Editorial trending proxy: recent articles with topical keyword overlap.
 No fabricated traffic, view counts or real-time search popularity."""
 now=dt.datetime.now(dt.timezone.utc)
 pool=[]
 for p in POSTS:
  if exclude is not None and slug(p)==slug(exclude):continue
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
 return [p for _,p in pool[:limit]]

def trending_section(lang,exclude=None):
 selected=trending_posts(exclude,6)
 if not selected:return ''
 heading='Trending on GlobeWire Daily' if lang=='en' else 'GlobeWire Daily पर चर्चित खबरें'
 note='Selected from recent coverage and related topics; not live search rankings.' if lang=='en' else 'हालिया खबरों और संबंधित विषयों पर आधारित चयन; लाइव सर्च रैंकिंग नहीं।'
 return '<section class="trending-news trending-feature"><h2>'+heading+'</h2><p class="muted">'+note+'</p><div class="trending-list">'+''.join('<a href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="120" height="80" src="/images/{slug(q)}.jpg" alt="">' if has_featured(q) else '<span class="related-placeholder">News</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in selected)+'</div></section>'

def display_date(value):
 try:
  stamp=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
  if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=dt.timezone.utc)
  return stamp.astimezone(dt.timezone(dt.timedelta(hours=5,minutes=30))).strftime('%d %b %Y, %I:%M %p IST')
 except (ValueError,TypeError):return str(value or '')[:10]

def limit_article_words(raw,limit=10000):
 parts=re.findall(r'\\S+',str(raw or ''))
 if len(parts)<=limit:return str(raw or '')
 return ' '.join(parts[:limit]).rstrip(' ,;:')+'…'

for p in POSTS:image_for(p)
for p in POSTS:
 s=slug(p)
 for lang in ('en','hi'):
  t=title(p,lang);raw=limit_article_words(p.get(lang+'_body') or p.get('en_body',''));url=f'{SITE}{article_path(p,lang)}';desc=p.get(lang+'_meta') or re.sub(r'[#\n]+',' ',raw)[:155]
  related=[q for q in POSTS if slug(q)!=s and category(q)==category(p) and has_featured(q)][:4]
  if len(related)<4:related += [q for q in POSTS if slug(q)!=s and q not in related][:4-len(related)]
  related_html=''.join('<a class="related-card" href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="320" height="180" src="/images/{slug(q)}.jpg" alt="{e(title(q,lang))}">' if has_featured(q) else '<span class="related-placeholder">GlobeWire Daily</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in related)
  keyword_html='<section class="article-tags"><strong>'+('Topics' if lang=='en' else 'संबंधित विषय')+'</strong><div class="tag-list">'+''.join('<span class="tag">'+e(term)+'</span>' for term in article_keywords(p,lang)[:7])+'</div></section>'
  trending=[q for q in POSTS if slug(q)!=s and has_featured(q)][:5]
  trending_html='<section class="trending-news"><h2>'+('Latest news' if lang=='en' else 'ताज़ा खबरें')+'</h2><div class="trending-list">'+''.join('<a href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="120" height="80" src="/images/{slug(q)}.jpg" alt="">' if has_featured(q) else '')+'<span>'+e(title(q,lang))+'</span></a>' for q in trending)+'</div></section>'
  schema={'@context':'https://schema.org','@type':'NewsArticle','headline':t,'articleSection':CATEGORIES[category(p)][0],'datePublished':p.get('date'),'dateModified':p.get('date'),'inLanguage':lang,'mainEntityOfPage':url,'image':([f'{SITE}/images/{s}.jpg'] if has_featured(p) else []),'author':{'@type':'Organization','name':author_name(p),'url':f'{SITE}/{lang}/author/{author_handle(p)}/'},'publisher':{'@type':'Organization','name':'GlobeWire Daily','url':SITE},'isBasedOn':p['source']}
  if not has_featured(p):schema.pop('image',None)
  schema['breadcrumb']={'@type':'BreadcrumbList','itemListElement':[
   {'@type':'ListItem','position':1,'name':'Home' if lang=='en' else 'होम','item':f'{SITE}/{lang}/'},
   {'@type':'ListItem','position':2,'name':CATEGORIES[category(p)][0 if lang=='en' else 1],'item':f'{SITE}/{lang}/{category(p)}/'},
   {'@type':'ListItem','position':3,'name':t,'item':url}]}
  schema['keywords']=article_keywords(p,lang)
  schema['description']=desc[:160]
  schema['url']=url
  schema_json=json.dumps(schema,ensure_ascii=False).replace('<',chr(92)+'u003c')
  extra_keywords='<meta name="keywords" content="'+e(', '.join(article_keywords(p,lang)))+'">'
  og_image=f'<meta property="og:image" content="{SITE}/images/{s}.jpg">' if has_featured(p) else ''
  extra=f'<meta property="og:type" content="article"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="GlobeWire Daily"><meta property="og:locale" content="{"en_US" if lang=="en" else "hi_IN"}"><meta property="og:title" content="{e(t)}"><meta property="og:description" content="{e(desc[:160])}"><meta property="article:published_time" content="{e(p.get("date",""))}"><meta property="article:section" content="{e(CATEGORIES[category(p)][0])}">{og_image}<meta name="twitter:card" content="{"summary_large_image" if has_featured(p) else "summary"}"><meta name="twitter:title" content="{e(t)}"><meta name="twitter:description" content="{e(desc[:160])}"><script type="application/ld+json">{schema_json}</script>'
  extra=extra_keywords+extra
  sourcehost=urlparse(p['source']).hostname or 'original source'
  summary=e(p.get(lang+'_summary') or p.get('en_summary') or re.sub(r'[#\n]+',' ',raw)[:270])
  featured_html=(f'<figure class="featured-figure"><img class="hero" src="/images/{s}.jpg" width="1280" height="720" fetchpriority="high" alt="{e(t)}"><figcaption class="image-credit">{e(image_caption(p,lang))}</figcaption></figure>' if has_featured(p) else '')
  share_text=('Share this article' if lang=='en' else 'यह खबर शेयर करें')
  copy_text=('Copy link' if lang=='en' else 'लिंक कॉपी करें')
  share_html=(f'<div class="article-share"><strong>{share_text}</strong><div class="share-actions">'
    f'<button type="button" class="native-share" data-share-url="{e(url)}" data-share-title="{e(t)}">↗ {share_text}</button>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://api.whatsapp.com/send?text={quote(t+" "+url)}">WhatsApp</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://www.facebook.com/sharer/sharer.php?u={quote(url,safe="")}">Facebook</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://t.me/share/url?url={quote(url,safe="")}&text={quote(t)}">Telegram</a>'
    f'<button type="button" class="copy-share" data-share-url="{e(url)}">{copy_text}</button></div></div>')
  related=[q for q in POSTS if slug(q)!=s and category(q)==category(p) and has_featured(q)][:4]
  if len(related)<4:related.extend([q for q in POSTS if slug(q)!=s and slug(q) not in {slug(x) for x in related} and category(q)!=category(p)][:4-len(related)])
  related_html=''.join('<a class="related-card" href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="320" height="180" src="/images/{slug(q)}.jpg" alt="{e(title(q,lang))}">' if has_featured(q) else '<span class="related-placeholder" aria-hidden="true">GlobeWire Daily</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in related)
  keyword_html='<section class="article-tags"><strong>'+('Topics' if lang=='en' else 'संबंधित विषय')+'</strong><div class="tag-list">'+''.join('<span class="tag">'+e(term)+'</span>' for term in article_keywords(p,lang)[:7])+'</div></section>'
  trending_html=trending_section(lang,p)
  content=f'''<div class="wrap"><article class="article"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/{lang}/">{'Home' if lang=='en' else 'होम'}</a> › <a href="/{lang}/{category(p)}/">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</a> › <span>{e(t)}</span></nav><div class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</div><h1>{e(t)}</h1><p class="date"><time datetime="{e(p.get('date',''))}">{e(display_date(p.get('date','')))}</time> · <a href="/{lang}/author/{author_handle(p)}/">{e(author_name(p))}</a></p>{featured_html}{share_html}<div class="summary"><strong>{'Key takeaways' if lang=='en' else 'मुख्य बातें'}</strong>{summary}</div><div class="story">{body_html(raw)}</div>{keyword_html}<div class="source"><strong>{'Read the original source' if lang=='en' else 'मूल स्रोत पढ़ें'}:</strong> <a href="{e(p['source'])}" rel="noopener noreferrer" target="_blank">{e(p.get('source_title') or sourcehost)}</a><p class="notice">{'AI-assisted reporting; source claims are attributed and have not been independently verified.' if lang=='en' else 'AI की सहायता से तैयार रिपोर्ट; मूल स्रोत के दावों की स्वतंत्र पुष्टि नहीं की गई है।'}</p></div><section class="author-about"><h2>{'About the author' if lang=='en' else 'लेखक के बारे में'}</h2><p><a href="/{lang}/author/{author_handle(p)}/">{e(author_name(p))}</a> — {'AI-assisted news based on attributed published sources.' if lang=='en' else 'प्रकाशित स्रोतों पर आधारित AI-सहायता प्राप्त खबरें।'}</p></section><h2>{'More to read' if lang=='en' else 'और पढ़ें'}</h2><div class="related">{related_html}</div>{trending_html}</article></div>'''
  write(OUT / article_path(p,lang).lstrip('/') / 'index.html',shell(lang,t,desc,url,content,extra))
for lang in ('en','hi'):
 h='Worldwide news, movies and technology explained' if lang=='en' else 'टेक्नोलॉजी की ताज़ा खबरें, आसान भाषा में'
 desc='Worldwide news, movies, entertainment, technology, business, sports and useful explainers.'
 latest=''.join(card(p,lang) for p in POSTS[:24]) or '<p>No articles yet. New verified-source explainers are being prepared.</p>'
 focus_posts=[p for p in POSTS if category(p) in ('technology','automobiles')][:6]
 focus_html='<section class="focus-news"><div class="sectiontitle"><h2>'+('Technology & Automobiles' if lang=='en' else 'टेक्नोलॉजी और ऑटोमोबाइल')+'</h2><a href="/'+lang+'/technology/">'+('More technology news' if lang=='en' else 'और टेक खबरें')+' →</a></div><div class="cards">'+''.join(card(p,lang) for p in focus_posts)+'</div></section>' if focus_posts else ''
 sidebar='<aside class="side"><div class="panel"><h2>Explore AI tools</h2>'+''.join(f'<a href="/{lang}/tools/">{e(x[0])} · {e(x[3])}</a>' for x in TOOLS[:6])+'</div><div class="panel"><h2>Our approach</h2><p>Read original sources. Check dates. Explain what matters. Corrections welcome.</p></div></aside>'
 featured=''.join(f'<article class="tool"><span class="pill">{e(cat)}</span><h3>{e(n)}</h3><p>{e(d)}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{ "Official website" if lang=="en" else "आधिकारिक वेबसाइट"} ↗</a></article>' for n,d,u,cat in TOOLS[:8])
 tools_home=f'<section class="featured-tools" aria-labelledby="featured-tools-heading"><div class="sectiontitle"><h2 id="featured-tools-heading">{"Explore AI Tools" if lang=="en" else "AI टूल्स खोजें"}</h2><a href="/{lang}/tools/">{"View all AI tools" if lang=="en" else "सभी AI टूल्स देखें"} →</a></div><p class="muted">{"Explore trusted official links for writing, research, coding and design." if lang=="en" else "लेखन, रिसर्च, कोडिंग और डिजाइन के लिए आधिकारिक AI टूल्स।"}</p><div class="tools featured-grid">{featured}</div></section>'
 home=f'<div class="wrap"><section class="lead"><div class="eyebrow">WORLDWIDE NEWS & EXPLAINERS</div><h1>{h}</h1><p class="muted">{desc}</p></section><div class="sectiontitle"><h2>{"Latest stories" if lang=="en" else "नई खबरें"}</h2><a href="/{lang}/tools/">AI Tools →</a></div><div class="layout"><div class="cards">{latest}</div>{sidebar}</div>{focus_html}{trending_section(lang)}{tools_home}</div>'
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
   write(OUT / cat_path.lstrip('/') / 'index.html',shell(lang,heading+(f' — Page {cat_page}' if cat_page>1 else '')+' | GlobeWire Daily',intro,f'{SITE}{cat_path}',catbody))

 toolcards=''.join(f'<article class="tool"><span class="pill">{e(cat)}</span><h2>{e(n)}</h2><p>{e(d)}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">Official website ↗</a></article>' for n,d,u,cat in TOOLS)
 tools=f'<div class="wrap"><section class="lead"><div class="eyebrow">AI TOOLS DIRECTORY</div><h1>{"Explore useful AI tools" if lang=="en" else "काम के AI टूल्स खोजें"}</h1><p class="muted">Official links, brief descriptions and categories. Availability and pricing can change; verify on provider websites.</p></section><div class="tools">{toolcards}</div></div>'
 write(OUT/lang/'tools/index.html',shell(lang,'AI Tools Directory | GlobeWire Daily','Explore popular AI assistants, research, coding and design tools.',f'{SITE}/{lang}/tools/',tools))
 pages={
 'about':('About GlobeWire Daily','GlobeWire Daily is an independent bilingual technology publication focused on useful explainers and news. We use AI-assisted drafting and translation, link to source materials, and welcome corrections. We do not claim to independently verify every publisher statement.'),
 'editorial':('Editorial Policy','Our articles are based on attributed source material. We prioritize official announcements, documentation and credible reporting. AI may assist drafting and translation. We require useful source-supported context, practical implications, clear distinctions between confirmed facts and uncertainty, and transparent attribution. We prohibit fabricated quotes, unsupported claims, misleading headlines, and unattributed copying. When a claim cannot be confirmed, we label uncertainty or do not publish it. Readers can request corrections.'),
 'corrections':('Corrections Policy','Report factual errors, misleading headlines, inaccurate translations, or rights concerns to contact@globewiredaily.org with the article URL and supporting evidence. Substantive corrections should be reflected in the article with an updated date.'),
 'privacy':('Privacy Policy','GlobeWire Daily publishes static news and informational pages. Hosting providers may process IP addresses, device information and technical request logs for security and delivery. We use Google AdSense advertising technology, which may use cookies or similar identifiers to serve and measure ads, subject to applicable consent requirements and Google policies. You can learn how Google uses data from partner sites at https://policies.google.com/technologies/partner-sites and manage Google ad preferences at https://myadcenter.google.com/. Third-party websites linked from our articles have separate privacy practices. We do not operate reader accounts or a newsletter. For privacy or data requests, contact contact@globewiredaily.org.'),
 'contact':('Contact GlobeWire Daily','For news tips, corrections, image rights requests, privacy matters or editorial feedback, email contact@globewiredaily.org. Do not include sensitive personal information.'),
 'affiliate':('Affiliate Disclosure','Our AI Tools directory currently contains informational links. If affiliate partnerships or paid placements are introduced, they will be clearly identified. We do not claim that editorial recommendations are paid placements.')}
 if lang=='hi':
  pages['about']=('GlobeWire Daily के बारे में','GlobeWire Daily एक स्वतंत्र द्विभाषी समाचार और जानकारी देने वाली वेबसाइट है। हमारा उद्देश्य तकनीक, AI, करियर, सरकारी योजनाओं और विश्व समाचार पर उपयोगी, स्रोत-आधारित जानकारी उपलब्ध कराना है। लेख तैयार करने और अनुवाद में AI की मदद ली जा सकती है। हम हर बाहरी दावे की स्वतंत्र पुष्टि का दावा नहीं करते। गलती मिलने पर पाठक सुधार का अनुरोध कर सकते हैं।')
  pages['contact']=('GlobeWire Daily से संपर्क करें','समाचार सुझाव, तथ्यात्मक सुधार, चित्र अधिकार, गोपनीयता या संपादकीय प्रतिक्रिया के लिए contact@globewiredaily.org पर ईमेल करें। संबंधित लेख का लिंक और समस्या का विवरण भेजें। संवेदनशील निजी जानकारी न भेजें।')
  pages['corrections']=('सुधार नीति','किसी लेख में गलत तथ्य, भ्रामक शीर्षक या अनुवाद की त्रुटि मिले तो लेख का लिंक और प्रमाण contact@globewiredaily.org पर भेजें। महत्वपूर्ण सुधार प्रकाशित लेख में दर्शाए जाने चाहिए।')
  pages['editorial']=('संपादकीय नीति','हम आधिकारिक सूचनाओं, दस्तावेजों और विश्वसनीय समाचार स्रोतों को प्राथमिकता देते हैं। AI का उपयोग लेखन या अनुवाद में हो सकता है। अपुष्ट दावे, गढ़े हुए उद्धरण, भ्रामक शीर्षक और बिना श्रेय की नकल स्वीकार्य नहीं हैं। स्रोत लेख के अंत में दिया जाता है और पाठक सुधार भेज सकते हैं।')
 for s,(t,d) in pages.items():
  content=f'<div class="wrap"><article class="article"><div class="eyebrow">GLOBEWIRE DAILY</div><h1>{e(t)}</h1><div class="story"><p>{e(d)}</p></div><p>Contact: <a href="mailto:{CONTACT}">{CONTACT}</a></p></article></div>'
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
write(OUT/'index.html','<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url=/en/"><link rel="canonical" href="'+SITE+'/en/"></head><body><a href="/en/">English</a></body></html>')
write(OUT/'favicon.svg','''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0a1429"/><circle cx="32" cy="32" r="23" fill="none" stroke="#5ce0dc" stroke-width="2"/><path d="M9 32h46M32 9c-12 12-12 34 0 46M32 9c12 12 12 34 0 46" fill="none" stroke="#5ce0dc" stroke-width="1.5"/><text x="32" y="40" text-anchor="middle" fill="white" font-family="Arial,sans-serif" font-size="21" font-weight="bold">GW</text></svg>''')
write(OUT/'robots.txt',f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/news-sitemap.xml\n')
urls=[f'/{lang}/{path}' for lang in ('en','hi') for path in ('','author/editorial-desk/','tools/','government-schemes/','sarkari-naukri/','private-vacancy/','movies-entertainment/','world-news/','business/','sports/','automobiles/','health-science/','gaming/','environment/','travel/','education/','lifestyle/','technology/','about/','editorial/','corrections/','privacy/','contact/','affiliate/')]+[f'/{lang}/page/{page}/' for lang in ('en','hi') for page in range(2,max(1,(len(POSTS)+23)//24)+1)]+[f'/{lang}/{cat}/page/{page}/' for lang in ('en','hi') for cat in CATEGORIES for page in range(2,max(1,(sum(1 for p in POSTS if category(p)==cat)+23)//24)+1)]+[f'/{lang}/author/{handle}/' for lang in ('en','hi') for handle in sorted(set(AUTHOR_HANDLES.values()))]+[article_path(p,lang) for p in POSTS for lang in ('en','hi')]
write(OUT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(SITE+u)+'</loc></url>' for u in urls)+'</urlset>')
recent=[]
for p in POSTS:
 try:
  if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(p['date'].replace('Z','+00:00'))).total_seconds()>172800:continue
 except (ValueError,KeyError,TypeError):continue
 for lang in ('en','hi'):
  recent.append('<url><loc>'+xml_escape(f'{SITE}{article_path(p,lang)}')+'</loc><news:news><news:publication><news:name>GlobeWire Daily</news:name><news:language>'+lang+'</news:language></news:publication><news:publication_date>'+e(p['date'])+'</news:publication_date><news:title>'+xml_escape(title(p,lang))+'</news:title></news:news></url>')
write(OUT/'news-sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'+''.join(recent)+'</urlset>')
# Preserve old article URLs as permanent redirects to canonical descriptive URLs.
redirects=[]
for p in POSTS:
 for lang in ('en','hi'):
  redirects.append(f'/{lang}/news/{slug(p)}/ {article_path(p,lang)} 301')
write(OUT/'_redirects','\n'.join(redirects)+'\n')
write(OUT/'ads.txt','google.com, pub-1849673109734274, DIRECT, f08c47fec0942fa0\n')
write(OUT/'_headers','/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/style.css\n  Cache-Control: public, max-age=3600\n/images/*\n  Cache-Control: public, max-age=86400\n')
print('Built',len(POSTS),'posts; AI Tools, bilingual pages, news sitemap and responsive layout')
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
write(OUT/'style.css',CSS)
JS='''addEventListener('scroll',()=>{let d=document.documentElement;let m=d.scrollHeight-d.clientHeight;let b=document.querySelector('.reading');if(b)b.style.width=(m>0?100*d.scrollTop/m:0)+'%';},{passive:true});'''
JS += """document.addEventListener('click',async function(ev){const share=ev.target.closest('.native-share');if(share){const data={title:share.dataset.shareTitle,url:share.dataset.shareUrl};if(navigator.share){try{await navigator.share(data)}catch(err){if(err.name!=='AbortError')location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}else{location.href='https://api.whatsapp.com/send?text='+encodeURIComponent(data.title+' '+data.url)}}const copy=ev.target.closest('.copy-share');if(copy){try{await navigator.clipboard.writeText(copy.dataset.shareUrl);const old=copy.textContent;copy.textContent='✓ Copied';setTimeout(()=>copy.textContent=old,1800)}catch(err){prompt('Copy link:',copy.dataset.shareUrl)}}});"""
CSS += """.category-pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:30px 0 48px;flex-wrap:wrap}.category-pagination a{display:inline-block;background:#fff;border:1px solid #d9e5f0;border-radius:9px;padding:8px 13px;text-decoration:none}"""
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
write(OUT/'style.css',CSS)
write(OUT/'site.js',JS)
def shell(lang,t,desc,url,body,extra=''):
 nav=[('Home','होम',''),('Tech & AI','टेक और AI','technology/'),('Entertainment','मनोरंजन','movies-entertainment/'),('Jobs & Schemes','नौकरी और योजनाएँ','sarkari-naukri/')]
 links=''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in nav)
 more=[('AI Tools','AI टूल्स','tools/'),('Government Schemes','सरकारी योजनाएँ','government-schemes/'),('Private Jobs','प्राइवेट नौकरी','private-vacancy/'),('World','दुनिया','world-news/'),('Business','बिज़नेस','business/'),('Sports','खेल','sports/'),('Gaming','गेमिंग','gaming/'),('Automobiles','ऑटोमोबाइल','automobiles/'),('Health & Science','स्वास्थ्य और विज्ञान','health-science/'),('Environment','पर्यावरण','environment/'),('Travel','यात्रा','travel/'),('Education','शिक्षा','education/'),('Lifestyle','लाइफस्टाइल','lifestyle/'),('About','हमारे बारे में','about/'),('Editorial','संपादकीय नीति','editorial/'),('Contact','संपर्क','contact/')]
 more_html='<details class="nav-more"><summary>'+('More' if lang=='en' else 'और देखें')+'</summary><div class="nav-more-list">'+''.join(f'<a href="/{lang}/{path}">{e(en if lang=="en" else hi)}</a>' for en,hi,path in more)+'</div></details>'
 return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="google-site-verification" content="IjjkuYPqG93dE2SwPvi0HJ258E5WwNGAhIu7LB9qQqE"><meta name="theme-color" content="#0a1429"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1849673109734274" crossorigin="anonymous"></script><title>{e(t)}</title><meta name="description" content="{e(desc[:160])}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{e(url)}"><link rel="alternate" hreflang="en" href="{e(url.replace('/hi/','/en/'))}"><link rel="alternate" hreflang="hi" href="{e(url.replace('/en/','/hi/'))}"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta name="color-scheme" content="light"><link rel="stylesheet" href="/style.css">{extra}</head><body><div class="reading"></div><header class="top"><div class="wrap"><a class="logo" href="/{lang}/">GlobeWire <span>Daily</span></a><nav aria-label="Primary">{links}<a class="langswitch" href="/{'hi' if lang=='en' else 'en'}/">{'हिन्दी' if lang=='en' else 'English'}</a></nav><div class="category-menu">{more_html}</div></div></header><main>{body}</main><footer class="footer"><div class="wrap"><div><strong>GlobeWire Daily</strong><p>Independent bilingual news and explainers, with clear sourcing, corrections and transparent editorial standards.</p><a href="mailto:{CONTACT}">{CONTACT}</a></div><div class="footerlinks">{''.join(f'<a href="/{lang}/{s}/">{s.title()}</a>' for s in ['about','privacy','contact','editorial','corrections','affiliate','tools'])}</div></div></footer><script defer src="/site.js"></script></body></html>'''
def has_featured(p):
 # Existing licensed/credited images always take priority.
 return (R/'content'/'featured'/f'{slug(p)}.jpg').is_file() or (OUT/'images'/f'{slug(p)}.jpg').is_file()

def image_for(p):
 """Keep existing photos; generate clearly labeled original editorial artwork only when missing."""
 s=slug(p);dest=OUT/'images'/f'{s}.jpg';dest.parent.mkdir(parents=True,exist_ok=True)
 existing=R/'content'/'featured'/f'{s}.jpg'
 if existing.is_file():
  shutil.copy2(existing,dest)
  return
 # No third-party photos are scraped or reused without documented rights.
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
def body_html(raw):
 # Render the small, supported Markdown subset without exposing formatting tokens.
 def inline(value):
  safe=e(value)
  safe=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',safe)
  safe=re.sub(r'(^|[^*])\*([^*\n]+)\*(?!\*)',r'\1<em>\2</em>',safe)
  return safe
 parts=[];buf=[];items=[]
 def flush():
  if buf:parts.append('<p>'+inline(' '.join(buf))+'</p>');buf.clear()
 def flush_items():
  if items:parts.append('<ul>'+''.join('<li>'+inline(item)+'</li>' for item in items)+'</ul>');items.clear()
 for line in str(raw).splitlines():
  line=line.strip()
  if not line:flush();flush_items();continue
  if line.startswith('### '):
   flush();flush_items();parts.append('<h3>'+inline(line[4:])+'</h3>')
  elif line.startswith('## '):
   flush();flush_items();parts.append('<h2>'+inline(line[3:])+'</h2>')
  elif re.match(r'^(?:[-*] |\d+\. )',line):
   flush();items.append(re.sub(r'^(?:[-*] |\d+\. )','',line))
  else:flush_items();buf.append(line)
 flush();flush_items();return ''.join(parts)
def image_caption(p,lang):
 s=slug(p)
 metadata=R/'content'/'featured'/f'{s}.json'
 if metadata.is_file():
  try:
   info=json.loads(metadata.read_text(encoding='utf-8'))
   if info.get('kind') in ('licensed_source','publisher_source'):
    credit=str(info.get('attribution') or 'Original publisher')
    license_name=str(info.get('license') or 'Creative Commons')
    return (f'Image: {credit} — {license_name}' if lang=='en' else f'चित्र: {credit} — {license_name}')
  except (OSError,ValueError):pass
 if not metadata.is_file():
  if (R/'content'/'featured'/f'{s}.jpg').is_file():
   return 'Featured image; source information not supplied.' if lang=='en' else 'फीचर्ड चित्र; स्रोत की जानकारी उपलब्ध नहीं है।'
  return 'Original GlobeWire Daily editorial illustration — not an event photograph.' if lang=='en' else 'GlobeWire Daily की मूल सांकेतिक तस्वीर — घटना की वास्तविक फोटो नहीं।'
 return 'Featured image; provenance not specified.' if lang=='en' else 'फीचर्ड चित्र; स्रोत निर्दिष्ट नहीं है।'
def card(p,lang):
 s=slug(p);t=title(p,lang)
 picture=f'<img loading="lazy" src="/images/{s}.jpg" width="1280" height="720" alt="{e(t)}">' if has_featured(p) else ''
 return f'<article class="card"><a href="{article_path(p,lang)}">{picture}<div class="inner"><span class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=="en" else 1])}</span><h2>{e(t)}</h2><div class="date">{e(p.get("date","")[:10])}</div></div></a></article>'

AUTHOR_HANDLES={'technology':'tech-desk','business':'business-desk','world-news':'world-desk','sports':'sports-desk','health-science':'science-desk','government-schemes':'public-services-desk','sarkari-naukri':'careers-desk','private-vacancy':'careers-desk','movies-entertainment':'entertainment-desk','automobiles':'auto-desk','gaming':'gaming-desk','environment':'climate-desk','travel':'travel-desk','education':'education-desk','lifestyle':'lifestyle-desk'}
def author_handle(p):return AUTHOR_HANDLES.get(category(p),'editorial-desk')
def author_name(p):return 'GlobeWire Daily '+author_handle(p).replace('-',' ').title()
def article_keywords(p,lang):
 raw=p.get(lang+'_keywords') or p.get('en_keywords') or []
 if isinstance(raw,str):raw=re.split(r'[,;|]',raw)
 if not isinstance(raw,list):raw=[]
 terms=[str(x).strip() for x in raw if str(x).strip()]
 terms.extend([title(p,lang),CATEGORIES[category(p)][0 if lang=='en' else 1],'GlobeWire Daily'])
 seen=set();result=[]
 for term in terms:
  key=term.casefold()
  if key not in seen and len(term)<=100:
   seen.add(key);result.append(term)
 return result[:12]
def trending_posts(exclude=None,limit=6):
 """Editorial trending proxy: recent articles with topical keyword overlap.
 No fabricated traffic, view counts or real-time search popularity."""
 now=dt.datetime.now(dt.timezone.utc)
 pool=[]
 for p in POSTS:
  if exclude is not None and slug(p)==slug(exclude):continue
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
 return [p for _,p in pool[:limit]]

def trending_section(lang,exclude=None):
 selected=trending_posts(exclude,6)
 if not selected:return ''
 heading='Trending on GlobeWire Daily' if lang=='en' else 'GlobeWire Daily पर चर्चित खबरें'
 note='Selected from recent coverage and related topics; not live search rankings.' if lang=='en' else 'हालिया खबरों और संबंधित विषयों पर आधारित चयन; लाइव सर्च रैंकिंग नहीं।'
 return '<section class="trending-news trending-feature"><h2>'+heading+'</h2><p class="muted">'+note+'</p><div class="trending-list">'+''.join('<a href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="120" height="80" src="/images/{slug(q)}.jpg" alt="">' if has_featured(q) else '<span class="related-placeholder">News</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in selected)+'</div></section>'

def display_date(value):
 try:
  stamp=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
  if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=dt.timezone.utc)
  return stamp.astimezone(dt.timezone(dt.timedelta(hours=5,minutes=30))).strftime('%d %b %Y, %I:%M %p IST')
 except (ValueError,TypeError):return str(value or '')[:10]

def limit_article_words(raw,limit=10000):
 parts=re.findall(r'\\S+',str(raw or ''))
 if len(parts)<=limit:return str(raw or '')
 return ' '.join(parts[:limit]).rstrip(' ,;:')+'…'

for p in POSTS:image_for(p)
for p in POSTS:
 s=slug(p)
 for lang in ('en','hi'):
  t=title(p,lang);raw=limit_article_words(p.get(lang+'_body') or p.get('en_body',''));url=f'{SITE}{article_path(p,lang)}';desc=p.get(lang+'_meta') or re.sub(r'[#\n]+',' ',raw)[:155]
  related=[q for q in POSTS if slug(q)!=s and category(q)==category(p) and has_featured(q)][:4]
  if len(related)<4:related += [q for q in POSTS if slug(q)!=s and q not in related][:4-len(related)]
  related_html=''.join('<a class="related-card" href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="320" height="180" src="/images/{slug(q)}.jpg" alt="{e(title(q,lang))}">' if has_featured(q) else '<span class="related-placeholder">GlobeWire Daily</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in related)
  keyword_html='<section class="article-tags"><strong>'+('Topics' if lang=='en' else 'संबंधित विषय')+'</strong><div class="tag-list">'+''.join('<span class="tag">'+e(term)+'</span>' for term in article_keywords(p,lang)[:7])+'</div></section>'
  trending=[q for q in POSTS if slug(q)!=s and has_featured(q)][:5]
  trending_html='<section class="trending-news"><h2>'+('Latest news' if lang=='en' else 'ताज़ा खबरें')+'</h2><div class="trending-list">'+''.join('<a href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="120" height="80" src="/images/{slug(q)}.jpg" alt="">' if has_featured(q) else '')+'<span>'+e(title(q,lang))+'</span></a>' for q in trending)+'</div></section>'
  schema={'@context':'https://schema.org','@type':'NewsArticle','headline':t,'articleSection':CATEGORIES[category(p)][0],'datePublished':p.get('date'),'dateModified':p.get('date'),'inLanguage':lang,'mainEntityOfPage':url,'image':([f'{SITE}/images/{s}.jpg'] if has_featured(p) else []),'author':{'@type':'Organization','name':author_name(p),'url':f'{SITE}/{lang}/author/{author_handle(p)}/'},'publisher':{'@type':'Organization','name':'GlobeWire Daily','url':SITE},'isBasedOn':p['source']}
  if not has_featured(p):schema.pop('image',None)
  schema['breadcrumb']={'@type':'BreadcrumbList','itemListElement':[
   {'@type':'ListItem','position':1,'name':'Home' if lang=='en' else 'होम','item':f'{SITE}/{lang}/'},
   {'@type':'ListItem','position':2,'name':CATEGORIES[category(p)][0 if lang=='en' else 1],'item':f'{SITE}/{lang}/{category(p)}/'},
   {'@type':'ListItem','position':3,'name':t,'item':url}]}
  schema['keywords']=article_keywords(p,lang)
  schema['description']=desc[:160]
  schema['url']=url
  schema_json=json.dumps(schema,ensure_ascii=False).replace('<',chr(92)+'u003c')
  extra_keywords='<meta name="keywords" content="'+e(', '.join(article_keywords(p,lang)))+'">'
  og_image=f'<meta property="og:image" content="{SITE}/images/{s}.jpg">' if has_featured(p) else ''
  extra=f'<meta property="og:type" content="article"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="GlobeWire Daily"><meta property="og:locale" content="{"en_US" if lang=="en" else "hi_IN"}"><meta property="og:title" content="{e(t)}"><meta property="og:description" content="{e(desc[:160])}"><meta property="article:published_time" content="{e(p.get("date",""))}"><meta property="article:section" content="{e(CATEGORIES[category(p)][0])}">{og_image}<meta name="twitter:card" content="{"summary_large_image" if has_featured(p) else "summary"}"><meta name="twitter:title" content="{e(t)}"><meta name="twitter:description" content="{e(desc[:160])}"><script type="application/ld+json">{schema_json}</script>'
  extra=extra_keywords+extra
  sourcehost=urlparse(p['source']).hostname or 'original source'
  summary=e(p.get(lang+'_summary') or p.get('en_summary') or re.sub(r'[#\n]+',' ',raw)[:270])
  featured_html=(f'<img class="hero" src="/images/{s}.jpg" width="1280" height="720" fetchpriority="high" alt="{e(t)}"><p class="notice">{e(image_caption(p,lang))}</p>' if has_featured(p) else '')
  share_text=('Share this article' if lang=='en' else 'यह खबर शेयर करें')
  copy_text=('Copy link' if lang=='en' else 'लिंक कॉपी करें')
  share_html=(f'<div class="article-share"><strong>{share_text}</strong><div class="share-actions">'
    f'<button type="button" class="native-share" data-share-url="{e(url)}" data-share-title="{e(t)}">↗ {share_text}</button>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://api.whatsapp.com/send?text={quote(t+" "+url)}">WhatsApp</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://www.facebook.com/sharer/sharer.php?u={quote(url,safe="")}">Facebook</a>'
    f'<a target="_blank" rel="noopener noreferrer" href="https://t.me/share/url?url={quote(url,safe="")}&text={quote(t)}">Telegram</a>'
    f'<button type="button" class="copy-share" data-share-url="{e(url)}">{copy_text}</button></div></div>')
  related=[q for q in POSTS if slug(q)!=s and category(q)==category(p) and has_featured(q)][:4]
  if len(related)<4:related.extend([q for q in POSTS if slug(q)!=s and slug(q) not in {slug(x) for x in related} and category(q)!=category(p)][:4-len(related)])
  related_html=''.join('<a class="related-card" href="'+article_path(q,lang)+'">'+(f'<img loading="lazy" width="320" height="180" src="/images/{slug(q)}.jpg" alt="{e(title(q,lang))}">' if has_featured(q) else '<span class="related-placeholder" aria-hidden="true">GlobeWire Daily</span>')+'<span>'+e(title(q,lang))+'</span></a>' for q in related)
  keyword_html='<section class="article-tags"><strong>'+('Topics' if lang=='en' else 'संबंधित विषय')+'</strong><div class="tag-list">'+''.join('<span class="tag">'+e(term)+'</span>' for term in article_keywords(p,lang)[:7])+'</div></section>'
  trending_html=trending_section(lang,p)
  content=f'''<div class="wrap"><article class="article"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/{lang}/">{'Home' if lang=='en' else 'होम'}</a> › <a href="/{lang}/{category(p)}/">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</a> › <span>{e(t)}</span></nav><div class="eyebrow">{e(CATEGORIES[category(p)][0 if lang=='en' else 1])}</div><h1>{e(t)}</h1><p class="date"><time datetime="{e(p.get('date',''))}">{e(display_date(p.get('date','')))}</time> · <a href="/{lang}/author/{author_handle(p)}/">{e(author_name(p))}</a> · Source: {e(sourcehost)}</p>{featured_html}{share_html}<div class="summary"><strong>{'Key takeaways' if lang=='en' else 'मुख्य बातें'}</strong>{summary}</div><div class="story">{body_html(raw)}</div>{keyword_html}<div class="source"><strong>{'Read the original source' if lang=='en' else 'मूल स्रोत पढ़ें'}:</strong> <a href="{e(p['source'])}" rel="noopener noreferrer" target="_blank">{e(p.get('source_title') or sourcehost)}</a><p class="notice">{'AI-assisted reporting; source claims are attributed and have not been independently verified.' if lang=='en' else 'AI की सहायता से तैयार रिपोर्ट; मूल स्रोत के दावों की स्वतंत्र पुष्टि नहीं की गई है।'}</p></div><section class="author-about"><h2>{'About the author' if lang=='en' else 'लेखक के बारे में'}</h2><p><a href="/{lang}/author/{author_handle(p)}/">{e(author_name(p))}</a> — {'AI-assisted news based on attributed published sources.' if lang=='en' else 'प्रकाशित स्रोतों पर आधारित AI-सहायता प्राप्त खबरें।'}</p></section><h2>{'More to read' if lang=='en' else 'और पढ़ें'}</h2><div class="related">{related_html}</div>{trending_html}</article></div>'''
  write(OUT / article_path(p,lang).lstrip('/') / 'index.html',shell(lang,t,desc,url,content,extra))
for lang in ('en','hi'):
 h='Worldwide news, movies and technology explained' if lang=='en' else 'टेक्नोलॉजी की ताज़ा खबरें, आसान भाषा में'
 desc='Worldwide news, movies, entertainment, technology, business, sports and useful explainers.'
 latest=''.join(card(p,lang) for p in POSTS[:24]) or '<p>No articles yet. New verified-source explainers are being prepared.</p>'
 focus_posts=[p for p in POSTS if category(p) in ('technology','automobiles')][:6]
 focus_html='<section class="focus-news"><div class="sectiontitle"><h2>'+('Technology & Automobiles' if lang=='en' else 'टेक्नोलॉजी और ऑटोमोबाइल')+'</h2><a href="/'+lang+'/technology/">'+('More technology news' if lang=='en' else 'और टेक खबरें')+' →</a></div><div class="cards">'+''.join(card(p,lang) for p in focus_posts)+'</div></section>' if focus_posts else ''
 sidebar='<aside class="side"><div class="panel"><h2>Explore AI tools</h2>'+''.join(f'<a href="/{lang}/tools/">{e(x[0])} · {e(x[3])}</a>' for x in TOOLS[:6])+'</div><div class="panel"><h2>Our approach</h2><p>Read original sources. Check dates. Explain what matters. Corrections welcome.</p></div></aside>'
 featured=''.join(f'<article class="tool"><span class="pill">{e(cat)}</span><h3>{e(n)}</h3><p>{e(d)}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{ "Official website" if lang=="en" else "आधिकारिक वेबसाइट"} ↗</a></article>' for n,d,u,cat in TOOLS[:8])
 tools_home=f'<section class="featured-tools" aria-labelledby="featured-tools-heading"><div class="sectiontitle"><h2 id="featured-tools-heading">{"Explore AI Tools" if lang=="en" else "AI टूल्स खोजें"}</h2><a href="/{lang}/tools/">{"View all AI tools" if lang=="en" else "सभी AI टूल्स देखें"} →</a></div><p class="muted">{"Explore trusted official links for writing, research, coding and design." if lang=="en" else "लेखन, रिसर्च, कोडिंग और डिजाइन के लिए आधिकारिक AI टूल्स।"}</p><div class="tools featured-grid">{featured}</div></section>'
 home=f'<div class="wrap"><section class="lead"><div class="eyebrow">WORLDWIDE NEWS & EXPLAINERS</div><h1>{h}</h1><p class="muted">{desc}</p></section><div class="sectiontitle"><h2>{"Latest stories" if lang=="en" else "नई खबरें"}</h2><a href="/{lang}/tools/">AI Tools →</a></div><div class="layout"><div class="cards">{latest}</div>{sidebar}</div>{focus_html}{trending_section(lang)}{tools_home}</div>'
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
   write(OUT / cat_path.lstrip('/') / 'index.html',shell(lang,heading+(f' — Page {cat_page}' if cat_page>1 else '')+' | GlobeWire Daily',intro,f'{SITE}{cat_path}',catbody))

 toolcards=''.join(f'<article class="tool"><span class="pill">{e(cat)}</span><h2>{e(n)}</h2><p>{e(d)}</p><a href="{e(u)}" target="_blank" rel="noopener noreferrer">Official website ↗</a></article>' for n,d,u,cat in TOOLS)
 tools=f'<div class="wrap"><section class="lead"><div class="eyebrow">AI TOOLS DIRECTORY</div><h1>{"Explore useful AI tools" if lang=="en" else "काम के AI टूल्स खोजें"}</h1><p class="muted">Official links, brief descriptions and categories. Availability and pricing can change; verify on provider websites.</p></section><div class="tools">{toolcards}</div></div>'
 write(OUT/lang/'tools/index.html',shell(lang,'AI Tools Directory | GlobeWire Daily','Explore popular AI assistants, research, coding and design tools.',f'{SITE}/{lang}/tools/',tools))
 pages={
 'about':('About GlobeWire Daily','GlobeWire Daily is an independent bilingual technology publication focused on useful explainers and news. We use AI-assisted drafting and translation, link to source materials, and welcome corrections. We do not claim to independently verify every publisher statement.'),
 'editorial':('Editorial Policy','Our articles are based on attributed source material. We prioritize official announcements, documentation and credible reporting. AI may assist drafting and translation. We require useful source-supported context, practical implications, clear distinctions between confirmed facts and uncertainty, and transparent attribution. We prohibit fabricated quotes, unsupported claims, misleading headlines, and unattributed copying. When a claim cannot be confirmed, we label uncertainty or do not publish it. Readers can request corrections.'),
 'corrections':('Corrections Policy','Report factual errors, misleading headlines, inaccurate translations, or rights concerns to contact@globewiredaily.org with the article URL and supporting evidence. Substantive corrections should be reflected in the article with an updated date.'),
 'privacy':('Privacy Policy','GlobeWire Daily publishes static news and informational pages. Hosting providers may process IP addresses, device information and technical request logs for security and delivery. We use Google AdSense advertising technology, which may use cookies or similar identifiers to serve and measure ads, subject to applicable consent requirements and Google policies. You can learn how Google uses data from partner sites at https://policies.google.com/technologies/partner-sites and manage Google ad preferences at https://myadcenter.google.com/. Third-party websites linked from our articles have separate privacy practices. We do not operate reader accounts or a newsletter. For privacy or data requests, contact contact@globewiredaily.org.'),
 'contact':('Contact GlobeWire Daily','For news tips, corrections, image rights requests, privacy matters or editorial feedback, email contact@globewiredaily.org. Do not include sensitive personal information.'),
 'affiliate':('Affiliate Disclosure','Our AI Tools directory currently contains informational links. If affiliate partnerships or paid placements are introduced, they will be clearly identified. We do not claim that editorial recommendations are paid placements.')}
 for s,(t,d) in pages.items():
  content=f'<div class="wrap"><article class="article"><div class="eyebrow">GLOBEWIRE DAILY</div><h1>{e(t)}</h1><div class="story"><p>{e(d)}</p></div><p>Contact: <a href="mailto:{CONTACT}">{CONTACT}</a></p></article></div>'
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
write(OUT/'index.html','<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url=/en/"><link rel="canonical" href="'+SITE+'/en/"></head><body><a href="/en/">English</a></body></html>')
write(OUT/'favicon.svg','''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0a1429"/><circle cx="32" cy="32" r="23" fill="none" stroke="#5ce0dc" stroke-width="2"/><path d="M9 32h46M32 9c-12 12-12 34 0 46M32 9c12 12 12 34 0 46" fill="none" stroke="#5ce0dc" stroke-width="1.5"/><text x="32" y="40" text-anchor="middle" fill="white" font-family="Arial,sans-serif" font-size="21" font-weight="bold">GW</text></svg>''')
write(OUT/'robots.txt',f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/news-sitemap.xml\n')
urls=[f'/{lang}/{path}' for lang in ('en','hi') for path in ('','author/editorial-desk/','tools/','government-schemes/','sarkari-naukri/','private-vacancy/','movies-entertainment/','world-news/','business/','sports/','automobiles/','health-science/','gaming/','environment/','travel/','education/','lifestyle/','technology/','about/','editorial/','corrections/','privacy/','contact/','affiliate/')]+[f'/{lang}/page/{page}/' for lang in ('en','hi') for page in range(2,max(1,(len(POSTS)+23)//24)+1)]+[f'/{lang}/{cat}/page/{page}/' for lang in ('en','hi') for cat in CATEGORIES for page in range(2,max(1,(sum(1 for p in POSTS if category(p)==cat)+23)//24)+1)]+[f'/{lang}/author/{handle}/' for lang in ('en','hi') for handle in sorted(set(AUTHOR_HANDLES.values()))]+[article_path(p,lang) for p in POSTS for lang in ('en','hi')]
write(OUT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(SITE+u)+'</loc></url>' for u in urls)+'</urlset>')
recent=[]
for p in POSTS:
 try:
  if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(p['date'].replace('Z','+00:00'))).total_seconds()>172800:continue
 except (ValueError,KeyError,TypeError):continue
 for lang in ('en','hi'):
  recent.append('<url><loc>'+xml_escape(f'{SITE}{article_path(p,lang)}')+'</loc><news:news><news:publication><news:name>GlobeWire Daily</news:name><news:language>'+lang+'</news:language></news:publication><news:publication_date>'+e(p['date'])+'</news:publication_date><news:title>'+xml_escape(title(p,lang))+'</news:title></news:news></url>')
write(OUT/'news-sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'+''.join(recent)+'</urlset>')
# Preserve old article URLs as permanent redirects to canonical descriptive URLs.
redirects=[]
for p in POSTS:
 for lang in ('en','hi'):
  redirects.append(f'/{lang}/news/{slug(p)}/ {article_path(p,lang)} 301')
write(OUT/'_redirects','\n'.join(redirects)+'\n')
write(OUT/'ads.txt','google.com, pub-1849673109734274, DIRECT, f08c47fec0942fa0\n')
write(OUT/'_headers','/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n/style.css\n  Cache-Control: public, max-age=3600\n/images/*\n  Cache-Control: public, max-age=86400\n')
print('Built',len(POSTS),'posts; AI Tools, bilingual pages, news sitemap and responsive layout')
