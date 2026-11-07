"""Bounded worldwide locality discovery. A place name is a search lead, not verified reporting."""
import datetime as dt
from functools import lru_cache
import gzip
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlencode,urlparse

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/world_localities.json.gz'
BLOCKED_PUBLISHERS=('google.com','googleusercontent.com','bing.com','youtube.com',
                    'facebook.com','instagram.com','twitter.com','x.com','reddit.com')
LOCAL_TERMS={
 'en':'local OR district OR village OR town OR county',
 'hi':'गांव OR गाँव OR कस्बा OR जिला OR शहर',
 'fr':'local OR village OR commune OR département',
 'es':'local OR pueblo OR municipio OR provincia',
 'pt':'local OR vila OR município OR distrito',
 'de':'lokal OR Dorf OR Landkreis OR Gemeinde',
 'ar':'محلي OR قرية OR مدينة OR محافظة',
 'ru':'местные OR деревня OR район OR город',
 'zh':'本地 OR 村 OR 县 OR 镇',
 'ja':'地域 OR 村 OR 町 OR 市',
 'ko':'지역 OR 마을 OR 군 OR 시',
 'id':'daerah OR desa OR kabupaten OR kecamatan',
 'tr':'yerel OR köy OR ilçe OR kasaba',
 'vi':'địa phương OR huyện OR xã OR làng',
 'bn':'গ্রাম OR জেলা OR শহর',
 'ur':'گاؤں OR ضلع OR شہر',
 'fa':'محلی OR روستا OR شهرستان OR شهر',
 'th':'ท้องถิ่น OR หมู่บ้าน OR อำเภอ',
 'sw':'mtaa OR kijiji OR wilaya',
}
@lru_cache(maxsize=1)
def world_registry():
 try:
  with gzip.open(DATA,'rt',encoding='utf-8') as handle:data=json.load(handle)
  return data.get('countries',{})
 except (OSError,ValueError,TypeError):return {}

def registry_stats():
 countries=world_registry()
 return {'country_territory_count':len(countries),
         'place_name_count':sum(len(row.get('places',[])) for row in countries.values()),
         'countries_with_places':sum(bool(row.get('places')) for row in countries.values())}

def world_city_feeds(publishers,now=None,limit=32,period=7200):
 now=now if now is not None else dt.datetime.now(dt.timezone.utc).timestamp()
 countries=world_registry();codes=sorted(countries)
 if not codes:return []
 count=min(max(0,int(limit)),len(codes));cycle=int(now//max(1,period))
 preferred={}
 for domain,country,language,edition in publishers:
  preferred.setdefault(country,[]).append((domain,language,edition))
 rows=[]
 for index in range(count):
  position=cycle*count+index;code=codes[position%len(codes)];visit=position//len(codes)
  record=countries[code];name=record['name'];native=record.get('local_name',name)
  language=record.get('languages','en').split(',')[0].split('-')[0]
  country_terms='"'+name.replace('"','')+'"'
  if native!=name:country_terms='('+country_terms+' OR "'+native.replace('"','')+'")'
  places=record.get('places',[])
  local=LOCAL_TERMS.get(language,LOCAL_TERMS['en'])
  # Country searches also catch villages below the gazetteer's population floor.
  # On alternate visits narrow to another place; never infer incident location.
  if places and visit%2:
   place=places[(visit//2)%len(places)].replace('"','')
   query=country_terms+' "'+place+'" when:2d'
  else:query=country_terms+' ('+local+') when:2d'
  options=preferred.get(code,[])
  # Known publishers alternate with open discovery of original local publishers.
  domain=''
  if options and not visit%2:
   domain,hl,edition=options[(visit//2)%len(options)]
   query='site:'+domain+' '+query
   gl=code
  else:hl,gl,edition='en-US','US','en'
  params=urlencode({'q':query,'hl':hl,'gl':gl,'ceid':gl+':'+edition})
  rows.append(('https://news.google.com/rss/search?'+params,
               'india-news' if code=='IN' else 'world-news',domain))
 return rows

def public_publisher_host(url):
 try:
  parsed=urlparse(str(url))
  host=(parsed.hostname or '').lower().rstrip('.').removeprefix('www.')
  if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443):return ''
  host=host.encode('idna').decode('ascii')
  if '.' not in host or any(host==d or host.endswith('.'+d) for d in BLOCKED_PUBLISHERS):return ''
  if host.endswith(('.local','.localhost','.internal','.invalid','.test','.example')):return ''
  try:ipaddress.ip_address(host);return ''
  except ValueError:pass
  if any(not part or len(part)>63 or part.startswith('-') or part.endswith('-') or not all(c.isalnum() or c=='-' for c in part) for part in host.split('.')):return ''
  return host
 except (ValueError,UnicodeError):return ''

def matched_publisher(source_url,article_url):
 source=public_publisher_host(source_url);article=public_publisher_host(article_url)
 if source and article and (article==source or article.endswith('.'+source)):return source
 if source in ('bbc.com','bbc.co.uk') and article in ('bbc.com','bbc.co.uk'):return source
 return ''

def load_local_publishers(root):
 try:
  raw=json.loads((Path(root)/'content/pending/_world_local_publishers.json').read_text(encoding='utf-8'))
  values=raw.get('domains',[]) if isinstance(raw,dict) else []
 except (OSError,ValueError):return set()
 if not isinstance(values,list):return set()
 return {host for value in values[:5000] if isinstance(value,str)
         for host in [public_publisher_host('https://'+value)] if host==value}

def save_local_publishers(root,domains):
 valid=sorted({host for value in domains if isinstance(value,str)
               for host in [public_publisher_host('https://'+value)] if host==value})[:5000]
 if not valid:return
 path=Path(root)/'content/pending/_world_local_publishers.json'
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps({'source':'Original article hosts matched to Google News RSS publisher metadata',
                            'domains':valid},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':print(json.dumps(registry_stats(),sort_keys=True))
