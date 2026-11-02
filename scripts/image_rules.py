"""Identity checks for automatically selected representative photographs."""
import json
import re
import unicodedata
from urllib.parse import unquote

def words(value):
    value=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower()
    value=re.sub(r'\biit\b','indian institute of technology',value)
    return ' '.join(re.findall(r'[a-z0-9]+',value))

def institution(subject):
    return bool(re.search(r'\b(university|college|institute|iit|iim|nit)\b',str(subject),re.I))

def campus_image(subject,title,description=''):
    text=words(title+' '+description)
    tokens=set(text.split())
    if tokens & {'cat','cats','kitten','dog','dogs','puppy','portrait','professor','selfie'}:return False
    if tokens & {'logo','seal','poster','banner','map','drawing'}:return False
    if tokens & {'campus','building','buildings','entrance','gate','library','hostel','apartments','auditorium','academic'}:return True
    name=set(words(subject).split())
    filename=set(words(title).split())-{'file','jpg','jpeg','png','webp'}
    return filename==name

def canonical(url):
    return unquote(str(url)).split('?')[0].replace(' ','_')

def saved_photo_allowed(info,root=None):
    if str(info.get('review_status','')).lower() in ('replace','rejected','needs_replacement'):return False
    if info.get('kind')!='licensed_photo':return True
    subject=info.get('subject','')
    if institution(subject):
        return campus_image(subject,info.get('matched_title',''),info.get('image_description',''))
    return True
