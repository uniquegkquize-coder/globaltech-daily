"""Offline completeness and bounded staging/public HTTP verification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import requests
import threading
import os
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
    sessions=threading.local()
    def check(path):
        if not hasattr(sessions,'client'):sessions.client=requests.Session()
        row=routes[path];response=sessions.client.get(origin.rstrip('/')+path,timeout=(5,30),allow_redirects=False)
        if 'redirect' in row:
            if response.status_code!=row['status'] or response.headers.get('Location')!=row['redirect']:raise ValueError('HTTP redirect mismatch: '+path)
        else:
            actual_hash=digest(response.content)
            actual_type=response.headers.get('Content-Type','')
            expected_type=row['type'].split(';')[0]
            if response.status_code!=200 or actual_hash!=row['sha256'] or expected_type not in actual_type:
                # No body or secret values in CI logs; distinguish wrong route,
                # stale cache, encoding, and MIME mismatch before changing delivery.
                details={
                    'path':path,'status':response.status_code,
                    'expected_sha256':row['sha256'],'actual_sha256':actual_hash,
                    'expected_bytes':row['bytes'],'actual_bytes':len(response.content),
                    'expected_type':row['type'],'actual_type':actual_type,
                    'content_encoding':response.headers.get('Content-Encoding',''),
                    'etag':response.headers.get('ETag',''),
                    'cf_cache_status':response.headers.get('CF-Cache-Status',''),
                    'server':response.headers.get('Server',''),
                    'redirect_location':response.headers.get('Location',''),
                }
                raise ValueError('HTTP content/hash/MIME mismatch: '+json.dumps(details,sort_keys=True))
        return path
    workers=max(1,min(12,int(os.environ.get('DELIVERY_HTTP_WORKERS','8'))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0,len(paths),256):
            list(pool.map(check,paths[start:start+256]))
            if start%1024==0:print('HTTP_VERIFIED',min(start+256,len(paths)),'/',len(paths),flush=True)
    for path in ('/en/news/definitely-missing-check/','/images/definitely-missing-check.jpg'):
        if requests.get(origin.rstrip('/')+path,timeout=20).status_code!=404:raise ValueError('Unknown URL is not 404')
    if requests.post(origin.rstrip('/')+'/en/',timeout=20).status_code!=405:raise ValueError('POST must be 405')
    h=requests.head(origin.rstrip('/')+'/en/',timeout=20)
    if h.status_code!=200 or h.content:raise ValueError('HEAD behavior failed')
    r=requests.get(origin.rstrip('/')+'/en/',headers={'If-None-Match':h.headers.get('ETag','')},timeout=20)
    if r.status_code!=304:
        raise ValueError('Conditional GET failed: '+json.dumps({
            'status':r.status_code,
            'head_etag':h.headers.get('ETag',''),
            'get_etag':r.headers.get('ETag',''),
            'get_cache_status':r.headers.get('CF-Cache-Status',''),
            'head_cache_status':h.headers.get('CF-Cache-Status',''),
            'get_content_type':r.headers.get('Content-Type',''),
            'get_bytes':len(r.content),
            'expected_sha256':package['url_inventory']['/en/']['sha256'],
            'actual_sha256':digest(r.content),
            'vary':r.headers.get('Vary',''),
        },sort_keys=True))
    return {'http_urls_checked':len(paths),'all_urls':all_urls,'origin':origin}


def main():
    p=argparse.ArgumentParser();p.add_argument('--origin');p.add_argument('--all-urls',action='store_true');a=p.parse_args()
    package=json.loads((ROOT/'build/r2-package/package.json').read_text());baseline=json.loads((ROOT/'content/published-url-inventory.json').read_text())
    result=audit(package,baseline)
    if a.origin:result.update(smoke(a.origin,package,a.all_urls))
    (ROOT/'build/delivery-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
