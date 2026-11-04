"""Report Cloudflare Pages output growth without deleting any published content."""
from collections import Counter
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1] / "dist"
files = [p for p in root.rglob("*") if p.is_file()]
sections = Counter()
for p in files:
    rel = p.relative_to(root).parts
    if len(rel) >= 2 and rel[0] in ("en", "hi"):
        sections[f"{rel[0]}/{rel[1]}"] += 1
    else:
        sections[rel[0]] += 1
report = {"total": len(files), "cloudflare_pages_limit": 20000,
          "remaining": 20000 - len(files),
          "by_section": dict(sections.most_common())}
print("PAGES_GROWTH_AUDIT", json.dumps(report, sort_keys=True))
if len(files) > 20000:
    print("Pages deployment exceeds limit. No files were deleted.")
