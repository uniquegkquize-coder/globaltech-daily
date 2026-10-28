"""Optional licensed image importer for GlobeWire Daily.
Usage: python scripts/import_image.py POST_ID IMAGE_URL SOURCE_URL LICENSE CREDIT [KIND]
Kinds: licensed_source, publisher_source. Only use after verifying the image's actual terms.
Does not delete existing media or change publishing automation.
"""
import sys, json, io, pathlib
from urllib.parse import urlparse
import requests
from PIL import Image, ImageOps
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    if len(sys.argv)<6:
        raise SystemExit(__doc__)
    post_id,url,source,license_name,credit=sys.argv[1:6]
    kind=sys.argv[6] if len(sys.argv)>6 else 'licensed_source'
    if kind not in ('licensed_source','publisher_source'):
        raise SystemExit('Invalid kind')
    if not post_id or any(c not in '0123456789abcdef' for c in post_id.lower()) or len(post_id)>32:
        raise SystemExit('Expected hexadecimal post ID')
    if any(urlparse(u).scheme!='https' for u in (url,source)):
        raise SystemExit('HTTPS image and attribution URLs required')
    if not license_name.strip() or not credit.strip():
        raise SystemExit('License and credit must be provided')
    response=requests.get(url,timeout=20,headers={'User-Agent':'GlobeWireDailyImageImporter/1.0 (editorial media use)'})
    response.raise_for_status()
    if len(response.content)>15_000_000:
        raise SystemExit('Image too large')
    im=Image.open(io.BytesIO(response.content))
    im=ImageOps.exif_transpose(im).convert('RGB')
    if im.width<1200:
        raise SystemExit('Image must be at least 1200 pixels wide')
    im.thumbnail((1600,1200))
    folder=ROOT/'content'/'featured'
    folder.mkdir(parents=True,exist_ok=True)
    im.save(folder/(post_id+'.jpg'),quality=84,optimize=True)
    (folder/(post_id+'.json')).write_text(json.dumps({'kind':kind,'attribution':credit,'license':license_name,'source_url':source,'image_url':url},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Imported image with attribution metadata:',post_id)
if __name__=='__main__':main()
