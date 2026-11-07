"""Conservative structured-data enrichment from publisher/official pages.
Only import explicitly labeled facts; never infer missing prices or fees.
"""
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin, quote
import unicodedata
import feedparser
import requests
from bs4 import BeautifulSoup
from public_page_fetch import fetch_public_html
from directory_facts import source_tables,specification_rows,framework_pairs,label,FOCUS,programme_cards,pdf_page,model_scope,embedded_model_rows
from directory_refresh import MUTABLE, refresh_fields, refresh_sources, protect_reviewed, merge_rows

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
 'colleges':{'programmes':('programmes','programs','course','courses','degrees','degree programmes'),'duration':('duration','course duration'),'fees':('tuition','fees','tuition fees','annual fee'),'admissions':('admission','application','eligibility','entry requirements'),'placement':('placement','employment'),'scholarships':('scholarships','financial aid'),'accreditation':('accreditation','recognition'),'application_process':('application process','how to apply'),'eligibility':('eligibility','entry requirements'),'country':('country','addresscountry'),'region':('state','addressregion'),'city':('city','addresslocality')},
 'phones':{'display':('display','screen','display size','screen size'),'processor':('chipset','processor make','processor','soc','cpu'),'battery':('battery','battery capacity'),'ram':('ram','memory'),'storage':('storage','internal storage'),'cameras':('camera','cameras','rear camera','main camera'),'charging':('charging','fast charging'),'connectivity':('connectivity','network','network technology'),'launch_date':('launch date','announced','releasedate'),'price':('price','msrp'),'manufacturer':('manufacturer','brand')},
 'cars':{'price':('price','msrp','starting price'),'powertrain':('engine','powertrain','engine type','motor'),'variants':('trim levels','variant','variants'),'mileage':('fuel economy','mileage','range'),'transmission':('transmission','gearbox'),'dimensions':('dimensions','length','width','height','wheelbase'),'safety':('safety','airbags','safety features'),'features':('features','standard features'),'availability':('availability','market availability'),'manufacturer':('manufacturer','brand')},
 'bikes':{'price':('price','msrp'),'engine':('engine','displacement','engine capacity'),'power':('power','max power','maximum power'),'torque':('torque','max torque'),'mileage':('mileage','fuel economy'),'brakes':('brakes','front brake','rear brake'),'variants':('variants','variant'),'specifications':('specifications','kerb weight','seat height'),'manufacturer':('manufacturer','brand')}
}

for kind in ('phones','cars','bikes'):
 FIELDS[kind]['price']=('price','selling price','sale price','offer price','ex-showroom price','ex showroom price','starting price','msrp','mrp','lowprice','minprice','min price')
 FIELDS[kind]['availability']=('availability','stock status')
FIELDS['colleges']['fees']=('tuition','fee','fees','tuition fee','tuition fees','annual fee','annual fees','total fee','total fees','course fees')

FIELDS['phones'].update({'os':('operating system','os','software'),'front_camera':('front camera','selfie camera'),'weight':('weight','body weight'),'dimensions':('dimensions','body dimensions'),'protection':('protection','water resistance','ip rating'),'color':('colours','colors','colour','color')})
FIELDS['cars'].update({'displacement':('displacement','engine displacement'),'power':('max power','power','maximum power'),'torque':('max torque','torque'),'fuel_tank':('fuel tank capacity','fuel capacity'),'seating_capacity':('seating capacity','seats'),'boot_space':('boot space','boot capacity')})
FIELDS['bikes'].update({'transmission':('transmission','gearbox'),'weight':('kerb weight','weight'),'seat_height':('seat height','saddle height'),'wheelbase':('wheelbase',),'fuel_tank':('fuel tank capacity','fuel capacity'),'fuel_system':('fuel system',),'suspension':('suspension','front suspension','rear suspension')})

def merge_facts(current,extra):
 for key,value in extra.items():
  if key in ('courses','variants') and isinstance(value,list):
   current[key]=merge_rows(current.get(key,[]),value)
  elif key in ('source_tables','specification_rows') and isinstance(value,list):
   combined=list(current.get(key,[]));seen={json.dumps(r,sort_keys=True,ensure_ascii=False) for r in combined}
   for row in value:
    signature=json.dumps(row,sort_keys=True,ensure_ascii=False)
    if signature not in seen:combined.append(row);seen.add(signature)
   current[key]=combined[:300]
  elif key=='field_sources':current[key]={**current.get(key,{}),**value}
  else:current[key]=value
 return current

def reference_article(record,session):
 match=re.search(r'(Q[0-9]+)(?:$|[?#/])',str(record.get('source_url') or ''))
 if not match:return None
 try:
  r=session.get('https://www.wikidata.org/wiki/Special:EntityData/'+match.group(1)+'.json',timeout=(3,7));r.raise_for_status();entity=r.json()['entities'][match.group(1)]
  item=entity.get('sitelinks',{}).get('enwiki',{})
  if item.get('title'):return 'https://en.wikipedia.org/wiki/'+quote(item['title'].replace(' ','_'))
 except (requests.RequestException,ValueError,KeyError,TypeError):pass
 return None

def evidence_source(entry):
    for key in ('evidence_url','source_url','official_url'):
        url=str(entry.get(key) or '')
        if urlparse(url).scheme=='https' and (urlparse(url).hostname or '').lower() not in ('wikidata.org','www.wikidata.org'):
            return url
    return str(entry.get('source_url') or entry.get('official_url') or '')

def clean(value):
 if isinstance(value,(dict,list)):return ''
 return re.sub(r'\s+',' ',str(value)).strip()[:1200]

def collect(obj,out,entity_name=None):
 if isinstance(obj,list):
  for item in obj:collect(item,out,entity_name)
 elif isinstance(obj,dict):
  types=obj.get('@type',[])
  if isinstance(types,str):types=[types]
  if entity_name and any(t in ('Organization','LocalBusiness','CollegeOrUniversity','EducationalOrganization','Product') for t in types) and obj.get('name'):
   wanted=label(entity_name);actual=label(obj['name'])
   if wanted not in actual and actual not in wanted:return
  if any(t in ('ImageObject','VideoObject','WebSite','BreadcrumbList','Review','AggregateRating') for t in types):return
  # Schema.org PropertyValue entries store the label in name and the fact in value.
  if obj.get('name') and obj.get('value') is not None:
   key=clean(obj['name']).lower()
   val=clean(str(obj['value'])+' '+str(obj.get('unitText') or ''))
   if key and val:out.setdefault(key,val)
  for key,value in obj.items():
   if key in ('@graph','mainEntity','additionalProperty','specification','offers','itemListElement','hasPart'):
    collect(value,out,entity_name)
   elif isinstance(value,(str,int,float)):
    out.setdefault(key.lower(),clean(value))
   elif isinstance(value,(list,dict)):
    collect(value,out,entity_name)

def extract_pairs(soup,entity_name=None):
 found=framework_pairs(soup)
 aliases={label(a) for values in FIELDS.values() for names in values.values() for a in names}
 for tag in soup.find_all(['div','span','p','h2','h3','h4','h5','h6','strong'])[:6000]:
  if tag.find_parent(['nav','header','footer','aside']):continue
  key=clean(tag.get_text(' ',strip=True)).strip(': ')
  if len(key)>65 or label(key) not in aliases:continue
  sibling=tag.find_next_sibling()
  if sibling:
   value=clean(sibling.get_text(' ',strip=True))
   if value and label(value) not in aliases:found.setdefault(key.lower(),value)
 for tag in soup.select('script[type="application/ld+json"]')[:30]:
  try:collect(json.loads(tag.string or tag.get_text()),found,entity_name)
  except (ValueError,TypeError):pass
 for row in soup.select('tr')[:250]:
  cells=row.find_all(['th','td'],recursive=False)
  if len(cells)==2 and not all(c.name=='th' for c in cells):
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
 for heading in soup.select('h2,h3,h4')[:200]:
  key=clean(heading.get_text(' ',strip=True)).lower()
  if not any(key==alias for fields in FIELDS.values() for aliases in fields.values() for alias in aliases):continue
  sibling=heading.find_next_sibling()
  if sibling and sibling.name in ('p','ul','div'):
   value=clean(sibling.get_text(' ',strip=True))
   if value:found.setdefault(key,value)
 return found

def extract_course_rows(soup):
 rows=[]
 for table in soup.select('table')[:30]:
  trs=table.find_all('tr')
  if not trs:continue
  headers=[clean(c.get_text(' ',strip=True)).lower() for c in trs[0].find_all(['td','th'])]
  if not headers or not any(re.search(r'\b(course|courses|programme|programmes|program)\b',h) for h in headers):continue
  if not any(any(t in h for t in ('duration','fees','eligibility')) for h in headers):continue
  for row in trs[1:101]:
   cells=row.find_all(['td','th'])
   if len(cells)!=len(headers):continue
   data={h:clean(c.get_text(' ',strip=True)) for h,c in zip(headers,cells)}
   if any(data.values()):rows.append(data)
 return rows

def enrich(kind,name,record,session,url=None):
 url=url or evidence_source(record)
 if urlparse(url).scheme not in ('http','https'):return {}
 # Wikidata identifiers are not a substitute for official product specification pages.
 if urlparse(url).hostname in ('www.wikidata.org','wikidata.org'):return {}
 try:
  if urlparse(url).path.lower().endswith('.pdf'):
   soup,final_url=pdf_page(url,name,session);method='pdf'
   if soup is None:return {}
  else:
   html,final_url,method=fetch_public_html(url,session=session,timeout=(5,max(7,int(os.getenv('DIRECTORY_FETCH_TIMEOUT_SECONDS','20')))))
   if not html:
    print('SOURCE_FAILURE',json.dumps({'url':url,'reason':method}),flush=True);return {}
   if urlparse(final_url).scheme not in ('http','https'):return {}
   soup=BeautifulSoup(html,'html.parser')
  def words(value):
   value=unicodedata.normalize('NFKD',value.replace('+',' plus ')).encode('ascii','ignore').decode().lower()
   return re.findall(r'[a-z0-9]+',value)
  tokens=words(name.replace('IIT ','Indian Institute of Technology '))
  headings=' '.join(t.get_text(' ',strip=True) for t in soup.select('title,h1'))
  heading_words=set(words(headings.replace('IIT ','Indian Institute of Technology ')))
  required=[t for t in tokens if t not in ('the','of','and','at','in')]
  # Course pages often have only the programme in h1. Accept institution
  # identity in the page text only on that institution's known official host.
  official_host=(urlparse(record.get('official_url','')).hostname or '').removeprefix('www.')
  page_host=(urlparse(final_url).hostname or '').removeprefix('www.')
  if kind=='colleges' and official_host and (page_host==official_host or page_host.endswith('.'+official_host)):
   heading_words.update(words(soup.get_text(' ',strip=True)[:100000]))
  if required and not (all(t in heading_words for t in required) or ''.join(required) in ''.join(words(headings))):
   print('SOURCE_FAILURE',json.dumps({'url':url,'reason':'entity title mismatch','name':name}),flush=True)
   return {}
  h=soup.find('h1')
  if h:
   actual=' '.join(words(h.get_text(' ',strip=True)));expected=' '.join(words(name))
   if any(re.search(r'\b'+term+r'\b',actual) and not re.search(r'\b'+term+r'\b',expected) for term in ('ultra','roxx','xtec','pro max')):return {}
  soup=model_scope(soup,final_url)
  found=extract_pairs(soup,name)
  labels={alias for aliases in FIELDS[kind].values() for alias in aliases}
  matched=sum(re.sub(r'\s*\([^)]*\)\s*',' ',key).strip() in labels for key in found)
  if matched<2 and method in ('http','cached-http'):
   rendered,final_url,method=fetch_public_html(url,session=session,render=True)
   if rendered:
    soup=BeautifulSoup(rendered,'html.parser')
    headings=' '.join(t.get_text(' ',strip=True) for t in soup.select('title,h1'))
    if required and not (all(t in set(words(headings)) for t in required) or ''.join(required) in ''.join(words(headings))):return {}
    soup=model_scope(soup,final_url)
    found=extract_pairs(soup,name)
  # Expand semantic product labels from HTML meta properties where present.
  for meta in soup.select('meta[itemprop][content], meta[property][content]')[:120]:
   key=clean(meta.get('itemprop') or meta.get('property')).lower()
   val=clean(meta.get('content'))
   if key and val:found.setdefault(key,val)
  if found.get('product:price:amount'):found.setdefault('price',found['product:price:amount'])
  if found.get('product:price:currency'):found.setdefault('pricecurrency',found['product:price:currency'])
  embedded=embedded_model_rows(soup)
  for row in embedded:found.setdefault(row['label'].lower(),row['value'])
  output={}
  for field,aliases in FIELDS[kind].items():
   ranked=sorted(found.items(),key=lambda item: aliases.index(item[0]) if item[0] in aliases else len(aliases))
   for key,value in ranked:
    if label(key) in {label(a) for a in aliases} and value:
     unit=re.search(r'\((mAh|Ah|GB|MB|inches|mm|cm|kg|PS|Nm|cc|kW|bhp)\)',key,re.I)
     if unit and re.fullmatch(r'[\d., -]+',value):value+=' '+{'mah':'mAh','ah':'Ah','gb':'GB','mb':'MB','ps':'PS','nm':'Nm'}.get(unit.group(1).lower(),unit.group(1))
     if field in ('engine','power','torque','specifications','battery','ram','storage','charging') and re.fullmatch(r'[\d., -]+',value):continue
     if field in ('dimensions','specifications'):value=key+': '+value
     if field=='dimensions' and not re.search(r'\b(?:mm|cm|inches|in|metres)\b',value,re.I):continue
     if field=='city' and (len(value)>65 or re.search(r'\d{4,}|p\.?o\.?|dist\.',value,re.I)):continue
     if field=='price' and found.get('pricecurrency'):value=found['pricecurrency']+' '+value
     output[field]=value
     if field=='price':
      output['price_basis']=key+'; source-listed amount; market and variant as described by the source'
      if found.get('pricevaliduntil'):output['price_valid_until']=found['pricevaliduntil']
     break
  rows=specification_rows(soup)+embedded;tables=source_tables(soup)
  if rows:
   for row in rows:row['source_url']=final_url
   output['specification_rows']=rows
  if tables:
   for table in tables:table['source_url']=final_url
   output['source_tables']=tables
  if kind in ('cars','bikes'):
   dims=[r['label']+': '+r['value'] for r in rows if any(t in r['label'].lower() for t in ('length','width','height','wheelbase','clearance'))]
   if dims:output['dimensions']='; '.join(dict.fromkeys(dims))
  if kind=='colleges':
   courses=extract_course_rows(soup)+programme_cards(soup)
   for course in courses:course['source_url']=final_url
   if courses:
    output['courses']=courses
    for field,labels in {'programmes':('course','courses','programme','programmes'),
                         'duration':('duration',),'fees':('fees',),
                         'eligibility':('eligibility',),'admissions':('selection',)}.items():
     values=[]
     for row in courses:
      course=next((v for k,v in row.items() if k in ('course','courses','programme','programmes')),'')
      for key,value in row.items():
       if (key in labels if field=='programmes' else any(label in key for label in labels)):
        values.append(value if field=='programmes' else course+': '+key+' — '+value)
     if values:output[field]='; '.join(dict.fromkeys(values))[:2400]
  print('SOURCE_RESULT',json.dumps({'url':final_url,'name':name,'method':method,'matched_fields':list(output),'label_count':len(found)}),flush=True)
  if output:
   output['field_sources']={field:{'url':final_url,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat()} for field in output}
   output['source_url']=final_url
   output['evidence_url']=final_url
  return output
 except (requests.RequestException,ValueError,KeyError,OSError):return {}

def public_links(url,name,session):
 html,final,method=fetch_public_html(url,session=session)
 if not html:return
 soup=BeautifulSoup(html,'html.parser')
 tokens=[t for t in re.findall(r'[a-z0-9]+',name.lower()) if len(t)>2]
 host=urlparse(final).hostname
 links=[]
 for tag in soup.select('a[href],link[rel="alternate"][href],loc')[:400]:
  target=urljoin(final,tag.get('href') or tag.get_text(strip=True))
  if urlparse(target).hostname!=host:continue
  label=(target+' '+tag.get_text(' ',strip=True)).lower()
  if tokens and all(t in label for t in tokens):links.append(target)
 # Public feeds and declared sitemap links are discovery only; facts still come
 # from the linked entity page. Never use feed summaries as specification evidence.
 resources=[urljoin(final,t['href']) for t in soup.select('link[rel="alternate"][href]') if any(x in t.get('type','') for x in ('rss','atom'))][:1]
 resources += [urljoin(final,t['href']) for t in soup.select('a[href]') if 'sitemap' in t['href'].lower()][:1]
 for resource in resources:
  if urlparse(resource).hostname!=host:continue
  try:
   response=session.get(resource,timeout=(3,5))
   if response.status_code!=200 or len(response.content)>2000000:continue
   if 'xml' in response.headers.get('content-type',''):
    feed=feedparser.parse(response.content)
    candidates=[e.get('link','') for e in feed.entries[:100]]
    candidates+=re.findall(r'<loc>\s*([^<]+)\s*</loc>',response.text)[:200]
    for target in candidates:
     if urlparse(target).hostname==host and tokens and all(t in target.lower() for t in tokens):links.append(target)
  except requests.RequestException:continue
 links=list(dict.fromkeys(links));links.sort(key=lambda u:(-sum(t in u.lower() for t in ('spec','brochure','technical','course','program','admission','fee','placement','scholarship')),len(u)))
 for target in links[:4]:yield target

def discover(kind,name,session):
 # Search domain-constrained public RSS results, not generated or guessed article URLs.
 # Only fetch publisher pages with the requested entity in the result title.
 domains=DOMAINS[kind]
 start=(sum(ord(ch) for ch in name)+int(time.time()//21600)*int(os.getenv('DIRECTORY_DOMAINS_PER_ENTITY','4')))%len(domains)
 for domain in (domains[(start+i)%len(domains)] for i in range(min(len(domains),int(os.getenv('DIRECTORY_DOMAINS_PER_ENTITY','4'))))):
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


def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix('.tmp')
 temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 temp.replace(path)


def main():
 def read(path):
  try:return json.loads(path.read_text(encoding='utf-8'))
  except (OSError,ValueError):return {}
 records=read(RECORDS);details=read(TARGET);state_path=ROOT/'content/directory-research-state.json';state=read(state_path);report={}
 limit=max(1,int(os.getenv('DIRECTORY_RESEARCH_LIMIT','120')));budget=max(1,int(os.getenv('DIRECTORY_RESEARCH_SECONDS','480')));workers=max(1,min(6,int(os.getenv('DIRECTORY_RESEARCH_WORKERS','4'))))
 for kind in FIELDS:
  end=time.monotonic()+budget/len(FIELDS);details.setdefault(kind,{})
  entries=[{'name':name,**entry} for name,entry in details[kind].items() if isinstance(entry,dict)]+[r for r in records.get(kind,[]) if isinstance(r,dict) and r.get('name') not in details[kind]]
  published={p.get('directory_name') for path in (ROOT/'content/posts').glob('*.json') if (p:=read(path)).get('directory_kind')==kind}
  entries.sort(key=lambda r:(r.get('name') not in FOCUS.get(kind,[]),r.get('name') not in published,state.get(kind+':'+r.get('name',''),{}).get('attempted',0)))
  counts=Counter();failures=[];eligible=[]
  for record in entries:
   if not record.get('name'):continue
   if state.get(kind+':'+record['name'],{}).get('refresh_version')==2 and state.get(kind+':'+record['name'],{}).get('retry_after',0)>time.time():counts['cooldown']+=1
   else:eligible.append(record)
  def process(record):
   if time.monotonic()>=end:return None
   name=record['name'];existing=details[kind].get(name,{});base={**record,**existing};session=requests.Session();session.headers.update({'User-Agent':'GlobeWireDaily-DirectoryResearch/3.0 (contact@globewiredaily.org)'})
   try:
    additions=enrich(kind,name,base,session)
    # Complete specs must not suppress price/fee checks on their own pages.
    target_fields=refresh_fields(kind)
    for target in refresh_sources(kind,base)[:max(1,int(os.getenv('DIRECTORY_PRICE_PAGES_PER_ENTITY','6')))]:
     if time.monotonic()>=end:break
     if target==evidence_source(base):continue
     extra=enrich(kind,name,base,session,target)
     # Do not let a store's marketing copy overwrite reviewed static specs.
     target_fields=target_fields|{'price_basis','price_valid_until'}
     extra={k:v for k,v in extra.items() if k in target_fields or k in ('field_sources',)}
     extra['field_sources']={k:v for k,v in extra.get('field_sources',{}).items() if k in target_fields}
     merge_facts(additions,extra)
    if not additions and base.get('official_url') and time.monotonic()<end:
     for linked in public_links(base['official_url'],name,session):
      if time.monotonic()>=end:break
      merge_facts(additions,enrich(kind,name,base,session,linked))
    if not additions and time.monotonic()<end:
     reference=reference_article(record,session)
     if reference:merge_facts(additions,enrich(kind,name,base,session,reference))
    if (not additions.get('fees' if kind=='colleges' else 'price') or sum(bool((base|additions).get(f)) for f in FIELDS[kind])<5) and time.monotonic()<end:
     for found in discover(kind,name,session):
      if time.monotonic()>=end:break
      merge_facts(additions,enrich(kind,name,{**base,**additions},session,found))
    protect_reviewed(existing,additions)
    for field in ('courses','variants'):
     if isinstance(additions.get(field),list):additions[field]=merge_rows(existing.get(field,[]),additions[field])
    changes={k:v for k,v in additions.items() if (k in FIELDS[kind] or k in ('courses','source_tables','specification_rows')) and v!=existing.get(k)}
    return name,base,existing,additions,changes
   finally:session.close()
  with ThreadPoolExecutor(max_workers=workers) as pool:
   futures={pool.submit(process,r):r for r in eligible[:limit]}
   for future in as_completed(futures):
    try:result=future.result()
    except Exception as exc:counts['errors']+=1;failures.append({'name':futures[future]['name'],'reason':type(exc).__name__});continue
    if result is None:continue
    name,base,existing,additions,changes=result;counts['attempted']+=1
    checked={k:v for k,v in additions.get('field_sources',{}).items() if k in refresh_fields(kind)}
    if changes or checked:
     details[kind][name]={**base,**additions,'field_sources':{**existing.get('field_sources',{}),**additions.get('field_sources',{})}};save(TARGET,details);counts['updated' if changes and existing else 'new' if changes else 'price_fee_rechecked']+=1
    else:counts['no_new_facts']+=1;failures.append({'name':name,'reason':'no additional source-labelled facts available'})
    state[kind+':'+name]={'refresh_version':2,'attempted':time.time(),'retry_after':time.time()+(int(os.getenv('DIRECTORY_PRICE_REFRESH_SECONDS','10800')) if changes or checked else 21600)};save(state_path,state)
  report[kind]={**counts,'failures':failures[:50],'remaining':len(eligible)-counts['attempted'],'budget_exhausted':time.monotonic()>=end}
 save(ROOT/'content/directory-research-status.json',report);print('DIRECTORY_RESEARCH',json.dumps(report),flush=True)
if __name__=='__main__':main()
