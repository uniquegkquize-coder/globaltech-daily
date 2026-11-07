"""District feeds come from the publisher's public RSS directory, never guessed endpoints."""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlencode, urlparse
from bs4 import BeautifulSoup
import requests

CATALOG='https://www.livehindustan.com/rss'
STATES={'uttar-pradesh','bihar','jharkhand','uttarakhand','rajasthan','madhya-pradesh',
        'haryana','punjab','chhattisgarh','maharashtra','himachal-pradesh','delhi'}
PUBLISHERS=('bhaskar.com','livehindustan.com','amarujala.com','jagran.com','hindi.news18.com','patrika.com')
PINNED=('(Gorakhpur OR गोरखपुर)','(Sahjanwa OR सहजनवा) (Gorakhpur OR गोरखपुर)','(Gola Bazar OR गोलाबाजार OR गोला बाजार) (Gorakhpur OR गोरखपुर)')
SEEDS=['https://api.livehindustan.com/feeds/rss/uttar-pradesh/gorakhpur/rssfeed.xml']
PUBLIC_PAGES=[
 ('https://www.bhaskar.com/local/uttar-pradesh/gorakhpur/','india-news','bhaskar.com'),
 ('https://www.bhaskar.com/local/uttar-pradesh/gorakhpur/sahjanwa/','india-news','bhaskar.com'),
 ('https://www.livehindustan.com/uttar-pradesh/gorakhpur/news','india-news','livehindustan.com'),
 ('https://www.amarujala.com/gorakhpur','india-news','amarujala.com'),
]
def catalog_feeds(markup):
 result=set()
 for a in BeautifulSoup(markup,'html.parser').select('a[href]'):
  url=a.get('href','')
  parsed=urlparse(url)
  parts=parsed.path.strip('/').split('/')
  if parsed.scheme=='https' and parsed.hostname=='api.livehindustan.com' and len(parts)==5 and parts[:2]==['feeds','rss'] and parts[2] in STATES and parts[-1]=='rssfeed.xml':
   result.add(url)
 return sorted(result)

def district_feeds(root,now=None,limit=24,refresh=True):
 now=now or dt.datetime.now(dt.timezone.utc).timestamp()
 path=Path(root)/'content/pending/_district_sources.json'
 try:cache=json.loads(path.read_text(encoding='utf-8'))
 except (OSError,ValueError):cache={}
 if not isinstance(cache,dict):cache={}
 urls=sorted(set(SEEDS+catalog_feeds(''.join('<a href="'+u+'"></a>' for u in cache.get('feeds',[]) if isinstance(u,str)))))
 try:checked_at=float(cache.get('checked_at',0))
 except (ValueError,TypeError):checked_at=0
 if refresh and now-checked_at>86400:
  try:
   response=requests.get(CATALOG,timeout=(3,6),headers={'User-Agent':'Mozilla/5.0 (compatible; GlobeWireDaily/1.0)'})
   response.raise_for_status()
   discovered=catalog_feeds(response.text)
   if discovered:urls=sorted(set(urls+discovered))
  except requests.RequestException:pass
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps({'checked_at':now,'catalog':CATALOG,'feeds':urls},indent=2)+'\n',encoding='utf-8')
 print('DISTRICT_SOURCE_REGISTRY',len(urls),'district feeds',flush=True)
 pinned=[u for u in urls if '/gorakhpur/' in u]
 rest=[u for u in urls if u not in pinned]
 count=max(0,limit-len(pinned));start=(int(now//7200)*max(1,count))%max(1,len(rest))
 selected=pinned+[rest[(start+i)%len(rest)] for i in range(min(count,len(rest)))]
 return [(u,'india-news','livehindustan.com') for u in selected]

def district_search_feeds(regions,now=None,limit=16):
 now=now or dt.datetime.now(dt.timezone.utc).timestamp()
 cycle=int(now//7200)
 places=list(dict.fromkeys(city+' '+state for state,cities in regions.items() for city in cities))
 queries=[(domain,PINNED[0]) for domain in PUBLISHERS[:4]]
 queries += [(PUBLISHERS[(cycle+i)%len(PUBLISHERS)],place) for i,place in enumerate(PINNED[1:])]
 pairs=[(domain,place) for place in places for domain in PUBLISHERS]
 count=max(0,limit-len(queries));start=(cycle*max(1,count))%max(1,len(pairs))
 queries += [pairs[(start+i)%len(pairs)] for i in range(min(count,len(pairs)))]
 rows=[]
 for domain,place in queries:
  prefix='site:bhaskar.com/local/' if domain=='bhaskar.com' else 'site:'+domain
  params=urlencode({'q':prefix+' '+place+' समाचार when:2d','hl':'hi','gl':'IN','ceid':'IN:hi'})
  rows.append(('https://news.google.com/rss/search?'+params,'india-news',domain))
 return rows

# Full GeoNames-backed worldwide registry, shared by publisher and trending scans.
from world_local_sources import world_city_feeds
