"""Reusable reference resources built only from existing sourced records."""
import html
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def esc(v): return html.escape(str(v),quote=True)
def link(url,label):
 return '<a href="'+esc(url)+'">'+esc(label)+'</a>' if str(url).startswith(('https://','http://','/')) else esc(label)
def value(v):
 if isinstance(v,(list,dict)): return esc(json.dumps(v,ensure_ascii=False))
 return esc(v or '—')

def directory_rows(kind):
 details=json.loads((ROOT/'content/directory-details.json').read_text()).get(kind,{})
 rows=[]
 for name,r in sorted(details.items()):
  source=r.get('source_url') or r.get('official_url')
  if not source: continue
  checked=r.get('checked_at') or r.get('retrieved_at') or 'Not recorded'
  if kind=='colleges':
   for c in r.get('courses',[]):
    if not c.get('source_url'): continue
    rows.append([name,c.get('course',''),c.get('eligibility',''),c.get('annual_fee_inr','Not listed'),c.get('fee_basis',''),link(c['source_url'],'Source'),c.get('checked_at',checked)])
  elif kind in ('cars','bikes'):
   rows.append([name,r.get('model_version',''),r.get('powertrain') or r.get('engine',''),r.get('transmission',''),r.get('mileage','Not listed'),link(source,'Source'),checked])
  else:
   rows.append([name,r.get('model_version',''),r.get('processor') or r.get('chipset',''),r.get('display',''),r.get('battery',''),link(source,'Source'),checked])
 return rows

STYLE='''<style>.ref-table{overflow:auto;max-height:65vh;border:1px solid #cbd5e1;margin:20px 0}.ref-table table{border-collapse:collapse;min-width:760px;width:100%;font-size:15px}.ref-table th,.ref-table td{border:1px solid #cbd5e1;padding:12px;vertical-align:top;max-width:340px;overflow-wrap:anywhere}.ref-table th{position:sticky;top:0;background:#edf2f7;color:#122040}.ref-filter{padding:12px;width:min(100%,520px);margin:12px 0}.ref-check{display:block;white-space:nowrap}.ref-note{padding:16px;border-left:4px solid #007c91;background:#f1f7fa}</style>'''
SCRIPT='''<script>document.querySelectorAll('[data-reference]').forEach(section=>{const input=section.querySelector('input[type=search]'), compare=section.querySelector('input[type=checkbox][data-compare]'), rows=[...section.querySelectorAll('tbody tr')];const update=()=>rows.forEach(r=>{r.hidden=!r.textContent.toLowerCase().includes(input.value.toLowerCase())||(compare.checked&&!r.querySelector('input').checked)});input.addEventListener('input',update);section.addEventListener('change',update)})</script>'''

def table(headers,rows,lang):
 th=''.join('<th scope="col">'+esc(h)+'</th>' for h in ['Select' if lang=='en' else 'चुनें']+headers)
 body=''
 for i,row in enumerate(rows):
  cells=''.join('<td>'+str(cell)+'</td>' for cell in row)
  body+=f'<tr><td><input type="checkbox" aria-label="Select row {i+1}"></td>{cells}</tr>'
 return f'''<section data-reference><label>{'Filter by model, course or topic' if lang=='en' else 'मॉडल, कोर्स या विषय खोजें'}<br><input class="ref-filter" type="search"></label><label class="ref-check"><input type="checkbox" data-compare> {'Show selected rows only' if lang=='en' else 'केवल चुनी हुई पंक्तियाँ दिखाएँ'}</label><div class="ref-table"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div></section>'''

def render(out,site,posts,shell,article_path,title,write):
 notices=json.loads((ROOT/'content/official-exam-notices.json').read_text())
 for lang in ('en','hi'):
  hi=lang=='hi'; pages=[]
  for kind,en,hn,headers in [
   ('colleges','College admission and fee comparison','कॉलेज एडमिशन और फीस तुलना',['Institution','Course','Eligibility','Annual fee (INR)','Fee basis','Citation','Record checked']),
   ('cars','Car specification comparison','कार स्पेसिफिकेशन तुलना',['Model','Version / market','Powertrain','Transmission','Mileage basis','Citation','Record checked']),
   ('bikes','Motorcycle specification comparison','बाइक स्पेसिफिकेशन तुलना',['Model','Version / market','Engine','Transmission','Mileage basis','Citation','Record checked']),
   ('phones','Mobile specification database','मोबाइल स्पेसिफिकेशन डेटाबेस',['Model','Version / market','Processor','Display','Battery','Citation','Record checked'])]:
   rows=directory_rows(kind)
   # Escape plain text; only the explicit citation cell contains generated markup.
   rows=[[cell if idx==5 else value(cell) for idx,cell in enumerate(row)] for row in rows]
   pages.append((kind,hn if hi else en,headers,rows,
    'रिकॉर्ड में दी गई जानकारी की तुलना करें। खाली विवरण उपलब्ध नहीं है। फीस, मॉडल वर्ष, बाजार और वेरिएंट के आधार की जाँच स्रोत से करें; ये मौजूदा कोटेशन नहीं हैं।' if hi else 'Compare recorded information, not live offers. Missing values are not estimated. Check model year, market, variant and fee basis at the cited source; these records are not current quotations.'))
  rows=[[esc(n.get('date','')),esc(n.get(lang+'_title','')),esc(n.get('category','')),link(n.get('source',''),'Official notice')] for n in sorted(notices,key=lambda r:r.get('date',''),reverse=True)]
  pages.append(('exams','सरकारी परीक्षा नोटिफिकेशन ट्रैकर' if hi else 'Government exam notification tracker',['Record date','Notification','Type','Primary source'],rows,'संग्रहित नोटिस की सूची है; तारीख आवेदन की अंतिम तिथि नहीं है। आवेदन से पहले आधिकारिक PDF पढ़ें।' if hi else 'This lists stored notices. Record dates are not application deadlines. Read the official notification and amendments before applying.'))
  tools=[('ChatGPT','General writing and coding','https://chatgpt.com/'),('Gemini','Multimodal assistant','https://gemini.google.com/'),('NotebookLM','Research using supplied source material','https://notebooklm.google.com/'),('Hugging Face','Model and dataset exploration','https://huggingface.co/'),('Canva','Visual design','https://www.canva.com/')]
  pages.append(('ai-tools','AI टूल तुलना: काम के आधार पर चयन' if hi else 'AI tool comparison by task',['Tool','Task to evaluate','Official product'],[[esc(n),esc(t),link(u,'Product')] for n,t,u in tools],'अपना एक ही उदाहरण सभी टूल्स में आजमाएँ। तथ्य, स्रोत, गोपनीयता और निर्यात की जाँच करें। कोई बेंचमार्क, रेटिंग या असीमित फ्री उपयोग का दावा नहीं है।' if hi else 'Try the same task in each suitable tool. Check factual accuracy, source traceability, privacy controls and export formats. This is a task-based shortlist, not a benchmark, rating or claim of unlimited free use.'))
  defence=[p for p in posts if p.get('category') in ('defence','defence-news','world-news','international-news','conflict-news','military-tech')]
  defence.sort(key=lambda p:str(p.get('published_at') or p.get('date') or ''),reverse=True)
  rows=[[esc(p.get('published_at') or p.get('date') or 'Not recorded'),link(article_path(p,lang),title(p,lang)),link(p.get('source',''),'Coverage source')] for p in defence[:80]]
  pages.append(('defence-timeline','अंतरराष्ट्रीय रक्षा कवरेज टाइमलाइन' if hi else 'International defence coverage timeline',['Publication timestamp','Coverage','Source'],rows,'यह प्रकाशन क्रम है, घटनाओं की प्रमाणित तारीखों की टाइमलाइन नहीं। किसी घटना की तारीख को प्रकाशन समय से नहीं निकाला गया है।' if hi else 'This is a publication timeline, not an independently verified chronology of event dates. Publication timestamps are never substituted for event dates.'))
  index_links=[]
  for slug,heading,headers,rows,note in pages:
   url=f'{site}/{lang}/resources/{slug}/'
   schema={'@context':'https://schema.org','@type':'CollectionPage','name':heading,'url':url,'inLanguage':lang,'description':note}
   extra='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')+'</script>'
   body=STYLE+'<div class="wrap"><article class="article"><p>'+link(f'/{lang}/resources/','Resources / संदर्भ')+'</p><h1>'+esc(heading)+'</h1><p class="ref-note">'+esc(note)+'</p><h2>'+('How to compare' if not hi else 'तुलना कैसे करें')+'</h2><p>'+('Filter the records, select two or more rows, then show selected rows. Compare like-for-like fields and read each source before making a decision. Different fee bases and model variants cannot be compared as equal.' if not hi else 'रिकॉर्ड खोजें, दो या अधिक पंक्तियाँ चुनें और केवल चुनी पंक्तियाँ देखें। एक जैसे आधार पर तुलना करें और निर्णय से पहले प्रत्येक स्रोत पढ़ें। अलग फीस आधार या मॉडल वेरिएंट को समान न मानें।')+'</p>'+table(headers,rows,lang)+f'<p>{link(f"/{lang}/"+("tools" if slug=="ai-tools" else "jobs-exams" if slug=="exams" else "world-news" if slug=="defence-timeline" else slug)+"/", "Explore related coverage / संबंधित विवरण")}</p></article></div>'+SCRIPT
   write(out/lang/f'resources/{slug}/index.html',shell(lang,heading,note,url,body,extra))
   index_links.append('<li>'+link(url,heading)+'</li>')
  heading='संदर्भ और तुलना' if hi else 'Reference resources and comparisons'
  body=STYLE+'<div class="wrap"><article class="article"><h1>'+heading+'</h1><p>'+('स्रोत सहित रिकॉर्ड खोजें और तुलना करें।' if hi else 'Search and compare sourced records. Sources and record dates help you check the basis before deciding.')+'</p><ul>'+''.join(index_links)+'</ul></article></div>'
  write(out/lang/'resources/index.html',shell(lang,heading,heading,site+'/'+lang+'/resources/',body))
