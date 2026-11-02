"""Find original publisher photos for directory cards and profiles."""
import hashlib,json,os,time,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from directory_facts import FOCUS,meaningful,guide_images,safe_url
import generate_images as images
ROOT=Path(__file__).resolve().parents[1]
def sync_guide_photo(kind,name,ident):
 guide=guide_images().get((kind,name.casefold()))
 if not guide or not images.resolved_featured(ident):return
 if images.resolved_featured(guide) and not images.representative_featured(guide):return
 folder=images.IMAGES
 metadata=json.loads((folder/(ident+'.json')).read_text());metadata['post_id']=guide
 shutil.copy2(folder/(ident+'.jpg'),folder/(guide+'.jpg'))
 (folder/(guide+'.json')).write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')

def pinned_photo(entry,ident,name):
 image=entry.get('source_image_url');page=entry.get('image_source_url') or entry.get('official_url')
 if not image or not page or not safe_url(image) or not safe_url(page):return False
 try:return images.save_source_photo(ident,image,page,'',{},entry.get('manufacturer') or name,name)
 except images.requests.RequestException:return False

def main():
 data=json.loads((ROOT/'content/directory-details.json').read_text());end=time.monotonic()+int(os.getenv('DIRECTORY_PHOTO_SECONDS','120'));limit=int(os.getenv('DIRECTORY_PHOTO_LIMIT','24'))
 kinds=('colleges','cars','phones','bikes')
 tasks=[(kind,name,entry) for kind in kinds for name,entry in data.get(kind,{}).items() if meaningful(entry)]
 tasks.sort(key=lambda t:(t[1] not in FOCUS[t[0]],kinds.index(t[0]),t[1]))
 def fetch(task):
  if time.monotonic()>end:return 0
  kind,name,entry=task
  ident=hashlib.sha256(('directory:'+kind+':'+name).encode()).hexdigest()[:24]
  if images.resolved_featured(ident):
   sync_guide_photo(kind,name,ident);return 0
  if pinned_photo(entry,ident,name):
   sync_guide_photo(kind,name,ident);return 1
  for source in dict.fromkeys([entry.get('official_url'),entry.get('image_source_url'),entry.get('evidence_url'),entry.get('source_url')]):
   if not source or not source.startswith('https://') or source.lower().endswith('.pdf') or time.monotonic()>end:continue
   if images.licensed_source_image({'id':ident,'source':source,'en_title':name,'image_subject':name,'directory_name':name}):break
  sync_guide_photo(kind,name,ident)
  return 1
 with ThreadPoolExecutor(max_workers=4) as pool:done=sum(pool.map(fetch,tasks[:limit]))
 print('DIRECTORY_PHOTOS_ATTEMPTED',done)
if __name__=='__main__':main()
