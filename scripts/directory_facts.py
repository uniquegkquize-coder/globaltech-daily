"""Structured source facts and safe profile presentation. No inferred specifications."""
import hashlib,html,json,re,shutil
from pathlib import Path
from functools import lru_cache
from urllib.parse import urlparse,urljoin
ROOT=Path(__file__).resolve().parents[1]
FOCUS={'colleges':['Parul University'],'cars':['Mahindra Thar'],'phones':['Vivo X Fold 5'],'bikes':['Hero Splendor Plus']}
TERMS=('engine','displacement','transmission','gearbox','torque','power','mileage','fuel','length','width','height','wheelbase','weight','brake','seat','suspension','tyre','tire','display','screen','camera','ram','storage','memory','battery','charging','processor','chipset','price','fee','tuition','course','programme','program','eligibility','admission','duration','scholarship','placement','accreditation','network','connectivity','software','sensor','dimension','safety','variant')
def text(v,limit=1200):return re.sub(r'\s+',' ',str(v)).strip()[:limit]
def label(v):return re.sub(r'[^a-z0-9]','',re.sub(r'\([^)]*\)','',str(v).lower()))
def fact_label(v):return any(t in str(v).lower() for t in TERMS)
def safe_url(u):return urlparse(str(u)).scheme in ('http','https') and bool(urlparse(str(u)).hostname) and not urlparse(str(u)).username

def source_tables(soup):
 out=[]
 for table in soup.select('table')[:40]:
  rows=[]
  for row in table.select('tr')[:150]:
   cells=[text(c.get_text(' ',strip=True)) for c in row.find_all(['th','td'],recursive=False)]
   if cells and len(cells)<=16 and any(cells):rows.append(cells)
  if len(rows)<2 or not any(fact_label(r[0]) for r in rows if r):continue
  title=table.find('caption') or table.find_previous(['h2','h3','h4'])
  out.append({'title':text(title.get_text(' ',strip=True),120) if title else 'Source specifications','rows':rows})
 return out[:20]

def specification_rows(soup):
 rows=[];seen=set()
 for table in source_tables(soup):
  section=table['title']
  for row in table['rows']:
   if len(row)==1:section=row[0];continue
   if len(row)==2 and fact_label(row[0]) and (section,*row) not in seen:
    rows.append(dict(section=section,label=row[0],value=row[1]));seen.add((section,*row))
 for dl in soup.select('dl')[:50]:
  for dt in dl.find_all('dt'):
   dd=dt.find_next_sibling('dd')
   if dd and fact_label(dt.get_text()):rows.append(dict(section='Specifications',label=text(dt.get_text(' ',strip=True),100),value=text(dd.get_text(' ',strip=True))))
 return rows[:300]

def framework_pairs(soup):
 pairs={}
 def walk(node):
  if isinstance(node,list):
   for item in node[:500]:walk(item)
  elif isinstance(node,dict):
   key=node.get('label') or node.get('displayName') or node.get('specName');value=node.get('value') or node.get('displayValue') or node.get('specValue')
   if key and isinstance(value,(str,int,float)) and fact_label(key):pairs.setdefault(text(key,100).lower(),text(value))
   for v in node.values():
    if isinstance(v,(dict,list)):walk(v)
 for tag in soup.select('script#__NEXT_DATA__,script[type="application/json"]')[:10]:
  try:walk(json.loads(tag.string or tag.get_text()))
  except (ValueError,TypeError):pass
 return pairs

def programme_cards(soup):
 rows=[];h=soup.find('h1');course=text(h.get_text(' ',strip=True),160) if h else ''
 for pane in soup.select('.tab-pane')[:20]:
  values={}
  for block in pane.select('.table-values'):
   key=block.find(['h5','h6','strong'],recursive=False);value=block.find('p',recursive=False)
   if key and value:values[text(key.get_text(' ',strip=True)).lower()]=text(value.get_text(' ',strip=True))
  if values.get('duration') and (values.get('fee') or values.get('eligibility criteria')):rows.append(dict(course=course,entry_mode=text(pane.get('id','').replace('-',' ')),**values))
 return rows

def model_scope(soup,url):
 target=Path(urlparse(url).path).name.removesuffix('.html')
 for meta in soup.select('.section-metadata'):
  for row in meta.find_all('div',recursive=False):
   cells=row.find_all('div',recursive=False)
   if len(cells)==2 and cells[0].get_text(strip=True)=='id' and cells[1].get_text(strip=True)==target:return meta.parent
 return soup

def embedded_model_rows(soup):
 rows=[]
 for p in soup.select('.specifications-popup p'):
  raw=p.get_text(strip=True)
  if not raw.startswith('{'):continue
  try:data=json.loads(raw)
  except ValueError:continue
  for section,items in data.items():
   if isinstance(items,dict):
    for k,v in items.items():
     if isinstance(v,(str,int,float)):rows.append(dict(section=text(section,100),label=text(k,100),value=text(v)))
 return rows

def pdf_page(url,name,session):
 import io
 from pypdf import PdfReader
 from bs4 import BeautifulSoup
 r=session.get(url,timeout=(3,7));r.raise_for_status()
 if len(r.content)>12_000_000:return None,r.url
 try:body='\n'.join(p.extract_text(extraction_mode='layout') or '' for p in list(PdfReader(io.BytesIO(r.content)).pages)[:20])
 except Exception:return None,r.url
 wanted=set(re.findall('[a-z0-9]+',name.lower()))-{'the','of','and'}
 if not wanted<=set(re.findall('[a-z0-9]+',body.lower())):return None,r.url
 rows=[]
 for line in body.splitlines():
  cells=[text(c) for c in re.split(r'\s{2,}',line.strip()) if c.strip()]
  if len(cells)>=2 and fact_label(cells[0]):rows.append(cells[:12])
 if not rows:return None,r.url
 esc=lambda v:html.escape(v,quote=True)
 markup='<h1>'+esc(name)+'</h1><table>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
 return BeautifulSoup(markup,'html.parser'),r.url

def meaningful(entry):
 keys=('programmes','courses','eligibility','admissions','fees','placement','processor','display','battery','ram','storage','powertrain','engine','engines','power','torque','dimensions','variants','price','transmission','weight','safety','suspension','displacement','fuel_tank','specification_rows')
 return sum(bool(entry.get(k)) for k in keys)>=3 or len(entry.get('courses',[]))>=2 or len(entry.get('specification_rows',[]))>=4

@lru_cache(maxsize=1)
def guide_images():
 out={}
 for path in (ROOT/'content/posts').glob('*.json'):
  try:
   p=json.loads(path.read_text())
   if p.get('directory_kind') and p.get('directory_name'):out[(p['directory_kind'],p['directory_name'].casefold())]=p.get('id','')
  except (OSError,ValueError,AttributeError):pass
 return out

def photo(kind,name,out):
 from image_rules import saved_photo_allowed
 ids=[hashlib.sha256(('directory:'+kind+':'+name).encode()).hexdigest()[:24],guide_images().get((kind,name.casefold()),'')]
 for ident in ids:
  if not ident:continue
  src=ROOT/'content/featured'/(ident+'.jpg');dest=Path(out)/'images'/(ident+'.jpg')
  try:meta=json.loads((ROOT/'content/featured'/(ident+'.json')).read_text())
  except (OSError,ValueError):meta={}
  if src.is_file() and saved_photo_allowed(meta,ROOT) and meta.get('kind') in ('publisher_source','licensed_source','licensed_photo','source_original','manual_original'):
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
   return dict(src='/images/'+ident+'.jpg?v='+hashlib.sha256(dest.read_bytes()).hexdigest()[:12],credit=meta.get('attribution') or 'Source publisher',source=meta.get('source_image') or meta.get('source',''),original=True)
  if dest.is_file() and ident==guide_images().get((kind,name.casefold()),''):return dict(src='/images/'+ident+'.jpg?v='+hashlib.sha256(dest.read_bytes()).hexdigest()[:12],credit='Editorial illustration — source photograph unavailable',source='',original=False)
 return None

def media_html(kind,name,out):
 image=photo(kind,name,out)
 if not image:return ''
 esc=lambda v:html.escape(str(v),quote=True)
 link=' · <a target="_blank" rel="noopener noreferrer" href="'+esc(image['source'])+'">Photo source</a>' if safe_url(image['source']) else ''
 return '<figure class="directory-media"><img loading="lazy" width="1280" height="720" src="'+esc(image['src'])+'" alt="'+esc(name)+'"><figcaption>'+esc(image['credit'])+link+'</figcaption></figure>'

def value_html(value):
 esc=lambda v:html.escape(str(v),quote=True)
 if isinstance(value,dict):return '<ul>'+''.join('<li><strong>'+esc(k.replace('_',' ').title())+':</strong> '+value_html(v)+'</li>' for k,v in value.items())+'</ul>'
 if isinstance(value,list):return '<ul>'+''.join('<li>'+value_html(v)+'</li>' for v in value)+'</ul>'
 return esc(value)

def table_html(title,rows):
 esc=lambda v:html.escape(str(v),quote=True)
 columns=list(dict.fromkeys(k for r in rows for k in r if k not in ('field_sources','checked_at')))
 if not columns:return ''
 result='<section class="directory-card directory-wide"><h2>'+esc(title)+'</h2><div class="directory-table-wrap"><table><thead><tr>'+''.join('<th scope="col">'+esc(k.replace('_',' ').title())+'</th>' for k in columns)+'</tr></thead><tbody>'
 for row in rows:
  result+='<tr>'
  for k in columns:
   value=row.get(k,'—')
   cell='<a target="_blank" rel="noopener noreferrer" href="'+esc(value)+'">Source</a>' if isinstance(value,str) and k.endswith(('url','source')) and safe_url(value) else value_html(value)
   result+='<td>'+cell+'</td>'
  result+='</tr>'
 return result+'</tbody></table></div></section>'

def structured_html(entry,lang):
 names={'courses':('Courses, fees and eligibility','कोर्स, फीस और पात्रता'),'engines':('Engines and transmissions','इंजन और गियरबॉक्स'),'variants':('Variants and market-specific prices','वेरिएंट और बाजार के अनुसार कीमत'),'placement_statistics':('Placement outcomes by programme','कोर्स के अनुसार प्लेसमेंट'),'specification_rows':('Detailed source specifications','स्रोत से विस्तृत स्पेसिफिकेशन')};result=''
 for k,titles in names.items():
  rows=entry.get(k)
  if isinstance(rows,list) and rows and all(isinstance(r,dict) for r in rows):result+=table_html(titles[lang=='hi'],rows)
 for table in entry.get('source_tables',[])[:12]:
  rows=table.get('rows',[])
  if not rows:continue
  width=max(len(r) for r in rows);columns=rows[0] if len(rows[0])==width else ['Field']+['Value '+str(i) for i in range(1,width)]
  data=rows[1:] if len(rows[0])==width else rows
  result+=table_html(table.get('title','Source table'),[{columns[i]:r[i] if i<len(r) else '—' for i in range(width)} for r in data])
 # Render other structured factual fields (fee schedules, dimensions, campuses,
 # regulatory history) as tables; never expose internal audit/provenance objects.
 internal={'field_sources','audit_notes','reviewed_fields','unsupported_existing_claims','source_tables','placements'}
 handled=set(names)|internal
 for key,value in entry.items():
  if key in handled:continue
  title=key.replace('_',' ').title()
  if isinstance(value,dict):
   result+=table_html(title,[{'field':k.replace('_',' ').title(),'value':v} for k,v in value.items()])
  elif isinstance(value,list) and value:
   if all(isinstance(row,dict) for row in value):result+=table_html(title,value)
   elif all(isinstance(row,(str,int,float)) for row in value):result+=table_html(title,[{'value':row} for row in value])
 return result

def schema(kind,name,entry,url,image=None):
 obj={'@context':'https://schema.org','@type':'CollegeOrUniversity' if kind=='colleges' else 'Product','name':name,'url':url}
 if image:obj['image']=urljoin(url,image['src'])
 if kind=='colleges':
  obj['address']={'@type':'PostalAddress',**{k:entry[v] for k,v in [('addressCountry','country'),('addressRegion','region'),('addressLocality','city')] if entry.get(v)}}
  if entry.get('courses'):obj['hasCourse']=[{'@type':'Course','name':c.get('course','Programme'),'provider':{'@type':'CollegeOrUniversity','name':name},**({'url':c['source_url']} if c.get('source_url') else {})} for c in entry['courses'] if isinstance(c,dict)]
 elif entry.get('manufacturer'):obj['brand']={'@type':'Brand','name':entry['manufacturer']}
 obj['additionalProperty']=[{'@type':'PropertyValue','name':k.replace('_',' '),'value':v} for k,v in entry.items() if isinstance(v,(str,int,float)) and not isinstance(v,bool) and k not in ('source_url','official_url','evidence_url','audit_notes') and not k.endswith('_url')][:35]
 return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+'</script>'
