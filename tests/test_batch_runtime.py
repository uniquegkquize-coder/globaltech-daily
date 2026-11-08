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

 def test_temporary_cooldown_resumes_without_restarting_collector(self):
  clock=[100.0]
  def advance(seconds):clock[0]+=seconds
  with patch.object(collect,'providers_ready',side_effect=lambda:clock[0]>=190),patch.object(collect,'provider_retry_delay',side_effect=lambda:max(0,190-clock[0])),patch.object(collect.time,'monotonic',side_effect=lambda:clock[0]),patch.object(collect.time,'sleep',side_effect=advance) as sleep:
   self.assertTrue(collect.wait_for_provider(300))
   self.assertEqual([c.args[0] for c in sleep.call_args_list],[60,30])

 def test_hard_block_or_insufficient_time_never_waits(self):
  for delay in (None,120):
   with self.subTest(delay=delay),patch.object(collect,'providers_ready',return_value=False),patch.object(collect,'provider_retry_delay',return_value=delay),patch.object(collect.time,'monotonic',return_value=100),patch.object(collect.time,'sleep') as sleep:
    self.assertFalse(collect.wait_for_provider(200))
    sleep.assert_not_called()

 def test_malformed_output_retried_and_charged_to_call_budget(self):
  class Response:
   ok=True
   def __init__(self,raw):self.raw=raw
   def json(self):return {'choices':[{'message':{'content':self.raw}}]}
  responses=[Response('{"body": "truncated'),Response('{"body":"Complete source-backed article."}')]
  with patch.dict(os.environ,{'GROQ_API_KEY':'placeholder'},clear=True),patch.object(collect,'provider_order',return_value=['groq']),patch.object(collect,'PROVIDER_COOLDOWNS',set()),patch.object(collect,'UNAVAILABLE_MODELS',set()),patch.object(collect,'CALLS',0),patch.object(collect,'MAX_CALLS',2),patch.object(collect,'RUN_DEADLINE',0),patch.object(collect.requests,'post',side_effect=responses) as request:
   data,provider=collect.call_provider('Source evidence')
   self.assertEqual(provider,'groq')
   self.assertEqual(data['body'],'Complete source-backed article.')
   self.assertEqual(collect.CALLS,2)
   self.assertIn('OUTPUT RETRY',request.call_args.kwargs['json']['messages'][0]['content'])

 def test_malformed_output_cannot_exceed_call_budget(self):
  class Response:
   ok=True
   def json(self):return {'choices':[{'message':{'content':'invalid'}}]}
  with patch.dict(os.environ,{'GROQ_API_KEY':'placeholder'},clear=True),patch.object(collect,'provider_order',return_value=['groq']),patch.object(collect,'PROVIDER_COOLDOWNS',set()),patch.object(collect,'UNAVAILABLE_MODELS',set()),patch.object(collect,'CALLS',0),patch.object(collect,'MAX_CALLS',1),patch.object(collect,'RUN_DEADLINE',0),patch.object(collect.requests,'post',return_value=Response()) as request:
   self.assertEqual(collect.call_provider('Source evidence'),(None,'groq'))
   self.assertEqual(request.call_count,1)

if __name__=='__main__':unittest.main()

class ProviderPacingTests(unittest.TestCase):
 def setUp(self):
  for name,value in [('PROVIDER_NEXT_REQUEST',{}),('MODEL_RETRY_AT',{}),('PROVIDER_RETRY_AT',{}),('MODEL_FAILURES',{}),('PROVIDER_COOLDOWNS',set()),('UNAVAILABLE_MODELS',set()),('CALLS',0),('MAX_CALLS',100),('RUN_DEADLINE',0)]:
   scope=patch.object(collect,name,value);scope.start();self.addCleanup(scope.stop)

 def test_pacing_reserves_slots_and_obeys_deadline(self):
  clock=[100.0]
  with patch.dict(os.environ,{'AI_REQUEST_INTERVAL_SECONDS':'8'},clear=True),patch.object(collect.time,'monotonic',side_effect=lambda:clock[0]),patch.object(collect.time,'sleep',side_effect=lambda delay:clock.__setitem__(0,clock[0]+delay)) as sleep:
   self.assertTrue(collect.reserve_provider_request('groq','test'))
   self.assertTrue(collect.reserve_provider_request('groq','test'))
   sleep.assert_called_once_with(8)
   self.assertEqual(collect.CALLS,2)
   with patch.object(collect,'RUN_DEADLINE',110):
    self.assertFalse(collect.reserve_provider_request('groq','test'))
   self.assertEqual(collect.CALLS,2)

 def test_daily_groq_model_limit_preserves_other_model_and_enforces_json(self):
  class Response:
   def __init__(self,status):self.status_code=status;self.ok=status==200
   def json(self):
    if not self.ok:return {'error':{'message':'Tokens per day (TPD) exhausted'}}
    return {'choices':[{'message':{'content':'{"body":"Source-backed story."}'}}]}
  with patch.dict(os.environ,{'GROQ_API_KEY':'placeholder','GROQ_MODELS':'openai/gpt-oss-120b,openai/gpt-oss-20b'},clear=True),patch.object(collect,'provider_order',return_value=['groq']),patch.object(collect.requests,'post',side_effect=[Response(429),Response(200)]) as request:
   data,provider=collect.call_provider('Return JSON based on source')
   self.assertEqual(data['body'],'Source-backed story.');self.assertEqual(provider,'groq')
   self.assertNotIn('groq',collect.PROVIDER_COOLDOWNS)
   self.assertIn(('groq','openai/gpt-oss-120b'),collect.UNAVAILABLE_MODELS)
   self.assertEqual(request.call_args.kwargs['json']['response_format'],{'type':'json_object'})
   self.assertEqual(request.call_args.kwargs['json']['reasoning_effort'],'low')

 def test_state_reuses_backoff_without_storing_credentials(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'providers.json'
   with patch.dict(os.environ,{'NEWS_PROVIDER_STATE_PATH':str(path),'GROQ_API_KEY':'secret-not-to-be-saved'},clear=True):
    collect.PROVIDER_COOLDOWNS.add('openrouter')
    collect.UNAVAILABLE_MODELS.add(('groq','daily-model'))
    collect.PROVIDER_RETRY_AT['gemini']=1234
    collect.MODEL_RETRY_AT[('groq','temp-model')]=1300
    collect.PROVIDER_NEXT_REQUEST['groq']=1400
    collect.save_provider_state()
    self.assertNotIn('secret-not-to-be-saved',path.read_text())
    collect.PROVIDER_COOLDOWNS.clear();collect.UNAVAILABLE_MODELS.clear()
    collect.PROVIDER_RETRY_AT.clear();collect.MODEL_RETRY_AT.clear();collect.PROVIDER_NEXT_REQUEST.clear()
    collect.load_provider_state()
   self.assertIn('openrouter',collect.PROVIDER_COOLDOWNS)
   self.assertIn(('groq','daily-model'),collect.UNAVAILABLE_MODELS)
   self.assertEqual(collect.PROVIDER_RETRY_AT['gemini'],1234)
   self.assertEqual(collect.MODEL_RETRY_AT[('groq','temp-model')],1300)
   self.assertEqual(collect.PROVIDER_NEXT_REQUEST['groq'],1400)
