import os,json,hashlib,datetime,pathlib,re,time
import requests,feedparser
root=pathlib.Path(__file__).resolve().parents[1]
if os.getenv('AUTO_POST','false')!='true' or not os.getenv('GEMINI_API_KEY'):
 print('Auto posting off or key missing');quit()
feeds=['https://blog.cloudflare.com/rss/','https://blog.google/rss/'];n=0
for feed in feeds:
 try:entries=feedparser.parse(requests.get(feed,timeout=20).content).entries
 except Exception as e:print(e);continue
 for e in entries[:20]:
  if n>=10:break
  link=e.get('link','');key=hashlib.sha256(link.encode()).hexdigest()[:12];f=root/'content/posts'/f'{key}.json'
  if f.exists():continue
  published=e.get('published_parsed') or e.get('updated_parsed')
  if not published or (datetime.datetime.now(datetime.timezone.utc).date()-datetime.date(*published[:3])).days not in range(4):continue
  summary=re.sub('<[^>]*>',' ',e.get('summary',''))
  if len(summary)<150:continue
  prompt='Summarize this technology vendor announcement cautiously using ONLY given metadata. Do not invent claims. JSON keys en_title, hi_title, en_body, hi_body. Write original English and Hindi paragraphs and attribute claims to the source. Return {} if insufficient. TITLE: '+e.get('title','')+' SUMMARY: '+summary[:1600]
  try:
   res=requests.post('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent',params={'key':os.environ['GEMINI_API_KEY']},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json'}},timeout=40);res.raise_for_status()
   x=json.loads(res.json()['candidates'][0]['content']['parts'][0]['text'])
   if not all(len(x.get(k,''))>50 for k in ['en_title','hi_title','en_body','hi_body']):continue
   x.update(id=key,source=link,date=str(datetime.datetime.now(datetime.timezone.utc)));f.write_text(json.dumps(x,ensure_ascii=False));n+=1;time.sleep(2)
  except Exception as ex:print('Skipped:',str(ex)[:120])
print('Published',n)
