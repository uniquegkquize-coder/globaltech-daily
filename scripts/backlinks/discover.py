"""Discover from repository sources, supplied search exports and public editorial links.
No automated search-engine scraping, fabricated domains or guessed contacts.
"""
import argparse
import re
from urllib.parse import urljoin
from .common import *

DENY={'facebook.com','twitter.com','x.com','youtube.com','instagram.com','linkedin.com','google.com','wikipedia.org','wikidata.org','github.com','amazon.com','t.me','whatsapp.com','bit.ly','pinterest.com'}
def usable(url):
 host=domain(url)
 return bool(host and host!=domain(SITE) and not any(host==d or host.endswith('.'+d) for d in DENY))

def seeds():
 found={}
 # Stored source URLs are leads, never endorsements or confirmed opportunities.
 for p in [ROOT/'scripts/news_config.py',ROOT/'scripts/focused_sources.py']:
  for url in re.findall(r'https?://[^\s\'"<>\)]+',p.read_text()):
   if usable(url): found.setdefault(domain(url),{'url':url,'discovered_from':p.relative_to(ROOT).as_posix()})
 for p in sorted((ROOT/'content/posts').glob('*.json')):
  try: row=json.loads(p.read_text()); url=row.get('source','')
  except (ValueError,OSError): continue
  if usable(url): found.setdefault(domain(url),{'url':url,'discovered_from':p.relative_to(ROOT).as_posix()})
 # Existing sourced college records supply a growing academic-resource candidate pool.
 record_path=ROOT/'content/directory-records.json'
 if record_path.exists():
  for record in json.loads(record_path.read_text()).get('colleges',[]):
   url=record.get('official_url','')
   if usable(url): found.setdefault(domain(url),{'url':url,'category':'education','discovered_from':record.get('source_url') or 'content/directory-records.json'})
 for item in read('search-import.json',[]):
  if usable(item.get('url','')): found[domain(item['url'])]=item
 return found

def research(fetcher,item):
 url,raw=fetcher.get(item['url']); b=soup(raw); content=b.find('article') or b.find('main') or b; text=content.get_text(' ',strip=True)
 title=b.title.get_text(' ',strip=True) if b.title else ''
 category=item.get('category') or classify(title+' '+text[:12000])
 if len(text.split())<100 or not title or not category: raise ValueError('insufficient topical editorial evidence')
 links=[(urljoin(url,a.get('href','')),a.get_text(' ',strip=True)) for a in b.find_all('a',href=True)]
 contact=next((u for u,label in links if domain(u)==domain(url) and re.search(r'contact|editorial|pitch|संपर्क',label,re.I)), '')
 about=next((u for u,label in links if domain(u)==domain(url) and re.search(r'about|editorial policy|corrections',label,re.I)), '')
 evidence={'topical':True,'article_markup':bool(re.search(r'NewsArticle|BlogPosting|Article',raw) or b.find('article')),'byline':bool(b.find(attrs={'rel':'author'}) or b.find(attrs={'name':'author'})),'policy_page':about,'contact_page':contact,'words':len(text.split())}
 emails=[]; contact_title=''; contact_excerpt=''
 if contact:
  try:
   final,cr=fetcher.get(contact); cb=soup(cr); ct=cb.get_text(' ',strip=True); contact=final
   contact_title=cb.title.get_text(' ',strip=True) if cb.title else ''
   contact_excerpt=ct[:400]
   # Only emails actually printed on the discovered contact page; review purpose manually.
   emails=sorted(set(re.findall(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',ct)))[:5]
   evidence['editorial_invitation']=bool(re.search(r'news tips|story ideas|editorial submissions|pitch|editorial queries',ct,re.I))
  except Exception as exc: evidence['contact_error']=str(exc)
 risk=bool(re.search(r'buy (?:quality |seo )?backlinks|guaranteed dofollow|link exchange|reciprocal link|guest post.{0,30}\$|casino guest post',text,re.I))
 evidence['spam_risk']=risk
 return {'id':uid(domain(url)),'domain':domain(url),'name':title[:160],'url':url,'category':category,'language':'hi' if len(re.findall(r'[\u0900-\u097f]',text[:5000]))>100 else 'en','contact_page':contact,'public_emails':emails,'email_purpose':'unreviewed; do not send','contact_title':contact_title,'contact_excerpt':contact_excerpt,'topic_excerpt':text[:400],'evidence':evidence,'discovered_from':item['discovered_from'],'last_checked':day(),'outreach_status':'not_prepared','review_status':'pending','estimated_audience':None,'quality_score_type':'observable heuristic, not authority or traffic measurement'},links

def run(fetcher,limit=30):
 state=read('prospects.json',[]); existing={r['domain']:r for r in state}; queue=read('candidates.json',{})
 for host,item in seeds().items(): queue.setdefault(host,item)
 # Rotate oldest candidates, so daily runs progress rather than repeat the first batch.
 ordered=sorted(queue.items(),key=lambda kv:(kv[1].get('last_attempt',''),kv[0]))
 attempts=0
 for host,item in ordered:
  if attempts>=limit or time.monotonic()>=fetcher.end: break
  if item.get('last_attempt')==day(): continue
  attempts+=1; item['last_attempt']=day()
  try:
   row,links=research(fetcher,item)
   if len(queue)>5000: links=[]
   previous=existing.get(row['domain'],{})
   for key in ('outreach_status','review_status','draft_id','first_seen'):
    if key in previous: row[key]=previous[key]
   row.setdefault('first_seen',day()); existing[row['domain']]=row; item.pop('error',None)
   # Follow only explicitly editorial/resource labelled external links, never social links.
   for u,label in links:
    if usable(u) and re.search(r'resource|publisher|partner|editorial|newsroom',label,re.I): queue.setdefault(domain(u),{'url':u,'discovered_from':row['url'],'category':row['category']})
   LOG.info('researched %s (%s)',host,row['category'])
  except Exception as exc: item['error']=str(exc); LOG.warning('%s: %s',host,exc)
 save('candidates.json',queue); save('prospects.json',sorted(existing.values(),key=lambda r:r['domain']))
 save('discovery-status.json',{'checked_at':day(),'attempts':attempts,'candidates':len(queue),'researched':len(existing),'goal':300,'goal_met':len(existing)>=300})
 return list(existing.values())
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--limit',type=int,default=30); args=p.parse_args(); run(Fetcher(),args.limit)
