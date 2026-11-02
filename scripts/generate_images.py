"""Optional Gemini image generation. Saves one reusable 16:9 featured image per post.
Falls back to build.py's original illustrations when image generation is unavailable.
"""
from pathlib import Path
import os, json, io, time, re, datetime, hashlib, threading, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image, ImageOps
from image_rules import saved_photo_allowed, institution, campus_image, words, directory_photo_matches

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
    except (OSError,ValueError,TypeError,AttributeError):kind=''
    # Replace representative Commons pictures and AI art when a genuine source image exists.
    # A JPEG without source provenance can be legacy artwork, not a confirmed publisher photo.
    return kind in ('licensed_source','licensed_photo','publisher_source','source_original','manual_original') and not generic_image(json.loads(meta.read_text()).get('source_image','')) and saved_photo_allowed(json.loads(meta.read_text()),ROOT)

def representative_featured(ident):
    """Reusable subject photos remain eligible for a better article-original photo."""
    try:
        meta=json.loads((IMAGES/(ident+'.json')).read_text())
        return meta.get('kind')=='licensed_photo' and resolved_featured(ident)
    except (OSError,ValueError,AttributeError):return False

PHOTO_DIAGNOSTICS={}
PHOTO_LOCK=threading.Lock()
DENIED=(401,403,407,429,451)

def diagnostic(ident,reason,**extra):
    with PHOTO_LOCK:PHOTO_DIAGNOSTICS[ident]={'reason':reason,**extra}
    print('PHOTO_DIAGNOSTIC',json.dumps({'id':ident,'reason':reason,**extra}),flush=True)

def generic_image(url):
    return bool(re.search(r'(?i)(logo|favicon|avatar|sprite|placeholder|tracking-pixel|default-image|site-icon|/assets/images/share/|/(?:app-store|appstore|social-share|share-banner|og-default)(?:[._/-]|$)|/rt\.gif$|/subject-and-industry-code-images/|incredible-india-og|/(?:facebook|twitter|instagram|linkedin|youtube|x)$)',urlparse(str(url)).path))

def source_candidates(soup,base,limit=12):
    rows=[]
    def add(value,license_url='',label='',origin=''):
        if isinstance(value,list):
            for v in value:add(v,license_url,label,origin)
        elif isinstance(value,dict):
            add(value.get('contentUrl') or value.get('url'),value.get('license') or license_url,value.get('caption') or value.get('name') or label,origin)
        elif isinstance(value,str):
            url=urljoin(base,value.strip())
            if urlparse(url).scheme in ('https','http') and urlparse(url).hostname and not generic_image(url):rows.append({'url':url,'license':license_url,'label':label,'origin':origin})
    def walk(node):
        if isinstance(node,list):
            for v in node:walk(v)
        elif isinstance(node,dict):
            kinds=node.get('@type',[]);kinds=[kinds] if isinstance(kinds,str) else kinds
            if set(kinds)&{'Article','NewsArticle','BlogPosting','Product','Car','Motorcycle','MobilePhone'}:
                add(node.get('image') or node.get('thumbnailUrl'),node.get('license',''),node.get('headline') or node.get('name',''),'structured')
            for key in ('@graph','mainEntity','mainEntityOfPage','subjectOf','hasPart','itemListElement','item'):
                if key in node:walk(node[key])
    for tag in soup.select('script[type="application/ld+json"]')[:40]:
        try:walk(json.loads(tag.string or tag.get_text()))
        except (ValueError,TypeError):pass
    for tag in soup.select('link[rel~="image_src"]'):
        add(tag.get('href'),origin='social')
    for key in ('og:image:secure_url','og:image','twitter:image','twitter:image:src'):
        tag=soup.find('meta',attrs={'property':key}) or soup.find('meta',attrs={'name':key})
        if tag:add(tag.get('content'),origin='social')
    for tag in soup.select('article img,main img,figure img,[itemprop="image"],picture source,.release-body img,.article-body img,[itemprop="articleBody"] img,.hero img')[:100]:
        srcset=tag.get('data-srcset') or tag.get('srcset') or ''
        sizes=[]
        for part in srcset.split(','):
            bits=part.strip().split()
            if bits:
                try:size=float(re.sub(r'[^0-9.]','',bits[1]) or '0') if len(bits)>1 else 0
                except ValueError:size=0
                sizes.append((size,bits[0]))
        for _,url in sorted(sizes,reverse=True):add(url,label=tag.get('alt',''),origin='article')
        for attr in ('data-original','data-full-src','data-lazy-src','data-src','data-lazy','src'):
            if tag.get(attr):add(tag[attr],label=tag.get('alt',''),origin='article')
    # Publisher hero photography may use lazy CSS backgrounds instead of img.
    for tag in soup.select('article [style],main [style],.hero[style],[class*="banner"][style],[data-bg],[data-background],[data-background-image]')[:100]:
        for attr in ('data-bg','data-background','data-background-image'):
            if tag.get(attr):add(tag[attr],origin='article')
        for value in re.findall(r'url\(\s*[\"\']?([^\"\')]+)',tag.get('style',''),re.I):
            add(value.strip(),origin='article')
    seen=set();out=[]
    for row in rows:
        if row['url'] not in seen:seen.add(row['url']);out.append(row)
    return out[:limit]

def save_source_photo(ident,image,source,license_url,authorized,credit,alt):
    response=requests.get(image,timeout=(4,12),headers={'User-Agent':'GlobeWireDaily/1.0 (contact@globewiredaily.org)','Referer':source,'Accept':'image/*'},stream=True)
    try:
        if not response.ok:return False # Decode the bytes; some valid CDNs send application/octet-stream.
        raw=bytearray()
        for chunk in response.iter_content(65536):
            raw.extend(chunk)
            if len(raw)>12_000_000:return False
        with Image.open(io.BytesIO(raw)) as im:
            if im.width<320 or im.height<180:return False
            original_size=im.size
            im=ImageOps.exif_transpose(im).convert('RGB')
            # Retain the complete product/subject instead of cropping off phones or wheels.
            im=ImageOps.pad(im,(1280,720),method=Image.Resampling.LANCZOS,color=(12,28,55))
            tmp=IMAGES/(ident+'.tmp.jpg');im.save(tmp,'JPEG',quality=86,optimize=True);tmp.replace(IMAGES/(ident+'.jpg'))
        meta={'kind':'publisher_source','source_image':image,'image_url':image,'source':source,
              'license':license_url,'attribution':authorized.get('attribution') or credit,'rights_status':'authorized' if authorized else ('source_license_claimed' if license_url else 'publisher_original_unverified'),
              'authorization':authorized,'post_id':ident,'width':1280,'height':720,'original_dimensions':original_size,
              'alt':alt,'modifications':'Resized and letterboxed to 16:9; no AI generation'}
        (IMAGES/(ident+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return True
    except (OSError,ValueError):return False
    finally:
        if hasattr(response,'close'):response.close()

def licensed_source_image(p):
    source=str(p.get('source') or '');ident=slug(p)
    if not source.startswith('https://') or not ident:return False
    if resolved_featured(ident) and not representative_featured(ident):return False
    try:
        page=requests.get(source,timeout=(4,10),headers={'User-Agent':'GlobeWireDaily/1.0 (contact@globewiredaily.org)'})
        code=getattr(page,'status_code',200)
        if code in DENIED:
            diagnostic(ident,'access_denied',source=source,status=code);return False
        if not page.ok or 'html' not in page.headers.get('content-type','').lower():
            diagnostic(ident,'source_unavailable',source=source,status=code);return False
        from public_page_fetch import restricted
        if restricted(page.text):diagnostic(ident,'restricted_page',source=source);return False
        soup=BeautifulSoup(page.text[:2000000],'html.parser')
        candidates=source_candidates(soup,page.url,60 if p.get('directory_name') else 12)
        if not candidates:
            if os.getenv('ENABLE_PUBLIC_BROWSER_FALLBACK','0')=='1':
                from public_page_fetch import fetch_public_html
                html,final,method=fetch_public_html(source,render=True)
                if html:soup=BeautifulSoup(html,'html.parser');candidates=source_candidates(soup,final,60 if p.get('directory_name') else 12)
        if not candidates:diagnostic(ident,'no_source_image',source=source);return False
        def meta(*keys):
            for key in keys:
                tag=soup.find('meta',attrs={'property':key}) or soup.find('meta',attrs={'name':key})
                if tag and tag.get('content'):return str(tag['content']).strip()
            return ''
        page_license=meta('license','dc.rights','dcterms.license','cc:license')
        link=soup.select_one('link[rel~="license"],a[rel~="license"]')
        if not page_license and link:page_license=urljoin(page.url,link.get('href',''))
        try:permissions=json.loads((ROOT/'content/image-authorizations.json').read_text())
        except (OSError,ValueError):permissions={}
        authorized_candidates=0
        for candidate in candidates:
            if p.get('directory_name') and not directory_photo_matches(p['directory_name'],candidate):continue
            image=candidate['url'];permission=permissions.get(image,{})
            license_url=candidate['license'] or page_license
            # Publisher originals are selected by the site owner's editorial policy.
            # Preserve rights metadata without inventing permission or a license.
            authorized_candidates+=1
            try:
                saved=save_source_photo(ident,image,page.url,license_url,permission,
                                        meta('dc.creator','author','og:site_name') or urlparse(page.url).hostname,
                                        candidate['label'] or str(p.get('en_title') or ''))
            except requests.RequestException:
                # One broken CDN candidate must not hide the next article image.
                continue
            if saved:
                diagnostic(ident,'source_photo_saved',source=page.url,image=image);return True
        reason='invalid_source_images'
        diagnostic(ident,reason,source=source,candidate_count=len(candidates),candidates=[c['url'] for c in candidates[:3]])
        return False
    except (requests.RequestException,ValueError,OSError,TypeError) as exc:
        diagnostic(ident,'source_error',source=source,error=type(exc).__name__);return False

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

_SUBJECTS=None

def normalized(value):
    value=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower().replace('+',' plus ')
    return ' '.join(re.findall(r'[a-z0-9]+',value))

def reviewed_subjects():
    try:data=json.loads((ROOT/'content/photo-subjects.json').read_text())
    except (OSError,ValueError):return {}
    return data if isinstance(data,dict) else {}

def reviewed_subject(p):
    title=' '+normalized(str(p.get('en_title',''))+' '+str(p.get('source_title','')))+' '
    matches=[]
    for subject,rule in reviewed_subjects().items():
        if p.get('id') in rule.get('article_ids',[]):return subject
        for alias in rule.get('aliases',[]):
            key=normalized(alias)
            if len(key.split())>=2 and ' '+key+' ' in title:
                matches.append((title.index(' '+key+' '),-len(key),subject))
    return min(matches)[2] if matches else ''

def commons_page_license(soup):
    # Multi-licensed files may list GFDL before a perfectly usable CC license.
    for block in soup.select('.licensetpl') or [soup]:
        short=block.select_one('.licensetpl_short');link=block.select_one('.licensetpl_link')
        short=short.get_text(' ',strip=True) if short else ''
        url=link.get_text(' ',strip=True) if link else ''
        if commons_reuse_allowed(short,url):return short,url
    return '',''

def exact_subject(p):
    global _SUBJECTS
    if p.get('image_subject'):return str(p['image_subject'])
    if p.get('directory_name'):return str(p['directory_name'])
    reviewed=reviewed_subject(p)
    if reviewed:return reviewed
    if _SUBJECTS is None:
        names=set()
        for filename in ('directory-details.json','directory-records.json'):
            try:data=json.loads((ROOT/'content'/filename).read_text())
            except (OSError,ValueError):continue
            for kind,rows in data.items():
                if kind not in ('cars','bikes','phones','colleges'):continue
                if isinstance(rows,dict):names.update(rows)
                elif isinstance(rows,list):names.update(r.get('name','') for r in rows if isinstance(r,dict))
        _SUBJECTS=[name for name in names if len(normalized(name).split())>=2]
    title=' '+normalized(str(p.get('en_title',''))+' '+str(p.get('source_title','')))+' '
    matches=[name for name in _SUBJECTS if ' '+normalized(name)+' ' in title]
    if matches:return min(matches,key=lambda n:(title.index(' '+normalized(n)+' '),-len(n)))
    parsed=urlparse(str(p.get('source','')))
    url_words=set(normalized((parsed.hostname or '')+' '+parsed.path).split())
    matches=[name for name in _SUBJECTS if set(normalized(name).split()).issubset(url_words)]
    return max(matches,key=len) if matches else ''

def subject_matches(subject,file_title,metadata):
    filename=normalized(file_title)
    if set(filename.split())&{'logo','icon','seal','map','poster','diagram','drawing','illustration','banner'}:return False
    description=normalized(re.sub('<[^>]+>',' ',metadata.get('ImageDescription',{}).get('value','')))
    # A photograph taken WITH a phone is not a photograph OF that phone.
    if re.search(r'taken with|shot on|photographed with|captured with',description):return False
    if institution(subject) and not campus_image(subject,file_title,description):return False
    tokens=set(words(subject).split())
    if not tokens or not tokens.issubset(set(words(file_title+' '+description).split())):return False
    tail=' '.join(normalized(subject).split()[-2:])
    if re.search(re.escape(tail)+r'\s+(pro|ultra|plus|fe|roxx|dzire)\b',description) and not set(normalized(subject).split())&{'pro','ultra','plus','fe','roxx','dzire'}:return False
    variants={'ultra','plus','pro','max','fe','roxx','4v','dzire','grand','cross','electrified','hybrid'}
    if (set(filename.split()) & variants)-tokens:return False
    return True

def public_commons_photo(p,subject):
    """Read public category/file pages, verify each file's own reuse terms."""
    from urllib.parse import quote
    ident=slug(p);headers={'User-Agent':'GlobeWireDaily/1.0 (contact@globewiredaily.org)'}
    category='https://commons.wikimedia.org/wiki/Category:'+quote(subject.replace(' ','_'),safe='')
    try:
        client=requests.Session()
        try:approved=json.loads((ROOT/'content/approved-photo-sources.json').read_text())
        except (OSError,ValueError):approved={}
        urls=list(approved.get(subject,[]))
        if urls:soup=BeautifulSoup('', 'html.parser')
        else:
            response=client.get(category,timeout=(4,10),headers=headers)
            soup=BeautifulSoup(response.text[:1500000] if response.ok else '', 'html.parser')
        for a in soup.select('.gallerytext a[href],.galleryfilename[href]'):
            url=urljoin(category,a.get('href',''))
            if '/wiki/File:' in url and url.lower().split('?')[0].endswith(('.jpg','.jpeg','.png','.webp')):urls.append(url)
        for page_url in list(dict.fromkeys(urls))[:6]:
            response=client.get(page_url,timeout=(4,10),headers=headers)
            if not response.ok:continue
            fs=BeautifulSoup(response.text[:1500000],'html.parser')
            text=fs.get_text(' ',strip=True)
            if re.search(r'copyright violation|missing permission|no permission|digitally upscaled|AI.generated',text,re.I):continue
            short,license_url=commons_page_license(fs)
            if not short and not license_url:continue
            description=fs.select_one('#fileinfotpl_desc+td')
            description=description.get_text(' ',strip=True) if description else ''
            categories=' '.join(a.get_text(' ',strip=True) for a in fs.select('#mw-normal-catlinks a') if 'taken with' not in a.get_text(' ',strip=True).lower())
            description+=' '+categories
            file_title=fs.select_one('#firstHeading')
            file_title=file_title.get_text(' ',strip=True) if file_title else ''
            if not subject_matches(subject,file_title,{'ImageDescription':{'value':description}}):continue
            photo=fs.select_one('.fullImageLink img')
            if not photo:continue
            srcset=photo.get('srcset','')
            original=fs.select_one('.fullImageLink a[href]')
            preview=srcset.split(',')[-1].strip().split(' ')[0] if srcset else photo.get('src')
            image_urls=[urljoin(page_url,preview or '')]
            if original:image_urls.append(urljoin(page_url,original.get('href','')))
            saved=False
            for image in list(dict.fromkeys(image_urls))[:2]:
                if urlparse(image).scheme!='https':continue
                res=client.get(image,timeout=(4,14),headers={**headers,'Referer':page_url})
                if res.status_code in DENIED:break
                if not res.ok or len(res.content)>12_000_000:continue
                try:
                    with Image.open(io.BytesIO(res.content)) as im:
                        if im.width<600 or im.height<320:continue
                        im=ImageOps.exif_transpose(im).convert('RGB')
                        im=ImageOps.pad(im,(1280,720),method=Image.Resampling.LANCZOS,color=(12,28,55))
                        im.save(IMAGES/(ident+'.jpg'),'JPEG',quality=86,optimize=True)
                    saved=True;break
                except (OSError,ValueError):continue
            if not saved:continue
            author=fs.select_one('#fileinfotpl_aut+td')
            author=author.get_text(' ',strip=True)[:240] if author else 'Wikimedia Commons contributor'
            author=reviewed_subjects().get(subject,{}).get('credits',{}).get(page_url,author)
            metadata={'kind':'licensed_photo','post_id':ident,'subject':subject,'source_image':page_url,'image_url':image,
                      'license':license_url,'license_name':short,'attribution':author,'rights_status':'licensed',
                      'matched_title':file_title,'image_description':description,'width':1280,'height':720,'alt':subject+' — licensed representative photograph',
                      'modifications':'Resized and letterboxed to 16:9; representative photograph, not an event photograph.'}
            (IMAGES/(ident+'.json')).write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
            diagnostic(ident,'licensed_subject_saved',subject=subject,image=image);return True
        return False
    except (requests.RequestException,ValueError,OSError,AttributeError):return False

def commons_photo(p):
    """Get relevant reusable REAL photographs, with clear source and credit."""
    ident=slug(p)
    if not ident or resolved_featured(ident):return False
    # Broad job-listing titles produce irrelevant office seals and foreign photos.
    # Prefer a documented employer-owned original image, else use an illustration.
    if p.get('category')=='private-vacancy':
        print('Commons skipped for generic private vacancy',ident,flush=True)
        return False
    title=str(p.get('source_title') or p.get('en_title') or '')
    subject=exact_subject(p)
    queries=[subject] if subject else []
    if not queries:
        print('Commons search skipped (insufficient subject keywords)',ident,flush=True)
        return False
    if public_commons_photo(p,subject):return True
    try:approved=json.loads((ROOT/'content/approved-photo-sources.json').read_text())
    except (OSError,ValueError):approved={}
    if subject in approved:return False
    headers={'User-Agent':'GlobeWireDaily/1.0 (contact@globewiredaily.org)'}
    for query in queries:
        try:
            response=requests.get('https://commons.wikimedia.org/w/api.php',params={
                'action':'query','generator':'search','gsrsearch':query,
                'gsrnamespace':6,'gsrlimit':4,'prop':'imageinfo',
                'iiprop':'url|size|extmetadata','iiurlwidth':1280,
                'format':'json'},headers=headers,timeout=(5,12))
            response.raise_for_status()
            pages=response.json().get('query',{}).get('pages',{})
            keywords=set(normalized(query).split())
            for page in sorted(pages.values(),key=lambda item:item.get('index',1000)):
                file_title=page.get('title','')
                # The MediaWiki thumbnail API also returns rendered PDF pages,
                # logos, maps and seals; those are not news event photographs.
                if not file_title.lower().endswith(('.jpg','.jpeg','.png','.webp')):continue
                filename_words=set(normalized(file_title).split())
                excluded={'logo','icon','clipart','screenshot','poster','seal','emblem',
                          'map','diagram','chart','document','manual','outline',
                          'illustration','drawing','stamp','flag','plan'}
                if filename_words & excluded:continue
                if not subject_matches(subject,file_title,(page.get('imageinfo') or [{}])[0].get('extmetadata',{})):continue

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
                    im=ImageOps.pad(im.convert('RGB'),(1280,720),method=Image.Resampling.LANCZOS,color=(12,28,55))
                    im.save(IMAGES/(ident+'.jpg'),'JPEG',quality=86,optimize=True)
                attribution=re.sub('<[^>]*>',' ',meta.get('Artist',{}).get('value','')).strip()[:240]
                (IMAGES/(ident+'.json')).write_text(json.dumps({
                    'kind':'licensed_photo','source_image':info.get('descriptionurl'),'image_url':image_url,'post_id':ident,'width':1280,'height':720,'subject':subject,
                    'license':license_url or short_name,'license_name':short_name,
                    'attribution':attribution or 'Wikimedia Commons',
                    'rights_status':'licensed','caption':'Licensed photograph of the named subject; representative, not the reported event.',
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
        if not ident or (resolved_featured(ident) and not representative_featured(ident)):continue
        try:
            stamp=datetime.datetime.fromisoformat(str(post.get('date','')).replace('Z','+00:00'))
            if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=datetime.timezone.utc)
            is_fresh=datetime.timedelta(0)<=now-stamp<=datetime.timedelta(days=3)
        except (TypeError,ValueError):is_fresh=False
        (fresh if is_fresh else older).append(post)
    mode=(mode or os.getenv('IMAGE_BACKFILL_MODE','mixed')).strip().lower()
    if mode=='new':
        # Complete the fresh publication batch; the wall-clock budget bounds work.
        fresh_limit=max(limit,len(fresh))
        return (fresh+older)[:fresh_limit],len(fresh),len(older)
    if mode in ('all','directory'):
        rows=fresh+older
        if mode=='directory':rows=[p for p in rows if p.get('content_type')=='evergreen_directory_guide']
        rows.sort(key=lambda p:(0 if p.get('directory_name') else 1,p.get('category',''),p.get('id','')))
        # Visit never-attempted/oldest-attempted posts first, including across time-budget exits.
        attempts=(cursor or {}).get('attempts',{})
        rows.sort(key=lambda p:attempts.get(slug(p),{}).get('retry_after',0))
        return rows[:limit],len(fresh),len(older)
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
    # Rotate fresh candidates too, so historic posts retain their reserved share
    # and repeated scheduled runs do not always select the same fresh images.
    selected=rotate(fresh,fresh_budget,'fresh_offset')+rotate(older,older_budget,'archive_offset')
    return selected,len(fresh),len(older)

def main():
    posts=[]
    for f in POSTS.glob('*.json'):
        try:
            p=json.loads(f.read_text(encoding='utf-8').removesuffix(chr(92)+'n'))
            if slug(p):posts.append(p)
        except (OSError,ValueError):pass
    try:cursor=json.loads(BACKFILL_STATE.read_text())
    except (OSError,ValueError):cursor={}
    if not isinstance(cursor,dict):cursor={}
    mode=os.getenv('IMAGE_BACKFILL_MODE') or ('new' if os.getenv('AUTO_POST','').lower() in ('true','1','yes') else 'mixed')
    candidates,fresh_count,older_count=choose_backfill(posts,cursor=cursor,mode=mode)
    if not candidates:
        print('IMAGE_BACKFILL_SUMMARY',json.dumps({'selected':0,'total_posts':len(posts)}),flush=True)
        return
    seconds=max(1,int(os.getenv('IMAGE_BACKFILL_SECONDS','420')))
    workers=max(1,min(12,int(os.getenv('IMAGE_BACKFILL_WORKERS','6'))))
    deadline=time.monotonic()+seconds
    attempts=cursor.setdefault('attempts',{});results=[]
    force=os.getenv('IMAGE_BACKFILL_FORCE','0')=='1'
    policy=hashlib.sha256(Path(__file__).read_bytes()+b''.join((ROOT/'content'/name).read_bytes() if (ROOT/'content'/name).exists() else b'' for name in ('approved-photo-sources.json','image-authorizations.json','photo-subjects.json'))).hexdigest()[:12]
    posts=list({slug(p):p for p in posts}.values())
    source_cache={};subject_cache={}
    for post in posts:
        ident=slug(post)
        if resolved_featured(ident):
            if post.get('source') and not representative_featured(ident):source_cache.setdefault(str(post['source']).split('#')[0],ident)
            try:meta=json.loads((IMAGES/(ident+'.json')).read_text())
            except (OSError,ValueError):meta={}
            if meta.get('subject') and commons_reuse_allowed(meta.get('license_name',''),meta.get('license','')):
                subject_cache.setdefault(normalized(meta['subject']),ident)
    def process(post):
        ident=slug(post);source=str(post.get('source','')).split('#')[0]
        if time.monotonic()>=deadline:return {'id':ident,'result':'time_budget'}
        previous=attempts.get(ident,{})
        if not force and previous.get('source')==source and previous.get('policy')==policy and previous.get('retry_after',0)>time.time():return {'id':ident,'result':'cooldown'}
        other=source_cache.get(source)
        if other and other!=ident:
            import shutil
            shutil.copy2(IMAGES/(other+'.jpg'),IMAGES/(ident+'.jpg'))
            data=json.loads((IMAGES/(other+'.json')).read_text());data.update(post_id=ident,reused_from=other)
            (IMAGES/(ident+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            return {'id':ident,'result':'source_cache_reused'}
        if licensed_source_image(post):result='source_photo_saved'
        elif resolved_featured(ident):
            result=PHOTO_DIAGNOSTICS.get(ident,{}).get('reason','no_article_original')
            diagnostic(ident,result,**{k:v for k,v in PHOTO_DIAGNOSTICS.get(ident,{}).items() if k!='reason'},existing_representative_preserved=True)
        else:result=PHOTO_DIAGNOSTICS.get(ident,{}).get('reason','no_suitable_photo')
        if result in ('source_photo_saved','licensed_subject_saved','licensed_subject_reused'):
            with PHOTO_LOCK:source_cache.setdefault(source,ident)
        return {'id':ident,'source':source,'policy':policy,'result':result,'retry_after':time.time()+21600}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(process,p):p for p in candidates}
        for future in as_completed(futures):
            try:row=future.result()
            except Exception as exc:row={'id':slug(futures[future]),'result':'worker_error','error':type(exc).__name__}
            results.append(row)
            if row['result'] not in ('cooldown','time_budget'):attempts[row['id']]=row
    BACKFILL_STATE.write_text(json.dumps(cursor,ensure_ascii=False,indent=2)+'\n')
    counts=dict(Counter(row['result'] for row in results))
    missing=[{'id':slug(p),'category':p.get('category'),'title':p.get('en_title'),'source':p.get('source'),'reason':PHOTO_DIAGNOSTICS.get(slug(p),{}).get('reason') or attempts.get(slug(p),{}).get('result','not_attempted')} for p in posts if not resolved_featured(slug(p))]
    report={'total_posts':len(posts),'selected':len(candidates),'results':counts,'still_missing':len(missing),
            'articles':results,'missing':missing,'missing_reasons':dict(Counter(row['reason'] for row in missing)),
            'existing_representatives_preserved':sum(bool(d.get('existing_representative_preserved')) for d in PHOTO_DIAGNOSTICS.values()),
            'diagnostics':PHOTO_DIAGNOSTICS,'mode':mode}
    serialized=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    (ROOT/'content/image-audit-status.json').write_text(serialized)
    audit_name='archive' if mode=='all' else ('directory' if mode=='directory' else 'news')
    (ROOT/'content'/('image-audit-'+audit_name+'.json')).write_text(serialized)
    print('IMAGE_BACKFILL_SUMMARY',json.dumps({k:v for k,v in report.items() if k not in ('articles','missing','diagnostics')}),flush=True)
if __name__=='__main__':main()
