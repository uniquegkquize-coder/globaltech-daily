"""Optional Gemini image generation. Saves one reusable 16:9 featured image per post.
Falls back to build.py's original illustrations when image generation is unavailable.
"""
from pathlib import Path
import os, json, io, time, re, datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
POSTS=ROOT/'content/posts'
IMAGES=ROOT/'content/featured'
IMAGES.mkdir(parents=True,exist_ok=True)
KEY=os.getenv('GEMINI_API_KEY','').strip()
MODEL=os.getenv('GEMINI_IMAGE_MODEL','gemini-2.5-flash-image').strip()
MODELS=list(dict.fromkeys([m.strip() for m in (MODEL+','+os.getenv('GEMINI_IMAGE_FALLBACK_MODELS','gemini-3-pro-image-preview')).split(',') if m.strip()]))
QUOTA_BLOCKED=set()
MAX_NEW=max(0,int(os.getenv('MAX_NEW_IMAGES','0')))  # 0 disables automatic image requests

def slug(p):return re.sub('[^a-f0-9]','',str(p.get('id','')))[:32]

def resolved_featured(ident):
    """Existing original/manual art is preserved; older Commons substitutes can be upgraded."""
    path=IMAGES/(ident+'.jpg')
    if not path.is_file():return False
    meta=IMAGES/(ident+'.json')
    try:
        kind=json.loads(meta.read_text(encoding='utf-8')).get('kind') if meta.is_file() else ''
    except (OSError,ValueError,TypeError):kind=''
    # Replace representative Commons pictures and AI art when a genuine source image exists.
    return kind not in ('licensed_photo','ai_generated','illustration')

def licensed_source_image(p):
    """Prioritize the actual article's published picture; record its origin and rights status.

    Metadata such as og:image is an image locator, NOT proof of a reusable license.
    This pipeline records that limitation instead of mislabelling publisher photos CC.
    """
    source=str(p.get('source') or '')
    ident=slug(p)
    if not source.startswith('https://') or not ident:return False
    if resolved_featured(ident):return False
    try:
        page=requests.get(source,timeout=(4,10),headers={
            'User-Agent':'Mozilla/5.0 (compatible; GlobeWireDaily/1.0; +https://globewiredaily.org)'
        },allow_redirects=True)
        if not page.ok or 'html' not in page.headers.get('content-type','').lower():return False
        if not str(page.url).startswith('https://'):return False
        soup=BeautifulSoup(page.text[:800000],'html.parser')
        def meta(*keys):
            for key in keys:
                tag=soup.find('meta',attrs={'property':key}) or soup.find('meta',attrs={'name':key})
                if tag and tag.get('content'):return str(tag['content']).strip()
            return ''
        image=meta('og:image:secure_url','og:image','twitter:image','twitter:image:src')
        if not image:
            # Some original articles expose their lead image only as NewsArticle JSON-LD.
            for script in soup.find_all('script',attrs={'type':'application/ld+json'}):
                try:payload=json.loads(script.string or script.get_text() or '{}')
                except (ValueError,TypeError):continue
                nodes=payload if isinstance(payload,list) else [payload]
                if isinstance(payload,dict) and isinstance(payload.get('@graph'),list):
                    nodes+=payload['@graph']
                for node in nodes:
                    if not isinstance(node,dict):continue
                    kinds=node.get('@type',[])
                    kinds=[kinds] if isinstance(kinds,str) else kinds
                    if not any(k in ('Article','NewsArticle','BlogPosting') for k in kinds):continue
                    field=node.get('image') or node.get('thumbnailUrl')
                    if isinstance(field,dict):field=field.get('url') or field.get('contentUrl')
                    if isinstance(field,list):field=next(iter(field),'')
                    if isinstance(field,dict):field=field.get('url') or field.get('contentUrl')
                    if isinstance(field,str) and field.strip():
                        image=field.strip();break
                if image:break
        if not image:return False
        image=urljoin(page.url,image)
        parsed=urlparse(image)
        if parsed.scheme!='https' or not parsed.hostname:return False
        # Explicitly reject icons, publisher logos, placeholders and trackers.
        if re.search(r'(?i)(?:logo|favicon|avatar|sprite|placeholder|tracking-pixel|default-image|site-icon|/assets/images/share/|/(?:app-store|appstore|social-share|share-banner|og-default)(?:[._/-]|$))',parsed.path):
            return False
        res=requests.get(image,timeout=(4,14),headers={
            'User-Agent':'Mozilla/5.0 (compatible; GlobeWireDaily/1.0)'
        },stream=True,allow_redirects=True)
        if not res.ok or 'image/' not in res.headers.get('content-type','').lower():return False
        if not str(res.url).startswith('https://'):return False
        raw=bytearray()
        for chunk in res.iter_content(65536):
            raw.extend(chunk)
            if len(raw)>12_000_000:return False
        with Image.open(io.BytesIO(raw)) as im:
            if im.width<600 or im.height<320:return False
            ratio=im.width/max(1,im.height)
            if ratio<0.65 or ratio>4.0:return False
            im=ImageOps.exif_transpose(im)
            im=ImageOps.fit(im.convert('RGB'),(1280,720),method=Image.Resampling.LANCZOS)
            im.save(IMAGES/(ident+'.jpg'),'JPEG',quality=86,optimize=True)
        license_url=meta('license','dc.rights','dcterms.license','cc:license')
        status='source_rights_unverified'
        if 'creativecommons.org/licenses/' in license_url.lower() or 'creativecommons.org/publicdomain/' in license_url.lower():
            status='source_license_claimed'
        (IMAGES/(ident+'.json')).write_text(json.dumps({
            'kind':'publisher_source','source_image':image,
            'license':license_url,'attribution':meta('dc.creator','author','article:author','og:site_name') or urlparse(page.url).hostname,
            'source':page.url,'rights_status':status,
            'caption':'Actual source-article image; publisher photo rights are not independently verified.',
            'modifications':'Cropped to 16:9 for the website'
        },ensure_ascii=False),encoding='utf-8')
        print('Original source-article photo',ident,source,flush=True)
        return True
    except (requests.RequestException,ValueError,OSError,TypeError):
        return False

# Search for the actual subject rather than an entire news headline. The previous
# pattern accidentally escaped \w and \s, turning almost every character into a
# space and making most Commons searches empty.
COMMONS_STOPWORDS={
    'latest','news','after','before','with','from','about','today','launch',
    'update','report','reports','india','world','amid','will','could','would',
    'says','said','claims','reveals','unveils','launches','announces','new',
    'first','over','under','into','the','and','for','that','this','its',
    'how','what','when','where','more','their','game','film','movie',
    'release','releases','official','watch','stream','streaming'
}

def commons_queries(title):
    """Return a few searchable names from the headline, never generic filler."""
    clean_title=re.sub(r'[^\w\s-]',' ',str(title or ''),flags=re.UNICODE)
    tokens=re.findall(r'[A-Za-z][A-Za-z0-9-]{2,}',clean_title)
    useful=[]
    used=set()
    for token in tokens:
        key=token.casefold()
        if key in COMMONS_STOPWORDS or key in used:continue
        useful.append(token)
        used.add(key)
    if len(useful)<1:return []
    return list(dict.fromkeys([' '.join(useful[:5]),' '.join(useful[:2]),useful[0]]))

def commons_reuse_allowed(short_name,license_url):
    """Only licenses permitting redistribution in a commercial news site."""
    short=re.sub(r'\s+',' ',short_name or '').strip().casefold()
    url=(license_url or '').lower()
    if re.search(r'(^|[-\s])(nc|nd)([-\s]|$)',short):return False
    if any(k in url for k in ('/by-nc/','/by-nd/','/by-nc-sa/','/by-nc-nd/')):return False
    if short in ('cc0','public domain','public domain mark'):return True
    if re.fullmatch(r'cc by(?:-sa)?(?:\s+\d+(?:\.\d+)?)?',short):return True
    return any(k in url for k in ('creativecommons.org/publicdomain/zero/',
                                  'creativecommons.org/licenses/by/',
                                  'creativecommons.org/licenses/by-sa/'))

def commons_photo(p):
    """Get relevant reusable REAL photographs, with clear source and credit."""
    ident=slug(p)
    if not ident or (IMAGES/(ident+'.jpg')).exists():return False
    # Broad job-listing titles produce irrelevant office seals and foreign photos.
    # Prefer a documented employer-owned original image, else use an illustration.
    if p.get('category')=='private-vacancy':
        print('Commons skipped for generic private vacancy',ident,flush=True)
        return False
    title=str(p.get('source_title') or p.get('en_title') or '')
    queries=commons_queries(title)
    if not queries:
        print('Commons search skipped (insufficient subject keywords)',ident,flush=True)
        return False
    headers={'User-Agent':'GlobeWireDaily/1.0 (contact@globewiredaily.org)'}
    for query in queries:
        try:
            response=requests.get('https://commons.wikimedia.org/w/api.php',params={
                'action':'query','generator':'search','gsrsearch':query,
                'gsrnamespace':6,'gsrlimit':8,'prop':'imageinfo',
                'iiprop':'url|size|extmetadata','iiurlwidth':1280,
                'format':'json'},headers=headers,timeout=(5,12))
            response.raise_for_status()
            pages=response.json().get('query',{}).get('pages',{})
            keywords={w.casefold() for w in re.findall(r'[A-Za-z]{4,}',query)}
            for page in sorted(pages.values(),key=lambda item:item.get('index',1000)):
                file_title=page.get('title','')
                # The MediaWiki thumbnail API also returns rendered PDF pages,
                # logos, maps and seals; those are not news event photographs.
                if not file_title.lower().endswith(('.jpg','.jpeg','.png','.webp')):continue
                filename_words={w.casefold() for w in re.findall(r'[A-Za-z]{4,}',file_title)}
                excluded={'logo','icon','clipart','screenshot','poster','seal','emblem',
                          'map','diagram','chart','document','manual','outline',
                          'illustration','drawing','stamp','flag','plan'}
                if filename_words & excluded:continue
                if len(keywords & filename_words)<min(2,len(keywords)):continue

                info=(page.get('imageinfo') or [{}])[0]
                meta=info.get('extmetadata') or {}
                short_name=re.sub('<[^>]*>','',meta.get('LicenseShortName',{}).get('value','')).strip()
                license_url=meta.get('LicenseUrl',{}).get('value','')
                if not commons_reuse_allowed(short_name,license_url):continue
                if info.get('width',0)<600 or info.get('height',0)<320:continue
                image_url=info.get('thumburl') or info.get('url')
                if not image_url or not image_url.startswith('https://'):continue
                res=requests.get(image_url,timeout=(5,18),headers=headers)
                if not res.ok or len(res.content)>12_000_000:continue
                with Image.open(io.BytesIO(res.content)) as im:
                    if im.width<600 or im.height<320:continue
                    im=ImageOps.fit(im.convert('RGB'),(1280,720),method=Image.Resampling.LANCZOS)
                    im.save(IMAGES/(ident+'.jpg'),'JPEG',quality=86,optimize=True)
                attribution=re.sub('<[^>]*>',' ',meta.get('Artist',{}).get('value','')).strip()[:240]
                (IMAGES/(ident+'.json')).write_text(json.dumps({
                    'kind':'licensed_photo','source_image':info.get('descriptionurl'),
                    'license':license_url or short_name,'license_name':short_name,
                    'attribution':attribution or 'Wikimedia Commons',
                    'rights_status':'licensed','caption':'Representative licensed photograph; not necessarily the reported event.',
                    'modifications':'Cropped to a 16:9 editorial format',
                    'matched_title':file_title,'search_query':query
                },ensure_ascii=False),encoding='utf-8')
                print('Licensed Commons photograph',ident,short_name,'query',query,flush=True)
                return True
            print('Commons: no licensed matching photo',ident,'query',query,flush=True)
        except (requests.RequestException,ValueError,OSError,KeyError,IndexError) as exc:
            print('Commons lookup unavailable',ident,type(exc).__name__,flush=True)
    return False

def create(p):
    ident=slug(p)
    if not ident:return False
    dest=IMAGES/(ident+'.jpg')
    if dest.exists():return False
    title=str(p.get('en_title') or p.get('source_title') or 'technology update')[:220]
    source=str(p.get('source_title') or '')[:180]
    detail=re.sub(r'\s+',' ',str(p.get('en_body') or ''))[:1400]
    prompt=(
      'Create one high-quality ORIGINAL 16:9 editorial conceptual illustration uniquely about the exact news event described below, not a generic category thumbnail. '
      'Category: '+str(p.get('category','technology'))+'. Topic: '+title+'. Source headline: '+source+'. Verified article context: '+detail+'. '
      'Show the most distinctive verifiable subject, product, setting, or action mentioned in this story. Avoid generic category icons, globes, film reels, stock-style placeholders, and unrelated technology objects. If the exact real-world scene cannot be faithfully depicted, use an unmistakably illustrative editorial interpretation grounded in the article. '
      'Absolutely NO text, letters, watermarks, fake screenshots, news logos, fake photographs of real people, or misleading depictions of specific events. '
      'Do not portray this as a documentary photograph. Leave safe margins for cropping. '
      'Landscape 16:9, premium professional news publication cover art. For government schemes use public-service visual metaphors; for recruitment use exam and careers imagery; for technology use topic-specific tech imagery; for movies depict a cinema environment, camera, projector, or generic film set without recreating copyrighted posters or real actors; for sports use sport-specific equipment; for world news use an accurate non-misleading conceptual scene.'
    )
    for model in MODELS:
      if model in QUOTA_BLOCKED:continue
      url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
      try:
        response=requests.post(url,headers={'x-goog-api-key':KEY},json={
          'contents':[{'parts':[{'text':prompt}]}],
          'generationConfig':{'responseModalities':['IMAGE','TEXT']}
        },timeout=(10,95))
        if not response.ok:
            print('Image API unavailable',model,response.status_code,response.text[:160],flush=True)
            if response.status_code in (429,403):
                QUOTA_BLOCKED.add(model)
            continue
        parts=response.json().get('candidates',[{}])[0].get('content',{}).get('parts',[])
        for part in parts:
            data=part.get('inlineData') or part.get('inline_data') or {}
            if data.get('data') and str(data.get('mimeType','image/')).startswith('image/'):
                import base64
                raw=base64.b64decode(data['data'],validate=True)
                if len(raw)>18_000_000:continue
                with Image.open(io.BytesIO(raw)) as img:
                    if img.width<400 or img.height<250:continue
                    img=ImageOps.fit(img.convert('RGB'),(1280,720),method=Image.Resampling.LANCZOS,centering=(.5,.5))
                    img.save(dest,'JPEG',quality=88,optimize=True)
                (IMAGES/(ident+'.json')).write_text(json.dumps({'kind':'ai_generated','model':model,'caption':'AI-generated conceptual illustration; not an event photograph.'}),encoding='utf-8')
                print('Generated featured image',ident,model,flush=True)
                return True
        print('Image API returned no image for',ident,model,flush=True)
      except (requests.RequestException,ValueError,OSError,KeyError,IndexError) as exc:
        print('Image generation failed',model,type(exc).__name__,str(exc)[:130],flush=True)
    return False

BACKFILL_STATE=ROOT/'content/image-backfill-state.json'

def choose_backfill(posts,now=None,limit=None,cursor=None,mode=None):
    """Search fresh news and historic posts, advancing persistent group cursors.

    Preserve existing source/owner images; allow older unrelated Commons photos
    to be upgraded to the original publisher image. Archive mode scans old posts.
    """
    now=now or datetime.datetime.now(datetime.timezone.utc)
    limit=max(0,int(limit if limit is not None else os.getenv('MAX_LICENSED_PHOTOS_PER_RUN','8')))
    if limit==0:return [],0,0
    fresh=[];older=[]
    for post in sorted(posts,key=lambda p:p.get('date',''),reverse=True):
        ident=slug(post)
        if not ident or resolved_featured(ident):continue
        try:
            stamp=datetime.datetime.fromisoformat(str(post.get('date','')).replace('Z','+00:00'))
            if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=datetime.timezone.utc)
            is_fresh=datetime.timedelta(0)<=now-stamp<=datetime.timedelta(days=3)
        except (TypeError,ValueError):is_fresh=False
        (fresh if is_fresh else older).append(post)
    mode=(mode or os.getenv('IMAGE_BACKFILL_MODE','mixed')).strip().lower()
    if mode=='archive' and older:
        fresh_budget=0
        older_budget=min(limit,len(older))
    else:
        # 60% new news, 40% historic archive, even with a continuous new-news queue.
        fresh_budget=min(len(fresh),max(1,(limit*3+4)//5)) if fresh else 0
        older_budget=min(len(older),limit-fresh_budget)
        if fresh_budget+older_budget<limit:
            room=limit-fresh_budget-older_budget
            fresh_budget+=min(room,len(fresh)-fresh_budget)
            room=limit-fresh_budget-older_budget
            older_budget+=min(room,len(older)-older_budget)
    def rotate(rows,n,key):
        if not rows or n<=0:return []
        if cursor is None:
            start=(int(now.timestamp()//900)*n)%len(rows)
        else:
            start=max(0,int(cursor.get(key,0)))%len(rows)
            cursor[key]=start+n
        return (rows[start:]+rows[:start])[:n]
    selected=fresh[:fresh_budget]+rotate(older,older_budget,'archive_offset')
    return selected,len(fresh),len(older)

def main():
    posts=[]
    for f in POSTS.glob('*.json'):
        try:
            p=json.loads(f.read_text(encoding='utf-8'))
            if slug(p):posts.append(p)
        except (OSError,ValueError):pass
    try:cursor=json.loads(BACKFILL_STATE.read_text(encoding='utf-8'))
    except (OSError,ValueError):cursor={}
    if not isinstance(cursor,dict):cursor={}
    candidates,fresh_count,older_count=choose_backfill(posts,cursor=cursor)
    if candidates:
        BACKFILL_STATE.parent.mkdir(parents=True,exist_ok=True)
        BACKFILL_STATE.write_text(json.dumps(cursor,indent=2)+'\n',encoding='utf-8')
    print('Image backfill mode:',os.getenv('IMAGE_BACKFILL_MODE','mixed'),flush=True)
    print('Fresh news awaiting reusable photos:',fresh_count,
          'older archive missing reusable photos:',older_count,flush=True)
    new_original=0
    for p in candidates:
        if licensed_source_image(p):
            new_original+=1
            continue
        # If the publisher has no usable image, build.py produces an editorial illustration.
        # Do not substitute unrelated Commons/stock photos for original article images.
        if MAX_NEW>0 and KEY and len(QUOTA_BLOCKED)<len(MODELS):
            create(p)
    print('Photo backfill attempted:',len(candidates),'original:',new_original,
          'fallback: editorial illustrations',flush=True)
if __name__=='__main__':main()
