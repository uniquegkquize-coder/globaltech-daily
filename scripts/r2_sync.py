"""Bounded, resumable immutable R2 uploads. No delete API exists in this module."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import json
import os
from pathlib import Path
import time
from delivery_package import digest, encoded


def retry(operation, attempts=3, pause=time.sleep):
    for attempt in range(attempts):
        try:return operation()
        except Exception as exc:
            response=getattr(exc,'response',{})
            code=response.get('ResponseMetadata',{}).get('HTTPStatusCode')
            if code and code not in (408,429) and code < 500:raise
            if attempt == attempts-1:raise
            pause(min(4,2**attempt))


def sync(client, bucket, root, package, receipt_path, workers=4, deep=False):
    root=Path(root);receipt_path=Path(receipt_path)
    receipt_path.unlink(missing_ok=True) # stale successful receipts must never survive a failed upload
    index_key='delivery/verified-index.json'
    try:
        verified_index=json.loads(retry(lambda:client.get_object(Bucket=bucket,Key=index_key)['Body'].read()))
    except Exception as exc:
        if getattr(exc,'response',{}).get('ResponseMetadata',{}).get('HTTPStatusCode')!=404:raise
        verified_index={}
    if not isinstance(verified_index,dict):raise ValueError('Invalid remote verification index')
    objects={}
    for page in client.get_paginator('list_objects_v2').paginate(Bucket=bucket):
        for item in page.get('Contents',[]):objects[item['Key']]=item['Size']
    new_bytes=sum(row['bytes'] for row in package['files'] if row['key'] not in objects)
    next_index={**verified_index,**{row['key']:{'sha256':row['sha256'],'bytes':row['bytes']} for row in package['files']}}
    index_data=encoded(next_index)
    storage_after=sum(objects.values())+new_bytes+len(index_data)-objects.get(index_key,0)
    if storage_after > 8_000_000_000:
        raise ValueError('R2 safety budget exceeded: retained objects plus new upload exceed 8 GB; no writes performed')
    changed_keys=[]
    def one(row):
        key=row['key'];data=(root/key).read_bytes()
        if digest(data)!=row['sha256'] or len(data)!=row['bytes']:
            raise ValueError('Package changed after inventory: '+key)
        # A prior successful byte verification + current full bucket listing establishes
        # unchanged immutable object existence without millions of redundant HEAD calls.
        prior=verified_index.get(key,{})
        if not deep and prior.get('sha256')==row['sha256'] and prior.get('bytes')==len(data) and objects.get(key)==len(data):
            return True
        absent=key not in objects
        if absent:
            # Atomic create-once protects an object created after our bucket listing.
            # A timeout followed by 412 can mean our first write committed; verify it.
            try:
                retry(lambda:client.put_object(Bucket=bucket,Key=key,Body=data,
                    ContentType=row.get('type','application/octet-stream'),
                    CacheControl='public, max-age=31536000, immutable',
                    Metadata={'sha256':row['sha256']},IfNoneMatch='*'))
            except Exception as exc:
                if getattr(exc,'response',{}).get('ResponseMetadata',{}).get('HTTPStatusCode')!=412:raise
        # GET provides metadata, length and bytes together. Never add redundant HEADs
        # to the initial audit, and never trust an unindexed object's claimed hash.
        remote=retry(lambda:client.get_object(Bucket=bucket,Key=key))
        stream=remote['Body']
        try:
            if remote.get('Metadata',{}).get('sha256')!=row['sha256'] or remote.get('ContentLength')!=len(data):
                raise ValueError('Existing immutable object mismatch: '+key)
            if digest(stream.read())!=row['sha256']:raise ValueError('Remote bytes differ: '+key)
        finally:stream.close()
        if absent:changed_keys.append(key)
        return not absent
    if not 1<=workers<=8:raise ValueError('workers must be 1..8')
    statuses=[]
    reported=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending=set();entries=iter(package['files'])
        try:
            while True:
                while len(pending)<workers:
                    row=next(entries,None)
                    if row is None:break
                    pending.add(pool.submit(one,row))
                if not pending:break
                done,pending=wait(pending,return_when=FIRST_COMPLETED)
                statuses.extend(future.result() for future in done)
                if len(statuses)-reported>=256 or len(statuses)==len(package['files']):
                    reported=len(statuses)
                    print(json.dumps({'verified_objects':reported,'total_objects':len(package['files']),'uploaded':statuses.count(False),'skipped':statuses.count(True)}),flush=True)
        except Exception:
            for future in pending:future.cancel()
            raise
    if index_data!=encoded(verified_index):
        retry(lambda:client.put_object(Bucket=bucket,Key=index_key,Body=index_data,
              ContentType='application/json',CacheControl='no-store',Metadata={'sha256':digest(index_data)}))
    receipt={'release_id':package['release_id'],'verified':True,'count':len(statuses),
             'inventory_sha256':digest(encoded(package['files'])),
             'changed_keys':sorted(changed_keys),'uploaded':statuses.count(False),'skipped':statuses.count(True),'deep':deep,
             'bucket_bytes_after':storage_after,'bucket_byte_limit':8_000_000_000,
             'estimated_class_b_ops_upper_bound':1+len(statuses)*3}
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    temporary=receipt_path.with_suffix('.tmp');temporary.write_bytes(encoded(receipt));temporary.replace(receipt_path)
    return receipt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--package',default='build/r2-package');ap.add_argument('--upload',action='store_true');ap.add_argument('--deep-verify',action='store_true');ap.add_argument('--workers',type=int,choices=range(1,9),default=4);a=ap.parse_args()
    root=Path(a.package);package=json.loads((root/'package.json').read_text())
    print(json.dumps({'release_id':package['release_id'],'objects':len(package['files']),'bytes':package['bytes']}))
    if not a.upload:
        print('Dry run; no remote writes and no verification receipt');return
    import boto3
    from botocore.config import Config
    client=boto3.client('s3',endpoint_url=f"https://{os.environ['CF_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],region_name='auto',
        config=Config(connect_timeout=5,read_timeout=20,max_pool_connections=8,retries={'total_max_attempts':1}))
    print(json.dumps(sync(client,os.environ.get('R2_BUCKET','globewire-media'),root,package,Path('build/r2-receipt.json'),workers=a.workers,deep=a.deep_verify)))

if __name__=='__main__':main()
