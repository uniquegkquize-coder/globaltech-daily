"""One-time archive of old articles before a fresh editorial launch."""
from pathlib import Path
import shutil
root = Path(__file__).resolve().parents[1]
marker = root / '.globaltech_reset_v1_done'
posts = root / 'content' / 'posts'
if marker.exists():
    print('One-time reset already completed')
else:
    archive = root / 'archive' / 'old_posts'
    archive.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in posts.glob('*.json'):
        shutil.move(str(p), str(archive / p.name))
        count += 1
    marker.write_text('Completed one-time archival of legacy posts. Do not delete this marker.\n')
    print('Archived old articles:', count)
