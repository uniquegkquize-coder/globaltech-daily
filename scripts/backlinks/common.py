"""Bounded, robots-aware public fetching and deterministic storage."""
import hashlib
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import socket
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get('BACKLINK_DATA_DIR', str(ROOT / 'data/backlinks')))
SITE = 'https://globewiredaily.org'
AGENT = 'GlobeWireResearchBot/1.0 (+https://globewiredaily.org/en/contact/)'
LOG = logging.getLogger('backlinks')
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
CATEGORIES = {
 'tech-ai': ['technology','artificial intelligence','machine learning',' ai ','software'],
 'cars-bikes': ['automobile','automotive','motorcycle',' car ','bike','vehicle'],
 'mobiles': ['smartphone','mobile','gadget','android','iphone'],
 'education': ['education','university','college','admission'],
 'jobs-exams': ['recruitment','sarkari','exam','government jobs','ssc','upsc'],
 'sports': ['cricket','sport','football'],
 'entertainment': ['entertainment','movie','cinema','actor','film'],
 'travel': ['travel','tourism','destination'],
 'defence-world': ['defence','defense','military','international','world news'],
 'regional': ['gorakhpur','uttar pradesh','regional','local news','हिंदी','समाचार'],
}
def day():
 from datetime import datetime, timezone
 return datetime.now(timezone.utc).date().isoformat()
def read(name, default):
 p=DATA/name
 return json.loads(p.read_text()) if p.exists() else default

def save(name, value):
 p=DATA/name; p.parent.mkdir(parents=True, exist_ok=True)
 raw=json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
 if not p.exists() or p.read_text()!=raw:
  temp=p.with_suffix(p.suffix+'.tmp'); temp.write_text(raw); temp.replace(p)

def canonical(url):
 p=urlsplit(url)
 if p.scheme not in ('http','https') or not p.hostname or p.username or p.password: return ''
 host=p.hostname.lower().removeprefix('www.')
 if p.port and p.port not in (80,443): return ''
 return urlunsplit(('https',host,p.path or '/',p.query,''))
def domain(url): return urlsplit(canonical(url)).hostname or ''
def uid(value): return hashlib.sha256(value.encode()).hexdigest()[:20]
def tokens(text): return set(re.findall(r'[a-z0-9\u0900-\u097f]{3,}',text.lower()))-{'the','and','for','with','from','news','daily','that','this','www','com','org','https','india','2026','2025','latest','new','updates','update','read','more','today','world','about','contact','editorial','team'}
def classify(text):
 text=' '+text.lower()+' '
 scores={k:sum(w in text for w in words) for k,words in CATEGORIES.items()}
 return max(scores,key=scores.get) if max(scores.values()) else ''
def soup(text):
 b=BeautifulSoup(text,'html.parser')
 for t in b(['script','style','noscript']): t.decompose()
 return b

class Fetcher:
 def __init__(self, seconds=450):
  self.end=time.monotonic()+seconds; self.robots={}; self.last={}
  self.session=requests.Session(); self.session.headers['User-Agent']=AGENT
  self.session.mount('https://',HTTPAdapter(max_retries=Retry(total=1,connect=1,read=0,redirect=0,status=0,backoff_factor=0.5)))
 def public(self,url):
  p=urlsplit(url)
  if p.scheme not in ('http','https') or p.username or p.password or p.port not in (None,80,443): raise ValueError('unsafe URL')
  try:
   addresses=socket.getaddrinfo(p.hostname,None)
  except socket.gaierror:
   # Restricted research environments may resolve only at the outbound proxy.
   # Explicit opt-in is local-only; standard GitHub runners retain strict DNS checks.
   if os.environ.get('BACKLINK_PROXY_DNS')!='1' or not requests.utils.get_environ_proxies(url).get('https'): raise
   host=(p.hostname or '').lower()
   if '.' not in host or host.endswith(('.localhost','.local','.internal')): raise ValueError('non-public hostname')
   try:
    if not ipaddress.ip_address(host).is_global: raise ValueError('non-public address')
   except ValueError as exc:
    if 'non-public' in str(exc): raise
   return
  if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise ValueError('non-public address')
 def raw(self,url):
  self.public(url)
  host=urlsplit(url).netloc
  delay=max(0,self.last.get(host,0)+self.delay(host)-time.monotonic())
  if time.monotonic()+delay>=self.end: raise TimeoutError('research budget exhausted')
  time.sleep(delay); self.last[host]=time.monotonic()
  remaining=max(0.1,self.end-time.monotonic())
  with self.session.get(url,timeout=(min(10,remaining),min(12,remaining)),allow_redirects=False,stream=True) as r:
   if r.is_redirect: return r.status_code,r.headers.get('Location','')
   if r.status_code in (429,503): raise requests.RequestException('rate limited; deferred to next run')
   r.encoding=r.encoding or 'utf-8'
   chunks=[]; size=0
   for chunk in r.iter_content(65536):
    if time.monotonic()>=self.end: raise TimeoutError('research budget exhausted')
    size+=len(chunk)
    if size>3_000_000: raise ValueError('response too large')
    chunks.append(chunk)
   return r.status_code,b''.join(chunks).decode(r.encoding,errors='replace')
 def delay(self,host):
  rule=self.robots.get(host)
  return max(2, (rule.crawl_delay(AGENT) or 0) if isinstance(rule,RobotFileParser) else 0)
 def allowed(self,url):
  p=urlsplit(url); host=p.netloc
  if host not in self.robots:
   self.robots[host]=False
   try:
    robots_url=f'{p.scheme}://{host}/robots.txt'
    for _ in range(5):
     status,body=self.raw(robots_url)
     if status not in (301,302,303,307,308): break
     robots_url=urljoin(robots_url,body)
    if status==404: body='User-agent: *\nAllow: /'
    elif status!=200: return False
    rule=RobotFileParser(); rule.parse(body.splitlines()); self.robots[host]=rule
   except (requests.RequestException,ValueError,OSError,TimeoutError): return False
  rule=self.robots[host]
  return bool(rule and rule.can_fetch(AGENT,url))
 def get(self,url):
  url=urlsplit(url)._replace(fragment='').geturl()
  for hop in range(6):
   if time.monotonic()>=self.end: raise TimeoutError('research budget exhausted')
   if not self.allowed(url): raise ValueError('robots unavailable or disallowed (network errors are deferred, never bypassed)')
   status,body=self.raw(url)
   if status in (301,302,303,307,308): url=urljoin(url,body); continue
   if status!=200: raise ValueError(f'HTTP {status}')
   return url,body
  raise ValueError('too many redirects')
