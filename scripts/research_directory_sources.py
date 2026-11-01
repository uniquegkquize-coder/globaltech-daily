"""Conservative structured-data enrichment from publisher/official pages.
Only import explicitly labeled facts; never infer missing prices or fees.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'content'/'directory-details.json'
RECORDS=ROOT/'content'/'directory-records.json'
FIELDS={
 'colleges':{'programmes':('programmes','programs','course','courses'),'fees':('tuition','fees'),'admissions':('admission','application'),'placement':('placement','employment')},
 'phones':{'display':('display','screen'),'processor':('processor','chipset'),'battery':('battery',),'ram':('ram',),'storage':('storage',)},
 'cars':{'price':('price','msrp'),'powertrain':('engine','powertrain'),'variants':('trim','variant'),'mileage':('fuel economy','mileage')},
 'bikes':{'price':('price','msrp'),'engine':('engine','displacement'),'power':('power',),'torque':('torque',),'mileage':('mileage','fuel economy')}
}
def clean(value):
 if isinstance(value,(dict,list)):return ''
 return re.sub(r'\s+',' ',str(value)).strip()[:180]

def collect(obj,out):
 if isinstance(obj,list):
  for item in obj:collect(item,out)
 elif isinstance(obj,dict):
  for key,value in obj.items():
   if key in ('@graph','mainEntity','additionalProperty','offers','itemListElement'):
    collect(value,out)
   elif isinstance(value,(str,int,float)):
    out.setdefault(key.lower(),clean(value))
   elif isinstance(value,(list,dict)):
    collect(value,out)

def enrich(kind,name,record,session):
 url=record.get('official_url') or record.get('source_url','')
 if not url.startswith('https://'):return {}
 # Wikidata identifiers are not a substitute for official product specification pages.
 if urlparse(url).hostname in ('www.wikidata.org','wikidata.org'):return {}
 try:
  response=session.get(url,timeout=8,allow_redirects=True)
  response.raise_for_status()
  if 'text/html' not in response.headers.get('Content-Type',''):return {}
  if len(response.content)>2000000:return {}
  soup=BeautifulSoup(response.text,'html.parser')
  found={}
  for tag in soup.select('script[type="application/ld+json"]')[:20]:
   try:collect(json.loads(tag.string or tag.get_text()),found)
   except (ValueError,TypeError):pass
  for row in soup.select('tr')[:100]:
   cells=row.find_all(['th','td'],recursive=False)
   if len(cells)==2:
    key=clean(cells[0].get_text(' ',strip=True)).lower()
    value=clean(cells[1].get_text(' ',strip=True))
    if key and value:found.setdefault(key,value)
  output={}
  for field,aliases in FIELDS[kind].items():
   if record.get(field):continue
   for key,value in found.items():
    if any(key==alias or key.startswith(alias+' ') for alias in aliases) and value and len(value)>2:
     output[field]=value
     break
  if output:
   output['source_url']=url
   output['official_url']=url
  return output
 except requests.RequestException:return {}

def main():
 try:records=json.loads(RECORDS.read_text(encoding='utf-8'))
 except (OSError,ValueError):records={}
 try:details=json.loads(TARGET.read_text(encoding='utf-8'))
 except (OSError,ValueError):details={}
 session=requests.Session()
 session.headers.update({'User-Agent':'GlobeWireDaily-DirectoryResearch/1.0 (contact@globewiredaily.org)'})
 checked=0
 for kind in FIELDS:
  details.setdefault(kind,{})
  for record in records.get(kind,[]):
   if checked>=36:break
   if not isinstance(record,dict):continue
   name=record.get('name','')
   if not name:continue
   existing=details[kind].get(name,{})
   if all(existing.get(k) for k in FIELDS[kind]):continue
   if not record.get('official_url'):continue
   checked+=1
   additions=enrich(kind,name,{**record,**existing},session)
   if additions:
    details[kind][name]={**record,**existing,**additions}
    print('Verified structured fields:',kind,name,list(additions),flush=True)
   time.sleep(.2)
 if checked:
  TARGET.write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Official page research attempts:',checked,flush=True)
if __name__=='__main__':main()
