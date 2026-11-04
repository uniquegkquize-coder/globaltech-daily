"""Regression tests for fair per-category publication ordering.

Evidence (2026-11-04 run, content/news-run-status.json): outcome
time_limit_reached, published 23, by_category {apps-software: 20,
sports: 3} while 46 configured categories received nothing. The old
final queue sort applied story_priority globally, letting one hot
category cluster at the head of the worker queue and consume the run
budget. fair_publication_order must preserve the round-robin rotation
built upstream while still lifting saved single-language drafts.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect import fair_publication_order, story_priority


def row(url, cat, age_hours):
    # story_priority favours the most recent leads; emulate with published ts.
    import datetime as dt
    published = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=age_hours)).isoformat()
    return (url, 'Title ' + url, cat, 'example.com', published)


def build_round_robin(rows_by_cat):
    """Mimic the upstream construction: per-category priority sort, then
    interleaved rounds, then a global priority tail."""
    grouped = {cat: sorted(rows, key=lambda r: story_priority((r[0], r[1], r[2], r[3])))
               for cat, rows in rows_by_cat.items()}
    ordered = []
    for _ in range(2):
        for cat in sorted(grouped):
            if grouped[cat]:
                ordered.append(grouped[cat].pop(0))
    for cat in sorted(grouped):
        ordered.extend(grouped[cat])
    return ordered


class FairOrderTests(unittest.TestCase):
    def test_hot_category_no_longer_clusters_at_head(self):
        hot = [row(f'https://s/{i}', 'apps-software', i) for i in range(1, 9)]
        others = {c: [row(f'https://s/{c}-{i}', c, 20 + i) for i in range(1, 5)]
                  for c in ('sports', 'business', 'world-news', 'gadgets')}
        rows_by_cat = dict(others)
        rows_by_cat['apps-software'] = hot
        ordered = build_round_robin(rows_by_cat)
        cats = {r[0]: r[2] for r in ordered}
        historical = {c: 50 for c in rows_by_cat}  # all above minimum
        result = fair_publication_order(ordered, set(), set(), historical, 2)
        first8 = [r[2] for r in result[:8]]
        self.assertEqual(len(set(first8)), 5, f'first 8 slots must span all 5 categories, got {first8}')
        self.assertEqual(first8[0], 'apps-software', 'most recent lead still opens the queue')

    def test_saved_single_language_draft_floats_to_front(self):
        hot = [row(f'https://s/{i}', 'apps-software', i) for i in range(1, 5)]
        calm = [row('https://s/calm-1', 'sports', 30)]
        rows_by_cat = {'apps-software': hot, 'sports': calm}
        ordered = build_round_robin(rows_by_cat)
        historical = {c: 50 for c in rows_by_cat}
        draft_url = 'https://s/calm-1'
        draft_id = __import__('hashlib').sha256(draft_url.encode()).hexdigest()[:12]
        result = fair_publication_order(ordered, {draft_id}, set(), historical, 2)
        self.assertEqual(result[0][0], draft_url, 'saved single-language draft must get the first AI slot')
        first4 = [r[2] for r in result[:4]]
        self.assertEqual(len(set(first4)), 2, 'interleaving must survive after the draft lift')

    def test_below_minimum_categories_lead_each_rotation(self):
        hot = [row(f'https://s/{i}', 'apps-software', i) for i in range(1, 5)]
        starving = [row('https://s/starve-1', 'travel', 40)]
        rows_by_cat = {'apps-software': hot, 'travel': starving}
        ordered = build_round_robin(rows_by_cat)
        historical = {'apps-software': 50, 'travel': 0}
        result = fair_publication_order(ordered, set(), set(), historical, 2)
        self.assertEqual(result[0][2], 'travel', 'category below minimum must lead the queue')


if __name__ == '__main__':
    unittest.main()
