"""Bounded official-board metadata index. Never imports third-party article bodies."""
import concurrent.futures
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin,urlparse
import urllib.request
from news_config import classify,EXAM_CATEGORIES

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'content/official-notice-archive.json'
SOURCES=[
 'https://sscnr.nic.in/newlook/site/Whatsnew.html',
 'https://sscnr.nic.in/newlook/site/admit_card.html',
 'https://ssc.gov.in/',
 'https://upsc.gov.in/',
 'https://nta.ac.in/',
]

def official_url(url):
    host=(urlparse(url).hostname or '').lower()
    return url.startswith('https://') and (host.endswith(('.gov.in','.nic.in','.ac.in','.edu.in')) or host in {'ibps.in','www.ibps.in'})

class BoardParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.groups=[];self.anchor=None;self.blocks=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style'):self.skip+=1
        if tag in ('li','tr','p'):self.groups.append({'tag':tag,'text':[],'links':[]})
        if tag=='a':self.anchor={'href':a.get('href',''),'text':[]}
    def handle_data(self,data):
        if self.skip:return
        if self.anchor is not None:self.anchor['text'].append(data)
        for group in self.groups:group['text'].append(data)
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
        if tag=='a' and self.anchor is not None:
            if self.groups:self.groups[-1]['links'].append(self.anchor)
            self.anchor=None
        if self.groups and tag==self.groups[-1]['tag']:
            group=self.groups.pop()
            self.blocks.extend((link,''.join(group['text'])) for link in group['links'])

MONTHS={name.lower():i for i,name in enumerate(['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']) if name}
def notice_date(text):
    m=re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b',text)
    if m:
        day,month,year=map(int,m.groups())
    else:
        m=re.search(r'\b(\d{1,2})\s+([A-Za-z]{3,9})[ ,.-]+(20\d{2})\b',text)
        if not m:return None
        day=int(m[1]);month=MONTHS.get(m[2][:3].lower(),0);year=int(m[3])
    try:return dt.date(year,month,day).isoformat()
    except ValueError:return None

def parse_board(page,url,checked_at=None):
    parser=BoardParser();parser.feed(page);records=[]
    for link,context in parser.blocks:
        title=re.sub(r'\s+',' ',''.join(link['text'])).strip()
        target=urljoin(url,link['href'])
        if len(title)<25 or len(title)>450 or not official_url(target):continue
        if not re.search(r'exam|recruit|admit|answer key|result|vacan|candidates?|application|syllabus|admission|भर्ती|परीक्षा',title,re.I):continue
        cat=classify(title,'sarkari-naukri')
        if cat not in EXAM_CATEGORIES:continue
        date=notice_date(context)
        path=urlparse(target).path.lower()
        if not date and not (path.endswith('.pdf') or '/content/' in path or '/whats-new/' in path):continue
        if date and date>dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).date().isoformat():continue
        # Only document metadata and direct government links, not source prose/PDF bodies.
        title=title[:240]
        records.append({'id':hashlib.sha256((target+title).encode()).hexdigest()[:16],
            'category':cat,'date':date,'en_title':title,'hi_title':'आधिकारिक नोटिस: '+title,
            'source':target,'source_index':url,'checked_at':checked_at or dt.datetime.now(dt.timezone.utc).isoformat()})
    return records

def fetch_board(url):
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'GlobeWireDaily-OfficialNoticeIndex/1.0'})
        with urllib.request.urlopen(request,timeout=15) as response:
            data=response.read(2_000_000).decode('utf-8',errors='replace')
        return parse_board(data,url),{'source':url,'status':'ok'}
    except Exception as exc:return [],{'source':url,'status':'unavailable','reason':type(exc).__name__}

def load_notices(root=ROOT):
    records=[]
    for name in ('official-notice-archive.json','official-exam-notices.json'):
        try:
            data=json.loads((root/'content'/name).read_text())
            records.extend(data if isinstance(data,list) else data.get('records',[]))
        except (OSError,ValueError,TypeError):pass
    unique={}
    for row in records:
        if official_url(row.get('source','')):
            row=dict(row)
            if '/pet-pst/' in urlparse(row['source']).path:row['category']='admit-cards'
            unique[(row['source'],row.get('en_title',''))]=row
    return sorted(unique.values(),key=lambda r:(r.get('date') or '',r.get('en_title','')),reverse=True)

def main():
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--merge':
        incoming=json.loads(Path(sys.argv[2]).read_text()).get('records',[])
        merged={(r['source'],r.get('en_title','')):r for r in load_notices()}
        for row in incoming:
            if official_url(row.get('source','')):merged.setdefault((row['source'],row.get('en_title','')),row)
        records=sorted(merged.values(),key=lambda r:(r.get('date') or '',r.get('en_title','')),reverse=True)[:3000]
        DEST.write_text(json.dumps({'records':records},ensure_ascii=False,indent=2)+'\n')
        return 0
    old=load_notices();merged={(x['source'],x.get('en_title','')):x for x in old};diagnostics=[];added=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for rows,diag in pool.map(fetch_board,SOURCES):
            diagnostics.append(diag)
            for row in rows:
                key=(row['source'],row['en_title'])
                if key not in merged:merged[key]=row;added+=1
    # No timestamp-only commits. Existing historical records survive transient source failures.
    if added or not DEST.exists():
        records=sorted(merged.values(),key=lambda r:(r.get('date') or '',r['en_title']),reverse=True)[:3000]
        DEST.write_text(json.dumps({'records':records},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'new_notices':added,'total_notices':len(merged),'sources':diagnostics},ensure_ascii=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
