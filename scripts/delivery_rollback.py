"""Snapshot only the routes this release owns; rollback never deletes content."""
import os
import re
import requests

PATTERNS={'globewiredaily.org'+p for p in ('/en/*','/hi/*','/images/*','/en','/hi')}
WORKER='globewire-delivery'


def api(method,path,body=None):
    response=requests.request(method,'https://api.cloudflare.com/client/v4/'+path,
        headers={'Authorization':'Bearer '+os.environ['CLOUDFLARE_API_TOKEN']},
        json=body,timeout=(5,30))
    if not response.ok:raise RuntimeError(f'Cloudflare {method} {path.split("/")[-1]} failed (HTTP {response.status_code})')
    data=response.json()
    if not data.get('success'):raise RuntimeError('Cloudflare API rejected '+method)
    return data.get('result')


def active_version(path):
    deployments=api('GET',path+'/deployments')['deployments']
    versions=deployments[0]['versions'] if deployments else []
    if len(versions)!=1 or versions[0]['percentage']!=100:
        raise ValueError('Expected one active Worker version at 100% traffic')
    return versions[0]['version_id']


def canonical_id(info):
    current=info.get('canonical_deployment') or {}
    if current.get('environment')!='production' or current.get('latest_stage',{}).get('status')!='success':
        raise ValueError('No successful Pages production rollback target exists')
    return current['id']


def scoped_routes(path):
    return {row['pattern']:row for row in api('GET',path) if row['pattern'] in PATTERNS}


def capture(project):
    account=os.environ['CF_ACCOUNT_ID'];zone=os.environ['CF_ZONE_ID']
    release=version=None
    info=api('GET',f'accounts/{account}/pages/projects/{project}')
    source=info.get('source') or {}
    if source and source.get('config',{}).get('production_deployments_enabled',True):
        raise ValueError('Disable automatic Git-triggered Pages production deployments before promoting the new delivery architecture')
    deployment=canonical_id(info)
    routes=scoped_routes(f'zones/{zone}/workers/routes')
    if routes:
        if set(routes)!=PATTERNS or any(row.get('script')!=WORKER for row in routes.values()):
            raise ValueError('Existing delivery routes do not match the complete owned route set')
        path=f'accounts/{account}/workers/scripts/{WORKER}'
        version=active_version(path)
        settings=api('GET',path+'/settings')
        release=next((row.get('text') for row in settings.get('bindings',[]) if row.get('name')=='RELEASE_ID'),None)
        if not re.fullmatch('[a-f0-9]{64}',release or ''):
            raise ValueError('Existing production Worker has no rollback release')
    return {'version':2,'project':project,'pages_deployment':deployment,'release_id':release,
            'worker_version':version,'routes':list(routes.values())}


def restore(snapshot):
    account=os.environ['CF_ACCOUNT_ID'];zone=os.environ['CF_ZONE_ID'];project=snapshot['project']
    if not re.fullmatch('[a-z0-9-]+',project):raise ValueError('Invalid rollback project')
    deployment=snapshot['pages_deployment']
    if not re.fullmatch('[a-f0-9-]+',deployment):raise ValueError('Invalid rollback deployment')
    pages=f'accounts/{account}/pages/projects/{project}'
    worker=f'accounts/{account}/workers/scripts/{WORKER}'
    route_path=f'zones/{zone}/workers/routes'
    errors=[]
    try:
        current=api('GET',pages)
        if (current.get('canonical_deployment') or {}).get('id')!=deployment:
            api('POST',f'{pages}/deployments/{deployment}/rollback')
        if canonical_id(api('GET',pages))!=deployment:
            raise RuntimeError('Previous Pages deployment is not active')
    except Exception as error:
        errors.append(f'Pages: {error}')
    try:
        version=snapshot['worker_version']
        if version:
            if active_version(worker)!=version:
                api('POST',worker+'/deployments',body={
                    'strategy':'percentage','versions':[{'version_id':version,'percentage':100}]})
            if active_version(worker)!=version:
                raise RuntimeError('Previous Worker version is not active')
        else:
            previous={row['id'] for row in snapshot['routes']}
            for row in scoped_routes(route_path).values():
                if row.get('script')==WORKER and row['id'] not in previous:
                    try:
                        api('DELETE',f'{route_path}/{row["id"]}')
                    except Exception as error:
                        errors.append(f'Route {row["pattern"]}: {error}')
        expected={row['pattern']:row.get('script') for row in snapshot['routes']}
        if {pattern:row.get('script') for pattern,row in scoped_routes(route_path).items()}!=expected:
            raise RuntimeError('Scoped routes differ from the rollback snapshot')
    except Exception as error:
        errors.append(f'Worker: {error}')
    return {'rollback':'failed' if errors else 'restored','pages_deployment':deployment,
            'release_id':snapshot.get('release_id'),'errors':errors}
