"""Incremental, source-attributed worldwide directory import. Never invent commercial facts."""
import datetime
import json
import os
import pathlib
import requests
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
TARGET=ROOT/'content'/'directory-records.json'
QUERY={'colleges':'Q3918','cars':'Q3231690','bikes':'Q34493','phones':'Q19723451'}
ENDPOINT='https://query.wikidata.org/sparql'
HEADERS={'User-Agent':'GlobeWireDailyDirectoryBot/1.0 (contact@globewiredaily.org)','Accept':'application/sparql-results+json'}

def fetch(kind,limit=100,offset=0):
 cls=QUERY[kind]
 q=f"""SELECT DISTINCT ?item ?itemLabel ?countryLabel ?inception ?website WHERE {{
 ?item wdt:P31 wd:{cls}.
 OPTIONAL {{ ?item wdt:P17 ?country. }}
 OPTIONAL {{ ?item wdt:P571 ?inception. }}
 OPTIONAL {{ ?item wdt:P856 ?website. }}
 SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
 }} ORDER BY ?item LIMIT {int(limit)} OFFSET {int(offset)}"""
 response=requests.get(ENDPOINT,params={'query':q,'format':'json'},headers=HEADERS,timeout=30)
 response.raise_for_status()
 rows=[]
 for b in response.json().get('results',{}).get('bindings',[]):
  get=lambda k: b.get(k,{}).get('value','')
  name=get('itemLabel').strip()
  item=get('item')
  if not name or name.startswith('Q') or not item.startswith('http'):continue
  rows.append({'name':name[:160],'country':get('countryLabel')[:90],
               'introduced':get('inception')[:10],'official_url':get('website')[:300],
               'source_url':item,'source':'Wikidata',
               'retrieved_at':datetime.datetime.now(datetime.timezone.utc).date().isoformat()})
 return rows

def main():
 try:data=json.loads(TARGET.read_text(encoding='utf-8'))
 except (OSError,ValueError):data={}
 if not isinstance(data,dict):data={}
 page_size=max(25,min(200,int(os.getenv('DIRECTORY_PAGE_SIZE','100'))))
 pages_per_run=max(1,min(8,int(os.getenv('DIRECTORY_PAGES_PER_RUN','3'))))
 for kind in QUERY:
  previous=data.get(kind,[])
  if not isinstance(previous,list):previous=[]
  by_id={r['source_url']:r for r in previous if isinstance(r,dict) and r.get('source_url')}
  # Resume from existing cache. Re-check the beginning only after a complete traversal.
  offset=len(by_id)
  for page in range(pages_per_run):
   try:
    rows=fetch(kind,page_size,offset)
    for row in rows:
     old=by_id.get(row['source_url'],{})
     by_id[row['source_url']]={**old,**{k:(v or old.get(k,'')) for k,v in row.items()}}
    print(kind,'offset',offset,'fetched',len(rows),'total',len(by_id),flush=True)
    if len(rows)<page_size:
     break
    offset+=page_size
    time.sleep(1)
   except (requests.RequestException,ValueError,KeyError) as exc:
    print(kind,'fetch failed, preserving cache',type(exc).__name__,flush=True)
    break
  data[kind]=sorted(by_id.values(),key=lambda r:r['source_url'])
 if any(data.get(k) for k in QUERY):
  TARGET.parent.mkdir(parents=True,exist_ok=True)
  serialized=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
  if not TARGET.exists() or TARGET.read_text(encoding='utf-8')!=serialized:
   TARGET.write_text(serialized,encoding='utf-8')

if __name__=='__main__':main()
