#!/usr/bin/env python3
"""Read-only Cloudflare Pages asset inventory. Never deletes or modifies posts."""
from pathlib import Path
from collections import Counter
import argparse, json
p=argparse.ArgumentParser()
p.add_argument("--dist",default="dist")
p.add_argument("--limit",type=int,default=20000)
a=p.parse_args()
root=Path(a.dist)
if not root.is_dir(): raise SystemExit(f"Missing output directory: {root}")
files=[f for f in root.rglob("*") if f.is_file()]
types=Counter(f.suffix.lower() or "[none]" for f in files)
prefix=Counter(f.relative_to(root).parts[0] for f in files)
redirects=[]
articles=[]
for f in files:
 if f.name!="index.html":continue
 rel=f.relative_to(root).as_posix()
 if "/news/" in "/"+rel:articles.append(rel)
 if f.stat().st_size<=4096:
  try:
   s=f.read_text(encoding="utf-8")
   if '<title>Article moved</title>' in s and '<meta http-equiv="refresh"' in s: redirects.append(rel)
  except (UnicodeError,OSError):pass
report={"total_files":len(files),"limit":a.limit,"over_limit":max(0,len(files)-a.limit),"by_extension":dict(types),"by_top_level":dict(prefix),"article_html_files":len(articles),"redirect_stub_files":len(redirects),"potential_savings_if_redirects_replaced":len(redirects),"post_content_files":len(list(Path("content/posts").glob("*.json"))),"warning":"Read-only audit. Do not delete articles, article HTML, images or redirect stubs without a verified URL-preserving replacement."}
print(json.dumps(report,indent=2,sort_keys=True))
