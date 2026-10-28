"""Quota-capped, source-first bilingual publishing. No external AI calls on import."""
import os, sys, json, hashlib, datetime as dt, pathlib, re, html, time
from urllib.parse import urlparse
import requests, feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parents[1]
POSTS=ROOT/'content/posts'; PENDING=ROOT/'content/pending'
POSTS.mkdir(parents=True,exist_ok=True); PENDING.mkdir(parents=True,exist_ok=True)
UTC=dt.timezone.utc
MIN_WORDS=0
MIN_HINDI_WORDS=0
MIN_HINDI_CHARS=int(os.getenv('MIN_HINDI_CHARS','0'))
def complete_body(body,lang):
 return bool(body and body.strip() and len(body.strip())>=MIN_HINDI_CHARS and len(re.findall(r'[.!?।]',body))>=2 and len(body.strip())>=120)
MAX_CALLS=min(100,max(0,int(os.getenv('MAX_AI_CALLS_PER_RUN','60'))))
POSTS_PER_RUN=max(1,min(30,int(os.getenv('POSTS_PER_RUN','30'))))
MIN_SOURCE_WORDS=0
OFFICIAL_JOB_DOMAINS=('upsc.gov.in','ssc.gov.in','rrbcdg.gov.in','indianrailways.gov.in','employmentnews.gov.in','nta.ac.in','gov.in','nic.in')
CALLS=0
# News discovery sources. Official-domain verification occurs BEFORE any AI request.
# Curated global discovery. Publisher RSS is for finding stories; the linked article is
# the factual source. Never treat a Google News redirect as an original source.

# Worldwide source registry: discovery only. Publisher articles must be original,
# independently summarized, attributed and sufficiently substantiated.
FEEDS=[
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
  # Prefer article content; never treat navigation or paywall previews as full reporting.
  for node in soup.select('[data-component="text-block"], [data-testid="paragraph"], .article__content, .entry-content, .post-content, .story-content')[:6]:
   paragraphs=[clean(p.get_text(' ',strip=True)) for p in node.find_all(['p','h2','h3'])]
   paragraphs=[p for p in paragraphs if len(p)>40]
   if paragraphs:candidates.append(' '.join(paragraphs))
  # Reject short navigation snippets rather than manufacture 300 words.
  return max(candidates,key=words,default='')[:24000]
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
   names=sorted(set(names),key=lambda n:(not ('flash-lite' in n),not ('flash' in n),n))
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
PROVIDER_COOLDOWNS=set()
UNAVAILABLE_MODELS=set()
def call_provider(prompt):
 global CALLS
 last=None
 for provider in provider_order():
  if CALLS>=MAX_CALLS:break
  if provider in PROVIDER_COOLDOWNS:continue
  key=os.getenv({'groq':'GROQ_API_KEY','gemini':'GEMINI_API_KEY','openrouter':'OPENROUTER_API_KEY','openai':'OPENAI_API_KEY'}[provider],'').strip()
  if not key:continue
  models=gemini_models(key) if provider=='gemini' else [os.getenv('GROQ_MODEL','openai/gpt-oss-120b') if provider=='groq' else (os.getenv('OPENAI_MODEL','gpt-4.1-mini') if provider=='openai' else os.getenv('OPENROUTER_MODEL','openrouter/free'))]
  for model in dict.fromkeys(models):
   if (provider,model) in UNAVAILABLE_MODELS:continue
   if CALLS>=MAX_CALLS:break
   CALLS+=1
   last=provider
   try:
    if provider=='gemini':
     r=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',headers={'x-goog-api-key':key},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':8192}},timeout=(10,100))
     raw=''.join(p.get('text','') for p in r.json()['candidates'][0]['content']['parts']) if r.ok else ''
    else:
     url=('https://api.groq.com/openai/v1/chat/completions' if provider=='groq' else ('https://api.openai.com/v1/chat/completions' if provider=='openai' else 'https://openrouter.ai/api/v1/chat/completions'))
     r=requests.post(url,headers={'Authorization':'Bearer '+key},json={'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':8192,'temperature':0.2},timeout=(10,110))
     raw=r.json()['choices'][0]['message']['content'] if r.ok else ''
    if not r.ok:
     print('Provider',provider,'model',model,'HTTP',r.status_code,flush=True)
     if r.status_code in (401,402,403,429):PROVIDER_COOLDOWNS.add(provider);break
     if r.status_code==404:
      UNAVAILABLE_MODELS.add((provider,model))
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
 return f'''You are a careful editor for a public-information news site. Write ONE original article in {language}. Return ONLY a JSON object with fields title, body, meta, keywords. Write a complete, professionally edited news report of natural length appropriate to the available verified facts. Aim for 450-800 words when sufficient verified source details exist; use fewer words when the source is limited; never invent, repeat, or pad. Use Markdown ## subheadings. Explain confirmed facts, background, user impact, uncertainties, and what readers can verify, with a clear link to the official source. Write a compelling, curiosity-driven but strictly accurate headline that clearly reflects the verified story. Never use misleading clickbait, fake urgency, unsupported superlatives or invented claims. Do not fabricate quotes, eligibility, deadlines, salaries, recruitment numbers, prices, application steps, or citations. No copied paragraphs. If source is insufficient for a detailed factual article, return {{"title":"","body":"","meta":"","keywords":""}}. Category: {cat}. Source title: {title}. Verified official/source URL: {source}. SOURCE TEXT:\n{source_material[:22000]}'''

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
def website_stories(item):
 feed,cat,domain=item
 path=WEBSITE_PATHS.get(cat,'/')
 # Keep all configured publishers; their sites are the primary discovery surface.
 base='https://'+domain+path
 try:
  response=requests.get(base,timeout=(5,10),headers={'User-Agent':'Mozilla/5.0 (compatible; GlobalTechDaily/1.0)'})
  response.raise_for_status()
  if not allowed(response.url,domain) or 'html' not in response.headers.get('content-type','').lower():return item,[]
  soup=BeautifulSoup(response.text[:900000],'html.parser')
  stories=[]; seen_urls=set()
  for a in soup.select('article a[href], h2 a[href], h3 a[href], main a[href]'):
   from urllib.parse import urljoin
   url=urljoin(response.url,a.get('href','')).split('#')[0].split('?')[0]
   title=clean(a.get_text(' ',strip=True) or a.get('aria-label',''))
   if not allowed(url,domain) or url in seen_urls or len(title)<35 or len(title)>210:continue
   if url.rstrip('/')==base.rstrip('/') or any(z in url.lower() for z in ('/tag/','/author/','/category/','/topics/','/video/','/live/','/search/')):continue
   if len(urlparse(url).path.strip('/').split('/'))<2:continue
   seen_urls.add(url);stories.append((url,title,cat,domain))
   if len(stories)>=15:break
  return item,stories
 except (requests.RequestException,ValueError):return item,[]

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
 query=GOOGLE_QUERIES.get(cat,cat.replace('-',' '))+' when:7d'
 url='https://news.google.com/rss/search?q='+quote(query)+'&hl=en-IN&gl=IN&ceid=IN:en'
 try:
  resp=requests.get(url,timeout=(5,12),headers={'User-Agent':'Mozilla/5.0'})
  resp.raise_for_status()
  entries=feedparser.parse(resp.content).entries[:18]
  stories=[]
  for entry in entries:
   # Resolve the Google News article link; never use the Google URL as evidence.
   link=entry.get('link','')
   if not link.startswith('https://'):continue
   target=resolve_google_news(link)
   host=(urlparse(target).hostname or '').lower()
   if not target or host.endswith('google.com') or host.endswith('googleusercontent.com'):continue
   if not any(allowed(target,d) for _,_,d in FEEDS):continue
   stories.append((target,clean(entry.get('title','')),cat,host))
  print('Google News',cat,'publisher stories',len(stories),flush=True)
  return stories
 except (requests.RequestException,ValueError):return []

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
 for path in sorted(PENDING.glob('*.json'),key=pending_priority):
  try:
   record=json.loads(path.read_text(encoding='utf-8'))
   url=record.get('source',''); title=record.get('source_title','')
   domain=urlparse(url).hostname or ''
   if title and record.get('category') in {c for _,c,_ in FEEDS} and any(allowed(url,d) for _,_,d in FEEDS) and url not in seen:
    seen.add(url)
    yield url,title,record.get('category','technology'),domain
  except (OSError,ValueError):pass
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
 # First search major publisher websites across every category.
 groups={cat:[] for _,cat,_ in FEEDS}
 with ThreadPoolExecutor(max_workers=10) as pool:
  website_results=list(pool.map(website_stories,FEEDS))
 for (feed,cat,domain),stories in website_results:
  print('Website',domain,'category',cat,'candidates',len(stories),flush=True)
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
  results=list(pool.map(read_feed,FEEDS))
 for (feed,cat,domain),entries in results:
  print('Feed',domain,'entries',len(entries),flush=True)
  for e in entries:
   url=e.get('link','').strip(); title=clean(e.get('title',''))
   if not allowed(url,domain) or not title or url in seen: continue
   seen.add(url)
   published=e.get('published_parsed') or e.get('updated_parsed')
   if not published: continue
   try: age=(dt.datetime.now(UTC).date()-dt.date(*published[:3])).days
   except (TypeError,ValueError): continue
   if age<0 or age>7:continue
   actual_cat=category(title,cat)
   groups[actual_cat].append((url,title,actual_cat,domain))
 for cat in groups:
  groups[cat].sort(key=lambda item:(not any(t in item[1].lower() for t in trending_terms),*story_priority(item)))
 for i in range(max(map(len,groups.values()),default=0)):
  for cat in sorted(groups, key=lambda c:(c not in missing, counts.get(c,0),c)):
   if i<len(groups[cat]): yield groups[cat][i]

def main():
 if os.getenv('AUTO_POST','false').lower()!='true':print('AUTO_POST disabled');return 0
 remaining=POSTS_PER_RUN
 print('Target posts this run:',remaining,flush=True)
 if not remaining:return 0
 if not any(os.getenv(k) for k in ('GROQ_API_KEY','GEMINI_API_KEY','OPENROUTER_API_KEY','OPENAI_API_KEY')):
  print('No AI provider configured');return 0
 published=0; inspected=0; completed_categories=set()
 for url,title,cat,domain in candidates():
  if CALLS>=MAX_CALLS or published>=remaining:break
  if cat in completed_categories:continue
  if cat not in {c for _,c,_ in FEEDS}:continue
  post_id=hashlib.sha256(url.encode()).hexdigest()[:12]
  if (POSTS/(post_id+'.json')).exists():continue
  pending=PENDING/(post_id+'.json')
  try:state=json.loads(pending.read_text()) if pending.exists() else {}
  except ValueError:state={}
  # Avoid retrying the same insufficient or failed source repeatedly within a day.
  if state.get('blocked_until','')>dt.datetime.now(UTC).isoformat():
   print('Pending draft cooling down:',post_id,flush=True)
   continue
  if any(complete_body(state.get(lang+'_body',''),lang) for lang in ('en','hi')):
   print('Resuming saved draft:',post_id,'English',words(state.get('en_body','')),'Hindi',words(state.get('hi_body','')),flush=True)
  inspected+=1
  if cat=='private-vacancy' and not any(allowed(url,d) for _,c,d in FEEDS if c=='private-vacancy'):
   continue
  if cat=='sarkari-naukri' and not any(allowed(url,d) for d in OFFICIAL_JOB_DOMAINS):
   print('Skipping recruitment story without an official government source:',url,flush=True)
   continue
  text=source_text(url,domain)
  if (not text.strip() or len(text.strip())<120) and not all(complete_body(state.get(lang+'_body',''),lang) for lang in ('en','hi')):
   # Preserve completed language drafts even if the publisher temporarily blocks scraping.
   state.update({'source':url,'source_title':title,'category':cat,'status':'source_unavailable','blocked_until':(dt.datetime.now(UTC)+dt.timedelta(hours=12)).isoformat(),'source_words':words(text)})
   if pending.exists(): save_state(pending,state)
   print('Skipping source before AI:',title[:65],'words',words(text),flush=True)
   continue
  state.update({'source':url,'source_title':title,'category':cat,'status':'draft','updated_at':dt.datetime.now(UTC).isoformat()})
  for lang in ('en','hi'):
   if complete_body(state.get(lang+'_body',''),lang):continue
   if CALLS>=MAX_CALLS:break
   prior=state.get(lang+'_body','')
   prompt=article_prompt(lang,title,url,text,cat)
   if prior and not complete_body(prior,lang):
    prompt += ('\nEXISTING ORIGINAL DRAFT (preserve its accurate material; return a COMPLETE revised body, not only an addendum):\n'+prior[:24000]+'\nImprove clarity and completeness using only SOURCE-SUPPORTED context. Never fabricate details.')
   data,provider=call_provider(prompt)
   if isinstance(data,dict):
    body=str(data.get('body') or '')
    if complete_body(body,lang) and len(str(data.get('title') or ''))>=20:
     state[lang+'_body']=body;state[lang+'_title']=str(data['title'])
     state[lang+'_meta']=str(data.get('meta') or '')
     state[lang+'_keywords']=str(data.get('keywords') or '')
     print('Draft ready:',lang,'words',words(body),'via',provider,flush=True)
    else: print('Draft unusable:',lang,'words',words(body),'via',provider,flush=True)
    if not complete_body(state.get(lang+'_body',''),lang): print('Partial draft saved:',lang,'words',words(state.get(lang+'_body','')),'via',provider,flush=True)
   # One failed request does not lead to a provider/model retry this run.
   save_state(pending,state)
   if not data or not complete_body(state.get(lang+'_body',''),lang):
    # Cool down only this failing story; do not retry the same provider immediately.
    state['blocked_until']=(dt.datetime.now(UTC)+dt.timedelta(hours=12)).isoformat()
    break
   save_state(pending,state)
  if all(complete_body(state.get(lang+'_body',''),lang) for lang in ('en','hi')):
   article={k:state.get(k,'') for k in ('en_title','hi_title','en_body','hi_body','en_meta','hi_meta','en_keywords','hi_keywords')}
   article.update(id=post_id,source=url,date=dt.datetime.now(UTC).isoformat(),source_title=title,category=cat,image_kind='conceptual')
   save_state(POSTS/(post_id+'.json'),article)
   pending.unlink(missing_ok=True)
   published+=1
   completed_categories.add(cat)
   print('Published',post_id,cat,flush=True)
  else:save_state(pending,state)
 print('AI requests used this run:',CALLS,'of',MAX_CALLS,flush=True)
 print('Published',published,'of',remaining,'target categories',flush=True)
 print('Categories completed:',', '.join(sorted(completed_categories)),flush=True)
 print('Categories still missing:',', '.join(sorted(set(c for _,c,_ in FEEDS)-completed_categories)),flush=True)
 return 0
if __name__=='__main__':sys.exit(main())
