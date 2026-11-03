"""CSV/JSON/Markdown dashboard and weekly ISO snapshots of verified observations."""
from collections import Counter
from datetime import date, timedelta
import csv
import io
from .common import *

def run(weekly=False):
 prospects=read('prospects.json',[]); drafts=read('drafts.json',[]); links=read('backlinks.json',[])
 live=[r for r in links if r['status']=='live']
 week_start=(date.fromisoformat(day())-timedelta(days=6)).isoformat()
 rel=Counter(v for r in live for a in r.get('matches',[]) for v in a['rel'])
 targets=Counter(r['target_url'] for r in live)
 categories=Counter(classify(r['target_url']) or 'unclassified' for r in live)
 summary={'checked_at':day(),'prospects_discovered':len(prospects),'qualified_prospects':sum(bool(r.get('qualified')) for r in prospects),'outreach_drafts_prepared':len(drafts),'emails_sent':0,'sending_integration':'not enabled','confirmed_live_backlinks':len(live),'unique_referring_domains':len({domain(r['resolved_source']) for r in live}),'new_backlinks_last_7_days':sum(r.get('first_seen','')>=week_start for r in live),'lost_backlinks':sum(r['status'] in ('removed','changed') and bool(r.get('first_seen')) for r in links),'inaccessible_sources':sum(r['status']=='inaccessible' for r in links),'relationship_attributes':dict(rel),'link_categories':dict(categories),'best_target_pages':dict(targets.most_common(20)),'placement_types':dict(Counter(r.get('placement_type','unknown') for r in live)),'prospect_goal':300,'limitations':['A heuristic score is not Google authority, Domain Authority or an audience estimate.','No link inventory API connected. Import source URLs to verify existing backlinks.','No causal claim about backlinks and search performance.','Public contact details require purpose, recipient and legal review before any manual send.']}
 baseline=read('search-performance-baseline.json',{})
 if baseline.get('rows'):
  rows=baseline['rows']; clicks=sum(r['clicks'] for r in rows); impressions=sum(r['impressions'] for r in rows)
  summary['search_performance']={'retrieved_at':baseline.get('retrieved_at'),'returned_range':baseline.get('returned_range'),'clicks':clicks,'impressions':impressions,'ctr':clicks/impressions if impressions else None,'daily_observations':rows,'note':'Stored baseline only; weekly API refresh unavailable; no causal backlink claim.'}
 save('summary.json',summary)
 for name,rows in [('prospects',prospects),('backlinks',links),('drafts',drafts)]:
  fields=sorted({k for row in rows for k in row}) or ['status']
  stream=io.StringIO(); writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
  for row in rows:
   record={k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()}
   # Prevent spreadsheet formula execution in third-party scraped text.
   record={k: "'"+str(v) if str(v).startswith(('=','+','-','@','\t','\r')) else v for k,v in record.items()}
   writer.writerow(record)
  (DATA/(name+'.csv')).write_text(stream.getvalue())
 lines=['# Editorial backlink research dashboard','',f'Checked: {day()}', '', '| Metric | Count |','|---|---:|']
 for k in ('prospects_discovered','qualified_prospects','outreach_drafts_prepared','emails_sent','confirmed_live_backlinks','unique_referring_domains','new_backlinks_last_7_days','lost_backlinks','inaccessible_sources'): lines.append(f'| {k.replace("_"," ")} | {summary[k]} |')
 lines+=['','Only source pages with an observed exact target link count as live. Unknown placement type is not claimed as editorial. Drafts are review-only.','',*['- '+v for v in summary['limitations']]]
 (DATA/'REPORT.md').write_text('\n'.join(lines)+'\n')
 if weekly:
  year,week,_=date.fromisoformat(day()).isocalendar(); path=f'history/{year}-W{week:02d}.json'
  # First weekly snapshot is immutable; daily summary can still change.
  if not (DATA/path).exists(): save(path,summary)
 return summary
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(); p.add_argument('--weekly',action='store_true'); run(p.parse_args().weekly)
