"""Accessible bilingual jobs/exams and all-news directories."""
import datetime as dt
import html
import json
import re
from pathlib import Path
from news_config import CATEGORIES, EXAM_CATEGORIES, OFFICIAL_LINKS, memberships, classify, PRIORITY, timestamp

e=lambda x:html.escape(str(x),quote=True)
HUB_CSS='''
.hub-hero{margin:30px 0 20px;padding:32px;border-radius:20px;background:#0c2240;color:white}.hub-hero h1{font-size:clamp(28px,4vw,46px);margin:10px 0}.hub-hero p{max-width:75ch;color:#d8e8f8}.hub-topics{display:flex;flex-wrap:wrap;gap:9px;margin:16px 0}.hub-topics a{padding:8px 12px;border:1px solid #ccd9e8;border-radius:9px;background:white;color:#173659;text-decoration:none;font-weight:650;font-size:14px}.hub-search{display:block;width:100%;max-width:700px;padding:14px 16px;font:inherit;border:1px solid #adbfd4;border-radius:10px;background:white;color:#17243b}.hub-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;align-items:start;margin:25px 0}.hub-section{background:white;border:1px solid #d5e1ed;border-radius:14px;overflow:hidden;min-width:0}.hub-section h2{font-size:21px;margin:0;padding:16px 18px;background:#14385d;color:white}.hub-section ul{list-style:none;padding:0 18px;margin:0}.hub-item{padding:14px 0;border-bottom:1px solid #e3eaf2}.hub-item a{font-weight:650;line-height:1.5;text-decoration:none;display:block;overflow-wrap:anywhere}.hub-item time{font-size:12px;color:#63758b;display:block;margin-top:5px}.hub-section .view-all{display:block;padding:15px 18px;font-weight:700}.hub-empty{padding:18px;color:#5c6c81}.hub-announcement{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}.hub-announcement a{padding:16px;background:#e9f5f8;border:1px solid #c6e0e8;border-radius:12px;color:#12415b;text-decoration:none;font-weight:700}.hub-news-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 24px;background:white;border:1px solid #d5e1ed;border-radius:15px;padding:12px 22px;list-style:none}.hub-status{font-size:14px;color:#5b6f87}.hub-links{padding:22px;background:#edf4fa;border-radius:15px;margin:26px 0}.hub-home{margin:25px 0}.hub-home h2{margin-bottom:12px}.hub-pill{font-size:12px;font-weight:700;color:#097478;background:#e3f6f4;padding:3px 7px;border-radius:5px;display:inline-block;margin-top:6px}@media(max-width:950px){.hub-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hub-announcement{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.hub-hero{padding:22px 18px}.hub-grid,.hub-news-list{grid-template-columns:1fr}.hub-announcement{gap:8px}.hub-announcement a{padding:12px;font-size:14px}.hub-grid{gap:15px}.hub-topics a{font-size:13px}}
'''
HUB_JS='''document.querySelectorAll('[data-news-search]').forEach(input=>{input.addEventListener('input',()=>{let q=input.value.trim().toLocaleLowerCase();let scope=input.closest('[data-news-hub]');let rows=scope.querySelectorAll('[data-search-text]');let count=0;rows.forEach(row=>{let match=row.dataset.searchText.toLocaleLowerCase().includes(q);row.hidden=!match;if(match)count++;});let status=scope.querySelector('[data-search-status]');if(status)status.textContent=scope.dataset.searchLanguage==='hi'?`${count} खबरें मिलीं`:`${count} matching updates`;});});'''

def news_sort(post):
    # Publication time is the primary signal. Topic preference only breaks ties.
    return (-timestamp(post.get('source_published_at') or post.get('date')),-max(PRIORITY.get(c,4) for c in memberships(post)),post.get('id',''))

def recent_priority(posts,limit=8,now=None):
    now=now or dt.datetime.now(dt.timezone.utc).timestamp()
    recent=[p for p in posts if 0<=now-timestamp(p.get('source_published_at') or p.get('date'))<=172800]
    return sorted(recent,key=lambda p:(int((now-timestamp(p.get('source_published_at') or p.get('date')))//21600),-max(PRIORITY.get(c,4) for c in memberships(p)),-timestamp(p.get('source_published_at') or p.get('date'))))[:limit]

def exam_bucket(post):
    text=post.get('en_title','')+' '+post.get('hi_title','')
    bucket=classify(text,post.get('category','technology'))
    if bucket=='sarkari-naukri':
        if re.search(r'holiday|current affairs|alleged|paper.?leak|prosecution|says|cautions|hiring report',text,re.I):return None
        if not re.search(r'recruitment|vacanc|application|apply|apprentice|internship|hiring|भर्ती|आवेदन|पदों',text,re.I):return None
    return bucket

def matches_category(post,cat):
    return exam_bucket(post)==cat if cat in EXAM_CATEGORIES else cat in memberships(post)

def official_notice_rows(cat,lang):
    notices=json.loads((Path(__file__).resolve().parents[1]/'content/official-exam-notices.json').read_text())
    rows=[]
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).date()
    for notice in notices:
        if notice['category']!=cat or not 0<=(today-dt.date.fromisoformat(notice['date'])).days<=14:continue
        text=notice[lang+'_title']
        rows.append('<li class="hub-item" data-search-text="'+e(text)+'"><a href="'+e(notice['source'])+'" target="_blank" rel="noopener noreferrer">'+e(text)+' ↗</a><time>'+e(notice['date'])+'</time><span class="hub-pill">'+('Official notice board' if lang=='en' else 'आधिकारिक नोटिस बोर्ड')+'</span></li>')
    return ''.join(rows)

def hub_link(lang,slug,label):
    return '<a href="/'+lang+'/'+slug+'/">'+e(label)+'</a>'

def render_hubs(out,site,posts,shell,article_path,title,write):
    posts=sorted(posts,key=news_sort)
    notices=json.loads((Path(__file__).resolve().parents[1]/'content/official-exam-notices.json').read_text())
    for lang in ('en','hi'):
        ix=0 if lang=='en' else 1
        name='Jobs & Exam Updates' if lang=='en' else 'नौकरी और परीक्षा अपडेट'
        intro='Latest jobs, results, admit cards, answer keys and admissions in one place. This is an independent news hub, not a government website.' if lang=='en' else 'नई नौकरियां, रिजल्ट, एडमिट कार्ड, आंसर की और एडमिशन की जानकारी एक जगह। यह स्वतंत्र समाचार हब है, सरकारी वेबसाइट नहीं।'
        generated=dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).strftime('%d %b %Y, %I:%M %p IST')
        def item(p):
            text=title(p,lang);date=p.get('date','')[:10]
            return '<li class="hub-item" data-search-text="'+e(text)+'"><a href="'+article_path(p,lang)+'">'+e(text)+'</a><time datetime="'+e(p.get('date',''))+'">'+e(date)+'</time></li>'
        def section(cat,label=None):
            selected=[p for p in posts if exam_bucket(p)==cat][:18]
            rows=''.join(item(p) for p in selected)
            rows=official_notice_rows(cat,lang)+rows
            empty='No published updates here yet. Check the official links below.' if lang=='en' else 'इस श्रेणी में अभी प्रकाशित अपडेट नहीं हैं। नीचे आधिकारिक लिंक देखें।'
            return '<section class="hub-section"><h2>'+e(label or CATEGORIES[cat][ix])+'</h2><ul>'+rows+'</ul>'+('' if rows else '<p class="hub-empty">'+empty+'</p>')+hub_link(lang,cat,'View all →' if lang=='en' else 'सभी देखें →').replace('<a ','<a class="view-all" ',1)+'</section>'
        sections=[('results',None),('admit-cards',None),('sarkari-naukri',None),('answer-keys',None),('syllabus',None),('admissions',None),('scholarships',None),('private-vacancy',None),('government-schemes',None)]
        quick=''.join(hub_link(lang,c,CATEGORIES[c][ix]) for c in ['sarkari-naukri','results','admit-cards','answer-keys','syllabus','admissions','scholarships','private-vacancy'])
        official=''.join('<a href="'+u+'" target="_blank" rel="noopener noreferrer">'+e(n)+' ↗</a>' for n,u in OFFICIAL_LINKS)
        highlights=''.join('<a href="'+article_path(p,lang)+'">'+e(title(p,lang))+'</a>' for p in [p for p in posts if exam_bucket(p) in EXAM_CATEGORIES][:8])
        notice='Check application dates, eligibility and fees in the original notice. Listing a report does not mean applications are still open.' if lang=='en' else 'आवेदन की तारीख, पात्रता और फीस मूल नोटिस से जांचें। किसी खबर के यहां होने का मतलब आवेदन अभी खुले होना नहीं है।'
        search_label='Search jobs, exams and updates' if lang=='en' else 'नौकरी, परीक्षा या अपडेट खोजें'
        body='<div class="wrap" data-news-hub data-search-language="'+lang+'"><section class="hub-hero"><div class="eyebrow">GLOBEWIRE DAILY</div><h1>'+name+'</h1><p>'+intro+'</p><label for="jobs-search">'+search_label+'</label><input class="hub-search" id="jobs-search" type="search" data-news-search placeholder="SSC, UPSC, Railway, PET…"></section><p class="hub-status">'+('Page refreshed: ' if lang=='en' else 'पेज अपडेट: ')+generated+'</p><nav class="hub-topics" aria-label="Exam sections">'+quick+'</nav><p>'+notice+'</p><div class="hub-announcement">'+highlights+'</div><p role="status" aria-live="polite" data-search-status></p><div class="hub-grid">'+''.join(section(c,n) for c,n in sections)+'</div><section class="hub-links"><h2>'+('Official websites' if lang=='en' else 'आधिकारिक वेबसाइटें')+'</h2><div class="hub-topics">'+official+'</div></section></div>'
        write(out/lang/'jobs-exams'/'index.html',shell(lang,name+' | GlobeWire Daily',intro,site+'/'+lang+'/jobs-exams/',body))
        label='All Latest News' if lang=='en' else 'सभी ताज़ा खबरें'
        nav=''.join(hub_link(lang,c,n[ix]) for c,n in CATEGORIES.items())
        rows=''.join(item(p) for p in posts)
        body='<div class="wrap" data-news-hub data-search-language="'+lang+'"><section class="hub-hero"><h1>'+label+'</h1><p>'+('Newest published reports first, across every category.' if lang=='en' else 'सभी श्रेणियों की प्रकाशित खबरें, सबसे नई पहले।')+'</p><label for="all-news-search">'+search_label+'</label><input id="all-news-search" class="hub-search" type="search" data-news-search placeholder="Jio, SSC, AI…"></section><div class="hub-topics">'+hub_link(lang,'jobs-exams',name)+nav+'</div><p role="status" aria-live="polite" data-search-status></p><ul class="hub-news-list">'+rows+'</ul></div>'
        write(out/lang/'all-news'/'index.html',shell(lang,label+' | GlobeWire Daily',label,site+'/'+lang+'/all-news/',body))
