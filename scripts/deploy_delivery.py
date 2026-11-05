"""Explicit staging deployment or promotion of the exact verified release.

Invoked by an approval-protected GitHub environment. Never reads or prints secrets.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from delivery_package import ROOT, assemble_pages
from verify_delivery import smoke

WRANGLER=['npx','--yes','wrangler@4.45.0']

def command(args):
    result=subprocess.run(WRANGLER+args,cwd=ROOT,env={**os.environ,'CLOUDFLARE_ACCOUNT_ID':os.environ['CF_ACCOUNT_ID']},text=True,capture_output=True)
    if result.returncode:
        # Wrangler's diagnostics do not include the token; avoid echoing arbitrary env/config.
        print(result.stdout[-2000:]);print(result.stderr[-2000:]);raise RuntimeError('Cloudflare command failed')
    return result.stdout+'\n'+result.stderr


def config(release, production=False, asset_origin=None):
    value={'name':'globewire-delivery' if production else 'globewire-delivery-staging',
           'main':str(ROOT/'cloudflare/delivery/worker.mjs'),'compatibility_date':'2026-10-01',
           'workers_dev':not production,'r2_buckets':[{'binding':'MEDIA','bucket_name':'globewire-media'}],
           'vars':{'RELEASE_ID':release}}
    if asset_origin:value['vars']['ASSET_ORIGIN']=asset_origin
    if production:
        value['routes']=[{'pattern':'globewiredaily.org'+path,'zone_name':'globewiredaily.org'} for path in ('/en/*','/hi/*','/images/*','/en','/hi')]
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--production',action='store_true');p.add_argument('--all-urls',action='store_true');a=p.parse_args()
    package=json.loads((ROOT/'build/r2-package/package.json').read_text());receipt=json.loads((ROOT/'build/r2-receipt.json').read_text())
    project=os.environ['CLOUDFLARE_PAGES_PROJECT']
    if not re.fullmatch('[a-z0-9-]+',project):raise ValueError('Invalid Pages project')
    assemble_pages(ROOT/'build/rendered',package,receipt,ROOT/'build/pages')
    path=ROOT/'build/wrangler-delivery.json'
    if a.production:
        verified=json.loads((ROOT/'build/delivery-verification.json').read_text())
        if verified.get('release_id')!=package['release_id'] or not verified.get('origin','').endswith('.workers.dev'):
            raise ValueError('This exact release has not passed staging HTTP verification')
        # First production migration must exhaustively probe EVERY public route and image.
        if not verified.get('all_urls') and os.environ.get('DELIVERY_INITIAL_VERIFIED')!='true':
            raise ValueError('Initial production migration requires exhaustive staging HTTP verification')
        if os.environ.get('PRODUCTION_ROUTING_AUTHORIZED')!='true':
            raise ValueError('Production routing authorization missing')
        from delivery_rollback import capture, restore
        snapshot=capture(project)
        (ROOT/'build/rollback.json').write_text(json.dumps(snapshot,indent=2)+'\n')
        def deploy_worker(release):
            path.write_text(json.dumps(config(release,True)))
            command(['deploy','--config',str(path)])
        try:
            deploy_worker(package['release_id'])
            command(['pages','deploy','build/pages','--project-name',project,'--branch','main','--commit-dirty=true'])
            result=smoke('https://globewiredaily.org',package,all_urls=a.all_urls,changed_keys=receipt.get('changed_keys',[]))
        except Exception:
            # Keep the original failure visible, and preserve rollback diagnostics as an artifact.
            restored=restore(snapshot,deploy_worker)
            (ROOT/'build/rollback-result.json').write_text(json.dumps(restored,indent=2)+'\n')
            raise
    else:
        result=command(['pages','deploy','build/pages','--project-name',project,'--branch','r2-staging','--commit-dirty=true'])
        origins=re.findall(r'https://[a-z0-9.-]+\.pages\.dev',result)
        if not origins:raise RuntimeError('Pages preview URL missing')
        preview=origins[-1]
        path.write_text(json.dumps(config(package['release_id'],asset_origin=preview)))
        result=command(['deploy','--config',str(path)])
        origins=re.findall(r'https://[a-z0-9.-]+\.workers\.dev',result)
        if not origins:raise RuntimeError('Worker preview URL missing')
        result=smoke(origins[-1],package,all_urls=a.all_urls,changed_keys=receipt.get('changed_keys',[]))
        result['pages_preview']=preview
    result['release_id']=package['release_id']
    (ROOT/'build/delivery-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:f.write('## R2 delivery verification\n\n```json\n'+json.dumps(result,indent=2)+'\n```\n')

if __name__=='__main__':main()
