"""Check imported source URLs. A prospect or draft is never a backlink."""
from urllib.parse import urljoin, urlsplit
from .common import *

def inspect_html(source,expected,raw):
 b=soup(raw); matches=[]; other=[]
 for a in b.find_all('a',href=True):
  absolute=urljoin(source,a['href']); actual=canonical(absolute)
  if domain(actual)!=domain(SITE): continue
  rel=[str(x).lower() for x in a.get('rel',[])]
  parent=a.find_parent(['article','main','footer','header','nav','aside'])
  record={'target_url':absolute,'anchor':a.get_text(' ',strip=True),'rel':[r for r in rel if r in ('nofollow','sponsored','ugc')] or ['follow'],'placement':parent.name if parent else 'body'}
  if actual==canonical(expected): matches.append(record)
  else: other.append(record)
 return matches,other

def verify_one(fetcher,item,previous=None):
 previous=previous or {}; row={**previous,**item}; row['id']=uid(item['source_url']+'|'+item['target_url'])
 row['last_checked']=day(); row['previous_status']=previous.get('status','unverified')
 if domain(item['source_url'])==domain(SITE):
  row.update(status='rejected_internal',error='Internal link is not a backlink'); return row
 if domain(item['target_url'])!=domain(SITE):
  row.update(status='rejected_target',error='Target must belong to GlobeWireDaily'); return row
 try:
  final,raw=fetcher.get(item['source_url'])
  if domain(final)==domain(SITE): raise ValueError('source redirects to own site')
  matches,others=inspect_html(final,item['target_url'],raw)
  row.update({'resolved_source':final,'matches':matches,'other_site_links':others,'last_verified':day(),'status':'live' if matches else ('changed' if others else ('removed' if previous.get('first_seen') else 'not_found'))})
  row.pop('error',None)
  if matches: row.setdefault('first_seen',day())
 except Exception as exc: row.update({'status':'inaccessible','error':str(exc)})
 row.setdefault('placement_type','unknown')
 return row

def run(fetcher):
 previous={r['id']:r for r in read('backlinks.json',[])}
 items={uid(r['source_url']+'|'+r['target_url']):r for r in read('submissions.json',[])}
 # Keep monitoring previous verified sources even if an import is later removed.
 for key,r in previous.items(): items.setdefault(key,{k:r[k] for k in ('source_url','target_url','placement_type') if k in r})
 for key,item in items.items():
  if time.monotonic()>=fetcher.end: break
  previous[key]=verify_one(fetcher,item,previous.get(key))
 save('backlinks.json',sorted(previous.values(),key=lambda r:r['id'])); return list(previous.values())
if __name__=='__main__': run(Fetcher(240))
