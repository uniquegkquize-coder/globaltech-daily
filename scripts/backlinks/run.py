"""Independent bounded research job. Never calls news publishing or email sending."""
import argparse
from .common import *
from . import audit, discover, score, outreach, verify, report

def main():
 p=argparse.ArgumentParser(); p.add_argument('--limit',type=int,default=30); p.add_argument('--weekly',action='store_true'); p.add_argument('--seconds',type=int,default=480)
 args=p.parse_args(); fetcher=Fetcher(args.seconds); stages={}
 for name,fn in [('audit',lambda:audit.inventory(fetcher)),('discovery',lambda:discover.run(fetcher,args.limit)),('scoring',score.run),('drafts',outreach.run)]:
  try:
   fn(); stages[name]='completed (individual inaccessible sources may be deferred)'
  except Exception as exc:
   stages[name]='failed: '+str(exc); LOG.exception('%s failed',name); save(name+'-error.json',{'date':day(),'error':str(exc)})
 if args.weekly: verify.run(Fetcher(180))
 save('run-status.json',{'date':day(),'stages':stages,'weekly_requested':args.weekly}); result=report.run(args.weekly); LOG.info('%s',json.dumps(result))
if __name__=='__main__': main()
