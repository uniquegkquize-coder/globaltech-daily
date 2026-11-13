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
def prepare_image(content, *, minimum_width=1200, formats=None):
    if len(content) > 15_000_000:
        raise ValueError('Photo must be at most 15 MB.')
    try:
        with Image.open(io.BytesIO(content), formats=formats) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError('Photo must be at most 40 megapixels.')
            image = ImageOps.exif_transpose(image).convert('RGB')
    except Image.DecompressionBombError as exc:
        raise ValueError('Photo must be at most 40 megapixels.') from exc
    if image.width < minimum_width:
        raise ValueError(f'Photo must be at least {minimum_width} pixels wide.')
    return ImageOps.pad(image, (1280, 720), method=Image.Resampling.LANCZOS, color=(12,28,55))


def save_featured(root, post, content, kind, credit, license_name, source, url, *, uploaded=False):
    image = prepare_image(content, minimum_width=1 if uploaded else 1200,
                          formats=['JPEG', 'PNG', 'WEBP'] if uploaded else None)
    folder = root / 'content/featured'
    folder.mkdir(parents=True, exist_ok=True)
    post_id = post['id']
    image.save(folder / (post_id + '.jpg'), quality=84, optimize=True)
    metadata = {
        'kind': kind, 'attribution': credit, 'license': license_name, 'source_url': source,
        'image_url': url, 'post_id': post_id, 'width': 1280, 'height': 720,
        'alt': post.get('en_title', ''), 'rights_status': 'authorized',
        'modifications': 'Resized and letterboxed to 1280x720',
    }
    if uploaded:
        metadata.update(source_image=url, license_name=license_name)
    (folder / (post_id + '.json')).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )


def main():
    if len(sys.argv)<6:
        raise SystemExit(__doc__)
    post_id,url,source,license_name,credit=sys.argv[1:6]
    kind=sys.argv[6] if len(sys.argv)>6 else 'licensed_source'
    if kind not in ('licensed_source','publisher_source'):
        raise SystemExit('Invalid kind')
    if not post_id or any(c not in '0123456789abcdef' for c in post_id.lower()) or len(post_id)>32:
        raise SystemExit('Expected hexadecimal post ID')
    matches=[f for f in (ROOT/'content'/'posts').glob('*.json') if f.stem.startswith(post_id)]
    if len(matches)!=1:raise SystemExit('Post ID must resolve to exactly one existing article')
    post=json.loads(matches[0].read_text(encoding='utf-8'))
    post_id=str(post['id'])
    if any(urlparse(u).scheme!='https' for u in (url,source)):
        raise SystemExit('HTTPS image and attribution URLs required')
    if not license_name.strip() or not credit.strip():
        raise SystemExit('License and credit must be provided')
    response=requests.get(url,timeout=20,headers={'User-Agent':'GlobeWireDailyImageImporter/1.0 (editorial media use)'})
    response.raise_for_status()
    save_featured(ROOT, post, response.content, kind, credit, license_name, source, url)
    print('Imported image with attribution metadata:',post_id)
if __name__=='__main__':main()
