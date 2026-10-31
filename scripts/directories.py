"""Static, source-first directories. Facts are deliberately not invented."""
import html
from pathlib import Path

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
.directory-hero{padding:30px 0 12px}.directory-hero h1{font-size:clamp(30px,5vw,48px)}
.directory-controls{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}
.directory-controls input,.directory-controls select{font:inherit;padding:12px;border:1px solid #a7b7cb;border-radius:10px;background:#fff;min-width:180px;flex:1}
.directory-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:20px 0}
.directory-card{border:1px solid #d9e2ec;border-radius:14px;padding:20px;background:#fff;min-width:0}
.directory-card h2{font-size:21px;margin:0 0 9px}.directory-card p{line-height:1.6}
.directory-card a{font-weight:700}.directory-note{background:#eef6fa;border-left:4px solid #138a9a;padding:15px;margin:18px 0}
.directory-links{display:flex;gap:10px;flex-wrap:wrap}.directory-links a{border:1px solid #b8d1e5;border-radius:9px;padding:10px 12px}
@media(max-width:650px){.directory-grid{grid-template-columns:1fr}.directory-controls input,.directory-controls select{flex-basis:100%}}
"""
JS="""
document.querySelectorAll('[data-directory]').forEach(root=>{
 const search=root.querySelector('[data-search]'),country=root.querySelector('[data-country]'),region=root.querySelector('[data-region]'),city=root.querySelector('[data-city]'),count=root.querySelector('[data-count]');
 const cards=[...root.querySelectorAll('[data-item]')];
 function update(){
  const q=search.value.trim().toLocaleLowerCase();
  let shown=0;
  cards.forEach(card=>{
   const match=card.dataset.search.includes(q)&&(!country.value||card.dataset.country===country.value)&&(!region.value||card.dataset.region===region.value)&&(!city.value||card.dataset.city===city.value);
   card.hidden=!match;if(match)shown++;
  });
  count.textContent=shown+' results';
 }
 function options(select,field){
  const previous=select.value;
  const values=[...new Set(cards.filter(card=>(!country.value||card.dataset.country===country.value)&&(field==='city'?(!region.value||card.dataset.region===region.value):true)).map(card=>card.dataset[field]).filter(Boolean))].sort();
  select.innerHTML='<option value="">All '+field+'s</option>'+values.map(v=>'<option value="'+v.replaceAll('&','&amp;').replaceAll('"','&quot;')+'">'+v.replaceAll('&','&amp;').replaceAll('<','&lt;')+'</option>').join('');
  select.value=values.includes(previous)?previous:'';
 }
 if(country){country.addEventListener('change',()=>{options(region,'region');options(city,'city');update()});region.addEventListener('change',()=>{options(city,'city');update()});city.addEventListener('change',update)}
 search.addEventListener('input',update);update();
});
"""
def render(out,site,shell,write):
 for lang in ('en','hi'):
  ishi=lang=='hi'
  def tr(en,hi):return hi if ishi else en
  links='<div class="directory-links">'+''.join(f'<a href="/{lang}/{key}/">{esc(tr(label[0],label[1]))}</a>' for key,label in [('colleges',('Colleges','कॉलेज')),('courses',('Courses','कोर्स')),('cars',('Cars','कारें')),('phones',('Phones','फोन')),('bikes',('Bikes','बाइक'))])+'</div>'
  for kind,items in DATA.items():
   name={'colleges':('Worldwide College Finder','दुनियाभर के कॉलेज खोजें'),'cars':('Car Explorer','कार एक्सप्लोरर'),'phones':('Phone Explorer','फोन एक्सप्लोरर'),'bikes':('Bike Explorer','बाइक एक्सप्लोरर')}[kind]
   countries=sorted(set(row[1] for row in items))
   controls='<div class="directory-controls"><input data-search aria-label="Search" placeholder="'+esc(tr('Search names or programmes','नाम या कोर्स खोजें'))+'">'
   controls+='<select data-country aria-label="Country"><option value="">'+tr('All countries','सभी देश')+'</option>'+''.join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in countries)+'</select>'
   if kind=='colleges':
    controls+='<select data-region aria-label="State or region"><option value="">All regions</option></select><select data-city aria-label="City"><option value="">All cities</option></select>'
   controls+='</div><p data-count role="status"></p>'
   cards=[]
   for row in items:
    if kind=='colleges':
     n,c,r,city,url,area=row
     attrs=f'data-country="{esc(c)}" data-region="{esc(r)}" data-city="{esc(city)}"'
     detail=f'<p>{esc(c)} · {esc(r)} · {esc(city)}</p><p>{esc(area)}</p>'
    else:
     n,c,area,url=row;attrs=f'data-country="{esc(c)}"'
     detail=f'<p>{esc(c)} · {esc(area)}</p>'
    cards.append(f'<article class="directory-card" data-item {attrs} data-search="{esc((" ".join(row)).lower())}"><h2>{esc(n)}</h2>{detail}<p>{tr("Fees, eligibility, placement or product prices: verify with official source.","फीस, पात्रता, प्लेसमेंट या कीमत: आधिकारिक स्रोत से जाँचें।")}</p><a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{tr("Official website","आधिकारिक वेबसाइट")} ↗</a></article>')
   note=tr('Starter directory, not an exhaustive global database. We do not invent fees, admissions, placements, prices or specifications. Official sites are the source of truth.','यह शुरुआती डायरेक्टरी है, पूरी विश्व सूची नहीं। फीस, एडमिशन, प्लेसमेंट, कीमत या स्पेसिफिकेशन बिना सत्यापन के नहीं दिए जाते।')
   body=f'<div class="wrap"><section class="directory-hero"><h1>{esc(tr(*name))}</h1><p class="directory-note">{esc(note)}</p>{links}</section><section data-directory>{controls}<div class="directory-grid">{"".join(cards)}</div></section></div>'
   write(out/lang/kind/'index.html',shell(lang,tr(*name),note,site+'/'+lang+'/'+kind+'/',body))
  cards=''.join(f'<article class="directory-card"><h2>{esc(n)}</h2><p>{esc(d)}</p><p>{tr("Check duration, syllabus, entrance tests, fees and application deadlines on each university’s official course page.","अवधि, सिलेबस, प्रवेश परीक्षा, फीस और अंतिम तिथि विश्वविद्यालय की आधिकारिक साइट पर जाँचें।")}</p></article>' for n,d in COURSES)
  body=f'<div class="wrap"><section class="directory-hero"><h1>{tr("Worldwide Course Explorer","दुनियाभर के कोर्स")}</h1><p class="directory-note">{tr("Course admission requirements and licensing vary by institution and country.","कोर्स की पात्रता और लाइसेंसिंग देश व संस्थान के अनुसार बदलती है।")}</p>{links}</section><div class="directory-grid">{cards}</div></div>'
  write(out/lang/'courses'/'index.html',shell(lang,tr('Worldwide Course Explorer','दुनियाभर के कोर्स'),'Course guides and official admissions guidance',site+'/'+lang+'/courses/',body))
