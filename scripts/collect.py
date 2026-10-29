"""Quota-capped, source-first bilingual publishing. No external AI calls on import."""
import os, sys, json, hashlib, datetime as dt, pathlib, re, html, time, threading
from functools import lru_cache
from urllib.parse import urlparse
import requests, feedparser
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parents[1]
POSTS=ROOT/'content/posts'; PENDING=ROOT/'content/pending'
POSTS.mkdir(parents=True,exist_ok=True); PENDING.mkdir(parents=True,exist_ok=True)
UTC=dt.timezone.utc
# Moderate, configurable quality floors for NEW drafts; existing posts are untouched.
MIN_WORDS=max(0,int(os.getenv('MIN_ARTICLE_WORDS_EN','140')))
MIN_HINDI_WORDS=max(0,int(os.getenv('MIN_ARTICLE_WORDS_HI','90')))
MIN_HINDI_CHARS=max(0,int(os.getenv('MIN_HINDI_CHARS','0')))
def complete_body(body,lang):
 if not body or not body.strip():return False
 text=body.strip()
 minimum=MIN_HINDI_WORDS if lang=='hi' else MIN_WORDS
 return bool(len(text)>=max(120,MIN_HINDI_CHARS if lang=='hi' else 0)
             and len(re.findall(r'\S+',text))>=minimum
             and len(re.findall(r'[.!?।]',text))>=2)
MAX_CALLS=min(100,max(0,int(os.getenv('MAX_AI_CALLS_PER_RUN','60'))))
POSTS_PER_RUN=max(1,min(60,int(os.getenv('POSTS_PER_RUN','30'))))
MIN_POSTS_PER_CATEGORY=max(1,int(os.getenv('MIN_POSTS_PER_CATEGORY','2')))
MIN_SOURCE_WORDS=0
OFFICIAL_JOB_DOMAINS=('upsc.gov.in','ssc.gov.in','rrbcdg.gov.in','indianrailways.gov.in','employmentnews.gov.in','nta.ac.in','gov.in','nic.in')
CALLS=0
# News discovery sources. Official-domain verification occurs BEFORE any AI request.
# Curated global discovery. Publisher RSS is for finding stories; the linked article is
# the factual source. Never treat a Google News redirect as an original source.

# Worldwide source registry: discovery only. Publisher articles must be original,
# independently summarized, attributed and sufficiently substantiated.
FEEDS=[
 ('https://news.google.com/rss/search?q=site%3Afreekaamaal.com%20freebies%20deals%20offers%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','lifestyle','freekaamaal.com'),
 ('https://news.google.com/rss/search?q=site%3Acoolztricks.com%20freebies%20deals%20offers%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','lifestyle','coolztricks.com'),
 ('https://news.google.com/rss/search?q=site%3Adesidime.com%20deals%20offers%20savings%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','lifestyle','desidime.com'),
 ('https://news.google.com/rss/search?q=site%3Athehackernews.com%20cybersecurity%20hacking%20latest%20news%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','technology','thehackernews.com'),
 ('https://news.google.com/rss/search?q=site%3Agithub.com%20GitHub%20trending%20open%20source%20projects%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','technology','github.com'),
 ('https://news.google.com/rss/search?q=site%3Agithub.blog%20GitHub%20developer%20software%20updates%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','technology','github.blog'),
 ('https://news.google.com/rss/search?q=site%3Adiversejobseeker.com%20private%20jobs%20recruitment%20hiring%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','private-vacancy','diversejobseeker.com'),
 ('https://news.google.com/rss/search?q=site%3Aartificialintelligence-news.com%20AI%20artificial%20intelligence%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','technology','artificialintelligence-news.com'),
 ('https://news.google.com/rss/search?q=site%3Aai.economictimes.com%20artificial%20intelligence%20AI%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','technology','ai.economictimes.com'),
 ('https://news.google.com/rss/search?q=site%3Aeducationworld.in%20schools%20colleges%20education%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','education','educationworld.in'),
 ('https://news.google.com/rss/search?q=site%3Atravelnewsdigest.in%20travel%20tourism%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','travel','travelnewsdigest.in'),
 ('https://news.google.com/rss/search?q=site%3Atravel.economictimes.indiatimes.com%20tourism%20hospitality%20travel%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','travel','travel.economictimes.indiatimes.com'),
 ('https://news.google.com/rss/search?q=site%3Abusiness-standard.com%20economy%20markets%20business%20latest%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','business','business-standard.com'),
 ('https://news.google.com/rss/search?q=site%3Agamerant.com%20gaming%20video%20games%20latest%20news%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','gaming','gamerant.com'),
 ('https://news.google.com/rss/search?q=site%3Ahindi.news18.com%20latest%20Hindi%20news%20when%3A7d&hl=hi&gl=IN&ceid=IN%3Ahi','world-news','hindi.news18.com'),
 ('https://news.google.com/rss/search?q=site%3Ainextlive.com%20Uttar%20Pradesh%20local%20news%20when%3A7d&hl=hi&gl=IN&ceid=IN%3Ahi','world-news','inextlive.com'),
 ('https://news.google.com/rss/search?q=site%3Adainikgorakhpur.com%20Gorakhpur%20Uttar%20Pradesh%20news%20when%3A7d&hl=hi&gl=IN&ceid=IN%3Ahi','world-news','dainikgorakhpur.com'),
 ('https://news.google.com/rss/search?q=site%3Anavbharattimes.indiatimes.com%20latest%20news%20when%3A7d&hl=hi&gl=IN&ceid=IN%3Ahi','world-news','navbharattimes.indiatimes.com'),
 ('https://news.google.com/rss/search?q=site%3Anavbharattimes.indiatimes.com%20sarkari%20naukri%20recruitment%20when%3A7d&hl=hi&gl=IN&ceid=IN%3Ahi','sarkari-naukri','navbharattimes.indiatimes.com'),
 ('https://news.google.com/rss/search?q=site%3Anavbharattimes.indiatimes.com%20sarkari%20yojana%20when%3A7d&hl=hi&gl=IN&ceid=IN%3Ahi','government-schemes','navbharattimes.indiatimes.com'),
 ('https://news.google.com/rss/search?q=site%3Asarkarikyp.com%20government%20scheme%20yojana%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','government-schemes','sarkarikyp.com'),
 ('https://news.google.com/rss/search?q=site%3Agovtschemes.in%20government%20scheme%20yojana%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','government-schemes','govtschemes.in'),
 ('https://news.google.com/rss/search?q=site%3Abharatjobzone.com%20sarkari%20yojana%20scheme%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','government-schemes','bharatjobzone.com'),
 ('https://news.google.com/rss/search?q=site%3Asahisarkarijobs.in%20uttar%20pradesh%20govt%20jobs%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','sahisarkarijobs.in'),
 ('https://news.google.com/rss/search?q=site%3Asarkariresult.com%20recruitment%20result%20admit%20card%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','sarkariresult.com'),
 ('https://news.google.com/rss/search?q=site%3Aofficialsarkarinaukri.com%20latest%20jobs%20recruitment%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','officialsarkarinaukri.com'),
 ('https://news.google.com/rss/search?q=site%3Aindiasarkarinaukri.com%20government%20jobs%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','indiasarkarinaukri.com'),
 ('https://news.google.com/rss/search?q=site%3Anaukri.com%20private%20jobs%20hiring%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','private-vacancy','naukri.com'),
 ('https://news.google.com/rss/search?q=site%3Aindeed.com%20India%20private%20jobs%20hiring%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','private-vacancy','indeed.com'),
 ('https://news.google.com/rss/search?q=site%3Alinkedin.com%20India%20jobs%20hiring%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','private-vacancy','linkedin.com'),
 ('https://news.google.com/rss/search?q=site%3Asarkariresult.com.cm%20recruitment%20OR%20admit%20card%20OR%20result%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','sarkariresult.com.cm'),
 ('https://news.google.com/rss/search?q=site%3Aamazon.jobs%20hiring&hl=en-IN&gl=IN&ceid=IN%3Aen','private-vacancy','amazon.jobs'),
 ('https://news.google.com/rss/search?q=site%3Acareers.microsoft.com%20jobs&hl=en-IN&gl=IN&ceid=IN%3Aen','private-vacancy','careers.microsoft.com'),
 ('https://feeds.bbci.co.uk/news/world/rss.xml', 'world-news', 'bbc.co.uk'),
 ('https://www.theguardian.com/world/rss', 'world-news', 'theguardian.com'),
 ('https://feeds.npr.org/1004/rss.xml', 'world-news', 'npr.org'),
 ('https://www.aljazeera.com/xml/rss/all.xml', 'world-news', 'aljazeera.com'),
 ('https://rss.dw.com/rdf/rss-en-top', 'world-news', 'dw.com'),
 ('https://www.france24.com/en/rss', 'world-news', 'france24.com'),
 ('https://feeds.skynews.com/feeds/rss/world.xml', 'world-news', 'skynews.com'),
 ('https://www.cbc.ca/webfeed/rss/rss-world', 'world-news', 'cbc.ca'),
 ('https://www.abc.net.au/news/feed/51120/rss.xml', 'world-news', 'abc.net.au'),
 ('https://timesofindia.indiatimes.com/rssfeedstopstories.cms', 'world-news', 'timesofindia.indiatimes.com'),
 ('https://feeds.nbcnews.com/nbcnews/public/world', 'world-news', 'nbcnews.com'),
 ('https://rss.nytimes.com/services/xml/rss/nyt/World.xml', 'world-news', 'nytimes.com'),
 ('https://techcrunch.com/feed/', 'technology', 'techcrunch.com'),
 ('https://techcrunch.com/category/artificial-intelligence/feed/', 'technology', 'techcrunch.com'),
 ('https://www.theverge.com/rss/index.xml', 'technology', 'theverge.com'),
 ('https://feeds.arstechnica.com/arstechnica/index', 'technology', 'arstechnica.com'),
 ('https://www.wired.com/feed/rss', 'technology', 'wired.com'),
 ('https://www.wired.com/feed/tag/ai/latest/rss', 'technology', 'wired.com'),
 ('https://www.engadget.com/rss.xml', 'technology', 'engadget.com'),
 ('https://blog.google/rss/', 'technology', 'blog.google'),
 ('https://www.nasa.gov/feed/', 'technology', 'nasa.gov'),
 ('https://www.technologyreview.com/feed/', 'technology', 'technologyreview.com'),
 ('https://www.bleepingcomputer.com/feed/', 'technology', 'bleepingcomputer.com'),
 ('https://www.cnet.com/rss/news/', 'technology', 'cnet.com'),
 ('https://www.techradar.com/feeds.xml', 'technology', 'techradar.com'),
 ('https://feeds.npr.org/1019/rss.xml', 'technology', 'npr.org'),
 ('https://variety.com/feed/', 'movies-entertainment', 'variety.com'),
 ('https://variety.com/v/film/feed/', 'movies-entertainment', 'variety.com'),
 ('https://deadline.com/feed/', 'movies-entertainment', 'deadline.com'),
 ('https://www.hollywoodreporter.com/feed/', 'movies-entertainment', 'hollywoodreporter.com'),
 ('https://www.theguardian.com/film/rss', 'movies-entertainment', 'theguardian.com'),
 ('https://www.theguardian.com/culture/rss', 'movies-entertainment', 'theguardian.com'),
 ('https://feeds.npr.org/1045/rss.xml', 'movies-entertainment', 'npr.org'),
 ('https://ew.com/feed/', 'movies-entertainment', 'ew.com'),
 ('https://www.rollingstone.com/feed/', 'movies-entertainment', 'rollingstone.com'),
 ('https://news.abplive.com/entertainment/movies/feed', 'movies-entertainment', 'news.abplive.com'),
 ('https://news.abplive.com/entertainment/television/feed', 'movies-entertainment', 'news.abplive.com'),
 ('https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms', 'movies-entertainment', 'timesofindia.indiatimes.com'),
 ('https://www.theguardian.com/business/rss', 'business', 'theguardian.com'),
 ('https://feeds.bbci.co.uk/news/business/rss.xml', 'business', 'bbc.co.uk'),
 ('https://feeds.bloomberg.com/markets/news.rss', 'business', 'bloomberg.com'),
 ('https://feeds.bloomberg.com/economics/news.rss', 'business', 'bloomberg.com'),
 ('https://feeds.content.dowjones.io/public/rss/RSSMarketsMain', 'business', 'wsj.com'),
 ('https://feeds.npr.org/1006/rss.xml', 'business', 'npr.org'),
 ('https://news.abplive.com/business/feed', 'business', 'news.abplive.com'),
 ('https://www.espn.com/espn/rss/news', 'sports', 'espn.com'),
 ('https://www.espn.com/espn/rss/soccer/news', 'sports', 'espn.com'),
 ('https://www.espn.com/espn/rss/nba/news', 'sports', 'espn.com'),
 ('https://feeds.bbci.co.uk/sport/rss.xml', 'sports', 'bbc.co.uk'),
 ('https://www.theguardian.com/sport/rss', 'sports', 'theguardian.com'),
 ('https://www.france24.com/en/sport/rss', 'sports', 'france24.com'),
 ('https://news.abplive.com/sports/feed', 'sports', 'news.abplive.com'),
 ('https://news.abplive.com/auto/feed', 'automobiles', 'news.abplive.com'),
 ('https://www.engadget.com/rss.xml', 'automobiles', 'engadget.com'),
 ('https://www.nasa.gov/feed/', 'health-science', 'nasa.gov'),
 ('https://www.wired.com/feed/category/science/latest/rss', 'health-science', 'wired.com'),
 ('https://feeds.arstechnica.com/arstechnica/science', 'health-science', 'arstechnica.com'),
 ('https://news.abplive.com/health/feed', 'health-science', 'news.abplive.com'),
 ('https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=22', 'government-schemes', 'pib.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Apib.gov.in%20scheme%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen', 'government-schemes', 'pib.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Aupsc.gov.in%20recruitment%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen', 'sarkari-naukri', 'upsc.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Assc.gov.in%20notice%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen', 'sarkari-naukri', 'ssc.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Arrbcdg.gov.in%20notification%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen', 'sarkari-naukri', 'rrbcdg.gov.in'),
 ('https://www.ign.com/rss/articles/feed', 'gaming', 'ign.com'),
 ('https://www.gamespot.com/feeds/mashup/', 'gaming', 'gamespot.com'),
 ('https://www.theguardian.com/environment/rss', 'environment', 'theguardian.com'),
 ('https://www.nasa.gov/feed/', 'environment', 'nasa.gov'),
 ('https://www.theguardian.com/travel/rss', 'travel', 'theguardian.com'),
 ('https://www.theguardian.com/education/rss', 'education', 'theguardian.com'),
 ('https://www.theguardian.com/lifeandstyle/rss', 'lifestyle', 'theguardian.com'),
]


# Additional public discovery feeds. These are leads, not permission to republish text or images.
# Social/community feeds are treated as tips; verify claims with primary reporting.
FEEDS.extend([
 ('https://www.reddit.com/r/worldnews/.rss','world-news','reddit.com'),
 ('https://www.reddit.com/r/news/.rss','world-news','reddit.com'),
 ('https://www.reddit.com/r/technology/.rss','technology','reddit.com'),
 ('https://www.reddit.com/r/gadgets/.rss','technology','reddit.com'),
 ('https://www.reddit.com/r/cars/.rss','automobiles','reddit.com'),
 ('https://www.reddit.com/r/IndiaNews/.rss','world-news','reddit.com'),
 ('https://www.apple.com/newsroom/rss-feed.rss','technology','apple.com'),
 ('https://news.samsung.com/global/feed','technology','news.samsung.com'),
 ('https://www.microsoft.com/en-us/research/feed/','technology','microsoft.com'),
 ('https://www.prnewswire.com/rss/news-releases-list.rss','business','prnewswire.com'),
 ('https://www.businesswire.com/portal/site/home/news/','business','businesswire.com'),
 ('https://www.reutersagency.com/feed/','world-news','reutersagency.com'),
 ('https://news.google.com/rss/search?q=site%3Ahyundai.com%20press%20release%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','automobiles','hyundai.com'),
 ('https://news.google.com/rss/search?q=site%3Atesla.com%20news%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen','automobiles','tesla.com'),
 ('https://news.google.com/rss/search?q=site%3Aapple.com%2Fnewsroom%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen','technology','apple.com'),
 ('https://news.google.com/rss/search?q=site%3Anews.samsung.com%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen','technology','news.samsung.com'),
 ('https://news.google.com/rss/search?q=site%3Abusinesswire.com%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen','business','businesswire.com'),
 ('https://news.google.com/rss/search?q=site%3Aprnewswire.com%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen','business','prnewswire.com'),
])


# User-requested website landing pages: discovery only, not article URLs.
DIRECT_SOURCES=[
 ("https://www.sahisarkarijobs.in/state/uttar-pradesh-govt-jobs/","sarkari-naukri","sahisarkarijobs.in"),
 ("https://www.sarkariresult.com/","sarkari-naukri","sarkariresult.com"),
 ("https://officialsarkarinaukri.com/","sarkari-naukri","officialsarkarinaukri.com"),
 ("https://www.indiasarkarinaukri.com/","sarkari-naukri","indiasarkarinaukri.com"),
 ("https://www.naukri.com/sarkari-naukri-jobs","private-vacancy","naukri.com"),
 ("https://in.indeed.com/","private-vacancy","indeed.com"),
 ("https://in.linkedin.com/jobs","private-vacancy","linkedin.com"),
 ("https://govtschemes.in/","government-schemes","govtschemes.in"),
 ("https://bharatjobzone.com/सरकारी-काम/","government-schemes","bharatjobzone.com"),
 ("https://navbharattimes.indiatimes.com/","world-news","navbharattimes.indiatimes.com"),
 ("https://sarkarikyp.com/","government-schemes","sarkarikyp.com"),
 ("https://www.dainikgorakhpur.com/","world-news","dainikgorakhpur.com"),
 ("https://www.inextlive.com/","world-news","inextlive.com"),
 ("https://hindi.news18.com/","world-news","hindi.news18.com"),
 ("https://www.amarujala.com/","world-news","amarujala.com"),
 ("https://www.bhaskar.com/","world-news","bhaskar.com"),
 ("https://gamerant.com/","gaming","gamerant.com"),
 ("https://www.gamespot.com/","gaming","gamespot.com"),
 ("https://www.thehindu.com/","world-news","thehindu.com"),
 ("https://www.business-standard.com/","business","business-standard.com"),
 ("https://travel.economictimes.indiatimes.com/","travel","travel.economictimes.indiatimes.com"),
 ("https://travelnewsdigest.in/","travel","travelnewsdigest.in"),
 ("https://educationworld.in/","education","educationworld.in"),
 ("https://ai.economictimes.com/","technology","ai.economictimes.com"),
 ("https://www.artificialintelligence-news.com/","technology","artificialintelligence-news.com"),
 ("https://diversejobseeker.com/","private-vacancy","diversejobseeker.com"),
 ("https://github.blog/","technology","github.blog"),
 ("https://github.com/trending","technology","github.com"),
 ("https://thehackernews.com/","technology","thehackernews.com"),
 ("https://www.desidime.com/","lifestyle","desidime.com"),
 ("https://www.coolztricks.com/","lifestyle","coolztricks.com"),
 ("https://freekaamaal.com/","lifestyle","freekaamaal.com"),
]
for direct_url,direct_cat,direct_domain in DIRECT_SOURCES:
 if not any(c==direct_cat and d==direct_domain for _,c,d in FEEDS):
  FEEDS.append((direct_url,direct_cat,direct_domain))

# Nationwide India discovery: all states/UTs, major cities and regional publishers.
# Rotating local feeds keeps scheduled runs bounded while gradually covering India.
from urllib.parse import quote as quote_query
INDIA_REGIONS={
 'Andhra Pradesh':['Visakhapatnam','Vijayawada','Guntur','Tirupati'],
 'Arunachal Pradesh':['Itanagar','Tawang'],'Assam':['Guwahati','Dibrugarh','Silchar'],
 'Bihar':['Patna','Gaya','Muzaffarpur','Bhagalpur'],'Chhattisgarh':['Raipur','Bilaspur','Durg'],
 'Goa':['Panaji','Margao'],'Gujarat':['Ahmedabad','Surat','Vadodara','Rajkot'],
 'Haryana':['Gurugram','Faridabad','Hisar','Karnal'],'Himachal Pradesh':['Shimla','Mandi','Dharamshala'],
 'Jharkhand':['Ranchi','Jamshedpur','Dhanbad'],'Karnataka':['Bengaluru','Mysuru','Mangaluru','Hubballi'],
 'Kerala':['Kochi','Thiruvananthapuram','Kozhikode','Thrissur'],
 'Madhya Pradesh':['Bhopal','Indore','Gwalior','Jabalpur'],
 'Maharashtra':['Mumbai','Pune','Nagpur','Nashik','Thane','Aurangabad'],
 'Manipur':['Imphal'],'Meghalaya':['Shillong'],'Mizoram':['Aizawl'],
 'Nagaland':['Kohima','Dimapur'],'Odisha':['Bhubaneswar','Cuttack','Rourkela','Puri'],
 'Punjab':['Ludhiana','Amritsar','Jalandhar','Patiala'],
 'Rajasthan':['Jaipur','Jodhpur','Udaipur','Kota','Ajmer'],
 'Sikkim':['Gangtok'],'Tamil Nadu':['Chennai','Coimbatore','Madurai','Salem','Tiruchirappalli'],
 'Telangana':['Hyderabad','Warangal','Nizamabad'],
 'Tripura':['Agartala'],'Uttar Pradesh':['Lucknow','Kanpur','Varanasi','Prayagraj','Gorakhpur','Agra','Meerut','Noida','Ayodhya','Deoria','Kushinagar','Maharajganj','Basti'],
 'Uttarakhand':['Dehradun','Haridwar','Haldwani'],
 'West Bengal':['Kolkata','Howrah','Siliguri','Durgapur'],
 'Andaman and Nicobar Islands':['Port Blair'],'Chandigarh':['Chandigarh'],
 'Dadra and Nagar Haveli and Daman and Diu':['Daman','Silvassa'],
 'Delhi':['New Delhi','Delhi'],'Jammu and Kashmir':['Srinagar','Jammu'],
 'Ladakh':['Leh','Kargil'],'Lakshadweep':['Kavaratti'],'Puducherry':['Puducherry','Karaikal']
}
LOCAL_PUBLISHERS=('hindi.news18.com','inextlive.com','dainikgorakhpur.com','jagran.com','amarujala.com','livehindustan.com','bhaskar.com','indiatoday.in','timesofindia.indiatimes.com','thehindu.com','indianexpress.com','news18.com')
LOCAL_PRIMARY_DOMAINS=('pib.gov.in','mausam.imd.gov.in')
def local_news_feed(query,domain,cat='world-news'):
 return ('https://news.google.com/rss/search?q='+quote_query(query+' when:7d')+'&hl=en-IN&gl=IN&ceid=IN:en',cat,domain)
# Persist only lightweight source definitions; actual local feeds are sampled each run.
LOCAL_DISCOVERY=[]
for state,cities in INDIA_REGIONS.items():
 for domain in LOCAL_PUBLISHERS:
  LOCAL_DISCOVERY.append(local_news_feed('site:'+domain+' "'+state+'" latest news',domain))
 for city in cities:
  for domain in LOCAL_PUBLISHERS[:4]:
   LOCAL_DISCOVERY.append(local_news_feed('site:'+domain+' "'+city+'" news',domain))
 for domain in LOCAL_PRIMARY_DOMAINS:
  LOCAL_DISCOVERY.append(local_news_feed('site:'+domain+' "'+state+'" advisory OR notice',domain,'government-schemes'))
# Daily deterministic rotation: no state is permanently excluded.
LOCAL_DAILY_LIMIT=max(12,min(100,int(os.getenv('LOCAL_FEEDS_PER_RUN','48'))))
def rotating_local_feeds():
 # Sample across every state/UT on every run, then rotate city sources daily.
 day=dt.datetime.now(UTC).date().toordinal()
 selected=[]
 for state in INDIA_REGIONS:
  options=[item for item in LOCAL_DISCOVERY if quote_query('"'+state+'"') in item[0]]
  if options:
   selected.append(options[day%len(options)])
 remaining=max(0,LOCAL_DAILY_LIMIT-len(selected))
 cities=[item for item in LOCAL_DISCOVERY if item not in selected]
 if cities and remaining:
  start=(day*remaining)%len(cities)
  selected.extend(cities[(start+i)%len(cities)] for i in range(remaining))
 return selected
# Keep direct primary and regional media domains eligible for original-link verification.
for domain in LOCAL_PUBLISHERS+LOCAL_PRIMARY_DOMAINS:
 FEEDS.append(local_news_feed('site:'+domain+' India latest',domain))

# Social-platform news leads without scraping, login bypass or paid APIs.
# Discover publisher reports referring to public X/Facebook announcements and
# Public App local leads; articles must resolve to an existing approved publisher.
# Social posts themselves are NOT auto-published or treated as verified reporting.
SOCIAL_DISCOVERY_TERMS=(
 ('"posted on X" official announcement','world-news'),
 ('"shared on X" government announcement','world-news'),
 ('"Facebook post" district administration news','world-news'),
 ('"Facebook page" police official announcement','world-news'),
 ('"Public App" local news district','world-news'),
 ('"Public app" city incident local news','world-news'),
)
SOCIAL_DISCOVERY_DOMAINS=(
 'indiatoday.in','indianexpress.com','timesofindia.indiatimes.com',
 'news18.com','jagran.com','amarujala.com','livehindustan.com',
)
# One query per topic per publisher would be excessive: rotate a small,
# bounded set on each run and keep every existing feed intact.
def rotating_social_feeds():
 day=dt.datetime.now(UTC).date().toordinal()
 items=[]
 for term,cat in SOCIAL_DISCOVERY_TERMS:
  for domain in SOCIAL_DISCOVERY_DOMAINS:
   items.append(local_news_feed('site:'+domain+' '+term,domain,cat))
 count=max(1,min(8,int(os.getenv('SOCIAL_LEAD_FEEDS_PER_RUN','4'))))
 start=(day*7)%len(items)
 return [items[(start+i)%len(items)] for i in range(count)]

# No automatic republication of syndicated or paywalled text; independent articles only.

SCHEME=('scheme','yojana','subsidy','welfare','pension','scholarship','beneficiary','योजना','सब्सिडी','पेंशन')
JOB=('recruitment','vacancy','notification','admit card','exam','upsc','ssc','भर्ती','रिक्ति','नौकरी')
def category(title, default):
 t=title.lower()
 if default not in ('sarkari-naukri','government-schemes'): return default
 if any(x in t for x in JOB): return 'sarkari-naukri'
 if any(x in t for x in SCHEME): return 'government-schemes'
 return default

def clean(s): return re.sub(r'\s+',' ',html.unescape(BeautifulSoup(str(s or ''),'html.parser').get_text(' ',strip=True))).strip()
def words(s): return len(re.findall(r'\S+',s or ''))
def allowed(url,domain):
 h=(urlparse(url).hostname or '').lower()
 return url.startswith('https://') and (h==domain or h.endswith('.'+domain))
@lru_cache(maxsize=512)
def source_text(url,domain):
 try:
  if not allowed(url,domain):return ''
  r=requests.get(url,timeout=(8,18),headers={'User-Agent':'Mozilla/5.0 (compatible; GlobalTechDaily/1.0)','Accept':'text/html,application/xhtml+xml'})
  r.raise_for_status()
  if not allowed(r.url,domain) or 'html' not in r.headers.get('content-type','').lower():return ''
  soup=BeautifulSoup(r.text[:1800000],'html.parser')
  candidates=[]
  # JSON-LD articleBody is often present even when the visible article is JS-rendered.
  for script in soup.select('script[type="application/ld+json"]'):
   try:
    data=json.loads(script.string or script.get_text() or '{}')
    def visit(obj):
     if isinstance(obj,list):
      for value in obj:visit(value)
     elif isinstance(obj,dict):
      body=obj.get('articleBody')
      if isinstance(body,str) and len(body)>100:candidates.append(clean(body))
      for key in ('@graph','mainEntity','itemListElement'):
       if key in obj:visit(obj[key])
    visit(data)
   except (ValueError,TypeError,RecursionError):pass
  for tag in soup(['script','style','nav','footer','aside','form','header','noscript']):tag.decompose()
  selectors=('[itemprop="articleBody"]','[class*="article-body"]','[class*="articleBody"]','[class*="story-body"]','[data-testid*="article"]','article','main')
  for selector in selectors:
   for node in soup.select(selector)[:4]:
    paras=[clean(p.get_text(' ',strip=True)) for p in node.find_all(['h2','h3','p','li'])]
    paras=[p for p in paras if len(p)>40]
    if paras:candidates.append('\\n'.join(paras))
  # Universal extraction fallback: OpenGraph/JSON-LD + common CMS article containers.
  for node in soup.select('.article-content, .article-body, .story-body, .story-detail, .content-body, .news-content, .post-body, .td-post-content, .single-post-content, [class*="articleContent"], [class*="storyContent"], [itemprop="mainEntityOfPage"]')[:8]:
   paragraphs=[clean(p.get_text(' ',strip=True)) for p in node.find_all(['p','h2','h3','li'])]
   paragraphs=[p for p in paragraphs if len(p)>45]
   if len(paragraphs)>=2:candidates.append('\\n'.join(paragraphs))
  # Prefer article content; never treat navigation or paywall previews as full reporting.
  for node in soup.select('[data-component="text-block"], [data-testid="paragraph"], .article__content, .entry-content, .post-content, .story-content')[:6]:
   paragraphs=[clean(p.get_text(' ',strip=True)) for p in node.find_all(['p','h2','h3'])]
   paragraphs=[p for p in paragraphs if len(p)>40]
   if paragraphs:candidates.append(' '.join(paragraphs))
  # Reject short navigation snippets rather than manufacture 300 words.
  best=max(candidates,key=words,default='')[:24000]
  if words(best)<65:print('EXTRACTION_INSUFFICIENT',domain,url[:130],'words',words(best),flush=True)
  return best
 except (requests.RequestException,ValueError,TypeError):return ''

def day_count():
 today=dt.datetime.now(UTC).date().isoformat()
 n=0
 for p in POSTS.glob('*.json'):
  try: n+=json.loads(p.read_text()).get('date','')[:10]==today
  except (OSError,ValueError): pass
 return n

def save_state(path,state):
 path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
def json_object(raw):
 try: return json.loads(raw)
 except (ValueError,TypeError):
  try:
   a=raw.index('{'); b=raw.rindex('}')+1
   return json.loads(raw[a:b])
  except (ValueError,AttributeError): return {}

GEMINI_MODEL_CACHE={}
def gemini_models(key):
 if key in GEMINI_MODEL_CACHE:return GEMINI_MODEL_CACHE[key]
 # Discover every model this API key can actually use for text generation.
 fallback=[x.strip() for x in os.getenv('GEMINI_MODELS','gemini-2.5-flash,gemini-2.5-flash-lite').split(',') if x.strip()]
 try:
  names=[];page=''
  for _ in range(5):
   resp=requests.get('https://generativelanguage.googleapis.com/v1beta/models',headers={'x-goog-api-key':key},params={'pageSize':100,**({'pageToken':page} if page else {})},timeout=(5,12))
   if not resp.ok:break
   payload=resp.json()
   for m in payload.get('models',[]):
    name=m.get('name','').removeprefix('models/')
    if 'generateContent' in m.get('supportedGenerationMethods',[]) and name.startswith('gemini-') and not any(x in name for x in ('embedding','image','tts','live','robotics')):
     names.append(name)
   page=payload.get('nextPageToken','')
   if not page:break
  if names:
   # Prefer Flash/free-friendly variants, avoid probing paid-only models unnecessarily.
   names=sorted(set(names),key=lambda n:(not ('flash-lite' in n),not ('flash' in n), tuple(-int(v) for v in re.findall(r'\d+',n)[:3]),n))
   print('Gemini generateContent models available:',len(names),flush=True)
   GEMINI_MODEL_CACHE[key]=names
   return names
 except (requests.RequestException,ValueError,TypeError):pass
 GEMINI_MODEL_CACHE[key]=fallback
 return fallback

def provider_order():
 # One generation attempt per language; no repeated model probing.
 order=os.getenv('AI_PROVIDER_ORDER','gemini,groq,openrouter').lower().split(',')
 return [p.strip() for p in order if p.strip() in ('groq','gemini','openrouter','openai')]
# Disable a rate-limited provider for the remainder of this run.
PROVIDER_LOCK=threading.RLock()
PROVIDER_COOLDOWNS=set()
UNAVAILABLE_MODELS=set()
def call_provider(prompt):
 global CALLS
 last=None
 for provider in provider_order():
  with PROVIDER_LOCK:
   if CALLS>=MAX_CALLS:break
   if provider in PROVIDER_COOLDOWNS:continue
  key=os.getenv({'groq':'GROQ_API_KEY','gemini':'GEMINI_API_KEY','openrouter':'OPENROUTER_API_KEY','openai':'OPENAI_API_KEY'}[provider],'').strip()
  if not key:continue
  models=gemini_models(key) if provider=='gemini' else [os.getenv('GROQ_MODEL','openai/gpt-oss-120b') if provider=='groq' else (os.getenv('OPENAI_MODEL','gpt-4.1-mini') if provider=='openai' else os.getenv('OPENROUTER_MODEL','openrouter/free'))]
  for model in dict.fromkeys(models):
   with PROVIDER_LOCK:
    if (provider,model) in UNAVAILABLE_MODELS:continue
   if CALLS>=MAX_CALLS:break
   with PROVIDER_LOCK:
    if CALLS>=MAX_CALLS:break
    CALLS+=1
   last=provider
   try:
    if provider=='gemini':
     r=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',headers={'x-goog-api-key':key},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':8192}},timeout=(7,55))
     raw=''.join(p.get('text','') for p in r.json()['candidates'][0]['content']['parts']) if r.ok else ''
    else:
     url=('https://api.groq.com/openai/v1/chat/completions' if provider=='groq' else ('https://api.openai.com/v1/chat/completions' if provider=='openai' else 'https://openrouter.ai/api/v1/chat/completions'))
     r=requests.post(url,headers={'Authorization':'Bearer '+key},json={'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':8192,'temperature':0.2},timeout=(7,55))
     raw=r.json()['choices'][0]['message']['content'] if r.ok else ''
    if not r.ok:
     print('Provider',provider,'model',model,'HTTP',r.status_code,flush=True)
     if r.status_code in (401,402,403,429):
      with PROVIDER_LOCK:PROVIDER_COOLDOWNS.add(provider)
      break
     if r.status_code in (404,503):
      # Avoid repeatedly spending requests on unavailable or overloaded models.
      with PROVIDER_LOCK:UNAVAILABLE_MODELS.add((provider,model))
      continue
     continue
    data=json_object(raw)
    if isinstance(data,dict) and data.get('body'):
     print('Provider success:',provider,'model',model,flush=True)
     return data,provider
    print('Provider',provider,'returned unusable JSON; trying next option',flush=True)
   except (requests.RequestException,ValueError,KeyError,IndexError,TypeError) as exc:
    print('Provider',provider,'error',type(exc).__name__,flush=True)
 return None,last

def article_prompt(lang,title,source,source_material,cat):
 if cat=='private-vacancy':
  source_material += '\nRequired coverage: employer, role, eligibility, location, salary, deadline, selection process, application steps and official application link. Mark missing details as not specified; never invent them.'
 language='English' if lang=='en' else 'Hindi (Devanagari)'
 return f'''You are a careful editor for a public-information news site. Write ONE original article in {language}. Return ONLY a JSON object with fields title, body, meta, keywords. Write a complete, professionally edited news report of natural length appropriate to the available verified facts. Aim for 450-800 words when sufficient verified source details exist; use fewer words when the source is limited; never invent, repeat, or pad. Use Markdown ## subheadings. Explain confirmed facts, background, user impact, uncertainties, and what readers can verify, with a clear link to the official source. Write a compelling, curiosity-driven but strictly accurate headline that clearly reflects the verified story. Never use misleading clickbait, fake urgency, unsupported superlatives or invented claims. Do not fabricate quotes, eligibility, deadlines, salaries, recruitment numbers, prices, application steps, or citations. No copied paragraphs. Add a useful independently written section on practical implications, relevant comparisons, what is confirmed versus unknown, and how readers can check the original announcement; only use details supported by the supplied source. Do not imply original interviews or firsthand reporting. Never copy source images or assume press-room, stock-photo, Creative Commons, or social-media embedding permissions: media rights and attribution must be checked against each asset's actual license or platform terms. If source is insufficient for a detailed factual article, return {{"title":"","body":"","meta":"","keywords":""}}. Category: {cat}. Source title: {title}. Verified official/source URL: {source}. SOURCE TEXT:\n{source_material[:22000]}'''

def published_categories():
 """Count only published posts, never drafts, toward category coverage."""
 counts={cat:0 for _,cat,_ in FEEDS}
 for path in POSTS.glob('*.json'):
  try:
   item=json.loads(path.read_text(encoding='utf-8'))
   cat=item.get('category')
   if cat in counts: counts[cat]+=1
  except (OSError,ValueError,TypeError):pass
 return counts

# Prioritize major editorial publishers and current popular headlines. RSS is only a
# discovery transport, never a reason to rank an independent blog above major news.
MAJOR_PUBLISHERS=('bbc.co.uk','theguardian.com','npr.org','aljazeera.com','dw.com','france24.com','skynews.com','cbc.ca','abc.net.au','nbcnews.com','nytimes.com','bloomberg.com','wsj.com','espn.com','variety.com','deadline.com','hollywoodreporter.com','technologyreview.com','nasa.gov','pib.gov.in','upsc.gov.in','ssc.gov.in')
POPULAR_TERMS=('breaking','live','major','record','world cup','election','launch','release','trailer','box office','ai','google','apple','microsoft','nvidia','openai','recruitment','scheme','योजना','भर्ती')
def story_priority(item):
 url,title,cat,domain=item
 t=title.lower()
 major=any(domain==d or domain.endswith('.'+d) for d in MAJOR_PUBLISHERS)
 popular=any(term in t for term in POPULAR_TERMS)
 return (not major,not popular,title.lower())

# Website-first discovery: visit publisher home/category pages before RSS fallback.
# Each website is attempted once per category, with bounded concurrency and timeouts.
WEBSITE_PATHS={'world-news':'/world','technology':'/technology','business':'/business','sports':'/sport','movies-entertainment':'/entertainment','automobiles':'/auto','health-science':'/science','government-schemes':'/','sarkari-naukri':'/','private-vacancy':'/','gaming':'/gaming','environment':'/environment','travel':'/travel','education':'/education','lifestyle':'/lifeandstyle'}
# Every configured publisher is eligible for direct discovery, including
# publishers previously represented only by Google News search URLs.
# Rotate the broader pool to bound HTTP traffic and preserve article-writing time.
def rotating_publisher_websites():
 direct={(cat,domain) for _,cat,domain in DIRECT_SOURCES}
 options={}
 for feed,cat,domain in FEEDS:
  if domain in ('reddit.com','news.google.com') or (cat,domain) in direct:continue
  if not domain or domain.endswith('google.com'):continue
  key=(cat,domain)
  if key not in options:
   options[key]=(feed,cat,domain) if feed.startswith('https://'+domain+'/') and '/rss' not in feed and '/feed' not in feed else ('https://'+domain+'/',cat,domain)
 values=list(options.values())
 if not values:return []
 limit=max(1,min(100,int(os.getenv('PUBLISHER_WEBSITES_PER_RUN','36'))))
 start=(dt.datetime.now(UTC).date().toordinal()*limit)%len(values)
 return [values[(start+i)%len(values)] for i in range(min(limit,len(values)))]

def website_stories(item):
 feed,cat,domain=item
 from urllib.parse import urljoin
 base=feed if item in DIRECT_SOURCES else 'https://'+domain+WEBSITE_PATHS.get(cat,'/')
 try:
  response=requests.get(base,timeout=(5,10),headers={'User-Agent':'Mozilla/5.0 (compatible; GlobeWireDaily/1.0)'})
  response.raise_for_status()
  if not allowed(response.url,domain) or 'html' not in response.headers.get('content-type','').lower():return item,[]
  soup=BeautifulSoup(response.text[:1000000],'html.parser')
  stories=[];seen_urls=set()
  selectors='article a[href], h2 a[href], h3 a[href], main a[href], .job-list a[href], .job-listing a[href], .job-title a[href], .post-title a[href], .entry-title a[href], [class*="job"] a[href]'
  # Universal discovery: semantic links, headline anchors, and structured article links.
  # Keep bounded scans; reject category/navigation links below.
  selectors+=', a[href][title], a[href][aria-label], [itemprop="headline"] a[href], a[href*="/20"], a[href*="/news/"], a[href*="/article/"]'
  for a in soup.select(selectors)[:900]:
   url=urljoin(response.url,a.get('href','')).split('#')[0].split('?')[0]
   title=clean(a.get_text(' ',strip=True) or a.get('aria-label','') or a.get('title',''))
   if not allowed(url,domain) or url in seen_urls or len(title)<24 or len(title)>210:continue
   if url.rstrip('/')==response.url.rstrip('/'):continue
   if any(z in url.lower() for z in ('/tag/','/author/','/category/','/topics/','/video/','/live/','/search/','/login','/signup','/privacy','/contact','/about','/taxonomy/','/complain/','/submission/','/articlelist/','/topic/','/forum/','/deals/','/collections/')):continue
   if len(urlparse(url).path.strip('/').split('/'))<2 and not re.search(r'\d{4,}|[a-z0-9]+[-_][a-z0-9]+',urlparse(url).path):continue
   if cat in ('sarkari-naukri','private-vacancy') and not re.search(r'job|vacan|recruit|hiring|career|भर्ती|नौकरी|पद|result|admit|exam',title+' '+url,re.I):continue
   seen_urls.add(url);stories.append((url,title,cat,domain))
   if len(stories)>=25:break
  return item,stories
 except (requests.RequestException,ValueError) as exc:
  print('Direct source fetch failed',domain,type(exc).__name__,flush=True)
  return item,[]

# Google Trends is a discovery signal only; articles always come from publishers.
def google_trending_terms():
 terms=set()
 for region in ('IN','US'):
  try:
   url='https://trends.google.com/trending?geo='+region
   r=requests.get(url,timeout=(5,10),headers={'User-Agent':'Mozilla/5.0'})
   if not r.ok:continue
   soup=BeautifulSoup(r.text[:700000],'html.parser')
   for a in soup.select('a[href*="explore?q="],a[href*="search?q="]'):
    from urllib.parse import parse_qs
    q=parse_qs(urlparse(a.get('href','')).query).get('q',[''])[0].strip().lower()
    if 3<=len(q)<=70:terms.add(q)
  except (requests.RequestException,ValueError):pass
 print('Google Trends discovered terms:',len(terms),flush=True)
 return terms

# Google News is the first discovery layer; publisher pages remain the factual source.
GOOGLE_QUERIES={
 'world-news':'world breaking news','technology':'technology AI','business':'business economy',
 'sports':'sports cricket football','health-science':'health science research',
 'movies-entertainment':'movies entertainment','gaming':'video games',
 'automobiles':'automobile electric vehicles','education':'education universities',
 'environment':'climate environment','government-schemes':'India government schemes',
 'sarkari-naukri':'India government recruitment official notification',
 'private-vacancy':'private sector job openings hiring application',
 'travel':'travel tourism','lifestyle':'lifestyle wellness'}
def resolve_google_news(link):
 """Resolve Google's opaque RSS ID to its original publisher URL."""
 from urllib.parse import urlencode
 if (urlparse(link).hostname or '')!='news.google.com':return link
 try:
  page=requests.get(link,timeout=(4,9),headers={'User-Agent':'Mozilla/5.0','Cookie':'CONSENT=YES+cb; SOCS=CAI'})
  if page.url!=link and (urlparse(page.url).hostname or '')!='news.google.com':return page.url
  match=re.search(r'data-n-a-id="([^"]+)"[^>]*data-n-a-ts="([^"]+)"[^>]*data-n-a-sg="([^"]+)"',page.text)
  if match:gid,ts,sg=match.groups()
  else:
   gid=urlparse(link).path.rstrip('/').split('/')[-1]
   ts_match=re.search(r'data-n-a-ts="([^"]+)"',page.text)
   sg_match=re.search(r'data-n-a-sg="([^"]+)"',page.text)
   if not ts_match or not sg_match:return ''
   ts,sg=ts_match.group(1),sg_match.group(1)
  inner=json.dumps(['garturlreq',[['X','X',['X','X'],None,None,1,1,'US:en',None,1,None,None,None,None,None,0,1],'X','X',1,[1,1,1],1,1,None,0,0,None,0],gid,int(ts),sg],separators=(',',':'))
  payload={'f.req':json.dumps([[['Fbv4je',inner,None,'generic']]],separators=(',',':'))}
  response=requests.post('https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je',data=payload,headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},timeout=(4,9))
  response.raise_for_status()
  for row in response.text.splitlines():
   if 'Fbv4je' not in row:continue
   try:
    records=json.loads(row)
    for record in records:
     if isinstance(record,list) and len(record)>2 and record[1]=='Fbv4je':
      decoded=json.loads(record[2])
      target=decoded[1]
      if isinstance(target,str) and target.startswith('https://'):return target
   except (ValueError,TypeError,IndexError):continue
  return ''
 except (requests.RequestException,ValueError,TypeError,IndexError):return ''

def google_news_stories(cat):
 from urllib.parse import quote
 base=GOOGLE_QUERIES.get(cat,cat.replace('-',' '))
 # Rotate related searches each hour, without accepting unverified sources.
 variants=(base,cat.replace('-',' ')+' latest',base+' breaking',base+' announcements')
 hour=dt.datetime.now(UTC).hour
 query=' OR '.join('('+variants[(hour+offset)%len(variants)]+')' for offset in range(3))+' when:7d'
 url='https://news.google.com/rss/search?q='+quote(query)+'&hl=en-IN&gl=IN&ceid=IN:en'
 try:
  resp=requests.get(url,timeout=(5,12),headers={'User-Agent':'Mozilla/5.0'})
  resp.raise_for_status()
  entries=feedparser.parse(resp.content).entries[:35]
  stories=[]
  for entry in entries:
   # Resolve the Google News article link; never use the Google URL as evidence.
   link=entry.get('link','')
   if not link.startswith('https://'):continue
   target=resolve_google_news(link)
   host=(urlparse(target).hostname or '').lower()
   if not target or host.endswith('google.com') or host.endswith('googleusercontent.com'):continue
   if not (any(allowed(target,d) for _,_,d in FEEDS) or any(allowed(target,d) for d in REGIONAL_PORTALS.get(cat,()))):continue
   stories.append((target,clean(entry.get('title','')),cat,host))
  print('Google News',cat,'publisher stories',len(stories),flush=True)
  return stories
 except (requests.RequestException,ValueError):return []

# Regional discovery uses established job and scheme aggregators as leads.
# Source URLs are attributed; do not infer application deadlines from search snippets.
REGIONAL_STATE_NAMES=tuple(INDIA_REGIONS)
REGIONAL_PORTALS={
 'sarkari-naukri':('freejobalert.com','sarkariresult.com','sarkariresult.com.cm','sahisarkarijobs.in','navbharattimes.indiatimes.com','officialsarkarinaukri.com','indiasarkarinaukri.com','mysarkarinaukri.com','jagranjosh.com','sarkaripaper.in','niyuktipost.com'),
 'government-schemes':('myscheme.gov.in','india.gov.in','jagranjosh.com','mzonews.com','govtschemes.in','bharatjobzone.com','sarkarikyp.com'),
 'private-vacancy':('freejobalert.com','mysarkarinaukri.com','jagranjosh.com','naukri.com','indeed.com','linkedin.com','diversejobseeker.com')
}
def regional_search_stories(cat):
 from urllib.parse import quote
 if cat not in REGIONAL_PORTALS:return []
 hour=dt.datetime.now(UTC).hour
 # Spread regional coverage across runs instead of querying every state each hour.
 states=[REGIONAL_STATE_NAMES[(hour*3+i)%len(REGIONAL_STATE_NAMES)] for i in range(3)]
 portals=REGIONAL_PORTALS[cat]
 queries=[]
 for state in states:
  keyword='government scheme yojana benefits' if cat=='government-schemes' else ('private jobs hiring' if cat=='private-vacancy' else 'sarkari naukri recruitment vacancy')
  queries.append(state+' '+keyword+' latest 2026')
 results=[]
 for query in queries:
  try:
   response=requests.get('https://www.bing.com/search?format=rss&q='+quote(query),timeout=(5,12),headers={'User-Agent':'Mozilla/5.0'})
   response.raise_for_status()
   for entry in feedparser.parse(response.content).entries[:20]:
    target=entry.get('link','').strip()
    host=(urlparse(target).hostname or '').lower()
    title=clean(entry.get('title',''))
    if not target.startswith('https://') or len(title)<25:continue
    if not any(host==domain or host.endswith('.'+domain) for domain in portals):continue
    results.append((target,title,cat,host))
  except (requests.RequestException,ValueError):continue
 print('Regional discovery',cat,'publisher stories',len(results),flush=True)
 return results

def bing_search_stories(cat):
 """Discover publisher URLs through Bing's public RSS search, with no API key.
 Search results are leads only: source_text() must verify the original page.
 """
 from urllib.parse import quote
 base=GOOGLE_QUERIES.get(cat,cat.replace('-',' '))
 variants=(base+' latest news',cat.replace('-',' ')+' announcement',base+' official update')
 query=variants[dt.datetime.now(UTC).hour%len(variants)]
 url='https://www.bing.com/search?format=rss&q='+quote(query)
 try:
  response=requests.get(url,timeout=(5,12),headers={'User-Agent':'Mozilla/5.0'})
  response.raise_for_status()
  stories=[]
  for entry in feedparser.parse(response.content).entries[:30]:
   target=entry.get('link','').strip()
   host=(urlparse(target).hostname or '').lower()
   title=clean(entry.get('title',''))
   if not target.startswith('https://') or len(title)<25:continue
   if not (any(allowed(target,d) for _,_,d in FEEDS) or any(allowed(target,d) for d in REGIONAL_PORTALS.get(cat,()))):continue
   if host.endswith('bing.com') or host.endswith('microsoft.com'):continue
   stories.append((target,title,cat,host))
  print('Bing search',cat,'publisher stories',len(stories),flush=True)
  return stories
 except (requests.RequestException,ValueError):
  return []

SOURCE_DIAGNOSTICS=Counter()
SOURCE_DIAGNOSTICS_LOCK=threading.Lock()
def source_metric(domain,metric,amount=1):
 with SOURCE_DIAGNOSTICS_LOCK: SOURCE_DIAGNOSTICS[(domain,metric)]+=amount

QUEUE_FILE=PENDING/'_discovery_queue.json'
QUEUE_MAX_AGE_HOURS=max(1,int(os.getenv('QUEUE_MAX_AGE_HOURS','36')))
QUEUE_LIMIT=max(30,int(os.getenv('QUEUE_LIMIT','120')))
def useful_lead(row):
 if not isinstance(row,(list,tuple)) or len(row)!=4 or not all(isinstance(x,str) for x in row):return False
 url,title,cat,domain=row
 if len(title)<24 or not allowed(url,domain) or len(url)>500:return False
 if any(part in urlparse(url).path.lower() for part in ('/taxonomy/','/complain/','/submission/','/articlelist/','/category/','/tag/','/topic/','/forum/','/deals/','/collections/')):return False
 if not (any(allowed(url,d) for _,_,d in FEEDS) or any(allowed(url,d) for d in REGIONAL_PORTALS.get(cat,()))):return False
 if (POSTS/(hashlib.sha256(url.encode()).hexdigest()[:12]+'.json')).exists():return False
 pending=PENDING/(hashlib.sha256(url.encode()).hexdigest()[:12]+'.json')
 if pending.exists():
  try:
   record=json.loads(pending.read_text(encoding='utf-8'))
   if record.get('status')=='source_unavailable' and not (record.get('en_body') or record.get('hi_body')):return False
  except (OSError,ValueError):pass
 return True
def load_discovery_queue():
 try:
  raw=json.loads(QUEUE_FILE.read_text(encoding='utf-8'))
  # Legacy list queues are dropped: they have no age metadata and accumulated stale headlines.
  if not isinstance(raw,dict):return []
  cutoff=dt.datetime.now(UTC)-dt.timedelta(hours=QUEUE_MAX_AGE_HOURS)
  rows=[]
  for entry in raw.get('items',[]):
   if not isinstance(entry,dict):continue
   try:added=dt.datetime.fromisoformat(entry['added_at'].replace('Z','+00:00'))
   except (KeyError,TypeError,ValueError):continue
   story=entry.get('story')
   if added>=cutoff and useful_lead(story):rows.append(tuple(story))
  return rows[:QUEUE_LIMIT]
 except (OSError,ValueError,TypeError):return []
def save_discovery_queue(rows):
 now=dt.datetime.now(UTC)
 old={}
 try:
  raw=json.loads(QUEUE_FILE.read_text(encoding='utf-8'))
  if isinstance(raw,dict):
   for entry in raw.get('items',[]):
    if isinstance(entry,dict) and isinstance(entry.get('story'),list):old[entry['story'][0]]=entry.get('added_at')
 except (OSError,ValueError,TypeError,KeyError,IndexError):pass
 entries=[];seen=set()
 for row in rows:
  if not useful_lead(row) or row[0] in seen:continue
  seen.add(row[0])
  added=old.get(row[0],now.isoformat())
  try:age=now-dt.datetime.fromisoformat(added.replace('Z','+00:00'))
  except (ValueError,TypeError):age=dt.timedelta(days=99)
  if age>dt.timedelta(hours=QUEUE_MAX_AGE_HOURS):continue
  entries.append({'story':list(row),'added_at':added})
  if len(entries)>=QUEUE_LIMIT:break
 temp=QUEUE_FILE.with_suffix('.tmp')
 temp.write_text(json.dumps({'version':2,'items':entries},ensure_ascii=False),encoding='utf-8')
 temp.replace(QUEUE_FILE)

def candidates():
 seen=set()
 counts=published_categories()
 trending_terms=google_trending_terms()
 missing={cat for cat,n in counts.items() if n==0}
 print('Categories without a published article:',', '.join(sorted(missing)) or 'none',flush=True)
 # Resume verified drafts first instead of spending calls on new headlines.
 # Finish the most complete bilingual drafts before starting any new story.
 def pending_priority(path):
  try:
   record=json.loads(path.read_text(encoding='utf-8'))
   complete=sum(complete_body(record.get(lang+'_body',''),lang) for lang in ('en','hi'))
   progress=sum(min(words(record.get(lang+'_body','')),MIN_WORDS) for lang in ('en','hi'))
   blocked=record.get('blocked_until','')>dt.datetime.now(UTC).isoformat()
   return (blocked,record.get('category') not in missing,-complete,-progress,path.name)
  except (OSError,ValueError,TypeError):return (True,0,0,path.name)
 for path in sorted((p for p in PENDING.glob('*.json') if p!=QUEUE_FILE),key=pending_priority):
  try:
   record=json.loads(path.read_text(encoding='utf-8'))
   url=record.get('source',''); title=record.get('source_title','')
   domain=urlparse(url).hostname or ''
   if record.get('blocked_until','')>dt.datetime.now(UTC).isoformat():continue
   if title and record.get('category') in {c for _,c,_ in FEEDS} and (any(allowed(url,d) for _,_,d in FEEDS) or any(allowed(url,d) for d in REGIONAL_PORTALS.get(record.get('category'),()))) and url not in seen:
    seen.add(url)
    yield url,title,record.get('category','technology'),domain
  except (OSError,ValueError):pass
 # Check explicit source pages ahead of broad search engines.
 with ThreadPoolExecutor(max_workers=10) as pool:
  direct_results=list(pool.map(website_stories,DIRECT_SOURCES))
 direct_groups={}
 for (feed,cat,domain),items in direct_results:
  print('Direct source',domain,'category',cat,'candidates',len(items),flush=True)
  source_metric(domain,'website_candidates',len(items))
  for story in items:
   if story[0] not in seen:
    seen.add(story[0]);direct_groups.setdefault(cat,[]).append(story)
 for i in range(max(map(len,direct_groups.values()),default=0)):
  for cat in sorted(direct_groups,key=lambda c:(c not in missing,counts.get(c,0),c)):
   if i<len(direct_groups[cat]):yield direct_groups[cat][i]
 # Google News category search is the first fresh-news discovery source.
 google_groups={cat:[] for cat in GOOGLE_QUERIES}
 with ThreadPoolExecutor(max_workers=7) as pool:
  google_results=list(pool.map(google_news_stories,google_groups))
 for cat,stories in zip(google_groups,google_results):
  for story in stories:
   if story[0] not in seen:
    seen.add(story[0]);google_groups[cat].append(story)
 for i in range(max(map(len,google_groups.values()),default=0)):
  for cat in sorted(google_groups,key=lambda c:(c not in missing,counts.get(c,0),c)):
   if i<len(google_groups[cat]):yield google_groups[cat][i]
 # Independent keyword search discovery complements Google News and RSS.
 # Only approved original publisher URLs proceed to factual extraction.
 bing_groups={cat:[] for cat in GOOGLE_QUERIES}
 with ThreadPoolExecutor(max_workers=7) as pool:
  bing_results=list(pool.map(bing_search_stories,bing_groups))
 for cat,stories in zip(bing_groups,bing_results):
  for story in stories:
   if story[0] not in seen:
    seen.add(story[0]);bing_groups[cat].append(story)
 for i in range(max(map(len,bing_groups.values()),default=0)):
  for cat in sorted(bing_groups,key=lambda x:(x not in missing,counts.get(x,0),x)):
   if i<len(bing_groups[cat]):yield bing_groups[cat][i]
 # Region-wise aggregators surface state job and scheme updates.
 with ThreadPoolExecutor(max_workers=3) as pool:
  regional_results=list(pool.map(regional_search_stories,REGIONAL_PORTALS))
 for cat,stories in zip(REGIONAL_PORTALS,regional_results):
  for story in stories:
   if story[0] not in seen:
    seen.add(story[0]);yield story
 # First search major publisher websites across every category.
 groups={cat:[] for _,cat,_ in FEEDS}
 with ThreadPoolExecutor(max_workers=10) as pool:
  website_results=list(pool.map(website_stories,rotating_publisher_websites()))
 for (feed,cat,domain),stories in website_results:
  print('Website',domain,'category',cat,'candidates',len(stories),flush=True)
  source_metric(domain,'website_candidates',len(stories))
  for story in stories:
   if story[0] not in seen:
    seen.add(story[0]);groups[cat].append(story)
 for cat in groups:groups[cat].sort(key=lambda item:(not any(t in item[1].lower() for t in trending_terms),*story_priority(item)))
 for i in range(max(map(len,groups.values()),default=0)):
  for cat in sorted(groups,key=lambda c:(c not in missing,counts.get(c,0),c)):
   if i<len(groups[cat]):yield groups[cat][i]
 # Only after publisher websites, use RSS feeds as fallback discovery.
 groups={cat:[] for _,cat,_ in FEEDS}
 def read_feed(item):
  feed,cat,domain=item
  try:
   r=requests.get(feed,timeout=(5,10),headers={'User-Agent':'Mozilla/5.0 (compatible; GlobalTechDaily/1.0)'})
   r.raise_for_status()
   return item,feedparser.parse(r.content).entries[:30]
  except (requests.RequestException,ValueError):
   return item,[]
 # Cap workers: dozens of global sources without making Actions run for hours.
 with ThreadPoolExecutor(max_workers=10) as pool:
  results=list(pool.map(read_feed,FEEDS+rotating_local_feeds()+rotating_social_feeds()))
 for (feed,cat,domain),entries in results:
  print('Feed',domain,'entries',len(entries),flush=True)
  source_metric(domain,'feed_entries',len(entries))
  for e in entries:
   url=e.get('link','').strip(); title=clean(e.get('title',''))
   if 'news.google.com' in (urlparse(url).hostname or ''):
    url=resolve_google_news(url)
   if not allowed(url,domain) or not title or url in seen: continue
   seen.add(url)
   published=e.get('published_parsed') or e.get('updated_parsed')
   if not published: continue
   try: age=(dt.datetime.now(UTC).date()-dt.date(*published[:3])).days
   except (TypeError,ValueError): continue
   if age<0 or age>7:continue
   actual_cat=category(title,cat)
   groups[actual_cat].append((url,title,actual_cat,domain))
   source_metric(domain,'feed_candidates')
 for cat in groups:
  groups[cat].sort(key=lambda item:(not any(t in item[1].lower() for t in trending_terms),*story_priority(item)))
 for i in range(max(map(len,groups.values()),default=0)):
  for cat in sorted(groups, key=lambda c:(c not in missing, counts.get(c,0),c)):
   if i<len(groups[cat]): yield groups[cat][i]

# Detect the same news event syndicated under different publisher URLs.
# Keep all existing articles; block only near-identical NEW stories.
DUPLICATE_STOPWORDS={'the','and','for','with','from','this','that','after','over','into','says','said','news','latest','update','updates','today','india','indian','a','an','of','to','in','on','at','is','are','as','by','has','have'}
def story_tokens(value):
 normalized=re.sub(r'[^a-z0-9\\s]',' ',str(value or '').casefold())
 return {w for w in normalized.split() if len(w)>2 and w not in DUPLICATE_STOPWORDS}
def same_story(a,b):
 x,y=story_tokens(a),story_tokens(b)
 if len(x)<4 or len(y)<4:return False
 common=len(x & y)
 return common>=4 and (common/min(len(x),len(y))>=0.86 or common/len(x | y)>=0.72)
def published_story_index():
 index=[]
 for path in POSTS.glob('*.json'):
  try:
   p=json.loads(path.read_text(encoding='utf-8'))
   if isinstance(p,dict):
    index.append((str(p.get('source','')).rstrip('/'),str(p.get('source_title') or p.get('en_title') or ''),str(p.get('category') or '')))
  except (OSError,ValueError,TypeError):continue
 return index
def duplicate_story(url,title,cat,index):
 target=str(url or '').rstrip('/')
 for old_url,old_title,old_cat in index:
  if target and target==old_url:return True
  if cat==old_cat and same_story(title,old_title):return True
 return False

def main():
 if os.getenv('AUTO_POST','false').lower()!='true':print('AUTO_POST disabled');return 0
 remaining=POSTS_PER_RUN
 print('Target posts this run:',remaining,flush=True)
 if not remaining:return 0
 if not any(os.getenv(k) for k in ('GROQ_API_KEY','GEMINI_API_KEY','OPENROUTER_API_KEY','OPENAI_API_KEY')):
  print('No AI provider configured');return 0
 published=0; inspected=0; category_published={}
 discovery_deadline=time.monotonic()+4*60  # Reserve time for article writing.
 deadline=time.monotonic()+15*60  # Reserve remaining time for build and Git push.
 print('Minimum target per category:',MIN_POSTS_PER_CATEGORY,flush=True)
 published_index=published_story_index()
 publication_lock=threading.RLock()
 def process_story(story):
  url,title,cat,domain=story
  if time.monotonic()>=deadline:return None
  if cat not in ({c for _,c,_ in FEEDS}|set(REGIONAL_PORTALS)):return None
  post_id=hashlib.sha256(url.encode()).hexdigest()[:12]
  if (POSTS/(post_id+'.json')).exists():return None
  with publication_lock:
   is_duplicate=duplicate_story(url,title,cat,published_index)
  if is_duplicate:
   print('Skipping duplicate news event:',title[:85],flush=True)
   return None
  pending=PENDING/(post_id+'.json')
  try:state=json.loads(pending.read_text()) if pending.exists() else {}
  except ValueError:state={}
  # Avoid retrying the same insufficient or failed source repeatedly within a day.
  if state.get('blocked_until','')>dt.datetime.now(UTC).isoformat():
   print('Pending draft cooling down:',post_id,flush=True)
   return None
  if any(complete_body(state.get(lang+'_body',''),lang) for lang in ('en','hi')):
   print('Resuming saved draft:',post_id,'English',words(state.get('en_body','')),'Hindi',words(state.get('hi_body','')),flush=True)
  if cat=='private-vacancy' and not (any(allowed(url,d) for _,c,d in FEEDS if c=='private-vacancy') or any(allowed(url,d) for d in REGIONAL_PORTALS['private-vacancy'])):
   return None
  if cat=='sarkari-naukri' and not (any(allowed(url,d) for d in OFFICIAL_JOB_DOMAINS) or any(allowed(url,d) for d in REGIONAL_PORTALS['sarkari-naukri'])):
   print('Skipping recruitment story from unapproved source:',url,flush=True)
   return None
  text=source_text(url,domain)
  if (not text.strip() or words(text)<65) and not all(complete_body(state.get(lang+'_body',''),lang) for lang in ('en','hi')):
   # Preserve completed language drafts even if the publisher temporarily blocks scraping.
   state.update({'source':url,'source_title':title,'category':cat,'status':'source_unavailable','blocked_until':(dt.datetime.now(UTC)+dt.timedelta(hours=12)).isoformat(),'source_words':words(text)})
   if pending.exists(): save_state(pending,state)
   print('Skipping source before AI:',title[:65],'words',words(text),flush=True)
   return None
  state.update({'source':url,'source_title':title,'category':cat,'status':'draft','updated_at':dt.datetime.now(UTC).isoformat()})
  # Generate the two languages concurrently; save draft updates under a per-story lock.
  def generate_language(lang):
   if time.monotonic()>=deadline or CALLS>=MAX_CALLS:return lang,None,None
   prior=state.get(lang+'_body','')
   prompt=article_prompt(lang,title,url,text,cat)
   if prior and not complete_body(prior,lang):
    prompt += ('\\nEXISTING ORIGINAL DRAFT (preserve its accurate material; return a COMPLETE revised body, not only an addendum):\\n'+prior[:24000]+'\\nImprove clarity and completeness using only SOURCE-SUPPORTED context. Never fabricate details.')
   data,provider=call_provider(prompt)
   return lang,data,provider
  languages=[lang for lang in ('en','hi') if not complete_body(state.get(lang+'_body',''),lang)]
  with ThreadPoolExecutor(max_workers=2) as language_pool:
   results=list(language_pool.map(generate_language,languages))
  for lang,data,provider in results:
   if isinstance(data,dict):
    body=str(data.get('body') or '')
    if complete_body(body,lang) and len(str(data.get('title') or ''))>=20:
     state[lang+'_body']=body;state[lang+'_title']=str(data['title'])
     state[lang+'_meta']=str(data.get('meta') or '')
     state[lang+'_keywords']=str(data.get('keywords') or '')
     print('Draft ready:',lang,'words',words(body),'via',provider,flush=True)
    else:print('Draft unusable:',lang,'words',words(body),'via',provider,flush=True)
   if not complete_body(state.get(lang+'_body',''),lang):
    state['blocked_until']=(dt.datetime.now(UTC)+dt.timedelta(hours=12)).isoformat()
   save_state(pending,state)
  if all(complete_body(state.get(lang+'_body',''),lang) for lang in ('en','hi')):
   article={k:state.get(k,'') for k in ('en_title','hi_title','en_body','hi_body','en_meta','hi_meta','en_keywords','hi_keywords')}
   article.update(id=post_id,source=url,date=dt.datetime.now(UTC).isoformat(),source_title=title,category=cat,image_kind='conceptual')
   save_state(POSTS/(post_id+'.json'),article)
   pending.unlink(missing_ok=True)
   with publication_lock:
    published_index.append((url.rstrip('/'),title,cat))
   print('Published',post_id,cat,flush=True)
  else:save_state(pending,state)
  return cat if (POSTS/(post_id+'.json')).exists() else None

 backlog=load_discovery_queue()
 print('Carried-over news candidates:',len(backlog),flush=True)
 stories=[]
 seen_urls={item[0] for item in stories}
 # Always discover fresh source links, even when the persisted queue is full.
 # Retain old leads, but reserve room for new discoveries each run.
 new_leads=[]
 for story in candidates():
  if story[0] not in seen_urls and useful_lead(story):
   new_leads.append(story)
   seen_urls.add(story[0])
  if len(new_leads)>=POSTS_PER_RUN:break
  if time.monotonic()>=discovery_deadline:break
 if new_leads:
  stories=new_leads+backlog
 else:
  stories=backlog
 print('Direct source priority candidates:',sum(any(allowed(row[0],d) for _,_,d in DIRECT_SOURCES) for row in new_leads),flush=True)
 print('Fresh discovered leads:',len(new_leads),flush=True)
 # Persist discovered leads before AI calls; the next run resumes them even if quota expires.
 save_discovery_queue(stories)
 print('Saved news candidates for retry:',len(stories),flush=True)
 # Prioritize two verified articles per category before filling additional slots.
 grouped={}
 for story in stories:
   grouped.setdefault(story[2],[]).append(story)
   source_metric(story[3],'queued')
 ordered=[]
 # Give categories with the fewest existing published stories first access to
 # limited AI calls; retain all other categories as eligible afterward.
 historical_counts=published_categories()
 categories=sorted(grouped,key=lambda cat:(historical_counts.get(cat,0),cat))
 missing_candidates=sorted(set(c for _,c,_ in FEEDS)-set(grouped))
 print('Categories without usable leads:',', '.join(missing_candidates) or 'none',flush=True)
 print('Verified candidate queue per category:',{cat:len(grouped[cat]) for cat in categories},flush=True)
 print('Category processing priority:',', '.join(categories),flush=True)
 for round_number in range(MIN_POSTS_PER_CATEGORY):
  for cat in categories:
   if grouped[cat]:ordered.append(grouped[cat].pop(0))
 # After the minimum-priority passes, there is no per-category maximum.
 while any(grouped.values()):
  for cat in categories:
   if grouped[cat]:ordered.append(grouped[cat].pop(0))
 article_workers=10
 print('Parallel article workers:',article_workers,flush=True)
 with ThreadPoolExecutor(max_workers=article_workers) as article_pool:
  futures={}
  next_story=iter(ordered)
  while time.monotonic()<deadline and published<remaining and CALLS<MAX_CALLS:
   while len(futures)<article_workers and published+len(futures)<remaining:
    try:story=next(next_story)
    except StopIteration:break
    futures[article_pool.submit(process_story,story)]=story
    source_metric(story[3],'attempted')
   if not futures:break
   done=next(as_completed(futures))
   story=futures.pop(done)
   try:cat=done.result()
   except Exception as exc:
    print('Article worker failed:',type(exc).__name__,str(exc)[:180],flush=True)
    source_metric(story[3],'worker_errors')
    continue
   if cat:
    source_metric(story[3],'published')
    published+=1
    category_published[cat]=category_published.get(cat,0)+1
 # Retain only recent, valid, bounded leads; stale or unusable items are discarded.
 remaining_queue=[item for item in stories if not (POSTS/(hashlib.sha256(item[0].encode()).hexdigest()[:12]+'.json')).exists()]
 save_discovery_queue(remaining_queue)
 print('Unpublished candidates retained for next run:',len(remaining_queue),flush=True)
 print('SOURCE DIAGNOSTICS BEGIN',flush=True)
 for domain in sorted(set(d for _,_,d in FEEDS)|set(d for d,_ in SOURCE_DIAGNOSTICS)):
  print('SOURCE',domain,' '.join(f'{key}={SOURCE_DIAGNOSTICS[(domain,key)]}' for key in ('feed_entries','feed_candidates','website_candidates','queued','attempted','published','worker_errors')),flush=True)
 print('SOURCE DIAGNOSTICS END',flush=True)
 print('AI requests used this run:',CALLS,'of',MAX_CALLS,flush=True)
 print('Published',published,'of',remaining,'target categories',flush=True)
 print('Per-category published counts:',dict(sorted(category_published.items())),flush=True)
 print('Categories reaching target:',', '.join(sorted(cat for cat,n in category_published.items() if n>=MIN_POSTS_PER_CATEGORY)),flush=True)
 print('Categories below two-post target:',', '.join(sorted(set(c for _,c,_ in FEEDS)-{cat for cat,n in category_published.items() if n>=MIN_POSTS_PER_CATEGORY})),flush=True)
 return 0
if __name__=='__main__':sys.exit(main())
