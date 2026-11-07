import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect

class BatchRuntimeTests(unittest.TestCase):
 def setUp(self):
  for name in ('MODEL_RETRY_AT','PROVIDER_RETRY_AT','MODEL_FAILURES'):
   scope=patch.object(collect,name,{})
   scope.start();self.addCleanup(scope.stop)
 def test_expired_batch_never_calls_provider(self):
  with patch.object(collect,'RUN_DEADLINE',1),patch.object(collect.time,'monotonic',return_value=2),patch.object(collect.requests,'post') as request:
   self.assertEqual(collect.call_provider('test'),(None,None))
   request.assert_not_called()
 def test_configured_model_limit_prevents_unbounded_probing(self):
  class Response:
   ok=False;status_code=500
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder'}),patch.object(collect,'RUN_DEADLINE',0),patch.object(collect,'CALLS',0),patch.object(collect,'MODELS_PER_PROVIDER',1),patch.object(collect,'PROVIDER_COOLDOWNS',set()),patch.object(collect,'UNAVAILABLE_MODELS',set()),patch.object(collect,'provider_order',return_value=['gemini']),patch.object(collect,'gemini_models',return_value=['one','two','three']),patch.object(collect.requests,'post',return_value=Response()) as request:
   collect.call_provider('test')
   self.assertEqual(request.call_count,1)
   self.assertEqual(collect.CALLS,1)
 def test_gemini_404_falls_back_to_second_discovered_model(self):
  class Response:
   def __init__(self,status):
    self.status_code=status
    self.ok=status==200
   def json(self):
    return {'candidates':[{'content':{'parts':[{'text':'{"title":"Verified title","body":"Verified content."}' }]}}]}
  def respond(url,**kwargs):
   return Response(404 if '/missing-model:' in url else 200)
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder','GEMINI_MODEL':'missing-model'},clear=True),patch.object(collect,'RUN_DEADLINE',0),patch.object(collect,'CALLS',0),patch.object(collect,'MAX_CALLS',18),patch.object(collect,'MODELS_PER_PROVIDER',2),patch.object(collect,'PROVIDER_COOLDOWNS',set()),patch.object(collect,'UNAVAILABLE_MODELS',set()),patch.object(collect,'provider_order',return_value=['gemini']),patch.object(collect,'gemini_models',return_value=['missing-model','other-model']),patch.object(collect.requests,'post',side_effect=respond) as request:
   data,provider=collect.call_provider('test')
   self.assertEqual(provider,'gemini')
   self.assertEqual(data['title'],'Verified title')
   self.assertEqual(request.call_count,2)
   self.assertEqual(collect.CALLS,2)
 def test_expired_discovery_preserves_item_order_without_requests(self):
  with patch.object(collect,'DISCOVERY_DEADLINE',1),patch.object(collect.time,'monotonic',return_value=2):
   with patch.object(collect.requests,'get') as request:
    rows=collect.discovery_map(collect.website_stories,[('a','b','c'),('d','e','f')],2,lambda item:(item,[]))
    self.assertEqual(rows,[(('a','b','c'),[]),(('d','e','f'),[])])
    request.assert_not_called()
 def test_run_report_distinguishes_partial_progress(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'content').mkdir()
   with patch.object(collect,'ROOT',root),patch.object(collect.time,'monotonic',return_value=20):
    collect.write_run_status('time_limit_reached',10,{'cricket':2,'car-launches':1},target=60)
   report=json.loads((root/'content/news-run-status.json').read_text())
   self.assertEqual(report['published'],3)
   self.assertEqual(report['outcome'],'time_limit_reached')
   self.assertEqual(report['target'],60)
 def test_queues_deduplicate_tracking_but_preserve_document_ids(self):
  rows=[('https://site.example/notice?id=1&utm_source=feed','one','results','site.example'),('https://site.example/notice?id=1','one','results','site.example'),('https://site.example/notice?id=2','two','results','site.example')]
  self.assertEqual(len(collect.unique_leads(rows)),2)
  self.assertTrue(collect.duplicate_story(rows[0][0],'one','results',[(rows[1][0],'one','results')]))
  self.assertFalse(collect.duplicate_story(rows[2][0],'two','results',[(rows[1][0],'one','results')]))
 def test_rate_limited_providers_are_not_treated_as_ready(self):
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder'},clear=True),patch.object(collect,'provider_order',return_value=['gemini']):
   with patch.object(collect,'PROVIDER_COOLDOWNS',{'gemini'}):self.assertFalse(collect.providers_ready())
   with patch.object(collect,'PROVIDER_COOLDOWNS',set()):self.assertTrue(collect.providers_ready())
 def test_global_native_sources_are_not_delayed_behind_search(self):
  rows=collect.native_feed_registry()
  categories={row[1] for row in rows}
  self.assertTrue({'world-news','business','sports','technology','health-science'}.issubset(categories))
  self.assertFalse(any('news.google.com' in row[0] for row in rows))
  self.assertEqual(len(rows),len(set(rows)))
 def test_configured_model_is_preferred_when_available(self):
  class Response:
   ok=False;status_code=500
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder','GEMINI_MODEL':'two'}),patch.object(collect,'RUN_DEADLINE',0),patch.object(collect,'CALLS',0),patch.object(collect,'MODELS_PER_PROVIDER',1),patch.object(collect,'PROVIDER_COOLDOWNS',set()),patch.object(collect,'UNAVAILABLE_MODELS',set()),patch.object(collect,'provider_order',return_value=['gemini']),patch.object(collect,'gemini_models',return_value=['one','two']),patch.object(collect.requests,'post',return_value=Response()) as request:
   collect.call_provider('test')
   self.assertIn('/two:generateContent',request.call_args.args[0])
   self.assertEqual(request.call_count,1)

 def test_temporary_503_model_is_retried_after_cooldown(self):
  class Response:
   status_code=503;ok=False;headers={'Retry-After':'2'}
   def json(self):return {'error':{'message':'Temporarily overloaded'}}
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder'},clear=True),patch.object(collect,'RUN_DEADLINE',0),patch.object(collect,'CALLS',0),patch.object(collect,'MAX_CALLS',100),patch.object(collect,'MODELS_PER_PROVIDER',1),patch.object(collect,'PROVIDER_COOLDOWNS',set()),patch.object(collect,'UNAVAILABLE_MODELS',set()),patch.object(collect,'provider_order',return_value=['gemini']),patch.object(collect,'gemini_models',return_value=['temporary-model']),patch.object(collect.time,'monotonic',return_value=100),patch.object(collect.requests,'post',return_value=Response()) as request:
   collect.call_provider('test')
   self.assertNotIn(('gemini','temporary-model'),collect.UNAVAILABLE_MODELS)
   self.assertFalse(collect.providers_ready())
   self.assertEqual(request.call_count,1)
   collect.call_provider('test')
   self.assertEqual(request.call_count,1)
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder'},clear=True),patch.object(collect,'PROVIDER_COOLDOWNS',set()),patch.object(collect,'provider_order',return_value=['gemini']),patch.object(collect.time,'monotonic',return_value=200):
   self.assertTrue(collect.providers_ready())
 def test_retry_after_and_daily_quota_are_distinguished(self):
  class Response:
   headers={'retry-after':'90'}
   def json(self):return {'error':{'message':'Too many requests per minute','details':[{'retryDelay':'120s'}]}}
  self.assertEqual(collect.retry_seconds(Response()),120)
  self.assertFalse(collect.daily_quota_exhausted(Response()))
  class Daily(Response):
   def json(self):return {'error':{'message':'Requests per day quota exhausted'}}
  self.assertTrue(collect.daily_quota_exhausted(Daily()))

if __name__=='__main__':unittest.main()
