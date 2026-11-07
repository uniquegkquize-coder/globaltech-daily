"""Shared topics, source discovery and transparent freshness-first ordering."""
import datetime as dt
import re
from functools import lru_cache
from urllib.parse import quote, urlparse
try:
    from .verticals import CATEGORIES as GLOBAL_CATEGORIES, PATTERNS as GLOBAL_PATTERNS, SCOPES, SOURCES, DIRECT, unconfirmed_story
except ImportError:
    from verticals import CATEGORIES as GLOBAL_CATEGORIES, PATTERNS as GLOBAL_PATTERNS, SCOPES, SOURCES, DIRECT, unconfirmed_story

CATEGORIES = {
 'technology':('Technology','टेक्नोलॉजी'), 'government-schemes':('Government Schemes','सरकारी योजनाएँ'),
 'sarkari-naukri':('Sarkari Naukri','सरकारी नौकरी'), 'private-vacancy':('Private Vacancies','प्राइवेट नौकरी'),
 'movies-entertainment':('Movies & Entertainment','फिल्में और मनोरंजन'), 'world-news':('World News','विश्व समाचार'),
 'business':('Business','बिज़नेस'), 'sports':('Sports','खेल'), 'automobiles':('Automobiles','ऑटोमोबाइल'),
 'health-science':('Health & Science','स्वास्थ्य और विज्ञान'), 'gaming':('Gaming','गेमिंग'),
 'environment':('Environment','पर्यावरण'), 'travel':('Travel','यात्रा'), 'education':('Education','शिक्षा'), 'lifestyle':('Lifestyle','लाइफस्टाइल'),
 'telecom':('Telecom & Operator News','टेलीकॉम और ऑपरेटर'), 'ai-news':('Artificial Intelligence','आर्टिफिशियल इंटेलिजेंस'),
 'cyber-security':('Cyber Safety','साइबर सुरक्षा'), 'gadgets':('Mobiles & Gadgets','मोबाइल और गैजेट्स'),
 'apps-software':('Apps & Software','ऐप्स और सॉफ्टवेयर'), 'results':('Exam Results','परीक्षा रिजल्ट'),
 'admit-cards':('Admit Cards','एडमिट कार्ड'), 'answer-keys':('Answer Keys','आंसर की'),
 'syllabus':('Syllabus & Exam Dates','सिलेबस और परीक्षा तिथियाँ'), 'admissions':('Admissions','एडमिशन'),
 'scholarships':('Scholarships','छात्रवृत्ति'), 'banking-finance':('Banking & Personal Finance','बैंकिंग और पर्सनल फाइनेंस'),
 'consumer-alerts':('Consumer Alerts','उपभोक्ता अलर्ट'), 'deals-offers':('Deals & Offers','डील्स और ऑफर्स'),
 'india-news':('India News','भारत की खबरें'),
}
CATEGORIES.update(GLOBAL_CATEGORIES)
EXAM_CATEGORIES={'sarkari-naukri','results','admit-cards','answer-keys','syllabus','admissions','scholarships'}
TOPIC_PATTERNS={
 'admit-cards':r'admit[- ]cards?|hall ticket|admission certificate|एडमिट कार्ड|प्रवेश पत्र',
 'answer-keys':r'answer key|answer keys|response sheet|आंसर की|उत्तर कुंजी',
 'results':r'final result|written result|declaration of result|(?:exam|ssc|upsc|rrb|railway|board|neet|jee|cet|recruitment|university|भर्ती|परीक्षा).*(?:result|merit|scorecard|cut.?off|रिजल्ट|परिणाम)|(?:result|merit list|scorecard|रिजल्ट).*(?:exam|ssc|upsc|board|परीक्षा)',
 'syllabus':r'syllabus|exam date|examination dates?|exam calendar|examination schedule|सिलेबस|परीक्षा तिथि',
 'scholarships':r'scholarship|छात्रवृत्ति', 'admissions':r'college admission|university admission|admission form|counselling|कॉलेज प्रवेश|एडमिशन',
 'telecom':r'\b(?:jio|airtel|bsnl|vodafone|telecom|trai|recharge|broadband|sim card)\b|रिचार्ज|टेलीकॉम|बीएसएनएल|एयरटेल|जियो',
 'cyber-security':r'cyber|phishing|ransomware|data breach|malware|security flaw|साइबर|फिशिंग',
 'ai-news':r'\b(?:ai|openai|chatgpt|gemini|claude|artificial intelligence)\b|आर्टिफिशियल इंटेलिजेंस',
 'gadgets':r'\b(?:smartphone|iphone|pixel phone|galaxy|laptop|earbuds|smartwatch)\b|स्मार्टफोन|मोबाइल फोन',
 'apps-software':r'\b(?:software|android|ios|whatsapp|windows|app update|github)\b|सॉफ्टवेयर|व्हाट्सऐप',
 'deals-offers':r'\b(?:discount|sale deals|black friday|cashback|freebies)\b|डिस्काउंट|कैशबैक',
 'consumer-alerts':r'\b(?:recall|consumer warning|scam alert|fraud alert|product safety)\b|ठगी|उपभोक्ता',
 'banking-finance':r'\b(?:upi|rbi|bank account|fixed deposit|credit card|income tax|personal finance)\b|बैंक खाता|आयकर',
}
PRIORITY={'telecom':10,'sarkari-naukri':10,'results':10,'admit-cards':10,'answer-keys':9,'ai-news':9,'cyber-security':9,'gadgets':8,'government-schemes':8,'banking-finance':8,'consumer-alerts':8,'apps-software':7,'education':7,'scholarships':7,'sports':7,'india-news':7}

SPORT_CONTEXT = re.compile(r'\b(?:sports?|cricket|football|soccer|rugby|tennis|badminton|hockey|basketball|baseball|boxing|golf|athletics|olympics?|paralympics?|fifa|uefa|ipl|bcci|icc|wicket|batsman|bowler|goalkeeper|grand prix|formula ?1|f1|wnba|nba|nfl|wrestling|volleyball|kabaddi|sangakkara|mbapp[eé])\b|क्रिकेट|फुटबॉल|खिलाड़ी|ओलंपिक|विकेट', re.I)
CIVIC_CONTEXT = re.compile(r'\b(?:supreme court|high court|bail|murder|molestation|demolitions?|police|arrested|mla|chief minister|union minister|elections?|electoral|voters?|opposition|bjp|jdu|jd\(u\)|india bloc|cec)\b|सुप्रीम कोर्ट|जमानत|हत्याकांड|विधायक|मुख्यमंत्री|चुनाव', re.I)
INDIA_CONTEXT = re.compile(r'\b(?:india|indian|bihar|patna|mokama|anant singh|yogi|uttarakhand|uttar pradesh|prayagraj|gorakhpur|bengaluru|delhi|kashmir|bjp|jdu|jd\(u\)|kharge|giriraj|supreme court)\b|भारत|बिहार|अनंत सिंह|सुप्रीम कोर्ट', re.I)

def sports_correction(title, default, url=''):
    """A section page can link to unrelated news; its label is only a hint."""
    if default not in {'sports', 'cricket'}:
        return default
    parsed = urlparse(str(url))
    parts = parsed.path.lower().strip('/').split('/')
    # The article's own sports section is stronger than a generic legal word.
    if any(p in {'sport', 'sports', 'football', 'cricket', 'rugby-union', 'rugby-league'} for p in parts[:-1]):
        return default
    if SPORT_CONTEXT.search(str(title)) or re.search(r'\b(?:odi|t20i?|test match|century|innings|hamstring|squad|sixers|cricketer)\b',str(title),re.I):
        return default
    if 'world' in parts[:-1] or 'international' in parts[:-1]:
        return 'world-news'
    if 'india' in parts[:-1] or 'india' in parsed.path.lower().split('/')[-1].split('-'):
        return 'india-news'
    if re.search(r'\b(?:singapore|serbia|iran|britain|british|uk parliament|chancellor)\b',str(title),re.I):
        return 'world-news'
    if CIVIC_CONTEXT.search(str(title)):
        return 'india-news' if INDIA_CONTEXT.search(str(title)) else 'world-news'
    # ABP /sports pages also contain /news and /videos/news recommendations.
    if parsed.hostname and parsed.hostname.endswith('abplive.com') and 'news' in parts[:-1]:
        return 'india-news' if INDIA_CONTEXT.search(str(title)) else 'world-news'
    return default

@lru_cache(maxsize=8192)
def classify(title, default='technology'):
    text=str(title).lower()
    corrected=sports_correction(text,default)
    if corrected!=default:return corrected
    if default in {'technology','gadgets','mobile-launches'} and re.search(r'\b(?:deals?|discount|on sale|all.time low price)\b',text):
        return 'deals-offers'
    for topic,pattern in sorted(GLOBAL_PATTERNS.items(),key=lambda x:x[0]!='controversies'):
        if topic in SCOPES and default not in SCOPES[topic]:continue
        if topic=='mobile-launches' and re.search(r'\b(?:wallet|cash card|apps?|software|security patch|one ui)\b',text):continue
        if topic=='mobile-launches' and re.search(r'\b(?:watch|smartwatch|tablet|ipad|laptop|macbook|earbuds)\b',text) and not re.search(r'\b(?:phone|smartphone|iphone)\b',text):continue
        if topic=='entertainment-rumours' and not unconfirmed_story(text):continue
        if re.search(pattern,text):return topic
    # Technical/business "results" must never become examination results.
    for topic,pattern in TOPIC_PATTERNS.items():
        if topic in EXAM_CATEGORIES and default not in EXAM_CATEGORIES|{'education','government-schemes'}:
            continue
        if re.search(pattern,text): return topic
    return default

def memberships(post):
    original=post.get('category','technology')
    if post.get('directory_kind') or post.get('content_type') == 'evergreen_directory_guide':
        return {original}
    topic=route_category(post.get('en_title') or post.get('source_title',''),original,post.get('source',''))
    # Only related parent sections may share a story. A discovery-page label
    # must not keep a court report in Sports after its primary topic is fixed.
    parents={'technology':{'telecom','ai-news','cyber-security','gadgets','apps-software','mobile-launches'},
             'sports':{'cricket'}, 'automobiles':{'car-launches','ev-clean-energy'},
             'movies-entertainment':{'movie-releases','celebrity-news','entertainment-rumours'}}
    return {topic,original} if topic in parents.get(original,set()) else {topic}


@lru_cache(maxsize=16384)
def route_category(title, default='technology', url=''):
    """Route the article itself, rather than the page which discovered it.

    Use explicit headline subjects first, then the source's section. Ambiguous
    headlines retain the existing category; article body boilerplate is excluded.
    """
    text=str(title)
    parsed=urlparse(str(url))
    parts=set(parsed.path.lower().strip('/').split('/')[:-1])
    def has(pattern):
        return re.search(pattern,text,re.I) is not None
    if parts & {'bike-news','bikes'} or (parsed.hostname or '').removeprefix('www.') == 'bikewale.com':
        return 'automobiles'
    if has(r'\b(?:car|suv|motorcycle|scooter)\b') and has(r'\b(?:launch|launched|specifications|variant|mileage|pricing|engine)\b'):
        return classify(text,'automobiles') if not has(r'\b(?:motorcycle|scooter)\b') else 'automobiles'
    cricket=has(r'\b(?:cricket|cricketer|ipl|bcci|wicket|batsman|bowler|batting|bowling|innings|t20i?|odi|hong kong sixes)\b|क्रिकेट|विकेट')
    cricket = cricket or 'cricket' in re.split(r'[/_-]',parsed.path.lower())
    sport=SPORT_CONTEXT.search(text) or has(r'\b(?:odi|t20i?|innings|squad|hamstring|sixers|cricketer)\b')
    civic=CIVIC_CONTEXT.search(text)
    # A financial "tank", the Shark Tank show and software armor are not weapons.
    if has(r'\bshark tank\b'):
        return 'movies-entertainment'
    if has(r'\b(?:share price|stock market|stock price|shares? (?:fall|falls|slump|tank|tumble)|nifty|sensex|quarterly (?:earnings|profit))\b'):
        return 'business'
    if has(r'\b(?:open.source|github|software)\b') and not has(r'\b(?:military|army|navy|weapon|fighter jet)\b'):
        return classify(text,'technology')
    # Vacancy / exam notices take precedence over the recruiting organisation.
    if not sport and default != 'private-vacancy' and (INDIA_CONTEXT.search(text) or default in EXAM_CATEGORIES or has(r'\b(?:ssc|upsc|rrb|hpsc|bel|ibps|sbi|railway|intelligence bureau)\b')) and has(r'\b(?:recruitment|vacanc(?:y|ies)|admit card|answer key|exam syllabus|exam date|exam result)\b|भर्ती|प्रवेश पत्र|उत्तर कुंजी'):
        exam=next((c for c in ('admit-cards','answer-keys','results','syllabus') if re.search(TOPIC_PATTERNS[c],text,re.I)), 'sarkari-naukri')
        return exam if not has(r'\b(?:paper leak|recruitment scam)\b') else ('india-news' if INDIA_CONTEXT.search(text) else 'world-news')
    if cricket or ('cricket' in parts and not civic):
        return 'cricket'
    if default == 'cricket' and sport and not has(r'\b(?:football|soccer|rugby|tennis|basketball|boxing|ufc|premier league|carabao cup)\b'):
        return 'cricket'
    sport_section=bool(parts & {'sport','sports','football','soccer','tennis','rugby','basketball'})
    if sport_section and (sport or not civic or default in {'sports','cricket'}):
        return 'sports'
    if sport and not civic:
        return 'sports'
    if has(r'\b(?:AI|chatgpt|gemini|claude|openai|artificial intelligence)\b'):
        return classify(text,'technology')
    if has(r'\b(?:army|navy|air force|air chief marshal|air marshal|armed forces|pentagon|nato|military|fighter jets?|warships?|corvettes?)\b') and not sport:
        return classify(text,'defence')
    if has(GLOBAL_PATTERNS['conflict-news']) and not sport:
        return 'conflict-news'
    if has(r'\b(?:scheme|yojana|subsidy|beneficiary|beneficiaries)\b|योजना|सब्सिडी') and not sport:
        return 'government-schemes'
    if civic and not sport and not has(r'\b(?:education|university|school|college|job aspirants|age relaxation|scheme|yojana|subsidy)\b'):
        return 'india-news' if INDIA_CONTEXT.search(text) or parts & {'india','india-news','national','cities','city','state','states'} else 'world-news'
    # Specific source sections outrank broad discovery labels. Do not examine
    # the slug: unrelated uses of words like "tank" occur there too.
    sections=[
        ('government-schemes',{'government-schemes','schemes','yojana'}),
        ('cyber-security',{'cyber-security','cybersecurity'}),
        ('gaming',{'gaming','video-games','games'}),
        ('movies-entertainment',{'entertainment','movies','television','tv','tv-news','bollywood','hollywood'}),
        ('business',{'business','markets','economy','finance'}),
        ('health-science',{'health','science'}),
        ('education',{'education'}),
        ('automobiles',{'auto','automobiles','car-news','bike-news','bikes','cars'}),
        ('technology',{'technology','tech','gadgets','software','apps'}),
        ('environment',{'environment','climate'}),
        ('travel',{'travel'}),
        ('india-news',{'india','india-news','national','cities','city','state','states'}),
        ('world-news',{'world','international','world-news'}),
    ]
    base=default if default in CATEGORIES else 'technology'
    for section, markers in sections:
        if parts & markers:
            children={'technology':{'telecom','ai-news','cyber-security','gadgets','apps-software','mobile-launches','deals-offers','gaming'},
                      'automobiles':{'car-launches','ev-clean-energy'},
                      'movies-entertainment':{'movie-releases','celebrity-news','entertainment-rumours'},
                      'education':EXAM_CATEGORIES | {'study-abroad'}}
            base=default if default in children.get(section,set()) or (section in {'india-news','world-news'} and default not in {'sports','cricket','india-news','world-news','technology'}) else section
            break
    # Overseas / domestic politics often comes from an opaque source URL.
    if base in {'government-schemes','sports','cricket'} and has(r'\b(?:election|elections|demolition|demolitions|police|arrested|murder|court)\b') and not sport:
        base='india-news' if INDIA_CONTEXT.search(text) else 'world-news'
    if base in {'technology','gadgets','mobile-launches','deals-offers','gaming'} and has(r'\b(?:deals?|discount|on sale|all.time low price)\b'):
        return 'deals-offers'
    return classify(text,base)

def timestamp(value):
    try:
        parsed=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed.timestamp() if parsed.tzinfo else 0
    except (ValueError,TypeError): return 0

def lead_priority(story, published=None, now=None):
    """Freshness first; topic weights are editorial, never claimed search volumes."""
    now=now or dt.datetime.now(dt.timezone.utc).timestamp()
    stamp=timestamp(published)
    age=(now-stamp)/3600 if stamp and stamp<=now+300 else None
    band=0 if age is not None and age<=6 else 1 if age is not None and age<=24 else 2 if age is not None and age<=48 else 3 if age is None else 4
    return (band,-PRIORITY.get(story[2],4),-stamp,story[1].lower())

def search_feed(domain,topic,query):
    return ('https://news.google.com/rss/search?q='+quote('site:'+domain+' '+query+' when:2d')+'&hl=en-IN&gl=IN&ceid=IN:en',topic,domain)

EXTRA_FEEDS=[search_feed(d,c,q) for d,c,q in [
 ('telecomtalk.info','telecom','Jio OR Airtel OR BSNL OR Vodafone recharge broadband'),
 ('trai.gov.in','telecom','telecom consumer notification'),
 ('myvi.in','telecom','Vi network recharge press release'),('pib.gov.in','telecom','BSNL telecom announcement'),
 ('jio.com','telecom','Jio news media recharge'),('airtel.in','telecom','press release'),
 ('blog.google','ai-news','Gemini artificial intelligence'),('openai.com','ai-news','announcement'),
 ('thehackernews.com','cyber-security','cybersecurity'),('bleepingcomputer.com','cyber-security','security'),
 ('gadgets360.com','gadgets','smartphone launch'),('blog.google','apps-software','Android Chrome update'),
 ('ssc.gov.in','results','examination result'),('nta.ac.in','results','result score'),
 ('sscnr.nic.in','admit-cards','admit card'),('upsc.gov.in','admit-cards','e admit card'),
 ('ssc.gov.in','answer-keys','answer key response sheet'),('nta.ac.in','answer-keys','answer key'),
 ('upsc.gov.in','syllabus','examination calendar syllabus'),('ssc.gov.in','syllabus','exam date'),
 ('nta.ac.in','admissions','admission counselling'),('ugc.gov.in','admissions','admission'),
 ('education.gov.in','scholarships','scholarship'),('scholarships.gov.in','scholarships','scholarship'),
 ('rbi.org.in','banking-finance','banking customer'),('pib.gov.in','consumer-alerts','consumer fraud safety'),
 ('gadgets360.com','deals-offers','deals offers discount'),('pib.gov.in','india-news','India announcement')]]
DIRECT_EXTRA=[('https://www.myvi.in/media/press-releases','telecom','myvi.in'),('https://www.jio.com/about/news-media/','telecom','jio.com'),('https://www.airtel.in/press-release/','telecom','airtel.in'),('https://trai.gov.in/notifications/press-release','telecom','trai.gov.in'),('https://sscnr.nic.in/newlook/site/admit_card.html','admit-cards','sscnr.nic.in'),('https://ssc.gov.in/','results','ssc.gov.in'),('https://nta.ac.in/','answer-keys','nta.ac.in')]
OFFICIAL_LINKS=[('SSC','https://ssc.gov.in/'),('UPSC','https://upsc.gov.in/'),('NTA','https://nta.ac.in/'),('Railway RRB','https://www.rrbcdg.gov.in/'),('UPSSSC','https://upsssc.gov.in/'),('IBPS','https://www.ibps.in/'),('Scholarships','https://scholarships.gov.in/')]

EXTRA_FEEDS.extend(search_feed(domain,cat,query) for domain,cat,query in SOURCES)
DIRECT_EXTRA.extend(DIRECT)
PRIORITY.update({"cricket":10,"car-launches":9,"mobile-launches":10,"movie-releases":9,"social-media":8,"defence":8,"conflict-news":9,"military-tech":7,"study-abroad":9,"visas-immigration":9,"tourism":7,"travel-packages":7,"freebies":8})

# Native publisher feeds run early in the collector, before opaque search links.
try:
    from .focused_sources import NATIVE_FEEDS, PAGES, SEARCH_SOURCES
except ImportError:
    from focused_sources import NATIVE_FEEDS, PAGES, SEARCH_SOURCES
EXTRA_FEEDS.extend(NATIVE_FEEDS)
EXTRA_FEEDS.extend(search_feed(d,c,q) for d,c,q in SEARCH_SOURCES)
DIRECT_EXTRA.extend(PAGES)

# Additional worldwide publisher discovery for under-covered sections.
# These are discovery candidates, not guarantees of accessible full text.
WORLDWIDE_SOURCE_EXPANSION = [
 ('apnews.com','world-news','world breaking news'),('reuters.com','world-news','international news'),
 ('dw.com','world-news','international news'),('france24.com','world-news','global news'),
 ('thehindu.com','india-news','India latest'),('indianexpress.com','india-news','India news'),
 ('livemint.com','business','business markets'),('cnbc.com','business','global business'),
 ('techcrunch.com','technology','technology startups'),('arstechnica.com','technology','technology'),
 ('theverge.com','gadgets','smartphone gadgets'),('androidauthority.com','gadgets','phone review launch'),
 ('9to5google.com','apps-software','Android software'),('bleepingcomputer.com','cyber-security','security alert'),
 ('venturebeat.com','ai-news','artificial intelligence'),('technologyreview.com','ai-news','AI research'),
 ('espn.com','sports','sports'),('skysports.com','sports','sports'),
 ('cricbuzz.com','cricket','cricket matches'),('espncricinfo.com','cricket','cricket news'),
 ('autocar.co.uk','automobiles','car industry'),('motor1.com','car-launches','new car launch'),
 ('carwale.com','car-launches','car prices launch'),('electrek.co','ev-clean-energy','electric cars'),
 ('gsmarena.com','mobile-launches','new smartphone'),('phonearena.com','mobile-launches','phone launch'),
 ('screenrant.com','movies-entertainment','movies entertainment'),('variety.com','movie-releases','movie releases'),
 ('deadline.com','celebrity-news','celebrity interview'),('hollywoodreporter.com','entertainment-rumours','casting reported'),
 ('apnews.com','controversies','public controversy'),('socialmediatoday.com','social-media','social media platforms'),
 ('who.int','health-science','health research'),('sciencedaily.com','health-science','science research'),
 ('nasa.gov','space-news','space science'),('space.com','space-news','space exploration'),
 ('ign.com','gaming','video games'),('gamespot.com','gaming','gaming news'),
 ('unep.org','environment','environment'),('carbonbrief.org','environment','climate research'),
 ('lonelyplanet.com','travel','travel destinations'),('nationalgeographic.com','tourism','tourism destinations'),
 ('intrepidtravel.com','travel-packages','travel tours'),('gov.uk','visas-immigration','visa immigration updates'),
 ('daad.de','study-abroad','international university study'),('timeshighereducation.com','education','universities education'),
 ('ugc.gov.in','admissions','university admission'),('education.gov.in','scholarships','scholarships'),
 ('ssc.gov.in','sarkari-naukri','recruitment notification'),('upsc.gov.in','results','examination results'),
 ('nta.ac.in','admit-cards','admit card'),('nta.ac.in','answer-keys','answer key'),
 ('upsc.gov.in','syllabus','exam syllabus'),('employmentnews.gov.in','private-vacancy','vacancies jobs'),
 ('pib.gov.in','government-schemes','government schemes'),('rbi.org.in','banking-finance','banking updates'),
 ('consumer.ftc.gov','consumer-alerts','consumer scam alerts'),('wired.com','telecom','telecom networks'),
 ('theverge.com','deals-offers','technology deals'),('epicgames.com','freebies','free games'),
 ('bbc.com','defence','defence news'),('un.org','conflict-news','conflict peace'),
 ('defensenews.com','military-tech','military vehicles technology'),('bbc.com','lifestyle','lifestyle'),
]
EXTRA_FEEDS.extend(search_feed(domain,cat,query) for domain,cat,query in WORLDWIDE_SOURCE_EXPANSION)
