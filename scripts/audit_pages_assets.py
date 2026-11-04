"""Read-only Cloudflare Pages asset audit; never deletes posts, images, or URLs."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
POSTS = ROOT / "content" / "posts"
LIMIT = 20000
TARGET = 19000

def audit():
    files = [p for p in DIST.rglob("*") if p.is_file()]
    by_extension = Counter(p.suffix.lower() or "[none]" for p in files)
    by_section = Counter("/".join(p.relative_to(DIST).parts[:3]) for p in files)
    redirect_stubs = []
    article_pages = []
    for p in files:
        rel = p.relative_to(DIST).as_posix()
        if re.match(r"^(en|hi)/news/.+/index\.html$", rel):
            article_pages.append(rel)
        if p.name == "index.html" and p.stat().st_size < 2048:
            try:
                data = p.read_text(encoding="utf-8")
                if "<title>Article moved</title>" in data and 'http-equiv="refresh"' in data:
                    redirect_stubs.append(rel)
            except (UnicodeError, OSError):
                pass
    source_posts = list(POSTS.glob("*.json"))
    result = {
        "total_files": len(files),
        "cloudflare_limit": LIMIT,
        "target": TARGET,
        "over_limit": max(0, len(files)-LIMIT),
        "over_target": max(0, len(files)-TARGET),
        "source_article_json_count": len(source_posts),
        "article_html_count": len(article_pages),
        "redirect_stub_count": len(redirect_stubs),
        "by_extension": dict(by_extension),
        "largest_sections": by_section.most_common(25),
        "non_destructive": True,
    }
    print("PAGES_ASSET_AUDIT " + json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    audit()
