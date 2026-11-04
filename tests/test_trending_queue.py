"""Queue-based trending architecture: discovery never deploys alone.

Guards the Phase 6 restructure:
- trending_watch.persist_post() honours TREND_QUEUE_MODE (drafts go to the
  shared cache, never straight into content/posts).
- ingest_trending_drafts applies cached drafts idempotently.
- Workflow schedules stay separated: trending every 4 hours with no build
  or push, publishing every 2 hours with the ingest step present.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import trending_watch
import ingest_trending_drafts

ROOT = Path(__file__).resolve().parents[1]

def sample_post(post_id='abc123def456', updated_at='2026-01-02T03:04:05+00:00'):
    return {
        'id': post_id,
        'en_title': 'Test headline',
        'hi_title': 'परीक्षण शीर्षक',
        'en_body': 'English body long enough to count as complete for tests.',
        'hi_body': 'हिंदी बॉडी इतनी लंबी कि पूर्ण मानी जाए।',
        'updated_at': updated_at,
    }

class PersistPostQueueModeTest(unittest.TestCase):
    def test_queue_mode_writes_draft_cache_not_posts(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft_dir = Path(tmp) / 'drafts'
            posts_dir = Path(tmp) / 'posts'
            posts_dir.mkdir()
            post = sample_post()
            with mock.patch.dict('os.environ', {'TREND_QUEUE_MODE': '1', 'TREND_DRAFT_DIR': str(draft_dir)}), \
                 mock.patch.object(trending_watch.newsroom, 'POSTS', posts_dir):
                trending_watch.persist_post(post)
            files = list(draft_dir.glob('*.json'))
            self.assertEqual([p.stem for p in files], [post['id']])
            self.assertEqual(list(posts_dir.glob('*.json')), [])
            data = json.loads(files[0].read_text(encoding='utf-8'))
            self.assertEqual(data['id'], post['id'])
            self.assertTrue(data['en_body'] and data['hi_body'])

    def test_legacy_mode_writes_posts_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts_dir = Path(tmp) / 'posts'
            posts_dir.mkdir()
            post = sample_post()
            with mock.patch.dict('os.environ', {'TREND_QUEUE_MODE': ''}), \
                 mock.patch.object(trending_watch.newsroom, 'POSTS', posts_dir):
                trending_watch.persist_post(post)
            self.assertTrue((posts_dir / (post['id'] + '.json')).exists())

class IngestDraftsTest(unittest.TestCase):
    def test_new_draft_is_queued_into_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft_dir = Path(tmp) / 'drafts'; posts_dir = Path(tmp) / 'posts'; pending = Path(tmp) / 'pending'
            draft_dir.mkdir(); posts_dir.mkdir(); pending.mkdir()
            (draft_dir / 'newid000000.json').write_text(json.dumps(sample_post('newid000000')), encoding='utf-8')
            result = ingest_trending_drafts.ingest(draft_dir, posts_dir, pending)
            self.assertEqual(result['new'], 1)
            self.assertTrue((pending / 'newid000000.json').exists())

    def test_update_applies_only_when_newer(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft_dir = Path(tmp) / 'drafts'; posts_dir = Path(tmp) / 'posts'; pending = Path(tmp) / 'pending'
            draft_dir.mkdir(); posts_dir.mkdir(); pending.mkdir()
            live = sample_post('liveid000001', updated_at='2026-01-01T00:00:00+00:00')
            (posts_dir / 'liveid000001.json').write_text(json.dumps(live), encoding='utf-8')
            newer = sample_post('liveid000001', updated_at='2026-01-02T00:00:00+00:00')
            newer['en_title'] = 'Updated headline'
            (draft_dir / 'liveid000001.json').write_text(json.dumps(newer), encoding='utf-8')
            stale = sample_post('liveid000001', updated_at='2025-12-31T00:00:00+00:00')
            (draft_dir / 'other.json').write_text(json.dumps(stale), encoding='utf-8')
            result = ingest_trending_drafts.ingest(draft_dir, posts_dir, pending)
            self.assertEqual(result['updates'], 1)
            self.assertEqual(result['stale'], 1)
            self.assertEqual(json.loads((posts_dir / 'liveid000001.json').read_text(encoding='utf-8'))['en_title'], 'Updated headline')

    def test_incomplete_draft_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft_dir = Path(tmp) / 'drafts'; posts_dir = Path(tmp) / 'posts'; pending = Path(tmp) / 'pending'
            draft_dir.mkdir(); posts_dir.mkdir(); pending.mkdir()
            bad = sample_post('badid0000001'); bad.pop('hi_body')
            (draft_dir / 'badid0000001.json').write_text(json.dumps(bad), encoding='utf-8')
            result = ingest_trending_drafts.ingest(draft_dir, posts_dir, pending)
            self.assertEqual(result['invalid'], 1)
            self.assertEqual(list(pending.glob('*.json')), [])

class WorkflowArchitectureTest(unittest.TestCase):
    def test_trending_watch_runs_every_four_hours_without_deploying(self):
        text = (ROOT / '.github/workflows/trending-watch.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '23 */4 * * *'", text)
        self.assertNotIn('2,17,32,47', text)
        self.assertIn("TREND_QUEUE_MODE: '1'", text)
        self.assertNotIn('git push', text)
        self.assertNotIn('scripts/build.py', text)
        self.assertNotIn('git commit', text)
        self.assertIn('.cache/trending-drafts', text)

    def test_publishing_workflow_ingests_trending_drafts(self):
        text = (ROOT / '.github/workflows/news-auto.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '7 */2 * * *'", text)
        self.assertIn('ingest_trending_drafts.py', text)
        self.assertIn('restore-keys: trending-watch-main-', text)
        self.assertIn('.cache/trending-drafts', text)

if __name__ == '__main__':
    unittest.main()
