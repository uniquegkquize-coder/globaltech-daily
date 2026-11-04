"""Read-only Cloudflare Pages asset audit. Never removes articles or images."""
from collections import Counter
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"
files = [p for p in OUT.rglob("*") if p.is_file()]
by_type = Counter(p.suffix.lower() or "[none]" for p in files)
by_section = Counter(p.relative_to(OUT).parts[0] for p in files)
by_route = Counter((lambda parts: parts[1] if len(parts)>1 and parts[0] in ("en","hi") else parts[0])(p.relative_to(OUT).parts) for p in files)
articles = [p for p in files if p.name == "index.html" and "/news/" in p.as_posix()]
redirect_stubs = []
for p in articles:
    if p.stat().st_size > 2048:
        continue
    try:
        if "<title>Article moved</title>" in p.read_text(encoding="utf-8"):
            redirect_stubs.append(p)
    except UnicodeError:
        continue
report = {
    "total_files": len(files),
    "pages_limit": 20000,
    "safety_target": 19000,
    "over_limit": max(0, len(files) - 20000),
    "over_safety_target": max(0, len(files) - 19000),
    "by_type": dict(by_type),
    "by_section": dict(by_section),
    "by_route": dict(by_route.most_common()),
    "directory_files": sum(by_route.get(section,0) for section in ("cars","phones","bikes","colleges")),
    "safe_to_delete_articles": False,
    "news_html_paths": len(articles),
    "generated_redirect_stubs": len(redirect_stubs),
}
print(json.dumps(report, indent=2, sort_keys=True))
