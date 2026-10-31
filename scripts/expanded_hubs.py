"""International topic hubs, practical guides and an honest notice archive."""
import datetime as dt
import html,json,re
from pathlib import Path
from news_config import CATEGORIES,EXAM_CATEGORIES,memberships
from news_hub import news_sort,exam_bucket
from official_notices import load_notices
from notice_details import notice_path
from verticals import unconfirmed_story

e=lambda x:html.escape(str(x or ''),quote=True)
CSS='''
.topic-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin:24px 0}.topic-box{background:white;border:1px solid #d6e1ee;border-radius:15px;padding:22px;min-width:0}.topic-box h2{font-size:23px;margin-top:0}.topic-box ul{padding-left:20px}.topic-box li{margin:10px 0}.topic-box a{overflow-wrap:anywhere}.topic-note{border-left:4px solid #168b92;background:#edf8fa;padding:15px 19px;margin:18px 0;border-radius:8px}.detail-label{display:inline-block;background:#fff0cf;color:#634700;font-weight:700;padding:6px 10px;border-radius:7px;margin:10px 0}.filter-row{display:flex;gap:12px;align-items:end;flex-wrap:wrap;margin:18px 0}.filter-row label{display:block;font-weight:650}.filter-row input,.filter-row select{padding:12px;border:1px solid #b5c7d9;border-radius:8px;font:inherit;background:white;max-width:100%}.topic-box .more{font-weight:750;display:block;margin-top:18px}.archive-note{color:#61718a;font-size:13px}.study-steps{counter-reset:steps}.study-steps li{margin:12px 0;line-height:1.7}@media(max-width:950px){.topic-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.topic-grid{grid-template-columns:1fr}.topic-box{padding:19px}.filter-row input{width:100%}}
'''
JS='''document.querySelectorAll('[data-archive-filter]').forEach(root=>{let input=root.querySelector('input'),select=root.querySelector('select'),status=root.querySelector('[role="status"]');function run(){let q=input.value.toLocaleLowerCase(),year=select.value,n=0;root.querySelectorAll('[data-archive-row]').forEach(row=>{let show=row.dataset.searchText.toLocaleLowerCase().includes(q)&&(!year||row.dataset.year===year);row.hidden=!show;if(show)n++;});status.textContent=root.dataset.lang==='hi'?`${n} रिकॉर्ड मिले`:`${n} records found`;}input.addEventListener('input',run);select.addEventListener('change',run);});'''
GROUPS={
 'launches':['car-launches','mobile-launches','movie-releases','ev-clean-energy'],
 'global-topics':['cricket','celebrity-news','entertainment-rumours','controversies','social-media','defence','conflict-news','military-tech','tourism','travel-packages','study-abroad','visas-immigration','space-news'],
 'freebies-deals':['freebies','deals-offers','travel-packages'],
}
TITLES={
 'launches':('Launches, Prices & Specifications','लॉन्च, कीमत और स्पेसिफिकेशन'),
 'global-topics':('Global News & Useful Topics','दुनियाभर की खबरें और उपयोगी विषय'),
 'freebies-deals':('Freebies, Discounts & Travel Deals','फ्रीबीज़, डिस्काउंट और ट्रैवल डील्स'),
}
RESOURCE_LINKS={
 'freebies-deals':[('Epic Games','https://store.epicgames.com/'),('GOG','https://www.gog.com/'),('Intrepid travel deals','https://www.intrepidtravel.com/en/travel-deals')],
 'launches':[('Samsung Newsroom','https://news.samsung.com/global/'),('Toyota Newsroom','https://global.toyota/en/newsroom/')],
 'global-topics':[('ICC Cricket','https://www.icc-cricket.com/news'),('TikTok Newsroom','https://newsroom.tiktok.com/'),('Instagram / Meta','https://about.fb.com/news/')],
}

def article_note(post,lang):
    text=post.get('en_title','')+' '+post.get('hi_title','')
    if post.get('category')=='entertainment-rumours' or unconfirmed_story(text):
        return '<p class="detail-label">'+('Reported / unconfirmed — see source and confirmation status.' if lang=='en' else 'रिपोर्टेड / अपुष्ट — स्रोत और पुष्टि की स्थिति देखें।')+'</p>'
    if memberships(post)&{'freebies','deals-offers','travel-packages'}:
        return '<p class="topic-note">'+('Dated offer report. Availability, eligibility and final costs must be checked on the merchant’s website.' if lang=='en' else 'यह तारीख सहित ऑफर की रिपोर्ट है। उपलब्धता, पात्रता और अंतिम खर्च स्टोर/ऑपरेटर की वेबसाइट पर जांचें।')+'</p>'
    return ''

def render_expanded_hubs(out,site,posts,shell,path,title,write):
    posts=sorted(posts,key=news_sort)
    for lang in ('en','hi'):
        ix=0 if lang=='en' else 1
        def row(p):return '<li class="hub-item"><a href="'+path(p,lang)+'">'+e(title(p,lang))+'</a><time>'+e(p.get('source_published_at') or p.get('date'))[:10]+'</time></li>'
        def chips(cats):return '<div class="hub-topics">'+''.join('<a href="/'+lang+'/'+c+'/">'+e(CATEGORIES[c][ix])+'</a>' for c in cats)+'</div>'
        for slug,cats in GROUPS.items():
            heading=TITLES[slug][ix]
            intro=('International coverage, newest reports first. Dates, prices and availability are market-specific.' if lang=='en' else 'अंतरराष्ट्रीय कवरेज में नई रिपोर्ट पहले। तारीख, कीमत और उपलब्धता संबंधित देश व बाजार के अनुसार देखें।')
            cards=[]
            for cat in cats:
                selected=[p for p in posts if cat in memberships(p)][:7]
                items=''.join(row(p) for p in selected)
                if not items:items='<li class="hub-empty">'+('No published report in this topic yet.' if lang=='en' else 'इस विषय में अभी कोई प्रकाशित रिपोर्ट नहीं है।')+'</li>'
                cards.append('<section class="hub-section"><h2>'+e(CATEGORIES[cat][ix])+'</h2><ul>'+items+'</ul><a class="view-all" href="/'+lang+'/'+cat+'/">'+('View all →' if lang=='en' else 'सभी देखें →')+'</a></section>')
            note=''
            if slug=='launches':note='Manufacturer-claimed mileage/range and independent test results are different. Prices must include country, currency and variant.' if lang=='en' else 'कंपनी का बताया माइलेज/रेंज और स्वतंत्र टेस्ट के परिणाम अलग हैं। कीमत के साथ देश, मुद्रा और वेरिएंट देखें।'
            if slug=='freebies-deals':note='These are published offer reports, not a live stock checker. Check offer dates, country, shipping, membership requirements and auto-renewal terms at the merchant.' if lang=='en' else 'ये प्रकाशित ऑफर रिपोर्ट हैं, लाइव स्टॉक की गारंटी नहीं। देश, तारीख, शिपिंग खर्च, सदस्यता और ऑटो-रिन्यूअल की शर्तें स्टोर पर जांचें।'
            resources='<div class="hub-topics">'+''.join('<a href="'+u+'" rel="noopener noreferrer" target="_blank">'+e(n)+' ↗</a>' for n,u in RESOURCE_LINKS[slug])+'</div>'
            body='<div class="wrap"><section class="hub-hero"><h1>'+heading+'</h1><p>'+intro+'</p></section>'+chips(cats)+('<p class="topic-note">'+note+'</p>' if note else '')+'<div class="hub-grid">'+''.join(cards)+'</div><section class="hub-links"><h2>'+('Official resources' if lang=='en' else 'आधिकारिक जानकारी')+'</h2>'+resources+'</section></div>'
            write(out/lang/slug/'index.html',shell(lang,heading+' | GlobeWire Daily',intro,site+'/'+lang+'/'+slug+'/',body))
        # Process guide: no invented fees, immigration guarantees or institution-wide rules.
        heading='Study Abroad: Planning & Official Resources' if lang=='en' else 'विदेश में पढ़ाई: तैयारी और आधिकारिक जानकारी'
        steps=(['Choose a country, course and recognised institution; check course-specific entry requirements.','Plan tuition, living expenses and funding using the institution’s current published information.','Prepare transcripts, required test results and application documents; verify the intake deadline.','Apply through the institution’s official portal and keep the offer and payment records.','Check the destination government’s current student-visa instructions, then plan housing, insurance and travel.'] if lang=='en' else ['देश, कोर्स और मान्यता प्राप्त संस्थान चुनें; उसी कोर्स की प्रवेश शर्तें जांचें।','संस्थान की मौजूदा जानकारी से ट्यूशन फीस, रहने का खर्च और फंडिंग की योजना बनाएं।','मार्कशीट, जरूरी टेस्ट और आवेदन दस्तावेज तैयार करें; चुने हुए इंटेक की अंतिम तारीख जांचें।','संस्थान के आधिकारिक पोर्टल से आवेदन करें और ऑफर व भुगतान के रिकॉर्ड रखें।','संबंधित देश की मौजूदा छात्र वीजा प्रक्रिया जांचें, फिर आवास, बीमा और यात्रा की तैयारी करें।'])
        countries=[('USA / अमेरिका','https://educationusa.state.gov/your-5-steps-us-study'),('UK / यूनाइटेड किंगडम','https://www.gov.uk/study-uk-student-visa'),('Australia / ऑस्ट्रेलिया','https://www.studyaustralia.gov.au/en/plan-your-move/visa-application-process'),('Germany / जर्मनी','https://www.daad.de/en/')]
        countrycards=''.join('<section class="topic-box"><h2>'+n+'</h2><p>'+('Use the official guide for current institution, application and visa information.' if lang=='en' else 'संस्थान, आवेदन और वीजा की ताजा जानकारी के लिए आधिकारिक गाइड देखें।')+'</p><a href="'+u+'" target="_blank" rel="noopener noreferrer">'+('Official guide ↗' if lang=='en' else 'आधिकारिक गाइड ↗')+'</a></section>' for n,u in countries)
        body='<div class="wrap"><section class="hub-hero"><h1>'+heading+'</h1><p>'+('A general planning checklist; exact requirements vary by course, institution and nationality.' if lang=='en' else 'यह तैयारी की सामान्य चेकलिस्ट है। वास्तविक शर्तें कोर्स, संस्थान और नागरिकता के अनुसार बदलती हैं।')+'</p></section>'+chips(['study-abroad','scholarships','admissions','visas-immigration'])+'<section class="topic-box"><h2>'+('Plan your application' if lang=='en' else 'आवेदन की तैयारी')+'</h2><ol class="study-steps">'+''.join('<li>'+e(s)+'</li>' for s in steps)+'</ol></section><div class="topic-grid">'+countrycards+'</div></div>'
        write(out/lang/'study-abroad-guide/index.html',shell(lang,heading+' | GlobeWire Daily',heading,site+'/'+lang+'/study-abroad-guide/',body))
        heading='Jobs & Exam Notice Archive' if lang=='en' else 'नौकरी और परीक्षा नोटिस का आर्काइव'
        records=[]
        for p in posts:
            if exam_bucket(p) in EXAM_CATEGORIES:records.append({'text':title(p,lang),'date':p.get('date','')[:10],'url':path(p,lang),'official':False})
        for n in load_notices():records.append({'text':n.get(lang+'_title') or n['en_title'],'date':n.get('date') or '', 'url':notice_path(n,lang),'official':False})
        records.sort(key=lambda x:x['date'],reverse=True)
        years=sorted({r['date'][:4] for r in records if r['date']},reverse=True)
        items=''.join('<li class="hub-item" data-archive-row data-year="'+e(r['date'][:4])+'" data-search-text="'+e(r['text'])+'"><a href="'+e(r['url'])+'"'+(' target="_blank" rel="noopener noreferrer"' if r['official'] else '')+'>'+e(r['text'])+(' ↗' if r['official'] else '')+'</a><time>'+e(r['date'] or ('Date not stated' if lang=='en' else 'तारीख उपलब्ध नहीं'))+'</time><span class="archive-note">'+('Official document / board' if r['official'] else 'GlobeWire Daily')+'</span></li>' for r in records)
        note='Historical records may be closed or superseded. This index contains our published coverage and available official-board metadata, not a complete copy of any third-party archive.' if lang=='en' else 'पुराने नोटिस बंद या नए नोटिस से बदले जा चुके हो सकते हैं। इस इंडेक्स में हमारी प्रकाशित खबरें और उपलब्ध आधिकारिक नोटिस हैं; यह किसी दूसरी वेबसाइट की पूरी कॉपी नहीं है।'
        body='<div class="wrap" data-archive-filter data-lang="'+lang+'"><section class="hub-hero"><h1>'+heading+'</h1><p>'+note+'</p></section><div class="filter-row"><label>'+('Search records' if lang=='en' else 'रिकॉर्ड खोजें')+'<input type="search" placeholder="SSC, UPSC, exam…"></label><label>'+('Year' if lang=='en' else 'वर्ष')+'<select><option value="">'+('All years' if lang=='en' else 'सभी वर्ष')+'</option>'+''.join('<option>'+y+'</option>' for y in years)+'</select></label></div><p role="status">'+str(len(records))+' '+('records' if lang=='en' else 'रिकॉर्ड')+'</p><ul class="hub-news-list">'+items+'</ul></div>'
        write(out/lang/'jobs-archive/index.html',shell(lang,heading+' | GlobeWire Daily',note,site+'/'+lang+'/jobs-archive/',body))
