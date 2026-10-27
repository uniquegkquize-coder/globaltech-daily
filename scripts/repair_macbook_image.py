"""One-time correction of unrelated MacBook featured art. Backup originals first."""
from pathlib import Path
from PIL import Image, ImageDraw
import json, shutil
ROOT=Path(__file__).resolve().parents[1]
posts=ROOT/'content/posts'; featured=ROOT/'content/featured'
featured.mkdir(parents=True,exist_ok=True)
count=0
for path in posts.glob('*.json'):
 try: p=json.loads(path.read_text(encoding='utf-8'))
 except (ValueError,OSError):continue
 title=' '.join(str(p.get(k,'')) for k in ('en_title','source_title')).lower()
 if 'macbook' not in title:continue
 ident=str(p.get('id',''))
 if not ident or not all(c in '0123456789abcdef' for c in ident):continue
 dest=featured/(ident+'.jpg')
 if dest.exists():
  backup=featured/(ident+'.previous.jpg')
  if not backup.exists():shutil.copy2(dest,backup)
 im=Image.new('RGB',(1280,720),'#101d32');d=ImageDraw.Draw(im)
 d.ellipse((590,-200,1510,620),fill='#224a70')
 d.rounded_rectangle((270,95,1010,530),radius=24,fill='#101722',outline='#a3c8e8',width=16)
 d.rounded_rectangle((298,123,982,503),radius=8,fill='#326f9d')
 d.ellipse((540,180,755,395),outline='#9edbf8',width=12)
 d.ellipse((612,252,684,324),fill='#d5f3ff')
 d.polygon([(220,530),(1060,530),(1185,620),(95,620)],fill='#a5b6c7')
 d.polygon([(520,546),(760,546),(804,579),(477,579)],fill='#6c7d90')
 d.line((95,621,1185,621),fill='#e3edf8',width=9)
 im.save(dest,'JPEG',quality=90,optimize=True)
 (featured/(ident+'.json')).write_text(json.dumps({'kind':'original_diagram','caption':'Original conceptual laptop illustration; not a product photograph.'}),encoding='utf-8')
 print('Replaced unrelated MacBook art:',ident,'backup preserved',flush=True)
 count+=1
print('MacBook images repaired:',count,flush=True)
