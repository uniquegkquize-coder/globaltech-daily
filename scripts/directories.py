"""Static, source-first directories. Facts are deliberately not invented."""
import html
import json
import math
from pathlib import Path
from functools import lru_cache
from directory_facts import structured_html,media_html,meaningful,photo,schema

def esc(v): return html.escape(str(v),quote=True)
DATA={
 'colleges':[
  ('Indian Institute of Technology Delhi','India','Delhi','New Delhi','https://home.iitd.ac.in/','Engineering, science and research'),
  ('University of Delhi','India','Delhi','Delhi','https://www.du.ac.in/','Arts, commerce, science and professional studies'),
  ('University of Oxford','United Kingdom','England','Oxford','https://www.ox.ac.uk/','Undergraduate and postgraduate programmes'),
  ('Massachusetts Institute of Technology','United States','Massachusetts','Cambridge','https://www.mit.edu/','Engineering, science and technology'),
  ('University of Toronto','Canada','Ontario','Toronto','https://www.utoronto.ca/','Undergraduate and graduate programmes'),
  ('University of Melbourne','Australia','Victoria','Melbourne','https://www.unimelb.edu.au/','Undergraduate and graduate programmes')],
 'cars':[
  ('Toyota','Japan','Cars','https://global.toyota/en/'),
  ('Hyundai','South Korea','Cars and SUVs','https://www.hyundai.com/worldwide/en'),
  ('Tata Motors','India','Passenger vehicles','https://cars.tatamotors.com/')],
 'phones':[
  ('Apple iPhone','United States','Smartphones','https://www.apple.com/iphone/'),
  ('Samsung Galaxy','South Korea','Smartphones','https://www.samsung.com/global/galaxy/'),
  ('Google Pixel','United States','Smartphones','https://store.google.com/category/phones')],
 'bikes':[
  ('Honda Motorcycles','Japan','Motorcycles','https://global.honda/en/motorcycle/'),
  ('Royal Enfield','India','Motorcycles','https://www.royalenfield.com/'),
  ('Yamaha Motorcycles','Japan','Motorcycles','https://global.yamaha-motor.com/')]
}
# Additional official-source directory entries. No unverified fees or prices.
DATA['colleges'].extend([
 ('Indian Institute of Technology Bombay','India','Maharashtra','Mumbai','https://www.iitb.ac.in/','Engineering, science and research'),
 ('Indian Institute of Science','India','Karnataka','Bengaluru','https://iisc.ac.in/','Science, engineering and research'),
 ('Indian Institute of Technology Madras','India','Tamil Nadu','Chennai','https://www.iitm.ac.in/','Engineering, science and research'),
 ('Jawaharlal Nehru University','India','Delhi','New Delhi','https://www.jnu.ac.in/','Humanities, social sciences and research'),
 ('Banaras Hindu University','India','Uttar Pradesh','Varanasi','https://www.bhu.ac.in/','Arts, science, medicine and professional studies'),
 ('University of Lucknow','India','Uttar Pradesh','Lucknow','https://www.lkouniv.ac.in/','Arts, science, commerce and professional studies'),
 ('Harvard University','United States','Massachusetts','Cambridge','https://www.harvard.edu/','Undergraduate and graduate programmes'),
 ('Stanford University','United States','California','Stanford','https://www.stanford.edu/','Engineering, humanities, science and business'),
 ('University of California Berkeley','United States','California','Berkeley','https://www.berkeley.edu/','Undergraduate and graduate programmes'),
 ('University of Cambridge','United Kingdom','England','Cambridge','https://www.cam.ac.uk/','Undergraduate and postgraduate programmes'),
 ('Imperial College London','United Kingdom','England','London','https://www.imperial.ac.uk/','Science, engineering, medicine and business'),
 ('National University of Singapore','Singapore','Singapore','Singapore','https://www.nus.edu.sg/','Undergraduate and postgraduate programmes'),
 ('Nanyang Technological University','Singapore','Singapore','Singapore','https://www.ntu.edu.sg/','Engineering, science, business and humanities'),
 ('University of Tokyo','Japan','Tokyo','Tokyo','https://www.u-tokyo.ac.jp/en/','Undergraduate and graduate programmes'),
 ('ETH Zurich','Switzerland','Zurich','Zurich','https://ethz.ch/en.html','Science, technology and engineering'),
 ('Technical University of Munich','Germany','Bavaria','Munich','https://www.tum.de/en/','Engineering, science and management'),
 ('University of British Columbia','Canada','British Columbia','Vancouver','https://www.ubc.ca/','Undergraduate and graduate programmes'),
 ('University of Sydney','Australia','New South Wales','Sydney','https://www.sydney.edu.au/','Undergraduate and graduate programmes')
])
DATA['cars'].extend([
 ('Maruti Suzuki','India','Cars and SUVs','https://www.marutisuzuki.com/'),
 ('Mahindra Auto','India','SUVs and electric vehicles','https://auto.mahindra.com/'),
 ('Kia','South Korea','Cars and SUVs','https://www.kia.com/'),
 ('Honda Cars','Japan','Cars and SUVs','https://global.honda/en/automobiles/'),
 ('BMW','Germany','Cars and SUVs','https://www.bmw.com/'),
 ('Mercedes-Benz','Germany','Cars and SUVs','https://www.mercedes-benz.com/'),
 ('Volkswagen','Germany','Cars and SUVs','https://www.volkswagen.com/'),
 ('Ford','United States','Cars and trucks','https://www.ford.com/'),
 ('Tesla','United States','Electric vehicles','https://www.tesla.com/')
])
DATA['bikes'].extend([
 ('Bajaj Auto','India','Motorcycles','https://www.bajajauto.com/'),
 ('Hero MotoCorp','India','Motorcycles and scooters','https://www.heromotocorp.com/'),
 ('TVS Motor','India','Motorcycles and scooters','https://www.tvsmotor.com/'),
 ('KTM','Austria','Motorcycles','https://www.ktm.com/'),
 ('Kawasaki','Japan','Motorcycles','https://www.kawasaki.com/'),
 ('Suzuki Motorcycles','Japan','Motorcycles','https://www.globalsuzuki.com/motorcycle/'),
 ('Ducati','Italy','Motorcycles','https://www.ducati.com/'),
 ('Triumph Motorcycles','United Kingdom','Motorcycles','https://www.triumphmotorcycles.com/')
])
DATA['phones'].extend([
 ('OnePlus','China','Smartphones','https://www.oneplus.com/'),
 ('Xiaomi','China','Smartphones','https://www.mi.com/global/'),
 ('Motorola','United States','Smartphones','https://www.motorola.com/'),
 ('Nothing','United Kingdom','Smartphones','https://nothing.tech/'),
 ('OPPO','China','Smartphones','https://www.oppo.com/'),
 ('vivo','China','Smartphones','https://www.vivo.com/'),
 ('realme','China','Smartphones','https://www.realme.com/'),
 ('HONOR','China','Smartphones','https://www.honor.com/')
])
@lru_cache(maxsize=1)
def load_records():
 path=Path(__file__).resolve().parents[1]/'content'/'directory-records.json'
 try:
  records=json.loads(path.read_text(encoding='utf-8'))
  return records if isinstance(records,dict) else {}
 except (OSError,ValueError):return {}

def external_records(kind):
 records=load_records().get(kind,[])
 if not isinstance(records,list):return []
 return [r for r in records if isinstance(r,dict) and r.get('name') and r.get('source_url')]

COURSES=[
 ('B.Tech / Engineering','Physics, mathematics and institution-specific entrance requirements; check official admission rules.'),
 ('MBBS / Medicine','Medical entrance, prerequisite subjects and country-specific medical licensing requirements.'),
 ('MBA / Management','Bachelor degree and sometimes entrance tests, work experience or interviews.'),
 ('BCA / Computer Applications','Secondary-school qualifications; mathematics requirements differ by institution.'),
 ('B.Pharm / Pharmacy','Science prerequisites, entrance rules and pharmacy council recognition vary by country.'),
 ('Nursing','Science prerequisites, clinical training, licensing and language requirements vary by country.'),
 ('Law','Undergraduate or graduate entry routes depend on jurisdiction and institution.'),
 ('Diploma / Vocational','Entry qualification and duration depend on the programme and accreditor.')]
CSS="""
.directory-wide{grid-column:1/-1}.directory-table-wrap{overflow-x:auto}.directory-card table{width:100%;border-collapse:collapse;font-size:14px}.directory-card th,.directory-card td{border-bottom:1px solid #d9e2ec;padding:10px;vertical-align:top;text-align:left;overflow-wrap:anywhere}.directory-media{margin:0 0 18px}.directory-media img{display:block;width:100%;height:auto;max-height:480px;object-fit:contain;background:#edf2f7;border-radius:12px}.directory-media figcaption{font-size:12px;color:#4b6076;margin-top:5px}.directory-card .directory-media img{aspect-ratio:16/9}

.directory-hero{padding:30px 0 12px}.directory-hero h1{font-size:clamp(30px,5vw,48px)}
.directory-controls{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}
.directory-controls input,.directory-controls select{font:inherit;padding:12px;border:1px solid #a7b7cb;border-radius:10px;background:#fff;min-width:180px;flex:1}
.directory-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:20px 0}
.directory-card[hidden]{display:none!important}\n.directory-card{border:1px solid #d9e2ec;border-radius:14px;padding:20px;background:#fff;min-width:0}
.directory-card h2{font-size:21px;margin:0 0 9px}.directory-card p{line-height:1.6}
.directory-card a{font-weight:700}.directory-note{background:#eef6fa;border-left:4px solid #138a9a;padding:15px;margin:18px 0}
.directory-links{display:flex;gap:10px;flex-wrap:wrap}.directory-links a{border:1px solid #b8d1e5;border-radius:9px;padding:10px 12px}
@media(max-width:650px){.directory-grid{grid-template-columns:1fr}.directory-controls input,.directory-controls select{flex-basis:100%}}
"""
JS="""

document.querySelectorAll('[data-directory-index]').forEach(root=>{
 const input=root.querySelector('[data-search]'),country=root.querySelector('[data-country]'),region=root.querySelector('[data-region]'),city=root.querySelector('[data-city]');
 const grid=root.querySelector('.directory-grid'),status=root.querySelector('[data-count]');
 const originalGrid=grid.innerHTML,originalStatus=status.textContent,staticPages=root.querySelector('[data-directory-pages]');
 const hi=root.dataset.language==='hi',size=48;let indexPromise,page=1,revision=0,timer;
 const pages=document.createElement('nav');pages.className='directory-links';pages.setAttribute('aria-label',hi?'खोज परिणाम पेज':'Search result pages');root.append(pages);
 function load(){if(!indexPromise)indexPromise=fetch(root.dataset.directoryIndex).then(r=>{if(!r.ok)throw Error('index');return r.json()}).catch(e=>{indexPromise=null;throw e});return indexPromise}
 function options(select,field,rows){if(!select)return;const old=select.value;select.replaceChildren(new Option(hi?'सभी':'All '+field+'s',''));[...new Set(rows.map(r=>r[field]).filter(Boolean))].sort().forEach(v=>select.add(new Option(v,v)));select.value=[...select.options].some(o=>o.value===old)?old:''}
 async function update(reset=true){const current=++revision;if(reset)page=1;
  if(!input.value.trim()&&!country?.value&&!region?.value&&!city?.value){grid.innerHTML=originalGrid;status.textContent=originalStatus;pages.replaceChildren();if(staticPages)staticPages.hidden=false;return}
  status.textContent=hi?'खोज रहे हैं…':'Searching…';
  try {const all=await load();if(current!==revision)return;
   const regional=all.filter(r=>!country?.value||r.country===country.value);options(region,'region',regional);options(city,'city',regional.filter(r=>!region?.value||r.region===region.value));
   const q=input.value.trim().toLocaleLowerCase(),rows=all.filter(r=>(r.name+' '+r.area+' '+r.country+' '+r.region+' '+r.city).toLocaleLowerCase().includes(q)&&(!country?.value||r.country===country.value)&&(!region?.value||r.region===region.value)&&(!city?.value||r.city===city.value));
   const total=Math.max(1,Math.ceil(rows.length/size));page=Math.min(page,total);grid.replaceChildren();pages.replaceChildren();if(staticPages)staticPages.hidden=true;
   rows.slice((page-1)*size,page*size).forEach(r=>{const card=document.createElement('article');card.className='directory-card';const h=document.createElement('h2'),a=document.createElement('a'),p=document.createElement('p');a.href=r.path;a.textContent=r.name;h.append(a);p.textContent=[r.country,r.region,r.city,r.area].filter(Boolean).join(' · ');card.append(h,p);grid.append(card)});
   status.textContent=hi?rows.length+' परिणाम · पेज '+page+'/'+total:rows.length+' results · page '+page+'/'+total;
   [[hi?'पिछला':'Previous',page-1],[hi?'अगला':'Next',page+1]].forEach(([label,target])=>{if(target<1||target>total)return;const b=document.createElement('button');b.type='button';b.textContent=label;b.addEventListener('click',()=>{page=target;update(false)});pages.append(b)});
  }catch(e){if(current===revision)status.textContent=hi?'खोज उपलब्ध नहीं है। नीचे दिए पेज लिंक से देखें।':'Search is unavailable. Browse using the page links below.'}
 }
 input.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>update(),180)});
 [country,region,city].filter(Boolean).forEach(select=>select.addEventListener('change',()=>update()));
 [region,city].filter(Boolean).forEach(select=>select.addEventListener('focus',async()=>{try{const rows=(await load()).filter(r=>(!country?.value||r.country===country.value)&&(!region?.value||select===region||r.region===region.value));options(select,select===region?'region':'city',rows)}catch(e){} }));
});

document.querySelectorAll('[data-directory]:not([data-directory-index])').forEach(root=>{
 const search=root.querySelector('[data-search]'),country=root.querySelector('[data-country]'),region=root.querySelector('[data-region]'),city=root.querySelector('[data-city]'),count=root.querySelector('[data-count]');
 const cards=[...root.querySelectorAll('[data-item]')];
 function update(){
  const q=search.value.trim().toLocaleLowerCase();
  let shown=0;
  cards.forEach(card=>{
   const match=card.dataset.search.includes(q)&&(!country||!country.value||card.dataset.country===country.value)&&(!region||!region.value||card.dataset.region===region.value)&&(!city||!city.value||card.dataset.city===city.value);
   card.hidden=!match;if(match)shown++;
  });
  count.textContent=shown+' results';
 }
 function options(select,field){
  const previous=select.value;
  const values=[...new Set(cards.filter(card=>(!country||!country.value||card.dataset.country===country.value)&&(field==='city'?(!region||!region.value||card.dataset.region===region.value):true)).map(card=>card.dataset[field]).filter(Boolean))].sort();
  select.innerHTML='<option value="">All '+field+'s</option>'+values.map(v=>'<option value="'+v.replaceAll('&','&amp;').replaceAll('"','&quot;')+'">'+v.replaceAll('&','&amp;').replaceAll('<','&lt;')+'</option>').join('');
  select.value=values.includes(previous)?previous:'';
 }
 if(country){country.addEventListener('change',()=>{if(region)options(region,'region');if(city)options(city,'city');update()});}\n if(region){region.addEventListener('change',()=>{if(city)options(city,'city');update()});options(region,'region');}\n if(city){city.addEventListener('change',update);options(city,'city');}
 search.addEventListener('input',update);update();
});
"""
def entry_slug(name):
 import re
 return re.sub(r'[^a-z0-9]+','-',name.lower().replace('+',' plus ')).strip('-')

@lru_cache(maxsize=1)
def detailed_profiles():
 path=Path(__file__).resolve().parents[1]/'content'/'directory-details.json'
 try:return json.loads(path.read_text(encoding='utf-8'))
 except (OSError,ValueError):return {}

def record_detail(kind,name,lang):
 records=external_records(kind)
 record=next((r for r in records if r.get('name','').casefold()==name.casefold()),None)
 if not record:return ''
 fields={'country':('Country','देश'),'introduced':('Introduced / established','शुरुआत / स्थापना'),'manufacturer':('Manufacturer','निर्माता'),'operator':('Operator','संचालक'),'location':('Location','स्थान'),'mass':('Mass (Wikidata units)','वजन (Wikidata इकाई)'),'height':('Height (Wikidata units)','ऊँचाई (Wikidata इकाई)'),'width':('Width (Wikidata units)','चौड़ाई (Wikidata इकाई)'),'length':('Length (Wikidata units)','लंबाई (Wikidata इकाई)'),'retrieved_at':('Last sourced','स्रोत अपडेट')}
 rows=''.join('<tr><th>'+esc(label[1] if lang=='hi' else label[0])+'</th><td>'+esc(record[key])+'</td></tr>' for key,label in fields.items() if record.get(key))
 source=record.get('source_url','')
 if not rows:return ''
 return '<section class="directory-card"><h2>'+('उपलब्ध डेटा' if lang=='hi' else 'Available sourced specifications')+'</h2><table class="directory-specs">'+rows+'</table><p><a href="'+esc(source)+'" target="_blank" rel="noopener noreferrer">Wikidata source record</a></p></section>'

def extra_detail(kind,name,lang):
 details=detailed_profiles().get(kind,{}).get(name,{})
 if not details:return ''
 labels={'price':('Price','कीमत'),'engine':('Engine','इंजन'),'power':('Power','पावर'),'torque':('Torque','टॉर्क'),'mileage':('Mileage','माइलेज'),'weight':('Weight','वजन'),'display':('Display','डिस्प्ले'),'processor':('Processor','प्रोसेसर'),'battery':('Battery','बैटरी'),'storage':('Storage','स्टोरेज'),'ram':('RAM','रैम'),'rear_camera':('Rear cameras','रियर कैमरे'),'front_camera':('Front cameras','फ्रंट कैमरे'),'fees':('Fees','फीस'),'placement':('Placement','प्लेसमेंट'),'admissions':('Admissions','प्रवेश'),'accreditation':('Accreditation','मान्यता')}
 rows=[]
 for k,v in details.items():
  if k in ('source_url','official_url','evidence_url','field_sources','audit_notes','reviewed_fields','image_source_url','source_image_url') or isinstance(v,(dict,list,bool)):continue
  label=labels.get(k,(k.replace('_',' ').title(),k.replace('_',' ').title()))
  provenance=details.get('field_sources',{}).get(k,{})
  evidence=provenance.get('url','') if isinstance(provenance,dict) else ''
  citation=(' <a class="fact-source" href="'+esc(evidence)+'" target="_blank" rel="noopener noreferrer">'+('स्रोत' if lang=='hi' else 'Source')+'</a>') if evidence.startswith(('https://','http://')) else ''
  if k in ('price','fees','mrp_inr','secondary_selling_price_inr') and isinstance(provenance,dict) and provenance.get('retrieved_at'):
   citation+=' <small>'+('जाँच: ' if lang=='hi' else 'Checked: ')+esc(str(provenance['retrieved_at'])[:10])+'</small>'
  rows.append('<tr><th>'+esc(label[1] if lang=='hi' else label[0])+'</th><td>'+esc(v)+citation+'</td></tr>')
 sources=''.join('<a target="_blank" rel="noopener noreferrer" href="'+esc(details[k])+'">'+('Source reference' if k=='source_url' else 'Manufacturer / institution')+'</a> ' for k in ('source_url','official_url') if details.get(k))
 return '<section class="directory-card directory-wide"><h2>'+('विस्तृत जानकारी' if lang=='hi' else 'Detailed specifications and information')+'</h2><table class="directory-specs">'+''.join(rows)+'</table><p>'+sources+'</p><small>'+('कीमतें और जानकारी स्रोत की तारीख के अनुसार बदल सकती हैं।' if lang=='hi' else 'Prices and specifications may change by market and date.')+'</small></section>'+structured_html(details,lang)

def entry_detail(kind,row,lang,out=None):
 ishi=lang=='hi'
 def tr(en,hi):return hi if ishi else en
 if kind=='colleges':
  name,country,region,city,url,area=row
  facts=[('Country / देश',country),('State / राज्य',region),('City / शहर',city),('Study areas / अध्ययन क्षेत्र',area)]
  sections=[
   ('Courses and eligibility','कोर्स और पात्रता','Check the institution\'s programme catalogue for exact degree names, subject prerequisites, entry tests, language requirements and deadlines.','सटीक डिग्री, विषय पात्रता, प्रवेश परीक्षा, भाषा आवश्यकताएँ और अंतिम तारीख संस्थान के आधिकारिक कोर्स कैटलॉग से जाँचें।'),
   ('Fees and scholarships','फीस और छात्रवृत्ति','Fees vary by course, academic year and domestic/international student status. Verify tuition, housing, financial aid and scholarships with admissions.','फीस कोर्स, वर्ष और घरेलू/विदेशी छात्र के अनुसार बदलती है। ट्यूशन, हॉस्टल और छात्रवृत्ति एडमिशन कार्यालय से जाँचें।'),
   ('Admissions process','प्रवेश प्रक्रिया','Choose a programme, verify requirements, prepare transcripts and test scores, apply through the official admissions portal and monitor the decision.','कोर्स चुनें, पात्रता जाँचें, अंकपत्र और परीक्षा स्कोर तैयार करें, आधिकारिक पोर्टल पर आवेदन करें और परिणाम देखें।'),
   ('Placements and outcomes','प्लेसमेंट और परिणाम','Request the latest official career report, programme-level employment outcomes, median salary methodology and internship details. Unverified placement percentages are not published.','नवीनतम आधिकारिक करियर रिपोर्ट, कोर्सवार रोजगार आँकड़े, वेतन की गणना और इंटर्नशिप देखें। अप्रमाणित प्लेसमेंट प्रतिशत प्रकाशित नहीं किए जाते।')]
 else:
  name,country,area,url=row
  facts=[('Country / देश',country),('Category / श्रेणी',area)]
  if kind=='cars':
   sections=[('Models and variants','मॉडल और वेरिएंट','Check the manufacturer\'s current model range, trims, launch status and market availability.','निर्माता की मौजूदा मॉडल सूची, वेरिएंट, लॉन्च स्थिति और बाजार में उपलब्धता देखें।'),('Price, mileage and safety','कीमत, माइलेज और सुरक्षा','Compare official ex-showroom/MSRP pricing, certified efficiency, crash-test ratings, warranties and local taxes. Prices vary by market and date.','आधिकारिक कीमत, प्रमाणित माइलेज, क्रैश टेस्ट, वारंटी और स्थानीय टैक्स की तुलना करें।')]
  elif kind=='bikes':
   sections=[('Models and engine specifications','मॉडल और इंजन स्पेसिफिकेशन','Compare official engine displacement, power, torque, weight, seat height, ABS and transmission by model and market.','मॉडल के अनुसार इंजन, पावर, टॉर्क, वजन, सीट की ऊँचाई, ABS और गियरबॉक्स देखें।'),('Price, efficiency and ownership','कीमत, माइलेज और रखरखाव','Verify local prices, certified fuel economy or range, service intervals, warranty and dealer availability.','स्थानीय कीमत, माइलेज या रेंज, सर्विस अंतराल, वारंटी और डीलर उपलब्धता जाँचें।')]
  else:
   sections=[('Models and specifications','मॉडल और स्पेसिफिकेशन','Compare official display, chipset, RAM, storage, cameras, battery, charging and software update policy for each phone model.','हर फोन मॉडल की डिस्प्ले, चिपसेट, RAM, स्टोरेज, कैमरा, बैटरी, चार्जिंग और अपडेट नीति देखें।'),('Pricing and availability','कीमत और उपलब्धता','Verify current country-specific official prices, release dates, regional variants and warranty conditions.','देश के अनुसार आधिकारिक कीमत, रिलीज तारीख, क्षेत्रीय वेरिएंट और वारंटी जाँचें।')]
 facts_html=''.join('<li><strong>'+esc(k)+':</strong> '+esc(v)+'</li>' for k,v in facts)
 sections_html=extra_detail(kind,name,lang)+record_detail(kind,name,lang)+('' if meaningful(detailed_profiles().get(kind,{}).get(name,{})) else ''.join('<section class="directory-card"><h2>'+esc(tr(en,hi))+'</h2><p>'+esc(tr(desc_en,desc_hi))+'</p></section>' for en,hi,desc_en,desc_hi in sections))
 note=tr('Source-listed reference profile. Prices, fees and availability depend on the market, programme, version and source date.','स्रोत आधारित विवरण। कीमत, फीस और उपलब्धता बाजार, कोर्स, वर्जन और स्रोत की तारीख पर निर्भर हैं।')
 return '<div class="wrap">'+(media_html(kind,name,out) if out else '')+'<section class="directory-hero"><h1>'+esc(name)+'</h1><p class="directory-note">'+esc(note)+'</p><ul>'+facts_html+'</ul><p><a href="'+esc(url)+'" rel="noopener noreferrer" target="_blank">'+tr('Open source','स्रोत खोलें')+'</a></p></section><div class="directory-grid">'+sections_html+'</div><p><a href="/'+lang+'/'+kind+'/">'+tr('Back to directory','डायरेक्टरी पर वापस')+'</a></p></div>'

PAGE_SIZE = 48


def listing_path(lang, kind, page=1):
 return f'/{lang}/{kind}/' if page == 1 else f'/{lang}/{kind}/page/{page}/'


def pagination(lang, kind, page, total):
 if total <= 1:return ''
 pages = sorted({1, total, *range(max(1, page-2), min(total, page+2)+1)})
 links = []
 if page > 1:links.append(f'<a rel="prev" href="{listing_path(lang,kind,page-1)}">'+('पिछला' if lang=='hi' else 'Previous')+'</a>')
 for n in pages:
  links.append(f'<span aria-current="page">{n}</span>' if n==page else f'<a href="{listing_path(lang,kind,n)}">{n}</a>')
 if page < total:links.append(f'<a rel="next" href="{listing_path(lang,kind,page+1)}">'+('अगला' if lang=='hi' else 'Next')+'</a>')
 return '<nav class="directory-links" data-directory-pages aria-label="'+('डायरेक्टरी पेज' if lang=='hi' else 'Directory pages')+'">'+' '.join(links)+'</nav>'


def render(out,site,shell,write):
 for lang in ('en','hi'):
  ishi=lang=='hi'
  def tr(en,hi):return hi if ishi else en
  links='<div class="directory-links">'+''.join(f'<a href="/{lang}/{key}/">{esc(tr(label[0],label[1]))}</a>' for key,label in [('colleges',('Colleges','कॉलेज')),('courses',('Courses','कोर्स')),('cars',('Cars','कारें')),('phones',('Phones','फोन')),('bikes',('Bikes','बाइक'))])+'</div>'
  for kind,base_items in DATA.items():
   items=list(base_items)
   existing={row[0].casefold() for row in items}
   for profile_name,profile in detailed_profiles().get(kind,{}).items():
    if profile_name.casefold() in existing:continue
    existing.add(profile_name.casefold())
    url=profile.get('official_url') or profile.get('source_url','#')
    country=profile.get('country') or 'Worldwide'
    if kind=='colleges':items.append((profile_name,country,profile.get('region') or '—',profile.get('city') or '—',url,profile.get('programmes') or 'University'))
    else:items.append((profile_name,country,'Detailed product profile',url))
   for record in external_records(kind):
    name=record['name'].strip()
    if name.casefold() in existing:continue
    existing.add(name.casefold())
    url=record.get('official_url') or record['source_url']
    country=record.get('country') or 'Worldwide'
    if kind=='colleges':items.append((name,country,record.get('region') or '—',record.get('city') or '—',url,'University / college'))
    else:items.append((name,country,'Historic / current model',url))
   name={'colleges':('Worldwide College Finder','दुनियाभर के कॉलेज खोजें'),'cars':('Car Explorer','कार एक्सप्लोरर'),'phones':('Phone Explorer','फोन एक्सप्लोरर'),'bikes':('Bike Explorer','बाइक एक्सप्लोरर')}[kind]
   countries=sorted(set(row[1] for row in items))
   controls='<div class="directory-controls"><input data-search aria-label="Search" placeholder="'+esc(tr('Search names or programmes','नाम या कोर्स खोजें'))+'">'
   controls+='<select data-country aria-label="Country"><option value="">'+tr('All countries','सभी देश')+'</option>'+''.join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in countries)+'</select>'
   if kind=='colleges':
    controls+='<select data-region aria-label="State or region"><option value="">All regions</option></select><select data-city aria-label="City"><option value="">All cities</option></select>'
   controls+='</div><p data-count role="status"></p>'
   cards=[]
   search_rows=[]
   seen_slugs=set()
   for row in items:
    profile_slug=entry_slug(row[0])
    if profile_slug in seen_slugs:continue
    seen_slugs.add(profile_slug)
    if kind=='colleges':
     n,c,r,city,url,area=row
     attrs=f'data-country="{esc(c)}" data-region="{esc(r)}" data-city="{esc(city)}"'
     detail=f'<p>{esc(c)} · {esc(r)} · {esc(city)}</p><p>{esc(area)}</p>'
    else:
     n,c,area,url=row;attrs=f'data-country="{esc(c)}"'
     detail=f'<p>{esc(c)} · {esc(area)}</p>'
    search_rows.append({'name':n,'country':c,'region':r if kind=='colleges' else '',
                        'city':city if kind=='colleges' else '', 'area':area,
                        'path':f'/{lang}/{kind}/{entry_slug(n)}/'})
    thumbnail=media_html(kind,n,out) if n in detailed_profiles().get(kind,{}) else ''
    cards.append(f'<article class="directory-card" data-item {attrs} data-search="{esc((" ".join(row)).lower())}">{thumbnail}<h2><a href="/{lang}/{kind}/{entry_slug(n)}/">{esc(n)}</a></h2>{detail}<p>{tr("Verify course eligibility, current fees and admissions with the institution." if kind=="colleges" else "Check model, market, specifications and current price with the manufacturer.","कोर्स की पात्रता, वर्तमान फीस और प्रवेश संस्थान से जाँचें।" if kind=="colleges" else "मॉडल, बाजार, स्पेसिफिकेशन और वर्तमान कीमत निर्माता से जाँचें।")}</p><a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{tr("Source website","स्रोत वेबसाइट")} ↗</a></article>')
    detail_url=site+'/'+lang+'/'+kind+'/'+entry_slug(n)+'/'
    entry=detailed_profiles().get(kind,{}).get(n,{})
    desc=(n+' — '+{'colleges':'courses, admissions, eligibility and fee references','cars':'car specifications, variants and price references','phones':'phone specifications, display, battery and price references','bikes':'bike specifications, engine, mileage and price references'}[kind]+'. Read source-linked details where available.') if lang=='en' else n+' की '+{'colleges':'कोर्स, प्रवेश, पात्रता और फीस','cars':'कार स्पेसिफिकेशन, वेरिएंट और कीमत','phones':'फोन स्पेसिफिकेशन, डिस्प्ले, बैटरी और कीमत','bikes':'बाइक स्पेसिफिकेशन, इंजन, माइलेज और कीमत'}[kind]+' की स्रोत सहित उपलब्ध जानकारी देखें।'
    seo_title=n+(' — '+{'colleges':'Courses, Fees & Admissions','cars':'Specs & Price References','phones':'Specs, Features & Price References','bikes':'Specs, Mileage & Price References'}[kind] if lang=='en' else ' — '+{'colleges':'कोर्स, फीस और प्रवेश','cars':'स्पेसिफिकेशन और कीमत की जानकारी','phones':'फीचर्स, स्पेसिफिकेशन और कीमत','bikes':'स्पेसिफिकेशन, माइलेज और कीमत'}[kind])
    page=shell(lang,seo_title,desc,detail_url,entry_detail(kind,row,lang,out))
    if meaningful(entry):page=page.replace('</head>',schema(kind,n,entry,detail_url,photo(kind,n,out))+'</head>')
    else:page=page.replace('content="index,follow,max-image-preview:large"','content="noindex,follow,max-image-preview:large"')
    write(out/lang/kind/entry_slug(n)/'index.html',page)
   note=tr('Browse source-linked '+kind+' profiles. '+('Check courses, fees and admission dates with each institution.' if kind=='colleges' else 'Check regional models, specifications and dated prices with the manufacturer.'), 'स्रोत सहित '+{'colleges':'कॉलेज','cars':'कार','phones':'फोन','bikes':'बाइक'}[kind]+' की जानकारी देखें। '+('कोर्स, फीस और प्रवेश की तारीख संस्थान से जाँचें।' if kind=='colleges' else 'क्षेत्रीय मॉडल, स्पेसिफिकेशन और तारीख वाली कीमत निर्माता से जाँचें।'))
   write(out/lang/kind/'search.json',json.dumps(search_rows,ensure_ascii=False,separators=(',',':')))
   total=max(1,math.ceil(len(cards)/PAGE_SIZE))
   for page in range(1,total+1):
    first=(page-1)*PAGE_SIZE; last=min(first+PAGE_SIZE,len(cards))
    count=tr(f'Showing {first+1 if cards else 0}–{last} of {len(cards)} entries. Search covers all entries.',f'कुल {len(cards)} में से {first+1 if cards else 0}–{last} प्रविष्टियाँ। खोज सभी प्रविष्टियों में होगी।')
    page_controls=controls.replace('<p data-count role="status"></p>','<p data-count role="status">'+esc(count)+'</p>')
    body=f'<div class="wrap"><section class="directory-hero"><h1>{esc(tr(*name))}</h1><p class="directory-note">{esc(note)}</p>{links}</section><section data-directory data-directory-index="/{lang}/{kind}/search.json" data-language="{lang}">{page_controls}<div class="directory-grid">{"".join(cards[first:last])}</div>{pagination(lang,kind,page,total)}</section></div>'
    heading=tr(*name)+(tr(f' — Page {page}',f' — पेज {page}') if page>1 else '')
    write(out/listing_path(lang,kind,page).lstrip('/')/'index.html',shell(lang,heading,note+tr(f' Page {page}.',f' पेज {page}।'),site+listing_path(lang,kind,page),body))
  cards=[]
  for n,d in COURSES:
   slugname=entry_slug(n)
   url=site+'/'+lang+'/courses/'+slugname+'/'
   desc=tr('Explore entry requirements, programme duration, accreditation, application deadlines and career pathways. Exact criteria vary by institution and country.','प्रवेश पात्रता, अवधि, मान्यता, आवेदन तिथि और करियर विकल्प देखें। सटीक नियम कॉलेज और देश के अनुसार अलग हैं।')
   detail=f'<div class="wrap"><section class="directory-hero"><h1>{esc(n)}</h1><p>{esc(d)}</p></section><div class="directory-grid"><section class="directory-card"><h2>{tr("Eligibility and admission","पात्रता और प्रवेश")}</h2><p>{esc(desc)}</p></section><section class="directory-card"><h2>{tr("Fees and scholarships","फीस और छात्रवृत्ति")}</h2><p>{tr("Confirm the current fees, funding and scholarships on each university’s official programme page.","वर्तमान फीस और छात्रवृत्ति कॉलेज की आधिकारिक कोर्स साइट पर जाँचें।")}</p></section><section class="directory-card"><h2>{tr("Career and licensing","करियर और लाइसेंसिंग")}</h2><p>{tr("Check accreditation, professional licensing and programme-level employment outcomes before applying.","आवेदन से पहले मान्यता, लाइसेंसिंग और कोर्सवार रोजगार परिणाम जाँचें।")}</p></section></div><p><a href="/{lang}/colleges/">{tr("Find colleges","कॉलेज खोजें")}</a></p></div>'
   write(out/lang/'courses'/slugname/'index.html',shell(lang,n,d,url,detail))
   cards.append(f'<article class="directory-card" data-item data-search="{esc((n+" "+d).lower())}"><h2><a href="/{lang}/courses/{slugname}/">{esc(n)}</a></h2><p>{esc(d)}</p></article>')
  body=f'<div class="wrap"><section class="directory-hero"><h1>{tr("Worldwide Course Explorer","दुनियाभर के कोर्स")}</h1><p class="directory-note">{tr("Course admission requirements and licensing vary by institution and country.","कोर्स की पात्रता और लाइसेंसिंग देश व संस्थान के अनुसार बदलती है।")}</p>{links}</section><section data-directory><div class="directory-controls"><input data-search aria-label="Search courses" placeholder="{tr("Search courses","कोर्स खोजें")}"></div><p data-count role="status"></p><div class="directory-grid">{"".join(cards)}</div></section></div>'
  write(out/lang/'courses'/'index.html',shell(lang,tr('Worldwide Course Explorer','दुनियाभर के कोर्स'),'Course guides and official admissions guidance',site+'/'+lang+'/courses/',body))
 add_profile_sitemap(out,site)


def add_profile_sitemap(out,site):
 import xml.etree.ElementTree as ET
 path=Path(out)/'sitemap.xml'
 if not path.exists():return
 ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
 root=ET.fromstring(path.read_text());existing={n.text for n in root.iter('{'+ns+'}loc')}
 for kind,entries in detailed_profiles().items():
  for name,entry in entries.items():
   if not meaningful(entry):continue
   for lang in ('en','hi'):
    url=site+'/'+lang+'/'+kind+'/'+entry_slug(name)+'/'
    if url not in existing:
     node=ET.SubElement(root,'{'+ns+'}url');ET.SubElement(node,'{'+ns+'}loc').text=url;existing.add(url)
 path.write_text(ET.tostring(root,encoding='unicode'))
