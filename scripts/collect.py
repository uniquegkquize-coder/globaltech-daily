"""Quota-capped, source-first bilingual publishing. No external AI calls on import."""
import os, sys, json, hashlib, datetime as dt, pathlib, re, html, time
from urllib.parse import urlparse
import requests, feedparser
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parents[1]
POSTS=ROOT/'content/posts'; PENDING=ROOT/'content/pending'
POSTS.mkdir(parents=True,exist_ok=True); PENDING.mkdir(parents=True,exist_ok=True)
UTC=dt.timezone.utc
MIN_WORDS=int(os.getenv('MIN_ARTICLE_WORDS','1200'))
MAX_CALLS=min(2,max(0,int(os.getenv('MAX_AI_CALLS_PER_RUN','2'))))
DAILY_LIMIT=int(os.getenv('DAILY_LIMIT','12'))
MIN_SOURCE_WORDS=int(os.getenv('MIN_SOURCE_WORDS','650'))
CALLS=0
# News discovery sources. Official-domain verification occurs BEFORE any AI request.
FEEDS=[
 ('https://www.nasa.gov/feed/','technology','nasa.gov'),
 ('https://www.cisa.gov/cybersecurity-advisories/all.xml','technology','cisa.gov'),
 ('https://blog.google/rss/','technology','blog.google'),
 ('https://blog.cloudflare.com/rss/','technology','blog.cloudflare.com'),
 ('https://news.google.com/rss/search?q=site%3Apib.gov.in%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','government-schemes','pib.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Apmindia.gov.in%20scheme%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','government-schemes','pmindia.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Aupsc.gov.in%20recruitment%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','upsc.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Assc.gov.in%20notice%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','ssc.gov.in'),
 ('https://news.google.com/rss/search?q=site%3Aemploymentnews.gov.in%20when%3A7d&hl=en-IN&gl=IN&ceid=IN%3Aen','sarkari-naukri','employmentnews.gov.in'),
]
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
 order=os.getenv('AI_PROVIDER_ORDER','groq,gemini,openrouter').lower().split(',')
 return [p.strip() for p in order if p.strip() in ('groq','gemini','openrouter')]
def call_provider(prompt):
 global CALLS
 if CALLS>=MAX_CALLS: return None,None
 for provider in provider_order():
  key=os.getenv({'groq':'GROQ_API_KEY','gemini':'GEMINI_API_KEY','openrouter':'OPENROUTER_API_KEY'}[provider],'').strip()
  if not key: continue
  # Each request is counted even if the provider returns an error.
  CALLS+=1
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
    print('Provider',provider,'HTTP',r.status_code,'(no retry)',flush=True)
    return None,provider
   return json_object(raw),provider
  except (requests.RequestException,ValueError,KeyError,IndexError,TypeError) as exc:
   print('Provider',provider,'error',type(exc).__name__,'(no retry)',flush=True)
   return None,provider
 return None,None

def article_prompt(lang,title,source,source_material,cat):
 language='English' if lang=='en' else 'Hindi (Devanagari)'
 return f'''You are a careful editor for a public-information news site. Write ONE original article in {language}. Return ONLY a JSON object with fields title, body, meta, keywords. The body should have at least {MIN_WORDS} meaningful words IF and ONLY IF the source supports that length; never invent or pad. Use Markdown ## subheadings. Explain confirmed facts, background, user impact, uncertainties, and what readers can verify, with a clear link to the official source. Do not fabricate quotes, eligibility, deadlines, salaries, recruitment numbers, prices, application steps, or citations. No copied paragraphs. If source is insufficient for a detailed factual article, return {{"title":"","body":"","meta":"","keywords":""}}. Category: {cat}. Source title: {title}. Verified official/source URL: {source}. SOURCE TEXT:\n{source_material[:22000]}'''

def candidates():
 seen=set()
 # Resume verified drafts first instead of spending calls on new headlines.
 for path in sorted(PENDING.glob('*.json')):
  try:
   record=json.loads(path.read_text(encoding='utf-8'))
   url=record.get('source',''); title=record.get('source_title','')
   domain=urlparse(url).hostname or ''
   if title and any(allowed(url,d) for _,_,d in FEEDS) and url not in seen:
    seen.add(url)
    yield url,title,record.get('category','technology'),domain
  except (OSError,ValueError):pass
 # Interleave categories so one technology blog cannot consume the whole quota.
 groups={'technology':[],'government-schemes':[],'sarkari-naukri':[]}
 for feed,cat,domain in FEEDS:
  try:
   r=requests.get(feed,timeout=(7,15),headers={'User-Agent':'Mozilla/5.0'});r.raise_for_status()
   entries=feedparser.parse(r.content).entries[:12]
   print('Feed',domain,'entries',len(entries),flush=True)
  except requests.RequestException:
   print('Feed unavailable',domain,flush=True);continue
  for e in entries:
   url=e.get('link','').strip(); title=clean(e.get('title',''))
   # Google News redirect URLs are NOT treated as verified official sources.
   if not allowed(url,domain) or not title or url in seen: continue
   seen.add(url)
   published=e.get('published_parsed') or e.get('updated_parsed')
   if not published: continue
   age=(dt.datetime.now(UTC).date()-dt.date(*published[:3])).days
   if age<0 or age>7:continue
   groups[cat].append((url,title,category(title,cat),domain))
 for i in range(max(map(len,groups.values()),default=0)):
  for cat in ('government-schemes','sarkari-naukri','technology'):
   if i<len(groups[cat]): yield groups[cat][i]

def main():
 if os.getenv('AUTO_POST','false').lower()!='true':print('AUTO_POST disabled');return 0
 remaining=max(0,DAILY_LIMIT-day_count())
 print('Remaining daily allowance:',remaining,flush=True)
 if not remaining:return 0
 if not any(os.getenv(k) for k in ('GROQ_API_KEY','GEMINI_API_KEY','OPENROUTER_API_KEY')):
  print('No AI provider configured');return 0
 published=0; inspected=0
 for url,title,cat,domain in candidates():
  if CALLS>=MAX_CALLS or published>=remaining or inspected>=12:break
  post_id=hashlib.sha256(url.encode()).hexdigest()[:12]
  if (POSTS/(post_id+'.json')).exists():continue
  pending=PENDING/(post_id+'.json')
  try:state=json.loads(pending.read_text()) if pending.exists() else {}
  except ValueError:state={}
  # Avoid retrying the same insufficient or failed source repeatedly within a day.
  if state.get('blocked_until','')>dt.datetime.now(UTC).isoformat():continue
  inspected+=1
  text=source_text(url,domain)
  if words(text)<MIN_SOURCE_WORDS:
   save_state(pending,{'source':url,'status':'insufficient_source','blocked_until':(dt.datetime.now(UTC)+dt.timedelta(hours=24)).isoformat(),'source_words':words(text)})
   print('Skipping source before AI:',title[:65],'words',words(text),flush=True)
   continue
  state.update({'source':url,'source_title':title,'category':cat,'status':'draft','updated_at':dt.datetime.now(UTC).isoformat()})
  for lang in ('en','hi'):
   if CALLS>=MAX_CALLS:break
   if words(state.get(lang+'_body',''))>=MIN_WORDS:continue
   data,provider=call_provider(article_prompt(lang,title,url,text,cat))
   if isinstance(data,dict):
    body=str(data.get('body') or '')
    if words(body)>=MIN_WORDS and len(str(data.get('title') or ''))>=20:
     state[lang+'_body']=body;state[lang+'_title']=str(data['title'])
     state[lang+'_meta']=str(data.get('meta') or '')
     state[lang+'_keywords']=str(data.get('keywords') or '')
     print('Draft ready:',lang,'words',words(body),'via',provider,flush=True)
    else: print('Draft below minimum:',lang,'words',words(body),'via',provider,flush=True)
   # One failed request does not lead to a provider/model retry this run.
   if not data or words(str(data.get('body',''))) < MIN_WORDS:
    state['blocked_until']=(dt.datetime.now(UTC)+dt.timedelta(hours=24)).isoformat()
    break
   save_state(pending,state)
  if all(words(state.get(lang+'_body',''))>=MIN_WORDS for lang in ('en','hi')):
   article={k:state.get(k,'') for k in ('en_title','hi_title','en_body','hi_body','en_meta','hi_meta','en_keywords','hi_keywords')}
   article.update(id=post_id,source=url,date=dt.datetime.now(UTC).isoformat(),source_title=title,category=cat,image_kind='conceptual')
   save_state(POSTS/(post_id+'.json'),article)
   pending.unlink(missing_ok=True)
   published+=1
   print('Published',post_id,cat,flush=True)
  else:save_state(pending,state)
 print('AI requests used this run:',CALLS,'of',MAX_CALLS,flush=True)
 print('Published',published,flush=True)
 return 0
if __name__=='__main__':sys.exit(main())
