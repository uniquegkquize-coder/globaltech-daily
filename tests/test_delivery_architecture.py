import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import delivery_package as dp
from build_output import OutputWriter
from r2_sync import sync, retry
from check_output_policy import check
from deploy_delivery import config

class Missing(Exception):
    response={'ResponseMetadata':{'HTTPStatusCode':404}}

class PreconditionFailed(Exception):
    response={'ResponseMetadata':{'HTTPStatusCode':412}}

class FakeR2:
    def __init__(self):self.objects={};self.writes=0;self.fail=0;self.corrupt=False
    def get_paginator(self,name):
        bucket=self
        class Paginator:
            def paginate(self,**kw):yield {'Contents':[{'Key':key,'Size':len(data[0])} for key,data in bucket.objects.items()]}
        return Paginator()
    def head_object(self,Bucket,Key):
        if Key not in self.objects:raise Missing()
        data,meta=self.objects[Key]
        return {'ContentLength':len(data),'Metadata':meta}
    def put_object(self,Bucket,Key,Body,Metadata,**kw):
        if kw.get('IfNoneMatch')=='*' and Key in self.objects:raise PreconditionFailed()
        self.writes+=1
        if self.fail:
            self.fail-=1;raise TimeoutError('transient')
        self.objects[Key]=(Body,Metadata)
    def get_object(self,Bucket,Key):
        if Key not in self.objects:raise Missing()
        return {'Body':io.BytesIO(b'corrupt' if self.corrupt else self.objects[Key][0]),
                'Metadata':self.objects[Key][1],'ContentLength':len(self.objects[Key][0])}

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patch=patch.object(dp,'ROOT',self.root);self.patch.start()
        self.render=self.root/'rendered';self.render.mkdir();self.output=self.root/'build/r2-package'
        for rel,body in {'en/news/science/test/index.html':'<html><head><link rel="canonical" href="https://globewiredaily.org/en/news/science/test/"></head><body>English</body></html>',
                         'hi/news/science/test/index.html':'<html lang="hi"><body>हिंदी</body></html>',
                         'images/test.jpg':'image bytes',
                         'en/index.html':'<html>home</html>',
                         'en/cars/a/index.html':'<html>directory</html>'}.items():
            p=self.render/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
        for name in ('404.html','_redirects','_headers','robots.txt','sitemap.xml','news-sitemap.xml'):(self.render/name).write_text('root asset')
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def package(self):
        return dp.build_package(self.render,{'/en/news/old/':['/en/news/science/test/','301']},self.output)
    def test_redirects_are_real_map_entries_without_html_stubs(self):
        p=self.package();self.assertEqual(p['url_inventory']['/en/news/old/'],{'redirect':'/en/news/science/test/','status':301})
        self.assertFalse((self.render/'en/news/old/index.html').exists())
        self.assertIn('/hi/news/science/test/',p['url_inventory'])
    def test_content_dedup_and_build_reproducibility(self):
        f=self.render/'en/cars/b/index.html';f.parent.mkdir();f.write_bytes((self.render/'en/cars/a/index.html').read_bytes())
        a=self.package();b=self.package();self.assertEqual(a,b);self.assertEqual(a['deduplicated_bodies'],1)
    def test_missing_alias_destination_and_loops_fail_closed(self):
        with self.assertRaises(ValueError):dp.build_package(self.render,{'/en/old/':['/en/nope/','301']},self.output)
        with self.assertRaises(ValueError):dp.build_package(self.render,{'/en/a/':['/en/b/','301'],'/en/b/':['/en/a/','301']},self.output)
    def test_pages_exclusion_requires_exact_remote_receipt(self):
        p=self.package()
        with self.assertRaises(ValueError):dp.assemble_pages(self.render,p,{},self.root/'build/pages')
        client=FakeR2();receipt=sync(client,'b',self.output,p,self.root/'receipt.json',deep=True)
        result=dp.assemble_pages(self.render,p,receipt,self.root/'build/pages')
        self.assertEqual(result['files'],6);self.assertFalse((self.root/'build/pages/images').exists())
        receipt['inventory_sha256']='wrong'
        with self.assertRaises(ValueError):dp.assemble_pages(self.render,p,receipt,self.root/'build/pages')
    def test_upload_is_idempotent_and_remote_objects_survive_rollback(self):
        p=self.package();client=FakeR2();receipt=self.root/'receipt.json'
        first=sync(client,'b',self.output,p,receipt,deep=True);self.assertGreater(first['uploaded'],0)
        writes=client.writes
        second=sync(client,'b',self.output,p,receipt);self.assertEqual(client.writes,writes);self.assertEqual(second['skipped'],len(p['files']))
        oldkeys=set(client.objects);oldrelease=p['release_id']
        (self.render/'en/index.html').write_text('<html>new home</html>');new=self.package();sync(client,'b',self.output,new,receipt)
        self.assertTrue(oldkeys<=set(client.objects));self.assertIn('releases/'+oldrelease+'.json',client.objects)
    def test_failed_verification_cannot_leave_successful_receipt(self):
        p=self.package();client=FakeR2();client.corrupt=True;receipt=self.root/'receipt.json';receipt.write_text('stale')
        with self.assertRaises(ValueError):sync(client,'b',self.output,p,receipt)
        self.assertFalse(receipt.exists())
    def test_immutable_remote_mismatch_is_never_overwritten(self):
        p=self.package();client=FakeR2();row=p['files'][0];client.objects[row['key']]=(b'wrong',{})
        with self.assertRaises(ValueError):sync(client,'b',self.output,p,self.root/'r.json')
    def test_racing_object_cannot_be_overwritten_after_a_negative_listing(self):
        p=self.package();client=FakeR2();put=client.put_object;first=p['files'][0]
        def race(**kw):
            if kw['Key']==first['key']:client.objects[kw['Key']]=(b'concurrent original',{})
            return put(**kw)
        with patch.object(client,'put_object',side_effect=race):
            with self.assertRaisesRegex(ValueError,'immutable object mismatch'):
                sync(client,'b',self.output,p,self.root/'r.json',workers=1)
        self.assertEqual(client.objects[first['key']][0],b'concurrent original')
        self.assertFalse((self.root/'r.json').exists())
    def test_timeout_after_commit_verifies_existing_bytes_without_overwriting(self):
        p=self.package();client=FakeR2();put=client.put_object;timed_out=[]
        def uncertain(**kw):
            result=put(**kw)
            if not timed_out and kw['Key']!='delivery/verified-index.json':
                timed_out.append(kw['Key']);raise TimeoutError('response lost after commit')
            return result
        with patch.object(client,'put_object',side_effect=uncertain),patch('r2_sync.retry',side_effect=lambda op:retry(op,pause=lambda _:None)):
            receipt=sync(client,'b',self.output,p,self.root/'r.json')
        self.assertTrue(receipt['verified']);self.assertEqual(len(timed_out),1)
        self.assertEqual(client.writes,len(p['files'])+1)
    def test_deep_audit_reuses_get_metadata_without_redundant_head_requests(self):
        p=self.package();client=FakeR2()
        with patch.object(client,'head_object',side_effect=AssertionError('Redundant HEAD')):
            first=sync(client,'b',self.output,p,self.root/'r.json',deep=True)
            second=sync(client,'b',self.output,p,self.root/'r.json',deep=True)
        self.assertEqual(first['uploaded'],len(p['files']));self.assertEqual(second['uploaded'],0)
    def test_retry_is_bounded_and_succeeds_after_transient_error(self):
        calls=[]
        def op():
            calls.append(1)
            if len(calls)<3:raise TimeoutError()
            return 'ok'
        self.assertEqual(retry(op,pause=lambda _:None),'ok');self.assertEqual(len(calls),3)
        with self.assertRaises(TimeoutError):retry(lambda:(_ for _ in ()).throw(TimeoutError()),pause=lambda _:None)
    def test_writer_rejects_conflicting_owners_and_skips_identical_write(self):
        writer=OutputWriter(self.render);p=self.render/'new.html';writer(p,'a');writer(p,'a');self.assertEqual(writer.identical_writes,1)
        writer.owner='other'
        with self.assertRaises(ValueError):writer(p,'b')
    def test_asset_guard_cannot_be_bypassed_by_upload_receipt(self):
        p=self.package();receipt=sync(FakeR2(),'b',self.output,p,self.root/'r.json')
        with patch.object(dp,'MAX_PAGES_FILES',1):
            with self.assertRaises(ValueError):dp.assemble_pages(self.render,p,receipt,self.root/'build/pages')
    def test_cleaner_cannot_target_source_directories(self):
        for target in (self.root/'content',self.root):
            with self.assertRaises(ValueError):dp.managed_reset(target)
    def test_scoped_routes_are_exact_and_preview_has_no_production_routes(self):
        self.assertNotIn('routes',config('a'*64))
        routes={r['pattern'] for r in config('a'*64,True)['routes']}
        self.assertEqual(routes,{'globewiredaily.org/en/*','globewiredaily.org/hi/*','globewiredaily.org/images/*','globewiredaily.org/en','globewiredaily.org/hi'})
    def test_policy_rejects_generated_tracking_and_duplicate_workflows(self):
        d=self.root/'.github/workflows';d.mkdir(parents=True)
        (d/'one.yml').write_text('name: test\non: push\n');(d/'two.yml').write_text((d/'one.yml').read_text())
        with self.assertRaises(ValueError):check(self.root,['dist/en/index.html','scripts/__pycache__/x.pyc'])
    def test_future_route_growth_does_not_increase_pages_files(self):
        for i in range(1000):
            p=self.render/f'en/news/future/article-{i}/index.html';p.parent.mkdir(parents=True);p.write_text('<html>unique '+str(i)+'</html>')
        p=self.package();receipt=sync(FakeR2(),'b',self.output,p,self.root/'r.json')
        self.assertEqual(dp.assemble_pages(self.render,p,receipt,self.root/'build/pages')['files'],6)


class UploadFailureTests(unittest.TestCase):
    setUp=DeliveryTests.setUp
    tearDown=DeliveryTests.tearDown
    package=DeliveryTests.package
    def test_upload_retry_recovers_without_duplicate_object_or_receipt(self):
        package=self.package();client=FakeR2();client.fail=1
        with patch('r2_sync.retry',side_effect=lambda operation:retry(operation,pause=lambda _:None)):
            result=sync(client,'bucket',self.output,package,self.root/'r.json')
        self.assertTrue(result['verified']);self.assertEqual(result['count'],len(package['files']))
    def test_bucket_budget_rejects_upload_before_any_remote_write(self):
        package=self.package();client=FakeR2()
        class Paginator:
            def paginate(self,**kwargs):yield {'Contents':[{'Key':'existing-data','Size':8_000_000_000}]}
        with patch.object(client,'get_paginator',return_value=Paginator()):
            with self.assertRaisesRegex(ValueError,'budget'):sync(client,'bucket',self.output,package,self.root/'r.json')
        self.assertEqual(client.writes,0)

class RollbackTests(unittest.TestCase):
    def test_first_cutover_removes_owned_routes_even_if_pages_rollback_fails(self):
        import delivery_rollback as rollback
        rows=[{'id':'new','pattern':'globewiredaily.org/en/*','script':'globewire-delivery'},
              {'id':'other','pattern':'globewiredaily.org/api/*','script':'other'}]
        calls=[]
        def api(method,path,**kwargs):
            calls.append((method,path))
            if method=='POST':
                raise RuntimeError('Pages API unavailable')
            if method=='DELETE':
                rows.pop(0)
            if path.endswith('/routes'):
                return rows
            return {'canonical_deployment':{'id':'new-pages'}}
        snapshot={'project':'globaltech-daily','pages_deployment':'abcd-1234','routes':[],
                  'release_id':None,'worker_version':None}
        with patch.object(rollback,'api',side_effect=api),patch.dict('os.environ',{'CF_ACCOUNT_ID':'account','CF_ZONE_ID':'zone'}):
            result=rollback.restore(snapshot)
        self.assertEqual([path for method,path in calls if method=='DELETE'],['zones/zone/workers/routes/new'])
        self.assertEqual(rows[0]['script'],'other')
        self.assertEqual(result['rollback'],'failed')
        self.assertIn('Pages API unavailable',result['errors'][0])

    def test_existing_release_rollback_restores_exact_worker_version(self):
        import delivery_rollback as rollback
        active={'pages':'new-pages','worker':'new-worker'}
        routes=[{'id':'existing','pattern':'globewiredaily.org/en/*','script':'globewire-delivery'}]
        def api(method,path,body=None):
            if path.endswith('/rollback'):
                active['pages']='abcd-1234'
            elif path.endswith('/routes'):
                return routes
            elif path.endswith('/deployments'):
                if method=='POST':
                    active['worker']=body['versions'][0]['version_id']
                return {'deployments':[{'versions':[{'version_id':active['worker'],'percentage':100}]}]}
            return {'canonical_deployment':{'id':active['pages'],'environment':'production','latest_stage':{'status':'success'}}}
        snapshot={'project':'globaltech-daily','pages_deployment':'abcd-1234','routes':routes,
                  'release_id':'a'*64,'worker_version':'old-worker'}
        with patch.object(rollback,'api',side_effect=api),patch.dict('os.environ',{'CF_ACCOUNT_ID':'account','CF_ZONE_ID':'zone'}):
            result=rollback.restore(snapshot)
        self.assertEqual(active,{'pages':'abcd-1234','worker':'old-worker'})
        self.assertEqual(result['rollback'],'restored')

if __name__=='__main__':unittest.main()
