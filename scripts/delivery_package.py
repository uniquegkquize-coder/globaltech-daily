"""Deterministic R2 release packages and fail-closed Pages assembly.

HTML and legacy /images/ are served by three scoped Worker routes. Root assets
stay on Pages. No source files or remote objects are ever deleted here.
"""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
MAX_PAGES_FILES = 19000
SCOPES = ('/en/', '/hi/', '/images/')
PROHIBITED = {'__pycache__', '.cache', 'node_modules', '.git'}
ROOT_ASSETS={'404.html','_headers','_redirects','ads.txt','d9e47b8c32a16f5098c7d6e5b4a3210f.txt','deployment.json','favicon.svg','googled7fc3627b4add656.html','index.html','news-sitemap.xml','publisher-logo.png','robots.txt','seo-audit.json','site.js','sitemap.xml','social-card.jpg','style.css'}

def root_allowed(relative):
    return relative in ROOT_ASSETS or bool(re.fullmatch(r'(?:news-sitemap-[0-9]+|sitemap-pages-[0-9]+)\.xml',relative))



def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def managed_reset(path):
    path = Path(path)
    # Only these fixed output directories are safe to replace.
    if path.resolve() not in {ROOT/'dist', ROOT/'build/pages', ROOT/'build/r2-package'} or path.is_symlink():
        raise ValueError('Not a managed deployment directory')
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def assert_pages(root):
    files = [p for p in Path(root).rglob('*') if p.is_file()]
    if len(files) > MAX_PAGES_FILES:
        raise ValueError(f'Pages asset guard: {len(files)} > {MAX_PAGES_FILES}')
    for p in files:
        relative=p.relative_to(root).as_posix()
        if '/' in relative and Path(relative).parts[0] not in ('en','hi','images'):raise ValueError('Unexpected deployment directory: '+relative)
        if '/' not in relative and not root_allowed(relative):raise ValueError('Unexpected root deployment artifact: '+relative)
        if PROHIBITED.intersection(p.parts) or p.suffix in ('.pyc', '.zip', '.log') or p.is_symlink():
            raise ValueError('Prohibited Pages artifact: ' + str(p))
    for name in ('404.html', '_redirects', '_headers', 'robots.txt', 'sitemap.xml', 'news-sitemap.xml'):
        if not (Path(root)/name).is_file():
            raise ValueError('Missing deployment artifact: ' + name)
    return len(files)


def publish_static(rendered, output):
    # Check BEFORE replacing the last working artifact. Rendering alone is not deployment.
    assert_pages(rendered)
    managed_reset(output)
    shutil.copytree(rendered, output, dirs_exist_ok=True)
    assert_pages(output)


def build_package(rendered, redirects, output, historical=None):
    rendered, output = Path(rendered), Path(output)
    managed_reset(output)
    routes = {}
    bodies = {}
    legacy_path=ROOT/'content/r2-image-baseline.json'
    legacy=json.loads(legacy_path.read_text()) if legacy_path.exists() else {}
    legacy_by_hash={}
    for name,sha in sorted(legacy.items()):legacy_by_hash.setdefault(sha,'images/'+name)

    def add_body(path, data, mime):
        sha = digest(data)
        from mimetypes import guess_extension
        extension='.html' if mime.startswith('text/html') else guess_extension(mime) or '.bin'
        key = legacy_by_hash.get(sha) if path.startswith('/images/') else None
        key = key or 'objects/' + sha + extension
        routes[path] = {'key':key, 'sha256':sha, 'bytes':len(data), 'type':mime}
        bodies.setdefault(key, data)
    projected=[]
    for p in sorted(rendered.rglob('*')):
        if not p.is_file():continue
        relative=p.relative_to(rendered).as_posix();top=Path(relative).parts[0]
        if top in ('en','hi'):
            if not relative.endswith('/index.html'):raise ValueError('Unexpected generated language artifact: '+relative)
        elif top=='images':
            if p.suffix.lower() not in ('.jpg','.jpeg','.png','.webp','.gif','.svg','.avif'):raise ValueError('Unexpected generated image artifact: '+relative)
        else:
            if not root_allowed(relative):raise ValueError('Unexpected Pages artifact: '+relative)
            projected.append(p)
    if len(projected)>MAX_PAGES_FILES:raise ValueError('Projected Pages asset guard exceeded')
    inputs = []
    if historical and Path(historical).is_dir():
        inputs.extend(sorted(Path(historical).rglob('*')))
    inputs.extend(sorted(rendered.rglob('*')))
    for p in inputs:
        if not p.is_file():continue
        base = rendered if p.is_relative_to(rendered) else Path(historical)
        rel = p.relative_to(base).as_posix()
        if rel.endswith('/index.html') and rel.startswith(('en/', 'hi/')):
            add_body('/'+rel.removesuffix('index.html'), p.read_bytes(), 'text/html; charset=utf-8')
        elif rel.startswith('images/'):
            from mimetypes import guess_type
            add_body('/'+rel, p.read_bytes(), guess_type(rel)[0] or 'application/octet-stream')
    for source, (target, code) in sorted(redirects.items()):
        if source == '/':continue  # Always handled on Pages.
        if not source.startswith(('/en/', '/hi/')) or not target.startswith(('/en/', '/hi/')):
            raise ValueError('Redirect outside delivery scope')
        # Flatten chains and fail on loops or missing destinations.
        seen = {source}
        while target in redirects:
            if target in seen:raise ValueError('Redirect loop: '+source)
            seen.add(target);target = redirects[target][0]
        if target not in routes:raise ValueError('Missing redirect target: '+target)
        routes[source] = {'redirect':target, 'status':int(code)}
    if not routes:raise ValueError('Empty release')
    shards = {}
    for path, row in sorted(routes.items()):
        shard = digest(path.encode())[:2]
        shards.setdefault(shard, {})[path] = row
    release = {'version':1, 'scopes':list(SCOPES), 'shards':{}}
    for shard, values in sorted(shards.items()):
        data = encoded(values);key = 'manifests/'+digest(data)+'.json'
        bodies[key] = data;release['shards'][shard] = key
    data = encoded(release);release_id = digest(data)
    bodies['releases/'+release_id+'.json'] = data
    inventory = []
    for key, data in sorted(bodies.items()):
        p = output/key;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        from mimetypes import guess_type
        inventory.append({'key':key,'sha256':digest(data),'bytes':len(data),'type':guess_type(key)[0] or 'application/octet-stream'})
    package = {'release_id':release_id,'routes':len(routes),'files':inventory,'pages_files':len(projected),'pages_bytes':sum(p.stat().st_size for p in projected),
               'url_inventory':routes,'bytes':sum(x['bytes'] for x in inventory),
               'by_scope':dict(Counter(next(s for s in SCOPES if p.startswith(s)) for p in routes)),
               'deduplicated_bodies':sum('key' in r for r in routes.values())-len({r['key'] for r in routes.values() if 'key' in r})}
    (output/'package.json').write_bytes(encoded(package))
    return package


def assemble_pages(rendered, package, receipt, output):
    # Receipt is produced only by upload+remote verification for THIS exact package.
    if receipt.get('release_id') != package['release_id'] or receipt.get('verified') is not True or receipt.get('count') != len(package['files']):
        raise ValueError('Missing/mismatched remote verification receipt')
    expected = digest(encoded(package['files']))
    if receipt.get('inventory_sha256') != expected:
        raise ValueError('Receipt does not cover this package')
    managed_reset(output)
    for p in sorted(Path(rendered).rglob('*')):
        if not p.is_file():continue
        rel = p.relative_to(rendered)
        if rel.parts[0] in ('en','hi','images'):continue
        dest = Path(output)/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    redirects=['/ /en/ 301']
    for name in ('news-sitemap-1.xml','news-sitemap-2.xml'):
        if not (Path(output)/name).exists():redirects.append('/'+name+' /news-sitemap.xml 301')
    (Path(output)/'_redirects').write_text('\n'.join(redirects)+'\n')
    count = assert_pages(output)
    return {'files':count, 'release_id':package['release_id']}


def verify_baseline(package, baseline):
    routes = package['url_inventory']
    missing = []
    for rel in baseline:
        if rel.startswith(('en/','hi/')) and rel.endswith('/index.html'):
            path = '/'+rel.removesuffix('index.html')
        elif rel.startswith('images/'):
            path = '/'+rel
        else:continue
        if path not in routes:missing.append(path)
    if missing:raise ValueError('Historical URLs lost: '+repr(missing[:20]))
    return True


def main():
    p = argparse.ArgumentParser();p.add_argument('--receipt');p.add_argument('--baseline');a = p.parse_args()
    rendered=ROOT/'build/rendered'
    redirects=json.loads((ROOT/'build/redirects.json').read_text())
    result=build_package(rendered, redirects, ROOT/'build/r2-package', ROOT/'content/historical-pages')
    if a.baseline:verify_baseline(result,json.loads(Path(a.baseline).read_text()))
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','url_inventory')}))
    if a.receipt:print(assemble_pages(rendered,result,json.loads(Path(a.receipt).read_text()),ROOT/'build/pages'))

if __name__ == '__main__':main()
