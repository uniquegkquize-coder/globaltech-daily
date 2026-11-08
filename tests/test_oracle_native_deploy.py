import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from install_oracle_native_deploy import transform
from oracle_render import output_directory
from redirect_assets import write_redirects


class NativeOracleTests(unittest.TestCase):
    def test_oracle_output_does_not_touch_pages_or_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('dist', 'content', 'build/rendered'):
                (root / name).mkdir(parents=True)
                (root / name / 'keep.txt').write_text(name)
            out = output_directory(root, True)
            self.assertFalse((out / 'keep.txt').exists())
            self.assertEqual((root / 'dist/keep.txt').read_text(), 'dist')
            self.assertEqual((root / 'content/keep.txt').read_text(), 'content')
            self.assertEqual(output_directory(root, False), root / 'dist')

    def test_all_oracle_aliases_are_retained_without_html_stubs(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'rendered'
            out.mkdir()
            def write(path, body):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body)
            lines = ['/ /en/ 301'] + [f'/en/news/{i:012x}/ /en/news/topic/article/ 301' for i in range(2100)]
            write_redirects(out, lines, write, 'https://globewiredaily.org', external=True)
            routes = json.loads((out.parent / 'redirects.json').read_text())
            self.assertEqual(len(routes), 2101)
            self.assertEqual(routes['/en/news/000000000833/'][1], '301')
            self.assertEqual(list(out.rglob('index.html')), [])
            # Existing Pages callers keep their bounded redirect output.
            write_redirects(out, lines[:3], write, 'https://globewiredaily.org', limit=1)
            self.assertEqual(len(list(out.rglob('index.html'))), 2)

    def test_installer_removes_merge_for_original_and_patched_deployers(self):
        merge = 'git(work, "-c", "user.name=GlobeWire Oracle Preview", "merge", "--no-edit", MIGRATION)'
        prefix = '''MIGRATION = "old"
def main():
    original = ACTIVE.read_bytes()
    shallow = git(CHECKOUT, "rev-parse")
    source = "old"
    release = MIGRATION
    if release_header(old) == release:
        return
    work = get_work()
    try:
        git(CHECKOUT, "worktree", "add", "--detach", work, source)
'''
        suffix = '''        epoch = git(work, "log")
        run(PYTHON, "scripts/build.py", "--render-only")
        preserve_old_urls()
        verify_candidate()
        promote_with_rollback()
    finally:
        cleanup_worktree()
'''
        for assembly in (
            '        ' + merge + '\n',
            '        try:\n            ' + merge + '\n        except subprocess.CalledProcessError:\n            resolve_known_conflicts()\n',
        ):
            updated = transform(prefix + assembly + suffix)
            self.assertNotIn('MIGRATION', updated)
            self.assertNotIn('"merge"', updated)
            self.assertIn('refs/remotes/origin/main', updated)
            for check in ('preserve_old_urls()', 'verify_candidate()', 'promote_with_rollback()', 'cleanup_worktree()'):
                self.assertIn(check, updated)
            self.assertEqual(transform(updated), updated)


if __name__ == '__main__':
    unittest.main()
