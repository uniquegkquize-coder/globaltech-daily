"""Snapshot only the routes this release owns; rollback never deletes content."""
import json
import os
from pathlib import Path
import re
import requests

PATTERNS={'globewiredaily.org'+p for p in ('/en/*','/hi/*','/images/*','/en','/hi')}


def api(method,path,allow_missing=False):
    response=requests.request(method,'https://api.cloudflare.com/client/v4/'+path,
        headers={'Authorization':'Bearer '+os.environ['CLOUDFLARE_API_TOKEN']},timeout=(5,30))
    if response.status_code==404 and allow_missing:return None
    if not response.ok:raise RuntimeError(f'Cloudflare {method} {path.split("/")[-1]} failed (HTTP {response.status_code})')
    data=response.json()
    if not data.get('success'):raise RuntimeError('Cloudflare API rejected '+method)
    return data.get('result')


def capture(project):
    account=os.environ['CF_ACCOUNT_ID'];zone=os.environ['CF_ZONE_ID']
    settings=api('GET',f'accounts/{account}/workers/scripts/globewire-delivery/settings',allow_missing=True)
    release=None
    if settings is not None:
        release=next((row.get('text') for row in settings.get('bindings',[]) if row.get('name')=='RELEASE_ID'),None)
        if not re.fullmatch('[a-f0-9]{64}',release or ''):raise ValueError('Existing production Worker has no rollback release; refusing to replace it')
    info=api('GET',f'accounts/{account}/pages/projects/{project}')
    source=info.get('source') or {}
    if source and source.get('config',{}).get('production_deployments_enabled',True):
        raise ValueError('Disable automatic Git-triggered Pages production deployments before promoting the new delivery architecture')
    deployment=(info.get('canonical_deployment') or {}).get('id')
    if not deployment:raise ValueError('No successful Pages production rollback target exists')
    routes=api('GET',f'zones/{zone}/workers/routes')
    owned=[r for r in routes if r['pattern'] in PATTERNS]
    if any(row.get('script') not in (None,'globewire-delivery') for row in owned):
        raise ValueError('A delivery route belongs to another Worker; refusing to take it over')
    return {'version':1,'project':project,'pages_deployment':deployment,'release_id':release,'routes':owned}


def restore(snapshot,deploy_worker):
    account=os.environ['CF_ACCOUNT_ID'];zone=os.environ['CF_ZONE_ID'];project=snapshot['project']
    if not re.fullmatch('[a-z0-9-]+',project):raise ValueError('Invalid rollback project')
    deployment=snapshot['pages_deployment']
    if not re.fullmatch('[a-f0-9-]+',deployment):raise ValueError('Invalid rollback deployment')
    api('POST',f'accounts/{account}/pages/projects/{project}/deployments/{deployment}/rollback')
    if snapshot.get('release_id'):
        if not re.fullmatch('[a-f0-9]{64}',snapshot['release_id']):raise ValueError('Invalid rollback release')
        deploy_worker(snapshot['release_id'])
    else:
        # Initial migration: remove ONLY newly added routes owned by this Worker.
        previous={r['id'] for r in snapshot['routes']}
        for row in api('GET',f'zones/{zone}/workers/routes'):
            if row['pattern'] in PATTERNS and row.get('script')=='globewire-delivery' and row['id'] not in previous:
                api('DELETE',f'zones/{zone}/workers/routes/{row["id"]}')
    return {'rollback':'restored','pages_deployment':deployment,'release_id':snapshot.get('release_id')}
