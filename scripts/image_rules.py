"""Identity checks for automatically selected representative photographs."""
import json
import re
import unicodedata
from urllib.parse import unquote,urlparse

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

def model_conflict(expected,value):
    def codes(raw):
        result={}
        for prefix,number in re.findall(r'\b([a-z]{1,8})\s*(\d{1,4})\b',words(raw)):
            result.setdefault(prefix,set()).add(number)
        return result
    want=codes(expected);found=codes(value)
    return any(prefix in found and not found[prefix].issubset(numbers) for prefix,numbers in want.items())

def directory_photo_matches(subject,candidate):
    value=unquote(candidate.get('url',''))+' '+candidate.get('label','')
    if model_conflict(subject,value):return False
    for variant in ('ultra','roxx','xtec'):
        if variant in words(value).split() and variant not in words(subject).split():return False
    compact=lambda raw:re.sub('[^a-z0-9]','',words(raw))
    tokens=words(subject).split()
    identifiers=re.findall(r'\b[a-z]{1,8}\s*\d{1,4}\b',words(subject))
    if identifiers and any(compact(code) in compact(value) for code in identifiers):return True
    model=' '.join(tokens[-2:] if tokens and tokens[-1] in ('plus','pro','max') else tokens[-1:])
    if model and compact(model) in compact(value):return True
    if institution(subject) and campus_image(subject,value):return True
    return candidate.get('origin') in ('social','structured')

def saved_photo_allowed(info,root=None):
    if str(info.get('review_status','')).lower() in ('replace','rejected','needs_replacement'):return False
    source_path=unquote(urlparse(str(info.get('source',''))).path)
    if model_conflict(source_path,info.get('source_image','')):return False
    if info.get('kind')!='licensed_photo':return True
    subject=info.get('subject','')
    if institution(subject):
        return campus_image(subject,info.get('matched_title',''),info.get('image_description',''))
    return True


def pipeline_fingerprint(root):
    """Version the deployed image code/config without relying on provider badges."""
    import hashlib
    from pathlib import Path
    digest=hashlib.sha256()
    for name in ('scripts/build.py','scripts/generate_images.py','scripts/image_rules.py','content/approved-photo-sources.json','content/photo-subjects.json'):
        digest.update(name.encode()+b'\0')
        digest.update((Path(root)/name).read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()
