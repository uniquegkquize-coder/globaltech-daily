"""Conservative structured-data enrichment from publisher/official pages.
Only import explicitly labeled facts; never infer missing prices or fees.
"""
import json
import datetime as dt
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import feedparser
import requests
from bs4 import BeautifulSoup

DOMAINS={
 'colleges':('collegedekho.com','shiksha.com','careers360.com','topuniversities.com','timeshighereducation.com','studyportals.com','universityadmissions.se','ucas.com','niche.com','usnews.com'),
 'phones':('gsmarena.com','gadgets360.com','91mobiles.com','smartprix.com','phonearena.com','notebookcheck.net','kimovil.com','devicespecifications.com','nanoreview.net','androidauthority.com','samsung.com','apple.com','store.google.com','mi.com','oneplus.com','motorola.com','oppo.com','vivo.com'),
 'cars':('cardekho.com','carwale.com','autocarindia.com','caranddriver.com','motortrend.com','edmunds.com','kbb.com','cars.com','topgear.com','whatcar.com','toyota.com','ford.com','hyundai.com','kia.com','bmw.com','mercedes-benz.com','tesla.com','mahindra.com'),
 'bikes':('bikedekho.com','bikewale.com','zigwheels.com','motorcycle.com','cycleworld.com','bennetts.co.uk','motorcyclenews.com','visordown.com','autocarindia.com','totalmotorcycle.com','heromotocorp.com','honda2wheelersindia.com','yamaha-motor-india.com','bajajauto.com','royalenfield.com','ktm.com')
}
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'content'/'directory-details.json'
RECORDS=ROOT/'content'/'directory-records.json'
FIELDS={
 'colleges':{'programmes':('programmes','programs','course','courses','degrees','degree programmes'),'fees':('tuition','fees','tuition fees','annual fee'),'admissions':('admission','application','eligibility','entry requirements'),'placement':('placement','employment')},
 'phones':{'display':('display','screen','display size'),'processor':('processor','chipset','cpu','soc'),'battery':('battery','battery capacity'),'ram':('ram','memory'),'storage':('storage','internal storage'),},
 'cars':{'price':('price','msrp','starting price'),'powertrain':('engine','powertrain','engine type','motor'),'variants':('trim','variant','model'),'mileage':('fuel economy','mileage','range')},
 'bikes':{'price':('price','msrp'),'engine':('engine','displacement','engine capacity'),'power':('power','max power','maximum power'),'torque':('torque','max torque'),'mileage':('mileage','fuel economy')}
}
def clean(value):
 if isinstance(value,(dict,list)):return ''
 return re.sub(r'\s+',' ',str(value)).strip()[:180]

def collect(obj,out):
 if isinstance(obj,list):
  for item in obj:collect(item,out)
 elif isinstance(obj,dict):
  # Schema.org PropertyValue entries store the label in name and the fact in value.
  if obj.get('name') and obj.get('value') is not None:
   key=clean(obj['name']).lower()
   val=clean(obj['value'])
   if key and val:out.setdefault(key,val)
  for key,value in obj.items():
   if key in ('@graph','mainEntity','additionalProperty','specification','offers','itemListElement','hasPart'):
    collect(value,out)
   elif isinstance(value,(str,int,float)):
    out.setdefault(key.lower(),clean(value))
   elif isinstance(value,(list,dict)):
    collect(value,out)

def extract_pairs(soup):
 found={}
 for tag in soup.select('script[type="application/ld+json"]')[:30]:
  try:collect(json.loads(tag.string or tag.get_text()),found)
  except (ValueError,TypeError):pass
 for row in soup.select('tr')[:250]:
  cells=row.find_all(['th','td'],recursive=False)
  if len(cells)==2:
   key=clean(cells[0].get_text(' ',strip=True)).lower()
   value=clean(cells[1].get_text(' ',strip=True))
   if key and value:found.setdefault(key,value)
 for dl in soup.select('dl')[:100]:
  for dt_tag in dl.find_all('dt'):
   dd=dt_tag.find_next_sibling('dd')
   if dd:
    key=clean(dt_tag.get_text(' ',strip=True)).lower()
    value=clean(dd.get_text(' ',strip=True))
    if key and value:found.setdefault(key,value)
 for item in soup.select('[itemprop="additionalProperty"],[itemprop="specification"]')[:120]:
  name=item.select_one('[itemprop="name"]')
  value=item.select_one('[itemprop="value"]')
  if name and value:found.setdefault(clean(name.get('content') or name.get_text(' ',strip=True)).lower(),clean(value.get('content') or value.get_text(' ',strip=True)))
 for row in soup.select('li,div')[:1200]:
  if not row.get('class'):continue
  classes=' '.join(row.get('class',[])).lower()
  if not any(t in classes for t in ('spec','attribute','feature','detail','parameter')):continue
  children=row.find_all(recursive=False)
  if len(children)!=2:continue
  key=clean(children[0].get_text(' ',strip=True)).lower()
  value=clean(children[1].get_text(' ',strip=True))
  if 2<len(key)<55 and 2<len(value)<180:found.setdefault(key,value)
 return found

def enrich(kind,name,record,session,url=None):
 url=url or record.get('official_url') or record.get('source_url','')
 if not url.startswith('https://'):return {}
 # Wikidata identifiers are not a substitute for official product specification pages.
 if urlparse(url).hostname in ('www.wikidata.org','wikidata.org'):return {}
 try:
  response=session.get(url,timeout=5,allow_redirects=True)
  response.raise_for_status()
  if 'text/html' not in response.headers.get('Content-Type',''):return {}
  if len(response.content)>2000000:return {}
  soup=BeautifulSoup(response.text,'html.parser')
  found=extract_pairs(soup)
  output={}
  for field,aliases in FIELDS[kind].items():
   if record.get(field):continue
   for key,value in found.items():
    if any(key==alias or key.startswith(alias+' ') or key.endswith(' '+alias) for alias in aliases) and value and len(value)>2:
     output[field]=value
     break
  if output:
   output['source_url']=url
   output['evidence_url']=url
  return output
 except requests.RequestException:return {}

def discover(kind,name,session):
 # Search domain-constrained public RSS results, not generated or guessed article URLs.
 # Only fetch publisher pages with the requested entity in the result title.
 domains=DOMAINS[kind]
 start=sum(ord(ch) for ch in name)%len(domains)
 for domain in (domains[(start+i)%len(domains)] for i in range(5)):
  try:
   terms={'colleges':'courses fees eligibility admissions','phones':'display chipset battery specifications','cars':'engine variants price specifications','bikes':'engine power torque specifications'}[kind]
   query=requests.utils.quote('site:'+domain+' "'+name+'" '+terms)
   response=session.get('https://www.bing.com/search?format=rss&q='+query,timeout=3)
   if response.status_code!=200:continue
   feed=feedparser.parse(response.content)
   for item in feed.entries[:2]:
    url=item.get('link','')
    host=(urlparse(url).hostname or '').lower()
    if not (host==domain or host.endswith('.'+domain)):continue
    tokens=[x for x in re.findall(r'[a-z0-9]+',name.lower()) if len(x)>2]
    title=item.get('title','').lower()
    if tokens and sum(t in title for t in tokens)<max(1,len(tokens)-1):continue
    yield url
  except requests.RequestException:continue


def main():
 try:records=json.loads(RECORDS.read_text(encoding='utf-8'))
 except (OSError,ValueError):records={}
 try:details=json.loads(TARGET.read_text(encoding='utf-8'))
 except (OSError,ValueError):details={}
 session=requests.Session()
 session.headers.update({'User-Agent':'GlobeWireDaily-DirectoryResearch/1.0 (contact@globewiredaily.org)'})
 checked=0
 for kind in FIELDS:
  checked_kind=0
  details.setdefault(kind,{})
  entries=[r for r in records.get(kind,[]) if isinstance(r,dict)]
  if entries:
   slot=int(dt.datetime.now(dt.timezone.utc).timestamp()//1800)
   offset=(slot*9)%len(entries)
   entries=entries[offset:]+entries[:offset]
  for record in entries:
   if checked_kind>=24:break
   if not isinstance(record,dict):continue
   name=record.get('name','')
   if not name:continue
   existing=details[kind].get(name,{})
   if all(existing.get(k) for k in FIELDS[kind]):continue
   if not (record.get('official_url') or record.get('source_url')):continue
   checked+=1
   checked_kind+=1
   base={**record,**existing}
   additions=enrich(kind,name,base,session)
   if not all((base|additions).get(field) for field in FIELDS[kind]):
    for found_url in discover(kind,name,session):
     extra=enrich(kind,name,{**base,**additions},session,found_url)
     additions.update(extra)
     if all((base|additions).get(field) for field in FIELDS[kind]):break
   if additions:
    details[kind][name]={**record,**existing,**additions}
    print('Verified structured fields:',kind,name,list(additions),flush=True)
   time.sleep(.2)
 if checked:
  TARGET.write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Official page research attempts:',checked,flush=True)
if __name__=='__main__':main()
