"""Inventory live sitemaps, falling back explicitly to generated local output."""
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from .common import *

def sitemap_urls(fetcher,url,seen=None):
 seen=seen or set()
 if url in seen or len(seen)>=20 or domain(url)!=domain(SITE): return []
 seen.add(url); _,body=fetcher.get(url); tree=ET.fromstring(body)
 locs=[n.text for n in tree.iter() if n.tag.endswith('}loc') or n.tag=='loc']
 if tree.tag.endswith('sitemapindex'):
  result=[]
  for child in locs: result+=sitemap_urls(fetcher,child,seen)
  return result
 return [u for u in locs if domain(u)==domain(SITE)]

def inventory(fetcher):
 urls=set(); status={}
 for filename in ('sitemap.xml','news-sitemap.xml'):
  try:
   found=sitemap_urls(fetcher,SITE+'/'+filename); status[filename]={'source':'live','urls':len(found)}
  except Exception as exc:
   local=ROOT/'dist'/filename
   found=[n.text for n in ET.fromstring(local.read_text()).iter() if n.tag.endswith('}loc')] if local.exists() else []
   status[filename]={'source':'local generated fallback','error':str(exc),'urls':len(found)}
  urls.update(found)
 targets=[]
 for url in sorted(urls):
  p=urlsplit(url).path
  local=ROOT/'dist'/p.lstrip('/')/'index.html'
  if not local.exists(): continue
  b=soup(local.read_text()); h=b.find('h1'); title=h.get_text(' ',strip=True) if h else ''
  body=b.find('article') or b.find('main') or b
  category=classify(p+' '+title)
  if not title or not category: continue
  if '/news/' not in p and not any(t in p for t in ('/resources/','/colleges/','/cars/','/bikes/','/phones/','/tools/','/notices/','/exams/')): continue
  text=body.get_text(' ',strip=True)
  targets.append({'url':url,'title':title,'category':category,'language':'hi' if p.startswith('/hi/') else 'en','words':len(text.split()),'excerpt':text[:500],'evergreen':'/news/' not in p})
 save('targets.json',targets)
 save('audit.json',{'checked_at':day(),'sitemaps':status,'important_urls':len(urls),'usable_targets':len(targets),'backlink_inventory':'unavailable: Search Analytics API does not expose Links report; import source URLs in submissions.json','resource_gaps':['Defence timeline requires independently checked dated events; news dates alone are not event dates.'],'prospect_goal':300})
 return targets
if __name__=='__main__': inventory(Fetcher(90))
