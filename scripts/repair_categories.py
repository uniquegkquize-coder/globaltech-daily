"""Repair primary news categories without changing article IDs or content.

Dry run by default. Previous categories feed build.py's permanent redirects.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

try:
    from .news_config import route_category
except ImportError:
    from news_config import route_category


def repair(posts_dir, write=False):
    changes = []
    for path in sorted(Path(posts_dir).glob('*.json')):
        post = json.loads(path.read_text(encoding='utf-8'))
        if post.get('directory_kind') or post.get('content_type') == 'evergreen_directory_guide':
            continue
        old = post.get('category', 'technology')
        new = route_category(post.get('en_title') or post.get('source_title', ''), old, post.get('source', ''))
        if new == old:
            continue
        # Refuse oscillating rules rather than moving an article on every run.
        if route_category(post.get('en_title') or post.get('source_title', ''), new, post.get('source', '')) != new:
            raise ValueError(f'Unstable category routing: {path.name}: {old} -> {new}')
        changes.append({'id': post['id'], 'from': old, 'to': new, 'title': post.get('en_title', '')})
        if write:
            post['previous_categories'] = sorted(set(post.get('previous_categories', [])) | {old})
            post['category'] = new
            path.write_text(json.dumps(post, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--posts', type=Path, default=Path(__file__).resolve().parents[1] / 'content/posts')
    args = parser.parse_args()
    changes = repair(args.posts, args.write)
    print(json.dumps({'changed': len(changes), 'written': args.write,
                      'routes': dict(Counter(f"{c['from']} -> {c['to']}" for c in changes))}, ensure_ascii=False))
