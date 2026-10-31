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
if __name__=='__main__':unittest.main()
