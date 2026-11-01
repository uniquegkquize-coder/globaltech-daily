"""Bounded Wikidata SPARQL directory refresh. Data provenance is retained; no invented pricing."""
import json, os, pathlib, requests, datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
TARGET=ROOT/'content'/'directory-records.json'
QUERY={
 'colleges':'Q3918',
 'cars':'Q3231690',
 'bikes':'Q34493',
 'phones':'Q19723451'
}
# Classes: university, automobile model, motorcycle model, smartphone model.
ENDPOINT='https://query.wikidata.org/sparql'
def fetch(kind,limit=150):
 cls=QUERY[kind]
 q=f"""SELECT DISTINCT ?item ?itemLabel ?countryLabel ?inception ?website WHERE {{
 ?item wdt:P31 wd:{cls}.
 OPTIONAL {{ ?item wdt:P17 ?country. }}
 OPTIONAL {{ ?item wdt:P571 ?inception. }}
 OPTIONAL {{ ?item wdt:P856 ?website. }}
 SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
 }} ORDER BY ?item LIMIT {int(limit)}"""
 r=requests.get(ENDPOINT,params={'query':q,'format':'json'},headers={'User-Agent':'GlobeWireDailyDirectoryBot/1.0 (contact@globewiredaily.org)','Accept':'application/sparql-results+json'},timeout=35)
 r.raise_for_status()
 rows=[]
 for b in r.json().get('results',{}).get('bindings',[]):
  get=lambda k: b.get(k,{}).get('value','')
  name=get('itemLabel').strip(); item=get('item')
  if not name or name.startswith('Q') or not item.startswith('http'):continue
  rows.append({'name':name[:160],'country':get('countryLabel')[:90],'introduced':get('inception')[:10],'official_url':get('website')[:300],'source_url':item,'source':'Wikidata','retrieved_at':datetime.datetime.now(datetime.timezone.utc).date().isoformat()})
 return rows
def main():
 data={}
 if TARGET.exists():
  try:data=json.loads(TARGET.read_text(encoding='utf-8'))
  except (ValueError,OSError):data={}
 for kind in QUERY:
  try:
   rows=fetch(kind,int(os.getenv('DIRECTORY_RECORD_LIMIT','150')))
   if rows:data[kind]=rows
   print(kind,'records',len(rows),flush=True)
  except (requests.RequestException,ValueError,KeyError) as exc:
   print(kind,'refresh failed; preserving cached records',type(exc).__name__,flush=True)
 if any(data.get(k) for k in QUERY):
  TARGET.parent.mkdir(parents=True,exist_ok=True)
  text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
  if not TARGET.exists() or TARGET.read_text(encoding='utf-8')!=text:TARGET.write_text(text,encoding='utf-8')
if __name__=='__main__':main()
