"""Ingest trending-discovery drafts into the publishing pipeline.

The trending workflow (every 4 hours) runs in queue mode: finished
bilingual articles land in .cache/trending-drafts instead of
content/posts, so trending discovery alone never triggers a Cloudflare
Pages deployment. This script runs inside the 2-hour publishing
workflow and applies the cached drafts:

- Update drafts (id already live in content/posts): overwrite the post
  only when the draft is newer (updated_at), preserving URL, slug and
  publication date.
- New drafts: copied into content/pending/<id>.json; collect.py picks
  them up with first-priority AI slots and publishes them in this run.

Idempotent: re-ingesting the same cache is a no-op.
"""
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def ingest(draft_dir,posts_dir,pending_dir):
 applied_updates=0;queued_new=0;skipped_stale=0;invalid=0
 draft_dir=Path(draft_dir)
 if not draft_dir.is_dir():
  print('No trending draft cache found; nothing to ingest')
  return {'updates':0,'new':0,'stale':0,'invalid':0}
 for path in sorted(draft_dir.glob('*.json')):
  try:post=json.loads(path.read_text(encoding='utf-8'))
  except (OSError,ValueError):invalid+=1;continue
  post_id=str(post.get('id') or '').strip()
  if not post_id or '/' in post_id or post_id.startswith('.'):invalid+=1;continue
  if not (post.get('en_body') and post.get('hi_body') and post.get('en_title') and post.get('hi_title')):
   invalid+=1;continue
  live=Path(posts_dir)/(post_id+'.json')
  if live.exists():
   try:current=json.loads(live.read_text(encoding='utf-8'))
   except (OSError,ValueError):current={}
   draft_stamp=str(post.get('updated_at') or '')
   current_stamp=str(current.get('updated_at') or '')
   if draft_stamp and current_stamp and draft_stamp<=current_stamp:
    skipped_stale+=1;continue
   tmp=live.with_suffix('.tmp');tmp.write_text(json.dumps(post,ensure_ascii=False,indent=2)+'\n');tmp.replace(live)
   applied_updates+=1
  else:
   target=Path(pending_dir)/(post_id+'.json')
   if target.exists():
    try:existing=json.loads(target.read_text(encoding='utf-8'))
    except (OSError,ValueError):existing={}
    if str(post.get('updated_at') or '')<=str(existing.get('updated_at') or ''):
     skipped_stale+=1;continue
   tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(post,ensure_ascii=False,indent=2)+'\n');tmp.replace(target)
   queued_new+=1
 print('TRENDING_INGEST updates=%d new=%d stale=%d invalid=%d'%(applied_updates,queued_new,skipped_stale,invalid),flush=True)
 return {'updates':applied_updates,'new':queued_new,'stale':skipped_stale,'invalid':invalid}

if __name__=='__main__':
 result=ingest(ROOT/'.cache/trending-drafts',ROOT/'content/posts',ROOT/'content/pending')
 if result['invalid']:
  print('::warning::Some trending drafts were invalid and were skipped',flush=True)
 sys.exit(0)
