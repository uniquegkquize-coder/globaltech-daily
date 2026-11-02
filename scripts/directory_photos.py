"""Find original publisher photos for directory cards and profiles."""
import hashlib,json,os,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from directory_facts import FOCUS,meaningful
import generate_images as images
ROOT=Path(__file__).resolve().parents[1]
def main():
 data=json.loads((ROOT/'content/directory-details.json').read_text());end=time.monotonic()+int(os.getenv('DIRECTORY_PHOTO_SECONDS','120'));limit=int(os.getenv('DIRECTORY_PHOTO_LIMIT','24'))
 kinds=('colleges','cars','phones','bikes')
 tasks=[(kind,name,entry) for kind in kinds for name,entry in data.get(kind,{}).items() if meaningful(entry)]
 tasks.sort(key=lambda t:(t[1] not in FOCUS[t[0]],kinds.index(t[0]),t[1]))
 def fetch(task):
  if time.monotonic()>end:return 0
  kind,name,entry=task
  ident=hashlib.sha256(('directory:'+kind+':'+name).encode()).hexdigest()[:24]
  if images.resolved_featured(ident):return 0
  for source in dict.fromkeys([entry.get('official_url'),entry.get('image_source_url'),entry.get('evidence_url'),entry.get('source_url')]):
   if not source or not source.startswith('https://') or source.lower().endswith('.pdf') or time.monotonic()>end:continue
   if images.licensed_source_image({'id':ident,'source':source,'en_title':name,'image_subject':name}):break
  return 1
 with ThreadPoolExecutor(max_workers=4) as pool:done=sum(pool.map(fetch,tasks[:limit]))
 print('DIRECTORY_PHOTOS_ATTEMPTED',done)
if __name__=='__main__':main()
