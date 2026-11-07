"""Read-only source diagnostics: no model calls, posts, credentials or paid APIs."""
import concurrent.futures
import json
from collections import Counter
from collect import native_feed_stories,website_stories,source_text,words,STORY_DATES,category_for_url
from focused_sources import PAGES,NATIVE_FEEDS
TARGETS={'car-launches','mobile-launches','movie-releases','controversies','automobiles','india-news','world-news'}

def main():
    leads=list(native_feed_stories(NATIVE_FEEDS))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        pages=list(pool.map(website_stories,PAGES))
    for item,rows in pages:
        print('SOURCE_PAGE',item[2],'candidates',len(rows),flush=True)
        leads.extend(rows)
    unique={row[0]:(row[0],row[1],category_for_url(row[1],row[2],row[0]),row[3]) for row in leads};counts=Counter(row[2] for row in unique.values())
    selected=[];domains=set();per_category=Counter()
    for row in sorted(unique.values(),key=lambda r:(r[3]!='bikewale.com',r[2] not in TARGETS,not bool(STORY_DATES.get(r[0])))):
        if row[2] not in TARGETS or per_category[row[2]]>=3 or row[3] in domains:continue
        selected.append(row);domains.add(row[3]);per_category[row[2]]+=1
    def check(row):
        text=source_text(row[0],row[3]);count=words(text)
        return {'category':row[2],'domain':row[3],'url':row[0],'words':count,'readable':count>=65,'dated':bool(STORY_DATES.get(row[0]))}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        checks=list(pool.map(check,selected))
    for row in checks:print('SOURCE_ARTICLE',json.dumps(row),flush=True)
    summary={'leads_by_category':dict(sorted(counts.items())),'article_checks':checks,'ai_calls':0}
    print('SOURCE_PROBE_SUMMARY',json.dumps(summary),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
