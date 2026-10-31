"""Original notice guides, safe links and bounded official-document fact extracts."""
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse, quote

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'content/official-notice-details.json'
e=lambda x:html.escape(str(x or ''),quote=True)
FIELDS={
 'dates':('Important dates','महत्वपूर्ण तारीखें',r'last date|closing date|opening date|exam(?:ination)? date|schedule|commenc'),
 'eligibility':('Eligibility & age','पात्रता और आयु सीमा',r'eligibility|qualification|age limit|years of age|degree|matriculation|12th|10th'),
 'vacancies':('Posts & vacancies','पद और रिक्तियां',r'vacanc|number of posts|pay level|pay scale'),
 'fees':('Application fee','आवेदन शुल्क',r'application fee|examination fee|fee payable|payment of fee'),
 'selection':('Selection process','चयन प्रक्रिया',r'selection process|computer.based|written exam|physical.*test|document verification|interview'),
}

def safe_link(url):
    p=urlparse(str(url));return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password

def inline(text):
    """Escape text, then render real HTTPS Markdown links and bare HTTPS URLs."""
    pattern=r'\[([^\]\n]+)\]\((https://[^\s<>]+?)\)|(https://[^\s<>\[\]]+)'
    parts=[];last=0
    for m in re.finditer(pattern,str(text)):
        parts.append(e(str(text)[last:m.start()]))
        label,url=(m[1],m[2]) if m[2] else (m[3],m[3])
        if not m[2]:url=url.rstrip('.,;');label=url
        if safe_link(url):parts.append('<a href="'+e(url)+'" target="_blank" rel="noopener noreferrer">'+e(label)+'</a>')
        else:parts.append(e(m[0]))
        last=m.end()
    parts.append(e(str(text)[last:]))
    value=''.join(parts)
    return re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',value)

def notice_id(row):
    return row.get('id') or hashlib.sha256((row['source']+row.get('en_title','')).encode()).hexdigest()[:16]
def notice_path(row,lang):return '/'+lang+'/exam-notice/'+notice_id(row)+'/'

def details_cache():
    try:return json.loads(CACHE.read_text())
    except (OSError,ValueError):return {}

def extract_facts(text):
    lines=[re.sub(r'\s+',' ',s).strip() for s in str(text).splitlines()]
    fields={};budget=85;seen=set()
    for key,(_,_,pattern) in FIELDS.items():
        matches=[]
        for index,line in enumerate(lines):
            if len(line)<15 or len(line)>450 or not re.search(pattern,line,re.I):continue
            if re.search(r'(?:from|on|as follows|:)\s*$',line,re.I) or (len(line.split())<=3 and not re.search(r'\d',line)):
                line=' '.join([line]+[v for v in lines[index+1:index+3] if v])
            if key=='dates' and not re.search(r'\d{1,2}[./-]\d{1,2}[./-](?:20)?\d{2}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',line,re.I):continue
            if key=='fees' and not re.search(r'\d|free|nil|exempt',line,re.I):continue
            if re.search(r'roll\s*(?:no|number)|candidate.?s? name|date of birth|@|password|captcha',line,re.I):continue
            if line in seen:continue
            words=line.split()
            if len(words)>budget or len(words)>55:continue
            matches.append(line);seen.add(line);budget-=len(words)
            if len(matches)==2:break
        if matches:fields[key]=matches
    return fields

def fetch_details(url):
    from official_notices import official_url
    import requests
    from bs4 import BeautifulSoup
    if not official_url(url):return {'status':'unavailable'}
    try:
        with requests.get(quote(url,safe=':/?=&%+#'),timeout=(6,12),stream=True) as r:
            r.raise_for_status()
            if not official_url(r.url):raise ValueError('Nonofficial redirect')
            chunks=[];size=0
            for chunk in r.iter_content(65536):
                size+=len(chunk)
                if size>8_000_000:raise ValueError('Document size limit')
                chunks.append(chunk)
            data=b''.join(chunks)
            if 'pdf' in r.headers.get('content-type','').lower() or urlparse(r.url).path.lower().endswith('.pdf'):
                from pypdf import PdfReader
                from io import BytesIO
                reader=PdfReader(BytesIO(data));text='\n'.join((reader.pages[i].extract_text() or '') for i in range(min(5,len(reader.pages))))
            else:
                soup=BeautifulSoup(data,'html.parser')
                for el in soup.select('script,style,header,footer,nav,form'):el.decompose()
                # Landing pages are resource links, not evidence for a specific notice.
                if urlparse(url).path in ('','/','/newlook/site/admit_card.html','/newlook/site/Whatsnew.html'):
                    return {'status':'board-only'}
                text=(soup.find('main') or soup.find('article') or soup).get_text('\n',strip=True)
            fields=extract_facts(text)
            return {'status':'extracted' if fields else 'no-readable-facts','fields':fields,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    except Exception as exc:return {'status':'unavailable','reason':type(exc).__name__}

def enrich(limit=24):
    from official_notices import load_notices
    import concurrent.futures
    cache=details_cache();sources=list(dict.fromkeys(r['source'] for r in load_notices()))
    def needs_refresh(url):
        entry=cache.get(url)
        if not entry or entry.get('schema_version')!=2:return True
        try:age=dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(entry.get('checked_at',''))
        except ValueError:return True
        return age.total_seconds()>86400
    # New documents first; older checks are refreshed daily rather than treated as permanent failures.
    pending=sorted((u for u in sources if needs_refresh(u)),key=lambda u:(u in cache,cache.get(u,{}).get('checked_at','')))[:limit]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for url,result in zip(pending,pool.map(fetch_details,pending)):
            result['schema_version']=2;result['checked_at']=dt.datetime.now(dt.timezone.utc).isoformat();cache[url]=result
    if pending:CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checked':len(pending),'documents':len(cache),'with_facts':sum(bool(x.get('fields')) for x in cache.values())}))

CSS='''
.exam-guide{border:1px solid #cbdbe9;border-radius:15px;padding:22px;margin:20px 0;background:#f7fbff}.exam-guide h2{margin-top:22px}.exam-table{width:100%;border-collapse:collapse;margin:18px 0;background:white}.exam-table th,.exam-table td{padding:13px;text-align:left;border:1px solid #cbdbe9;vertical-align:top;overflow-wrap:anywhere}.exam-table th{width:32%;background:#eaf3fa}.exam-actions{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}.exam-actions a{display:inline-block;padding:12px 16px;border-radius:9px;background:#145d8b;color:white!important;text-decoration:none;font-weight:700;overflow-wrap:anywhere}.exam-toc{display:flex;flex-wrap:wrap;gap:8px}.article .exam-toc a{color:#145d8b!important;background:white;padding:7px 10px;border:1px solid #bbcddd;border-radius:7px;text-decoration:none}.exam-missing{color:#5b6d80}.exam-guide blockquote{margin:12px 0;padding:12px 16px;border-left:3px solid #1d8e98;background:white;font-size:16px}.exam-guide p{overflow-wrap:anywhere}@media(max-width:600px){.exam-guide{padding:16px}.exam-table th,.exam-table td{padding:10px;font-size:14px}.exam-actions a{width:100%}}
'''

def official_actions(source,lang,label_override=None):
    from official_notices import official_url
    if not official_url(source):return ''
    label=('Download official notice (PDF)' if urlparse(source).path.lower().endswith('.pdf') else 'Open official notice / portal') if lang=='en' else ('आधिकारिक नोटिस PDF डाउनलोड करें' if urlparse(source).path.lower().endswith('.pdf') else 'आधिकारिक नोटिस / पोर्टल खोलें')
    if label_override:label=label_override
    return '<div class="exam-actions"><a href="'+e(source)+'" target="_blank" rel="noopener noreferrer">'+label+' ↗</a></div>'

def article_panel(post,lang):
    from news_hub import exam_bucket
    from news_config import EXAM_CATEGORIES,CATEGORIES
    from official_notices import official_url
    cat=exam_bucket(post)
    if cat not in EXAM_CATEGORIES:return ''
    ix=0 if lang=='en' else 1
    rows=[('Update type' if lang=='en' else 'अपडेट का प्रकार',CATEGORIES[cat][ix]),('Report date' if lang=='en' else 'रिपोर्ट की तारीख',str(post.get('date',''))[:10])]
    raw=post.get(lang+'_body') or post.get('en_body','')
    for key,(english,hindi,pattern) in FIELDS.items():
        hindi_patterns={'dates':'अंतिम तारीख|अंतिम तिथि|परीक्षा की तारीख|आवेदन शुरू','eligibility':'पात्रता|आयु सीमा|योग्यता','vacancies':'रिक्तियां|रिक्तियाँ|कुल पद|वेतन','fees':'आवेदन शुल्क|परीक्षा शुल्क','selection':'चयन प्रक्रिया|दस्तावेज सत्यापन'}
        lines=raw.splitlines();value=''
        for i,line in enumerate(lines):
            if not re.search(pattern+'|'+hindi_patterns[key],line,re.I):continue
            candidate=line
            if line.strip().startswith('#') and i+1<len(lines):candidate=' '.join(lines[i+1:i+3])
            candidate=re.sub(r'^[#* -]+','',candidate).strip()
            if len(candidate)>=15:
                value=candidate[:280];break
        rows.append((english if lang=='en' else hindi,value or ('Not specified in this report; verify the official notice.' if lang=='en' else 'इस रिपोर्ट में स्पष्ट विवरण उपलब्ध नहीं; आधिकारिक नोटिस जांचें।')))
    links=[]
    for url in re.findall(r'https://[^\s<>\]\)"\']+',raw):
        if official_url(url):links.append(url.rstrip('.,;'))
    if official_url(post.get('source','')):links.insert(0,post['source'])
    actions=''.join(official_actions(u,lang) for u in dict.fromkeys(links))
    note=('The report and its dated notice are below. An archived article does not confirm that applications, downloads or objections are still open. Use only the verified authority links; if a direct Apply link is not supplied, use the official portal.' if lang=='en' else 'नीचे विस्तृत रिपोर्ट और उसके नोटिस की जानकारी है। पुराने लेख का मौजूद होना आवेदन, डाउनलोड या आपत्ति विंडो के अभी खुले होने की पुष्टि नहीं है। दिए गए आधिकारिक लिंक से स्थिति जांचें; सीधा Apply लिंक उपलब्ध न हो तो आधिकारिक पोर्टल देखें।')
    return '<section class="exam-guide"><h2>'+('Quick details & official links' if lang=='en' else 'मुख्य विवरण और आधिकारिक लिंक')+'</h2><table class="exam-table">'+''.join('<tr><th scope="row">'+e(k)+'</th><td>'+e(v)+'</td></tr>' for k,v in rows)+'</table><p>'+note+'</p>'+actions+'</section>'

def render_notices(out,site,shell,write):
    from official_notices import load_notices
    from news_config import CATEGORIES
    cache=details_cache();notices=load_notices()
    for n in notices:
        for lang in ('en','hi'):
            en=lang=='en';ix=0 if en else 1;t=n.get(lang+'_title') or n['en_title'];url=site+notice_path(n,lang)
            labels=[('overview','Overview','संक्षिप्त जानकारी'),('dates','Important dates','महत्वपूर्ण तारीखें'),('eligibility','Eligibility & age','पात्रता और आयु'),('vacancies','Posts & vacancies','पद और रिक्तियां'),('fees','Application fee','आवेदन शुल्क'),('selection','Process & next steps','प्रक्रिया और अगले कदम'),('links','Important links','महत्वपूर्ण लिंक')]
            toc='<nav class="exam-toc" aria-label="'+('Contents' if en else 'विषय सूची')+'">'+''.join('<a href="#'+key+'">'+a[ix]+'</a>' for key,*a in labels)+'</nav>'
            authority=urlparse(n['source']).hostname
            rows=[('Authority / official website' if en else 'आधिकारिक वेबसाइट',authority),('Notice title' if en else 'नोटिस का शीर्षक',n['en_title']),('Notice listing date' if en else 'नोटिस की सूची में तारीख',n.get('date') or ('Not stated' if en else 'उपलब्ध नहीं')),('Update type' if en else 'अपडेट का प्रकार',CATEGORIES.get(n['category'],('Exam notice','परीक्षा नोटिस'))[ix])]
            intro=('This guide explains the official notice listed below and the steps for checking the relevant update. It is a notice-specific guide, not a fresh recruitment announcement unless the authority says so.' if en else 'इस पेज पर नीचे दिए गए आधिकारिक नोटिस की जानकारी और संबंधित अपडेट देखने की प्रक्रिया एक जगह दी गई है। केवल इस पेज के प्रकाशित होने से नई भर्ती या नया आवेदन शुरू होना नहीं माना जाना चाहिए।')
            intro += (' The listed subject is: ' if en else ' इस नोटिस का विषय है: ') + e(n['en_title'])
            sections='<section id="overview"><h2>'+('Notice overview' if en else 'नोटिस का विवरण')+'</h2><p>'+intro+'</p><table class="exam-table">'+''.join('<tr><th scope="row">'+e(k)+'</th><td>'+e(v)+'</td></tr>' for k,v in rows)+'</table></section>'
            details=cache.get(n['source'],{});fields=details.get('fields',{})
            for key,(english,hindi,_) in FIELDS.items():
                vals=fields.get(key,[])
                text=('Relevant lines from the official document (original language):' if en else 'आधिकारिक दस्तावेज की संबंधित पंक्तियां (मूल भाषा में):')
                body='<p>'+text+'</p>'+''.join('<blockquote>'+e(v)+'</blockquote>' for v in vals) if vals else '<p class="exam-missing">'+(({'dates':'The notice listing date is shown above; the actual exam/application deadline must be checked in the official notice.','eligibility':'Refer to the original recruitment advertisement for qualifications, age cut-off and relaxations.','vacancies':'Refer to the original advertisement and later vacancy amendments; this update does not confirm a fresh vacancy count.','fees':'Check the original advertisement and current official application portal. A result/admit-card notice does not imply a new application fee.','selection':'Match the examination stage in the notice and follow the authority’s instructions for the next step.'}[key] if en else {'dates':'सूची में नोटिस की तारीख ऊपर दी गई है। परीक्षा या आवेदन की वास्तविक अंतिम तारीख आधिकारिक नोटिस से जांचें।','eligibility':'योग्यता, आयु की कट-ऑफ तारीख और छूट के लिए मूल भर्ती विज्ञापन देखें।','vacancies':'पदों की संख्या और बदलाव मूल विज्ञापन तथा बाद के संशोधन से जांचें। इस अपडेट से नई रिक्तियों की पुष्टि नहीं होती।','fees':'मूल विज्ञापन और मौजूदा आधिकारिक आवेदन पोर्टल से शुल्क जांचें। रिजल्ट या एडमिट कार्ड अपडेट से नया आवेदन शुल्क लागू होना नहीं माना जाना चाहिए।','selection':'नोटिस में परीक्षा का चरण मिलाएं और अगले चरण के लिए प्राधिकरण के निर्देश पढ़ें।'}[key]))+'</p>'
                sections+='<section id="'+key+'"><h2>'+e(english if en else hindi)+'</h2>'+body+'</section>'
            steps=(['Open the official notice or portal using the link below and match the examination name and year.','Read all amendments and check whether this is an application, result, admit-card or schedule update.','For an application: use the authority’s Apply link, check eligibility, complete the form and keep the acknowledgement. For a result/admit card: use the relevant authority login or published document.','Keep registration credentials private. Do not enter them on this website.','Check the current deadline and follow later corrections from the issuing authority.'] if en else ['नीचे दिए आधिकारिक लिंक को खोलें और परीक्षा का नाम, वर्ष तथा नोटिस मिलाएं।','सभी संशोधन पढ़ें और देखें कि यह आवेदन, रिजल्ट, एडमिट कार्ड या परीक्षा कार्यक्रम का अपडेट है।','आवेदन के लिए प्राधिकरण का Apply लिंक खोलें, पात्रता जांचें और फॉर्म पूरा करके पावती रखें। रिजल्ट/एडमिट कार्ड के लिए संबंधित आधिकारिक लॉगिन या जारी दस्तावेज का उपयोग करें।','रजिस्ट्रेशन विवरण और पासवर्ड निजी रखें। इस वेबसाइट पर इन्हें दर्ज न करें।','मौजूदा अंतिम तारीख और बाद के संशोधन जारी करने वाले प्राधिकरण की वेबसाइट से जांचें।'])
            sections+='<section><h2>'+('How to check / apply / download' if en else 'कैसे देखें, आवेदन करें या डाउनलोड करें')+'</h2><ol>'+''.join('<li>'+s+'</li>' for s in steps)+'</ol></section>'
            status=('Archived / dated notice: current availability is not confirmed.' if en else 'पुराना / तारीख वाला नोटिस: मौजूदा उपलब्धता की पुष्टि नहीं है.') if n.get('date') and n['date']<dt.date.today().isoformat() else ('Check the official portal for current availability.' if en else 'मौजूदा उपलब्धता आधिकारिक पोर्टल पर जांचें।')
            links=official_actions(n['source'],lang)
            if n.get('source_index') and n['source_index']!=n['source']:links+=official_actions(n['source_index'],lang,'Official notice board' if en else 'आधिकारिक नोटिस बोर्ड')
            sections+='<section id="links"><h2>'+('Important official links' if en else 'महत्वपूर्ण आधिकारिक लिंक')+'</h2>'+links+'<p>'+('Only verified official destinations are linked. An Apply or Download button is not invented when its destination is unavailable.' if en else 'केवल सत्यापित आधिकारिक लिंक दिए गए हैं। सही लिंक न मिलने पर कोई काल्पनिक Apply या Download बटन नहीं जोड़ा गया है।')+'</p></section>'
            body='<div class="wrap"><article class="article"><a href="/'+lang+'/jobs-exams/">← '+('Jobs & Exams' if en else 'नौकरी और परीक्षा')+'</a><h1>'+e(t)+'</h1><p class="topic-note">'+status+'</p>'+toc+'<div class="exam-guide">'+sections+'</div><p>'+('Source' if en else 'स्रोत')+': '+e(authority)+'</p></article></div>'
            page=shell(lang,t+' | GlobeWire Daily',intro,url,body)
            if not fields:page=page.replace('content="index,follow,max-image-preview:large"','content="noindex,follow"')
            write(out/notice_path(n,lang).lstrip('/')/'index.html',page)
    return [notice_path(n,l) for n in notices if cache.get(n['source'],{}).get('fields') for l in ('en','hi')]

if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--merge':
        current=details_cache();incoming=json.loads(Path(sys.argv[2]).read_text())
        for key,value in incoming.items():
            if key not in current or value.get('checked_at','')>current[key].get('checked_at',''):current[key]=value
        CACHE.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
    else:enrich(int(sys.argv[1]) if len(sys.argv)>1 else 24)
