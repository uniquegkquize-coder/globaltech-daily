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

# City names narrow worldwide publisher discovery; this is a rotating seed list,
# not a complete list of every municipality or a guarantee of news coverage.
WORLD_CITIES={
 'US':('New York','Los Angeles','Chicago','Phoenix','Amherst','Fresno'),
 'GB':('London','Manchester','Leeds','Sunderland','Bradford','Cornwall'),
 'CA':('Toronto','Vancouver','Winnipeg','Halifax'),
 'AU':('Sydney','Melbourne','Perth','Ballarat'),
 'NZ':('Auckland','Wellington','Christchurch','Hamilton'),
 'ZA':('Johannesburg','Cape Town','Durban','Mthatha'),
 'KE':('Nairobi','Mombasa','Kisumu','Nakuru'),
 'NG':('Lagos','Abuja','Kano','Ibadan'),
 'GH':('Accra','Kumasi','Tamale','Cape Coast'),
 'PK':('Karachi','Lahore','Peshawar','Multan'),
 'BD':('Dhaka','Chattogram','Sylhet','Khulna'),
 'PH':('Manila','Cebu','Davao','Iloilo'),
 'MY':('Kuala Lumpur','Johor Bahru','Ipoh','Kuching'),
 'ID':('Jakarta','Surabaya','Bandung','Yogyakarta'),
 'TH':('Bangkok','Chiang Mai','Phuket','Khon Kaen'),
 'FR':('Paris','Marseille','Lyon','Lille'),
 'DE':('Berlin','Hamburg','Munich','Dresden'),
 'ES':('Madrid','Barcelona','Valencia','Seville'),
 'BR':('São Paulo','Rio de Janeiro','Recife','Manaus'),
 'JP':('Tokyo','Osaka','Fukuoka','Sendai'),
}
def world_city_feeds(publishers,now=None,limit=12):
 now=now if now is not None else dt.datetime.now(dt.timezone.utc).timestamp()
 pairs=[(domain,country,language,edition,city)
        for domain,country,language,edition in publishers
        for city in WORLD_CITIES.get(country,())]
 if not pairs:return []
 count=min(max(0,limit),len(pairs));start=(int(now//14400)*max(1,count))%len(pairs)
 rows=[]
 for i in range(count):
  domain,country,language,edition,city=pairs[(start+i)%len(pairs)]
  params=urlencode({'q':'site:'+domain+' "'+city+'" when:1d',
                    'hl':language,'gl':country,'ceid':country+':'+edition})
  rows.append(('https://news.google.com/rss/search?'+params,'world-news',domain))
 return rows
