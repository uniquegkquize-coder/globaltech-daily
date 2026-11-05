"""Keep Pages redirect rules within its static limit, retaining every old URL."""
import html
import re
from pathlib import PurePosixPath


def write_redirects(out,lines,write,site,limit=2000):
    rows={}
    for line in lines:
        source,target,code=line.split()
        if source==target:continue
        rows.setdefault(source,(target,code))
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


def export_bulk_redirects(out, lines, site):
    """Export legacy mappings for Cloudflare Bulk Redirects without removing fallbacks.

    Import/activate the list at Cloudflare before disabling any legacy HTML stubs.
    The export is a deployment artifact, not an assertion that Cloudflare rules exist.
    """
    import csv
    import io
    import json
    rows = {}
    for line in lines:
        source, target, code = line.split()
        if source == target:
            continue
        if not (source.startswith('/') and target.startswith('/') and not source.startswith('//') and not target.startswith('//')):
            raise ValueError('Unsafe bulk redirect mapping')
        rows.setdefault(source, (target, int(code)))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['source_url', 'target_url', 'status_code'])
    for source, (target, code) in sorted(rows.items()):
        writer.writerow([site.rstrip('/') + source, site.rstrip('/') + target, code])
    (out / 'bulk-redirects.csv').write_text(output.getvalue(), encoding='utf-8')
    (out / 'bulk-redirects-manifest.json').write_text(json.dumps({'count':len(rows),'requires_cloudflare_activation':True},sort_keys=True)+'\\n',encoding='utf-8')
    return len(rows)
