"""One-time manual test reset. Removes generated posts, never sources or configuration."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
posts = ROOT / 'content' / 'posts'
removed = 0
for path in posts.glob('*.json'):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = {}
    post_id = str(data.get('id') or path.stem)
    # Remove only the generated article record; build.py recreates dist/.
    path.unlink()
    removed += 1
    print('Removed post:', post_id)
print(f'Removed {removed} posts. Daily counter now starts at zero.')
