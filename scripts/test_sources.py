"""Fast offline checks for the nationwide news source registry."""
import ast
from pathlib import Path
source=Path(__file__).with_name("collect.py").read_text(encoding="utf-8")
tree=ast.parse(source)
assignments={n.targets[0].id:n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
regions=ast.literal_eval(assignments["INDIA_REGIONS"])
assert len(regions)==36, f"Expected 36 Indian states and UTs, found {len(regions)}"
assert all(cities for cities in regions.values())
assert len(set(regions))==36
assert sum(map(len,regions.values()))>=100
# Guard against regressions in the minimum-length quality gate.
assert "def duplicate_story(url,title,cat,index):" in source
assert "is_duplicate=duplicate_story(url,title,cat,published_index)" in source
assert "with publication_lock:" in source
assert "published_index.append((url.rstrip('/'),title,cat))" in source
assert "MIN_ARTICLE_WORDS_EN" in source
assert "MIN_ARTICLE_WORDS_HI" in source
assert "def complete_body(body,lang):" in source
assert "rotating_local_feeds()" in source
assert "resolve_google_news(url)" in source
assert "results=list(pool.map(read_feed,FEEDS+rotating_local_feeds()+rotating_social_feeds()))" in source
assert "if not allowed(url,domain) or url in seen:continue" in source
assert "if not url or not title:continue" in source
assert "resolver_pool.map(resolve_eligible,eligible)" in source
print(f"Source validation OK: {len(regions)} states/UTs, {sum(map(len,regions.values()))} cities")
