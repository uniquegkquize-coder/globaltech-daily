"""Shared topics, source discovery and transparent freshness-first ordering."""
import datetime as dt
import re
from functools import lru_cache
from urllib.parse import quote
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

@lru_cache(maxsize=8192)
def classify(title, default='technology'):
    text=str(title).lower()
    for topic,pattern in GLOBAL_PATTERNS.items():
        if topic in SCOPES and default not in SCOPES[topic]:continue
        if topic=='entertainment-rumours' and not unconfirmed_story(text):continue
        if re.search(pattern,text):return topic
    # Technical/business "results" must never become examination results.
    for topic,pattern in TOPIC_PATTERNS.items():
        if topic in EXAM_CATEGORIES and default not in EXAM_CATEGORIES|{'education','government-schemes'}:
            continue
        if re.search(pattern,text): return topic
    return default

def memberships(post):
    base=post.get('category','technology')
    topic=classify(str(post.get('en_title',''))+' '+str(post.get('hi_title','')),base)
    return {base,topic}

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
