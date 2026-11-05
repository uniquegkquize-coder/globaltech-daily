"""Keep Pages redirect rules within its static limit, retaining every old URL."""
import html
import re
import json
from pathlib import PurePosixPath


def write_redirects(out,lines,write,site,limit=2000,external=False):
    rows={}
    for line in lines:
        source,target,code=line.split()
        if source==target:continue
        rows.setdefault(source,(target,code))
    # A migration render records ALL aliases; the scoped delivery Worker emits real 301s.
    # No stub is removed from a live deployment until the R2 package is verified.
    if external:
        (out.parent/'redirects.json').write_text(json.dumps(rows,sort_keys=True)+'\n')
        write(out/'_redirects','/ /en/ 301\n')
        return {'server_redirects':1,'html_redirects':0,'r2_redirects':len(rows)-1}
    # Canonical duplicate URLs and the homepage take priority over legacy ID URLs.
    order=sorted(rows,key=lambda p:bool(re.fullmatch(r'/(en|hi)/news/[a-f0-9]+/',p)))
    server=[];fallback=0
    for source in order:
        target,code=rows[source]
        if len(server)<limit:
            server.append(f'{source} {target} {code}')
            continue
        if not source.startswith('/') or not target.startswith('/') or source.startswith('//') or target.startswith('//') or '..' in PurePosixPath(source).parts:
            raise ValueError('Unsafe legacy redirect path')
        escaped=html.escape(target,quote=True);canonical=html.escape(site.rstrip('/')+target,quote=True)
        lang='hi' if source.startswith('/hi/') else 'en'
        body=f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={escaped}"><link rel="canonical" href="{canonical}"><title>Article moved</title></head><body><a href="{escaped}">Continue to article</a></body></html>'
        write(out/source.lstrip('/')/'index.html',body);fallback+=1
    write(out/'_redirects','\n'.join(server)+'\n')
    return {'server_redirects':len(server),'html_redirects':fallback}
