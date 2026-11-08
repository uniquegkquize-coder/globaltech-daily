"""Resume one publishing target across bounded collector passes."""
from collections import Counter
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def read_status():
 try:return json.loads((ROOT/'content/news-run-status.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):return {}

def new_counts(before):
 counts=Counter()
 for path in (ROOT/'content/posts').glob('*.json'):
  if path.name in before:continue
  try:counts[json.loads(path.read_text(encoding='utf-8')).get('category','unknown')]+=1
  except (OSError,ValueError):continue
 return counts

def save_summary(target,before,attempts,started,outcome,latest):
 counts=new_counts(before)
 data={**latest,'finished_at':dt.datetime.now(dt.timezone.utc).isoformat(),
       'outcome':outcome,'duration_seconds':round(time.monotonic()-started,1),
       'target':target,'published':sum(counts.values()),'by_category':dict(counts),
       'ai_calls':sum(row.get('ai_calls',0) for row in attempts),
       'ai_limit':100*len(attempts),'attempts':attempts}
 path=ROOT/'content/news-run-status.json'
 temp=path.with_suffix('.tmp')
 temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 temp.replace(path)
 print('PUBLISH_BATCH_SUMMARY',json.dumps(data),flush=True)
 return data

def main():
 target=max(1,int(os.getenv('POSTS_PER_RUN','200')))
 passes=max(1,min(12,int(os.getenv('PUBLISH_MAX_PASSES','12'))))
 budget=max(180,min(3600,int(os.getenv('PUBLISH_BATCH_SECONDS','3600'))))
 started=time.monotonic();deadline=started+budget
 before={p.name for p in (ROOT/'content/posts').glob('*.json')}
 attempts=[];latest={};outcome='attempt_limit_reached'
 for number in range(1,passes+1):
  counts=new_counts(before);remaining=target-sum(counts.values())
  if remaining<=0:outcome='target_reached';break
  seconds=min(600,int(deadline-time.monotonic()-60))
  if seconds<120:outcome='time_limit_reached';break
  env=os.environ.copy()
  env.update(POSTS_PER_RUN=str(remaining),COLLECT_SECONDS=str(seconds),
             DISCOVERY_SECONDS='90' if number==1 else '30',
             NEWS_BATCH_CATEGORY_COUNTS=json.dumps(dict(counts)))
  # Each pass retains the existing 100-call guard and saved source-backed drafts.
  previous=read_status()
  print('PUBLISH_BATCH_PASS',number,'remaining',remaining,flush=True)
  try:
   completed=subprocess.run([sys.executable,'-u',str(ROOT/'scripts/collect.py')],
                            cwd=ROOT,env=env,timeout=seconds+55,check=False)
   code=completed.returncode
  except subprocess.TimeoutExpired:code=124
  latest=read_status()
  if latest==previous:
   latest={'outcome':'collector_failed','ai_calls':0,'retry_after_seconds':60}
  attempts.append({'pass':number,'exit_code':code,'published':max(0,sum(new_counts(before).values())-sum(counts.values())),
                   'ai_calls':latest.get('ai_calls',0),'outcome':latest.get('outcome')})
  outcome='target_reached' if sum(new_counts(before).values())>=target else str(latest.get('outcome') or 'collector_failed')
  report=save_summary(target,before,attempts,started,outcome,latest)
  if outcome=='target_reached' or number==passes:break
  if outcome in ('disabled','no_provider'):break
  delay=latest.get('retry_after_seconds')
  if outcome=='providers_unavailable' and delay is None:break
  delay=max(30,float(delay or 60))
  if delay+180>deadline-time.monotonic():outcome='time_limit_reached';break
  print('PUBLISH_BATCH_RETRY_AFTER',round(delay),'seconds',flush=True)
  # Log long waits in short intervals so a rate limit is visible in Actions.
  while delay>0:
   step=min(60,delay);time.sleep(step);delay-=step
 if attempts and outcome!='target_reached' and len(attempts)==passes:
  outcome='attempt_limit_reached' if outcome not in ('disabled','no_provider','providers_unavailable') else outcome
 report=save_summary(target,before,attempts,started,outcome,latest)
 return 0 if report['published'] else 2

if __name__=='__main__':sys.exit(main())
