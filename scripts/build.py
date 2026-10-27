from pathlib import Path
import os,html,json,shutil
r=Path(__file__).resolve().parents[1];out=r/'dist';shutil.rmtree(out,ignore_errors=True);out.mkdir()
posts=[]
for p in (r/'content/posts').glob('*.json'):
 try:
  x=json.loads(p.read_text());posts.append(x)
 except:pass
for lang in ('en','hi'):
 links=[]
 for p in posts:
  name=html.escape(p.get(lang+'_title','News'))
  slug=p['id'];target=out/lang/'news'/slug;target.mkdir(parents=True,exist_ok=True)
  body=html.escape(p.get(lang+'_body','')).replace('\n','<br>')
  (target/'index.html').write_text(f'<meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/style.css"><h1>{name}</h1><p>AI-assisted; source-backed, not independently fact-checked</p><article>{body}</article><p>Source: <a href="{html.escape(p["source"])}">Original announcement</a></p>')
  links.append(f'<a href="/{lang}/news/{slug}/"><h2>{name}</h2></a>')
 target=out/lang;target.mkdir(exist_ok=True)
 (target/'index.html').write_text('<meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/style.css"><h1>GlobalTech Daily</h1><nav><a href="/en/">English</a> · <a href="/hi/">हिन्दी</a> · <a href="/en/tools/">Tools</a></nav>'+''.join(links))
(out/'index.html').write_text('<meta http-equiv="refresh" content="0;url=/en/">')
(out/'style.css').write_text('body{font:18px/1.7 system-ui;background:#101b30;color:#eee;max-width:900px;margin:30px auto;padding:20px}a{color:#8ac5ff}article{background:#1e304d;padding:25px;border-radius:12px}')
(out/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+os.getenv('SITE_URL','https://example.pages.dev')+'/sitemap.xml')
site=os.getenv('SITE_URL','https://example.pages.dev');urls=['/en/','/hi/']+[f'/{l}/news/{p["id"]}/' for p in posts for l in ('en','hi')]
(out/'sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{site}{u}</loc></url>' for u in urls)+'</urlset>')
for slug,txt in [('about','AI-assisted news based on original vendor announcements; corrections via publisher contact.'),('privacy','Privacy policy must be customized before advertising.'),('affiliate','Affiliate links may earn commissions and will be disclosed.'),('tools','Tools and affiliate recommendations coming soon.')]:
 d=out/'en'/slug;d.mkdir(exist_ok=True);(d/'index.html').write_text('<h1>'+slug.title()+'</h1><p>'+txt+'</p>')
print('Built',len(posts),'posts')
