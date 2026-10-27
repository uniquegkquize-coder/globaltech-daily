"""Optional Gemini image generation. Saves one reusable 16:9 featured image per post.
Falls back to build.py's original illustrations when image generation is unavailable.
"""
from pathlib import Path
import os, json, io, time, re
import requests
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
POSTS=ROOT/'content/posts'
IMAGES=ROOT/'content/featured'
IMAGES.mkdir(parents=True,exist_ok=True)
KEY=os.getenv('GEMINI_API_KEY','').strip()
MODEL=os.getenv('GEMINI_IMAGE_MODEL','gemini-2.5-flash-image').strip()
MODELS=list(dict.fromkeys([m.strip() for m in (MODEL+','+os.getenv('GEMINI_IMAGE_FALLBACK_MODELS','gemini-3-pro-image-preview')).split(',') if m.strip()]))
QUOTA_BLOCKED=set()
MAX_NEW=max(0,min(30,int(os.getenv('MAX_NEW_IMAGES','30'))))

def slug(p):return re.sub('[^a-f0-9]','',str(p.get('id','')))[:32]

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

def main():
    if not KEY:
        print('GEMINI_API_KEY missing: no image generation',flush=True)
        return
    posts=[]
    for f in POSTS.glob('*.json'):
        try:
            p=json.loads(f.read_text(encoding='utf-8'))
            if slug(p):posts.append(p)
        except (OSError,ValueError):pass
    posts.sort(key=lambda p:p.get('date',''),reverse=True)
    count=0
    for p in posts:
        if count>=MAX_NEW or len(QUOTA_BLOCKED)>=len(MODELS):break
        if (IMAGES/(slug(p)+'.jpg')).exists():continue
        count+=1
        create(p)
    print('Image generation attempts:',count,flush=True)
if __name__=='__main__':main()
