"""Offline completeness and bounded staging/public HTTP verification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import requests
from delivery_package import ROOT, digest


def audit(package, baseline):
    routes=package['url_inventory'];errors=[]
    for path in baseline['urls']:
        if path not in routes:errors.append('Lost historical URL: '+path)
    for path,row in routes.items():
        if 'redirect' in row:
            if row['redirect'] not in routes or 'redirect' in routes[row['redirect']]:errors.append('Invalid redirect: '+path)
        else:
            p=ROOT/'build/r2-package'/row['key']
            if not p.is_file() or digest(p.read_bytes())!=row['sha256']:errors.append('Missing/changed object: '+path)
    # Every published source ID represented in either an article or a real 301 alias.
    for p in (ROOT/'content/posts').glob('*.json'):
        post=json.loads(p.read_text());ident=''.join(c for c in str(post.get('id','')) if c in '0123456789abcdef')[:32]
        if ident and str(post.get('source','')).startswith('https://') and len(post.get('en_body',''))>=150:
            for lang in ('en','hi'):
                if f'/{lang}/news/{ident}/' not in routes:errors.append('Source article lost: '+str(p))
    if errors:raise ValueError('\n'.join(errors[:30]))
    return {'historical_urls':len(baseline['urls']),'routes':len(routes),'images':sum(p.startswith('/images/') for p in routes),'errors':0}


def smoke(origin,package,all_urls=False,changed_keys=()):
    routes=package['url_inventory']
    if all_urls:paths=sorted(routes)
    else:
        # Every new/changed public object is checked before promotion, plus bounded coverage.
        changed=set(changed_keys)
        paths=[path for path,row in routes.items() if row.get('key') in changed]
        for prefix in ('/en/news/','/hi/news/','/images/','/en/cars/','/hi/phones/','/en/colleges/'):
            paths.extend([p for p,r in routes.items() if p.startswith(prefix) and 'key' in r][:4])
        ordered=sorted(routes);step=max(1,len(ordered)//48)
        paths=sorted(set(paths+['/en/','/hi/']+ordered[::step][:48]+[p for p,r in routes.items() if 'redirect' in r][:12]))
        if len(paths)>40000:raise ValueError('Changed-URL verification exceeds safe daily Worker test budget; explicit rollout planning required')
    def check(path):
        row=routes[path];response=requests.get(origin.rstrip('/')+path,timeout=(5,30),allow_redirects=False)
        if 'redirect' in row:
            if response.status_code!=row['status'] or response.headers.get('Location')!=row['redirect']:raise ValueError('HTTP redirect mismatch: '+path)
        elif response.status_code!=200 or digest(response.content)!=row['sha256'] or row['type'].split(';')[0] not in response.headers.get('Content-Type',''):
            raise ValueError('HTTP content/hash/MIME mismatch: '+path)
        return path
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(check,paths))
    for path in ('/en/news/definitely-missing-check/','/images/definitely-missing-check.jpg'):
        if requests.get(origin.rstrip('/')+path,timeout=20).status_code!=404:raise ValueError('Unknown URL is not 404')
    if requests.post(origin.rstrip('/')+'/en/',timeout=20).status_code!=405:raise ValueError('POST must be 405')
    h=requests.head(origin.rstrip('/')+'/en/',timeout=20)
    if h.status_code!=200 or h.content:raise ValueError('HEAD behavior failed')
    r=requests.get(origin.rstrip('/')+'/en/',headers={'If-None-Match':h.headers.get('ETag','')},timeout=20)
    if r.status_code!=304:raise ValueError('Conditional GET failed')
    return {'http_urls_checked':len(paths),'all_urls':all_urls,'origin':origin}


def main():
    p=argparse.ArgumentParser();p.add_argument('--origin');p.add_argument('--all-urls',action='store_true');a=p.parse_args()
    package=json.loads((ROOT/'build/r2-package/package.json').read_text());baseline=json.loads((ROOT/'content/published-url-inventory.json').read_text())
    result=audit(package,baseline)
    if a.origin:result.update(smoke(a.origin,package,a.all_urls))
    (ROOT/'build/delivery-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
