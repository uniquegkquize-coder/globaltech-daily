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
MIN_WORDS=int(os.getenv('MIN_ARTICLE_WORDS','800'))
MAX_CALLS=min(100,max(0,int(os.getenv('MAX_AI_CALLS_PER_RUN','60'))))
POSTS_PER_RUN=max(1,min(14,int(os.getenv('POSTS_PER_RUN','14'))))
MIN_SOURCE_WORDS=int(os.getenv('MIN_SOURCE_WORDS','450'))
CALLS=0
# News discovery sources. Official-domain verification occurs BEFORE any AI request.
# Curated global discovery. Publisher RSS is for finding stories; the linked article is
# the factual source. Never treat a Google News redirect as an original source.

# Worldwide source registry: discovery only. Publisher articles must be original,
# independently summarized, attributed and sufficiently substantiated.
FEEDS=[
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
  if not allowed(url,domain): return ''
  r=requests.get(url,timeout=(8,18),headers={'User-Agent':'Mozilla/5.0 (compatible; GlobalTechDaily/1.0)'})
  r.raise_for_status()
  if not allowed(r.url,domain) or 'html' not in r.headers.get('content-type','').lower(): return ''
  soup=BeautifulSoup(r.text[:1800000],'html.parser')
  for t in soup(['script','style','nav','footer','aside','form','header']): t.decompose()
  main=soup.find('article') or soup.find('main') or soup
  return '\n'.join(clean(p.get_text(' ',strip=True)) for p in main.find_all(['h2','h3','p','li']) if len(clean(p.get_text(' ',strip=True)))>40)[:24000]
 except (requests.RequestException,ValueError): return ''

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

def provider_order():
 # One generation attempt per language; no repeated model probing.
 order=os.getenv('AI_PROVIDER_ORDER','gemini,groq,openrouter').lower().split(',')
 return [p.strip() for p in order if p.strip() in ('groq','gemini','openrouter')]
# Disable a rate-limited provider for the remainder of this run.
PROVIDER_COOLDOWNS=set()
def call_provider(prompt):
 global CALLS
 if CALLS>=MAX_CALLS: return None,None
 last=None
 for provider in provider_order():
  if CALLS>=MAX_CALLS:break
  if provider in PROVIDER_COOLDOWNS:continue
  key=os.getenv({'groq':'GROQ_API_KEY','gemini':'GEMINI_API_KEY','openrouter':'OPENROUTER_API_KEY'}[provider],'').strip()
  if not key:continue
  CALLS+=1
  last=provider
  try:
   if provider=='gemini':
    model=os.getenv('GEMINI_MODEL','gemini-2.5-flash')
    r=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',headers={'x-goog-api-key':key},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':6500}},timeout=(10,100))
    raw=''.join(p.get('text','') for p in r.json()['candidates'][0]['content']['parts']) if r.ok else ''
   else:
    model=os.getenv('GROQ_MODEL','openai/gpt-oss-120b') if provider=='groq' else os.getenv('OPENROUTER_MODEL','openrouter/free')
    url='https://api.groq.com/openai/v1/chat/completions' if provider=='groq' else 'https://openrouter.ai/api/v1/chat/completions'
    r=requests.post(url,headers={'Authorization':'Bearer '+key},json={'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':6500,'temperature':0.3},timeout=(10,110))
    raw=r.json()['choices'][0]['message']['content'] if r.ok else ''
   if not r.ok:
    print('Provider',provider,'HTTP',r.status_code,'switching provider if available',flush=True)
    if r.status_code in (401,402,403,404,429):PROVIDER_COOLDOWNS.add(provider)
    continue
   data=json_object(raw)
   if isinstance(data,dict) and data.get('body'):
    print('Provider success:',provider,flush=True)
    return data,provider
   print('Provider',provider,'returned unusable JSON; switching if available',flush=True)
  except (requests.RequestException,ValueError,KeyError,IndexError,TypeError) as exc:
   print('Provider',provider,'error',type(exc).__name__,'switching if available',flush=True)
 return None,last

def article_prompt(lang,title,source,source_material,cat):
 language='English' if lang=='en' else 'Hindi (Devanagari)'
 return f'''You are a careful editor for a public-information news site. Write ONE original article in {language}. Return ONLY a JSON object with fields title, body, meta, keywords. The body should have at least {MIN_WORDS} meaningful words IF and ONLY IF the source supports that length; never invent or pad. Use Markdown ## subheadings. Explain confirmed facts, background, user impact, uncertainties, and what readers can verify, with a clear link to the official source. Do not fabricate quotes, eligibility, deadlines, salaries, recruitment numbers, prices, application steps, or citations. No copied paragraphs. If source is insufficient for a detailed factual article, return {{"title":"","body":"","meta":"","keywords":""}}. Category: {cat}. Source title: {title}. Verified official/source URL: {source}. SOURCE TEXT:\n{source_material[:22000]}'''

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

def candidates():
 seen=set()
 counts=published_categories()
 missing={cat for cat,n in counts.items() if n==0}
 print('Categories without a published article:',', '.join(sorted(missing)) or 'none',flush=True)
 # Resume verified drafts first instead of spending calls on new headlines.
 # Finish the most complete bilingual drafts before starting any new story.
 def pending_priority(path):
  try:
   record=json.loads(path.read_text(encoding='utf-8'))
   complete=sum(words(record.get(lang+'_body',''))>=MIN_WORDS for lang in ('en','hi'))
   progress=sum(min(words(record.get(lang+'_body','')),MIN_WORDS) for lang in ('en','hi'))
   blocked=record.get('blocked_until','')>dt.datetime.now(UTC).isoformat()
   return (blocked,record.get('category') not in missing,-complete,-progress,path.name)
  except (OSError,ValueError,TypeError):return (True,0,0,path.name)
 for path in sorted(PENDING.glob('*.json'),key=pending_priority):
  try:
   record=json.loads(path.read_text(encoding='utf-8'))
   url=record.get('source',''); title=record.get('source_title','')
   domain=urlparse(url).hostname or ''
   if title and any(allowed(url,d) for _,_,d in FEEDS) and url not in seen:
    seen.add(url)
    yield url,title,record.get('category','technology'),domain
  except (OSError,ValueError):pass
 # Interleave categories so one technology blog cannot consume the whole quota.
 groups={cat:[] for _,cat,_ in FEEDS}
 def read_feed(item):
  feed,cat,domain=item
  try:
   r=requests.get(feed,timeout=(5,10),headers={'User-Agent':'Mozilla/5.0 (compatible; GlobalTechDaily/1.0)'})
   r.raise_for_status()
   return item,feedparser.parse(r.content).entries[:12]
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
   if age<0 or age>3:continue
   groups[cat].append((url,title,category(title,cat),domain))
 for cat in groups:
  groups[cat].sort(key=lambda item: (-int(any(k in item[1].lower() for k in ('ai ', 'openai', 'google', 'apple', 'microsoft', 'nvidia', 'launch', 'breaking', 'trailer', 'box office', 'netflix', 'bollywood', 'hollywood', 'release', 'recruitment', 'scheme', 'योजना', 'भर्ती'))),item[1]))
 for i in range(max(map(len,groups.values()),default=0)):
  for cat in sorted(groups, key=lambda c:(c not in missing, counts.get(c,0),c)):
   if i<len(groups[cat]): yield groups[cat][i]

def main():
 if os.getenv('AUTO_POST','false').lower()!='true':print('AUTO_POST disabled');return 0
 remaining=POSTS_PER_RUN
 print('Target posts this run:',remaining,flush=True)
 if not remaining:return 0
 if not any(os.getenv(k) for k in ('GROQ_API_KEY','GEMINI_API_KEY','OPENROUTER_API_KEY')):
  print('No AI provider configured');return 0
 published=0; inspected=0; completed_categories=set()
 for url,title,cat,domain in candidates():
  if CALLS>=MAX_CALLS or published>=remaining or inspected>=120:break
  if cat in completed_categories:continue
  post_id=hashlib.sha256(url.encode()).hexdigest()[:12]
  if (POSTS/(post_id+'.json')).exists():continue
  pending=PENDING/(post_id+'.json')
  try:state=json.loads(pending.read_text()) if pending.exists() else {}
  except ValueError:state={}
  # Avoid retrying the same insufficient or failed source repeatedly within a day.
  if state.get('blocked_until','')>dt.datetime.now(UTC).isoformat():
   print('Pending draft cooling down:',post_id,flush=True)
   continue
  if any(words(state.get(lang+'_body',''))>=MIN_WORDS for lang in ('en','hi')):
   print('Resuming saved draft:',post_id,'English',words(state.get('en_body','')),'Hindi',words(state.get('hi_body','')),flush=True)
  inspected+=1
  text=source_text(url,domain)
  if words(text)<MIN_SOURCE_WORDS and not all(words(state.get(lang+'_body',''))>=MIN_WORDS for lang in ('en','hi')):
   # Preserve completed language drafts even if the publisher temporarily blocks scraping.
   state.update({'source':url,'source_title':title,'category':cat,'status':'source_unavailable','blocked_until':(dt.datetime.now(UTC)+dt.timedelta(hours=12)).isoformat(),'source_words':words(text)})
   save_state(pending,state)
   print('Skipping source before AI:',title[:65],'words',words(text),flush=True)
   continue
  state.update({'source':url,'source_title':title,'category':cat,'status':'draft','updated_at':dt.datetime.now(UTC).isoformat()})
  for lang in ('en','hi'):
   if words(state.get(lang+'_body',''))>=MIN_WORDS:continue
   if CALLS>=MAX_CALLS:break
   prior=state.get(lang+'_body','')
   prompt=article_prompt(lang,title,url,text,cat)
   if prior and words(prior)>=400:
    prompt += ('\nEXISTING ORIGINAL DRAFT (preserve its accurate material; return a COMPLETE revised body, not only an addendum):\n'+prior[:24000]+'\nImprove with additional SOURCE-SUPPORTED context until minimum length is met. Never fabricate details.')
   data,provider=call_provider(prompt)
   if isinstance(data,dict):
    body=str(data.get('body') or '')
    if words(body)>=max(300,words(state.get(lang+'_body',''))) and len(str(data.get('title') or ''))>=20:
     state[lang+'_body']=body;state[lang+'_title']=str(data['title'])
     state[lang+'_meta']=str(data.get('meta') or '')
     state[lang+'_keywords']=str(data.get('keywords') or '')
     print('Draft ready:',lang,'words',words(body),'via',provider,flush=True)
    else: print('Draft unusable:',lang,'words',words(body),'via',provider,flush=True)
    if words(state.get(lang+'_body',''))<MIN_WORDS: print('Partial draft saved:',lang,'words',words(state.get(lang+'_body','')),'via',provider,flush=True)
   # One failed request does not lead to a provider/model retry this run.
   save_state(pending,state)
   if not data or words(state.get(lang+'_body','')) < MIN_WORDS:
    # Cool down only this failing story; do not retry the same provider immediately.
    state['blocked_until']=(dt.datetime.now(UTC)+dt.timedelta(hours=12)).isoformat()
    break
   save_state(pending,state)
  if all(words(state.get(lang+'_body',''))>=MIN_WORDS for lang in ('en','hi')):
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
