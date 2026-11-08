import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import publish_news_batch as batch

class PublishBatchTests(unittest.TestCase):
 def test_passes_resume_remaining_target_and_merge_summary(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);posts=root/'content/posts';posts.mkdir(parents=True)
   seen=[]
   def run(command,**kwargs):
    seen.append(kwargs['env']['POSTS_PER_RUN'])
    count=2 if len(seen)==1 else 1
    for index in range(count):
     (posts/(str(len(list(posts.glob('*.json'))))+'.json')).write_text(json.dumps({'category':'world-news'}))
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'time_limit_reached','ai_calls':2,'retry_after_seconds':1}))
    return type('Completed',(),{'returncode':0})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{'POSTS_PER_RUN':'3','PUBLISH_MAX_PASSES':'5'}),patch.object(batch.subprocess,'run',side_effect=run),patch.object(batch.time,'sleep') as sleep:
    self.assertEqual(batch.main(),0)
   report=json.loads((root/'content/news-run-status.json').read_text())
   self.assertEqual(seen,['3','1'])
   self.assertEqual(report['published'],3)
   self.assertEqual(report['outcome'],'target_reached')
   self.assertEqual(report['ai_calls'],4)
   sleep.assert_called_once()
 def test_hard_provider_block_does_not_loop(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'content/posts').mkdir(parents=True)
   def run(*args,**kwargs):
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'providers_unavailable','retry_after_seconds':None}))
    return type('Completed',(),{'returncode':2})()
   with patch.object(batch,'ROOT',root),patch.object(batch.subprocess,'run',side_effect=run) as request,patch.object(batch.time,'sleep') as sleep:
    self.assertEqual(batch.main(),2)
   request.assert_called_once();sleep.assert_not_called()
 def test_each_cycle_reuses_counts_for_category_priority(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);posts=root/'content/posts';posts.mkdir(parents=True)
   seen=[]
   def run(*args,**kwargs):
    seen.append(json.loads(kwargs['env']['NEWS_BATCH_CATEGORY_COUNTS']))
    if len(seen)==1:
     (posts/'first.json').write_text(json.dumps({'category':'cricket'}))
    else:
     (posts/'second.json').write_text(json.dumps({'category':'world-news'}))
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'time_limit_reached','pass':len(seen)}))
    return type('Completed',(),{'returncode':0})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{'POSTS_PER_RUN':'2'}),patch.object(batch.subprocess,'run',side_effect=run),patch.object(batch.time,'sleep'):
    batch.main()
   self.assertEqual(seen,[{}, {'cricket':1}])

 def test_default_target_resumes_to_200_posts(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);posts=root/'content/posts';posts.mkdir(parents=True)
   targets=[]
   def run(*args,**kwargs):
    targets.append(kwargs['env']['POSTS_PER_RUN'])
    for index in range(100):
     (posts/(str(len(list(posts.glob('*.json'))))+'.json')).write_text(json.dumps({'category':'world-news'}))
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'ai_limit_reached','ai_calls':100,'pass':len(targets)}))
    return type('Completed',(),{'returncode':0})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{},clear=True),patch.object(batch.subprocess,'run',side_effect=run),patch.object(batch.time,'sleep'):
    self.assertEqual(batch.main(),0)
   report=json.loads((root/'content/news-run-status.json').read_text())
   self.assertEqual(targets,['200','100'])
   self.assertEqual(report['published'],200)
   self.assertEqual(report['outcome'],'target_reached')

 def test_repeat_mode_can_continue_after_five_passes(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);posts=root/'content/posts';posts.mkdir(parents=True)
   def run(*args,**kwargs):
    index=len(list(posts.glob('*.json')))
    (posts/(str(index)+'.json')).write_text(json.dumps({'category':'world-news'}))
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'time_limit_reached','cycle':index}))
    return type('Completed',(),{'returncode':0})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{'POSTS_PER_RUN':'6'},clear=True),patch.object(batch.subprocess,'run',side_effect=run) as request,patch.object(batch.time,'sleep'):
    self.assertEqual(batch.main(),0)
   self.assertEqual(request.call_count,6)
   self.assertEqual(json.loads((root/'content/news-run-status.json').read_text())['published'],6)

 def test_final_summary_records_deadline_instead_of_stale_pass_outcome(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'content/posts').mkdir(parents=True)
   def run(*args,**kwargs):
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'ai_limit_reached','retry_after_seconds':300}))
    return type('Completed',(),{'returncode':2})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{'PUBLISH_BATCH_SECONDS':'240'}),patch.object(batch.subprocess,'run',side_effect=run),patch.object(batch.time,'sleep') as sleep:
    self.assertEqual(batch.main(),2)
   sleep.assert_not_called()
   self.assertEqual(json.loads((root/'content/news-run-status.json').read_text())['outcome'],'time_limit_reached')

class SmallBatchTests(unittest.TestCase):
 def test_ten_small_batches_reach_one_200_post_target(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);posts=root/'content/posts';posts.mkdir(parents=True)
   seen=[];state_paths=[]
   def run(*args,**kwargs):
    env=kwargs['env'];seen.append(int(env['POSTS_PER_RUN']));state_paths.append(env['NEWS_PROVIDER_STATE_PATH'])
    self.assertEqual(json.loads(env['NEWS_BATCH_CATEGORY_COUNTS']).get('world-news',0),sum(seen[:-1]))
    for index in range(seen[-1]):
     (posts/f'{len(list(posts.glob("*.json")))}.json').write_text(json.dumps({'category':'world-news'}))
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'target_reached','ai_calls':seen[-1]}))
    return type('Completed',(),{'returncode':0})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{'POSTS_PER_RUN':'200','PUBLISH_POSTS_PER_PASS':'20','PUBLISH_MAX_PASSES':'40'},clear=True),patch.object(batch.subprocess,'run',side_effect=run),patch.object(batch.time,'sleep'):
    self.assertEqual(batch.main(),0)
   report=json.loads((root/'content/news-run-status.json').read_text())
   self.assertEqual(seen,[20]*10)
   self.assertEqual(len(set(state_paths)),1)
   self.assertEqual(report['published'],200);self.assertEqual(report['shortfall'],0)
   self.assertEqual(report['ai_calls'],200);self.assertTrue(report['target_met'])

 def test_partial_progress_is_saved_but_never_reported_as_success(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);posts=root/'content/posts';posts.mkdir(parents=True)
   def run(*args,**kwargs):
    (posts/'saved.json').write_text(json.dumps({'category':'cricket'}))
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'providers_unavailable','retry_after_seconds':None,'ai_calls':3}))
    return type('Completed',(),{'returncode':0})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{'POSTS_PER_RUN':'200'},clear=True),patch.object(batch.subprocess,'run',side_effect=run) as request:
    self.assertEqual(batch.main(),2)
   request.assert_called_once()
   report=json.loads((root/'content/news-run-status.json').read_text())
   self.assertEqual(report['published'],1);self.assertEqual(report['shortfall'],199)
   self.assertFalse(report['target_met']);self.assertTrue((posts/'saved.json').exists())

 def test_global_call_budget_is_not_reset_by_a_new_pass(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'content/posts').mkdir(parents=True);limits=[]
   def run(*args,**kwargs):
    limit=int(kwargs['env']['MAX_AI_CALLS_PER_RUN']);limits.append(limit)
    (root/'content/news-run-status.json').write_text(json.dumps({'outcome':'ai_limit_reached','ai_calls':limit,'pass':len(limits)}))
    return type('Completed',(),{'returncode':0})()
   with patch.object(batch,'ROOT',root),patch.dict(os.environ,{'PUBLISH_MAX_AI_CALLS':'150'},clear=True),patch.object(batch.subprocess,'run',side_effect=run),patch.object(batch.time,'sleep'):
    self.assertEqual(batch.main(),2)
   self.assertEqual(limits,[100,50])
   report=json.loads((root/'content/news-run-status.json').read_text())
   self.assertEqual(report['ai_calls'],150);self.assertEqual(report['ai_limit'],150)
