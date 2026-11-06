"""Export a verified, bounded staging handoff for Cloudflare's connected API.

No production pointer or route is changed. The immutable capsule contains only
public site assets, URL checksums, and a non-secret verification receipt.
"""
import base64
import gzip
import io
import json
import os
from pathlib import Path
import re
import subprocess
from delivery_package import ROOT, assemble_pages, assert_pages, digest, encoded
from r2_sync import sync

MAX_CAPSULE_BYTES=8_000_000
MAX_ROUTE_BYTES=32_000_000


def make_capsule(pages,package,receipt,source_commit,worker_sha256):
    if not receipt.get('verified') or receipt.get('release_id')!=package['release_id']:
        raise ValueError('A verified matching release is required')
    count=assert_pages(pages)
    files=[]
    from mimetypes import guess_type
    for path in sorted(Path(pages).rglob('*')):
        if not path.is_file():continue
        data=path.read_bytes()
        files.append({'path':path.relative_to(pages).as_posix(),'sha256':digest(data),'bytes':len(data),
                      'mime':guess_type(path.name)[0] or 'application/octet-stream','value':base64.b64encode(data).decode()})
    routes=encoded(package['url_inventory'])
    if len(routes)>MAX_ROUTE_BYTES:raise ValueError('Staging route handoff exceeds its bounded size')
    result={'version':1,'release_id':package['release_id'],'source_commit':source_commit,
        'worker_sha256':worker_sha256,'pages_files':count,'files':files,'routes_count':len(package['url_inventory']),
        'routes_gzip_b64':base64.b64encode(gzip.compress(routes,mtime=0)).decode(),
        'receipt':{k:v for k,v in receipt.items() if k!='changed_keys'}}
    data=encoded(result)
    if len(data)>MAX_CAPSULE_BYTES:raise ValueError('Staging capsule exceeds its bounded size')
    return result


def validate_capsule(value):
    if value.get('version')!=1 or not re.fullmatch('[a-f0-9]{64}',value.get('release_id','')):
        raise ValueError('Invalid staging capsule')
    if not value.get('receipt',{}).get('verified') or value['receipt'].get('release_id')!=value['release_id']:
        raise ValueError('Unverified staging capsule')
    with gzip.GzipFile(fileobj=io.BytesIO(base64.b64decode(value['routes_gzip_b64'],validate=True))) as compressed:
        routes=compressed.read(MAX_ROUTE_BYTES+1)
    if len(routes)>MAX_ROUTE_BYTES:raise ValueError('Route data too large')
    routes=json.loads(routes)
    if len(routes)!=value['routes_count']:raise ValueError('Route count mismatch')
    seen=set()
    for row in value['files']:
        path=Path(row['path'])
        if path.is_absolute() or '..' in path.parts or row['path'] in seen:raise ValueError('Unsafe/duplicate asset path')
        seen.add(row['path']);data=base64.b64decode(row['value'],validate=True)
        if len(data)!=row['bytes'] or digest(data)!=row['sha256']:raise ValueError('Asset checksum mismatch')
    if len(seen)!=value['pages_files']:raise ValueError('Pages asset count mismatch')
    return routes


def main():
    package=json.loads((ROOT/'build/r2-package/package.json').read_text())
    receipt=json.loads((ROOT/'build/r2-receipt.json').read_text())
    assemble_pages(ROOT/'build/rendered',package,receipt,ROOT/'build/pages')
    value=make_capsule(ROOT/'build/pages',package,receipt,
        subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        digest((ROOT/'cloudflare/delivery/worker.mjs').read_bytes()))
    validate_capsule(value);data=encoded(value)
    key='delivery/staging/'+package['release_id']+'/pages.json'
    path=ROOT/'build/r2-package'/key;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    capsule_package={'release_id':package['release_id'],'bytes':len(data),'files':[{'key':key,'sha256':digest(data),'bytes':len(data),'type':'application/json'}]}
    import boto3
    from botocore.config import Config
    client=boto3.client('s3',endpoint_url=f"https://{os.environ['CF_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],region_name='auto',
        config=Config(connect_timeout=5,read_timeout=20,max_pool_connections=8,retries={'total_max_attempts':1}))
    sync(client,'globewire-media',ROOT/'build/r2-package',capsule_package,ROOT/'build/capsule-receipt.json',workers=1,deep=True)
    print('STAGING_CAPSULE',json.dumps({'key':key,'release_id':package['release_id'],'bytes':len(data),'pages_files':len(value['files']),'routes':value['routes_count']}))

if __name__=='__main__':main()
