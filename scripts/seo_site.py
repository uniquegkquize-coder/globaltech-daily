"""Shared search metadata and canonical sitemap for every generated page family."""
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROBOTS = 'index,follow,max-image-preview:large'

def article_languages(post):
    languages=['en']
    if re.search(r'[\u0900-\u097f]',str(post.get('hi_body',''))):
        languages.append('hi')
    return languages

def iso_date(value):
    try:
        stamp=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if stamp.tzinfo is None:return None
        return stamp.isoformat()
    except (TypeError,ValueError):return None

def json_ld(value):
    return '<script type="application/ld+json">'+json.dumps(value,ensure_ascii=False).replace('<','\\u003c')+'</script>'

def head(lang,title,description,url,extra='',*,site,alternates=None,canonical=None,robots=ROBOTS):
    """Do not add competing Open Graph values when article/product extras supply them."""
    esc=lambda x:html.escape(str(x),quote=True)
    canonical=canonical or url
    alternates=alternates if alternates is not None else {
        'en':url.replace('/hi/','/en/',1),'hi':url.replace('/en/','/hi/',1)}
    if canonical != url or 'noindex' in robots.lower():
        alternates = {}
    tags=f'<title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="robots" content="{esc(robots)}"><link rel="canonical" href="{esc(canonical)}">'
    for code,target in alternates.items():tags+=f'<link rel="alternate" hreflang="{code}" href="{esc(target)}">'
    if alternates:tags+=f'<link rel="alternate" hreflang="x-default" href="{esc(alternates.get("en",canonical))}">'
    defaults={'og:type':'website','og:url':canonical,'og:site_name':'GlobeWire Daily','og:title':title,'og:description':description,'og:locale':'hi_IN' if lang=='hi' else 'en_US','og:image':site+'/social-card.jpg','og:image:width':'1200','og:image:height':'630','og:image:alt':'GlobeWire Daily — news and explainers','twitter:card':'summary_large_image','twitter:title':title,'twitter:description':description,'twitter:image':site+'/social-card.jpg'}
    for key,value in defaults.items():
        attr='name' if key.startswith('twitter:') else 'property'
        if not re.search(r'(?:name|property)=[\"\x27]'+re.escape(key)+r'[\"\x27]',extra):
            tags+=f'<meta {attr}="{key}" content="{esc(value)}">'
    org={'@type':'NewsMediaOrganization','@id':site+'/#publisher','name':'GlobeWire Daily','url':site+'/en/','email':'contact@globewiredaily.org','logo':{'@type':'ImageObject','url':site+'/publisher-logo.png','width':512,'height':512},'publishingPrinciples':site+'/'+lang+'/editorial/','correctionsPolicy':site+'/'+lang+'/corrections/'}
    website={'@type':'WebSite','@id':site+'/#website','url':site+'/en/','name':'GlobeWire Daily','inLanguage':['en','hi'],'publisher':{'@id':site+'/#publisher'}}
    path=urlparse(url).path;kind='WebPage'
    if path.endswith('/about/'):kind='AboutPage'
    elif path.endswith('/contact/'):kind='ContactPage'
    elif '/news/' not in path and not path.endswith(('/privacy/','/editorial/','/corrections/','/affiliate/')):kind='CollectionPage'
    page={'@type':kind,'@id':canonical+'#webpage','url':canonical,'name':title,'description':description,'inLanguage':lang,'isPartOf':{'@id':site+'/#website'}}
    tags+=json_ld({'@context':'https://schema.org','@graph':[org,website,page]})
    return tags+extra

_BRIEFS={
 'technology':('Technology news covering AI, software, devices and digital services, with source links and practical context.','AI, सॉफ्टवेयर, डिवाइस और डिजिटल सेवाओं की खबरें, मूल स्रोत और उपयोगी जानकारी के साथ।'),
 'government-schemes':('Government scheme updates, application information and eligibility explainers. Check the linked issuing authority for current rules.','सरकारी योजनाओं के अपडेट, आवेदन और पात्रता की जानकारी। वर्तमान नियम संबंधित विभाग के लिंक पर जाँचें।'),
 'sarkari-naukri':('Government recruitment, vacancy and selection-list reports, with official portal links and application context.','सरकारी भर्ती, रिक्तियों और चयन सूची की खबरें, आधिकारिक पोर्टल और आवेदन की जानकारी के साथ।'),
 'private-vacancy':('Private-sector hiring and job-opening reports. Confirm location, eligibility and application terms with the employer.','प्राइवेट नौकरी और हायरिंग की खबरें। स्थान, पात्रता और आवेदन की शर्तें नियोक्ता से जाँचें।'),
 'movies-entertainment':('Movie, streaming and entertainment news, including release reports, trailers and cast updates.','फिल्म, स्ट्रीमिंग और मनोरंजन की खबरें, रिलीज, ट्रेलर और कलाकारों के अपडेट के साथ।'),
 'world-news':('World news and international developments, with country context, reported developments and links to original coverage.','विश्व समाचार और अंतरराष्ट्रीय घटनाक्रम, देशों के संदर्भ और मूल रिपोर्ट के लिंक के साथ।'),
 'business':('Business and economy news covering companies, markets, banking and industry developments.','कंपनियों, अर्थव्यवस्था, बैंकिंग और उद्योग से जुड़ी बिज़नेस खबरें।'),
 'sports':('Sports reports, competition updates and athlete news. Read the dated coverage and original sources for context.','खेल प्रतियोगिताओं, खिलाड़ियों और मैचों के अपडेट। संदर्भ के लिए खबर की तारीख और मूल रिपोर्ट देखें।'),
 'automobiles':('Automotive news covering cars, bikes, launches and model information. Compare source-linked specifications and dated price references.','कार, बाइक, लॉन्च और मॉडल की खबरें। स्रोत सहित स्पेसिफिकेशन और तारीख वाली कीमतों की जानकारी देखें।'),
 'health-science':('Health and science reporting, research developments and explainers. Read original research and distinguish findings from speculation.','स्वास्थ्य और विज्ञान की खबरें, रिसर्च और आसान जानकारी। निष्कर्षों और अनुमान में अंतर समझने के लिए मूल स्रोत देखें।'),
 'gaming':('Video game updates, release reports, hardware news and developer announcements.','वीडियो गेम अपडेट, रिलीज, गेमिंग हार्डवेयर और डेवलपर घोषणाओं की खबरें।'),
 'environment':('Climate, wildlife and environmental developments, with research context and source-linked reporting.','जलवायु, वन्यजीव और पर्यावरण की खबरें, रिसर्च के संदर्भ और स्रोतों के साथ।'),
 'travel':('Travel and destination updates, tourism reports and useful trip-planning context.','यात्रा, गंतव्यों और पर्यटन की खबरें तथा यात्रा की योजना बनाने की उपयोगी जानकारी।'),
 'education':('Education news, school and university updates, admissions and examination reports.','शिक्षा, स्कूल, विश्वविद्यालय, प्रवेश और परीक्षाओं की खबरें।'),
 'lifestyle':('Lifestyle, shopping, culture and everyday explainers. Read offer dates and conditions before acting on promotional reports.','लाइफस्टाइल, खरीदारी, संस्कृति और रोजमर्रा की जानकारी। ऑफर की तारीख और शर्तें जाँचें।'),
 'telecom':('Telecom updates on Jio, Airtel, Vi, BSNL, broadband and digital phone services. Verify plans and availability with the provider.','Jio, Airtel, Vi, BSNL, ब्रॉडबैंड और डिजिटल फोन सेवाओं के अपडेट। प्लान और उपलब्धता ऑपरेटर से जाँचें।'),
 'ai-news':('Artificial intelligence news covering models, AI products, research and applications, with links to announcements.','AI मॉडल, उत्पाद, रिसर्च और उपयोग की खबरें, मूल घोषणाओं के लिंक के साथ।'),
 'cyber-security':('Cybersecurity news on vulnerabilities, breaches, scams and software fixes, with links to relevant advisories.','साइबर सुरक्षा, सॉफ्टवेयर कमजोरियों, डेटा लीक, ठगी और सुरक्षा अपडेट की खबरें।'),
 'gadgets':('Mobile, smartwatch, computer and gadget news, including features, updates and product announcements.','मोबाइल, स्मार्टवॉच, कंप्यूटर और गैजेट्स की खबरें, फीचर्स और अपडेट के साथ।'),
 'apps-software':('App and software news, operating-system updates, open-source projects and developer tools.','ऐप, सॉफ्टवेयर, ऑपरेटिंग सिस्टम अपडेट, ओपन-सोर्स प्रोजेक्ट और डेवलपर टूल्स की खबरें।'),
 'results':('Exam results, scorecards and merit-list reports. Use the linked official board or recruitment portal to check your result.','परीक्षा रिजल्ट, स्कोरकार्ड और मेरिट लिस्ट की खबरें। परिणाम संबंधित आधिकारिक पोर्टल पर देखें।'),
 'admit-cards':('Admit-card and hall-ticket updates, exam instructions and links to issuing authorities.','एडमिट कार्ड, हॉल टिकट, परीक्षा निर्देश और संबंधित आधिकारिक पोर्टल के अपडेट।'),
 'answer-keys':('Exam answer-key and response-sheet updates, with official notices and objection-process context.','परीक्षा आंसर की, रिस्पॉन्स शीट, आधिकारिक नोटिस और आपत्ति प्रक्रिया की खबरें।'),
 'syllabus':('Exam syllabus, schedule and date announcements. Check the issuing board for the latest notice.','परीक्षा सिलेबस, समय-सारणी और तारीखों की घोषणाएँ। वर्तमान सूचना संबंधित बोर्ड पर जाँचें।'),
 'admissions':('College and university admissions, counselling and application updates, with official source links.','कॉलेज प्रवेश, काउंसलिंग और आवेदन के अपडेट, आधिकारिक स्रोतों के साथ।'),
 'scholarships':('Scholarship and education-funding updates, application dates and eligibility context.','छात्रवृत्ति और शिक्षा फंडिंग, आवेदन तिथि और पात्रता की जानकारी।'),
 'banking-finance':('Banking and personal-finance news covering account services, payments and consumer money updates.','बैंकिंग सेवाओं, भुगतान और व्यक्तिगत वित्त से जुड़ी खबरें।'),
 'consumer-alerts':('Consumer warnings, product recalls and fraud alerts. Read the original notice and affected-product details.','उपभोक्ता चेतावनी, उत्पाद वापसी और ठगी के अलर्ट। मूल नोटिस और प्रभावित उत्पाद की जानकारी देखें।'),
 'deals-offers':('Shopping deals and promotional-offer reports. Check current prices, eligibility, dates and terms with the seller.','खरीदारी डील और प्रमोशनल ऑफर की खबरें। वर्तमान कीमत, पात्रता, तारीख और शर्तें विक्रेता से जाँचें।'),
}

def category_description(key,names,lang,page=1):
    en,hi=names
    brief=_BRIEFS.get(key,(f'{en}: source-linked news, announcements and explainers. Read publication dates and original reports for context.',f'{hi} से जुड़ी खबरें, घोषणाएँ और जानकारी। संदर्भ के लिए प्रकाशन की तारीख और मूल रिपोर्ट देखें।'))[lang=='hi']
    return brief+((' Page '+str(page)+'.') if lang=='en' else (' पृष्ठ '+str(page)+'।')) if page>1 else brief

class _Head(HTMLParser):
    def __init__(self):super().__init__();self.canonical=None;self.noindex=False;self.refresh=False;self.ld=False;self.data=[];self.dates=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href')
        if tag=='meta' and a.get('name','').lower()=='robots':self.noindex='noindex' in a.get('content','').lower()
        if tag=='meta' and a.get('http-equiv','').lower()=='refresh':self.refresh=True
        if tag=='script' and a.get('type')=='application/ld+json':self.ld=True;self.data=[]
    def handle_data(self,data):
        if self.ld:self.data.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.ld:
            self.ld=False
            try:
                value=json.loads(''.join(self.data))
                for row in value.get('@graph',[value]):
                    if row.get('@type') in ('Article','NewsArticle'):self.dates.append(iso_date(row.get('dateModified') or row.get('datePublished')))
            except (ValueError,TypeError,AttributeError):pass

def write_site_sitemap(out,site,generated_paths):
    """Publish only generated, indexable, self-canonical pages; never filesystem timestamps."""
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
    root=ET.Element('{'+ns+'}urlset');seen=set()
    for relative in sorted(set(generated_paths)):
        if not relative.endswith('/index.html'):continue
        path=Path(out)/relative
        if not path.is_file():continue
        head=_Head();head.feed(path.read_text(encoding='utf-8').split('</head>',1)[0])
        expected=site+'/'+relative.removesuffix('index.html')
        if head.noindex or head.refresh or head.canonical!=expected or expected in seen:continue
        seen.add(expected);row=ET.SubElement(root,'{'+ns+'}url');ET.SubElement(row,'{'+ns+'}loc').text=expected
        dates=[x for x in head.dates if x]
        if dates:ET.SubElement(row,'{'+ns+'}lastmod').text=max(dates)
    ET.ElementTree(root).write(Path(out)/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    return len(seen)

def related_index(posts,limit=4):
    """Prefer explicit editorial choices, then topical overlap, then the same desk."""
    stop=set('the a an for and with from over into about after amid news update latest says new what how why report reports'.split())
    tokens={p['id']:{x for x in re.findall(r'[^\W_]+',str(p.get('en_title','')).casefold()) if len(x)>2 and x not in stop} for p in posts}
    by_token={}
    for p in posts:
        for token in tokens[p['id']]:by_token.setdefault(token,set()).add(p['id'])
    by_id={p['id']:p for p in posts};groups={}
    for p in posts:groups.setdefault(p.get('category'),[]).append(p['id'])
    result={}
    for p in posts:
        ident=p['id'];preferred=[x for x in p.get('related_post_ids',[]) if x in by_id and x!=ident]
        candidates=set(groups.get(p.get('category'),[]))
        for token in tokens[ident]:candidates.update(by_token[token])
        candidates.discard(ident)
        def score(other):
            shared=len(tokens[ident]&tokens[other]);same=p.get('category')==by_id[other].get('category')
            return (shared>=2,shared,same,str(by_id[other].get('date','')),other)
        ranked=preferred+sorted(candidates-set(preferred),key=score,reverse=True)
        result[ident]=[by_id[x] for x in ranked[:limit]]
    return result
