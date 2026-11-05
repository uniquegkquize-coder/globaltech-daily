"""Single-owner, clean generated output. Source trees are never cleanup targets."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
RENDERED = ROOT / 'build/rendered'
REPORT = ROOT / 'build/output-report.json'


def reset_rendered():
    # Fixed, dedicated generated directory; never accept a caller-supplied cleanup path.
    if RENDERED.is_symlink() or (ROOT/'build').is_symlink():
        raise ValueError('Generated output must not be a symlink')
    if RENDERED.exists():
        shutil.rmtree(RENDERED)
    RENDERED.mkdir(parents=True)
    return RENDERED


class OutputWriter:
    def __init__(self, root):
        self.root = Path(root)
        self.owner = 'build'
        self.paths = {}
        self.identical_writes = 0

    def __call__(self, path, body):
        path = Path(path)
        relative = path.relative_to(self.root).as_posix()
        if '..' in Path(relative).parts or path.is_symlink():
            raise ValueError('Unsafe generated path: ' + relative)
        data = body.encode('utf-8') if isinstance(body, str) else body
        digest = hashlib.sha256(data).hexdigest()
        old = self.paths.get(relative)
        if old:
            if old['sha256'] == digest:
                self.identical_writes += 1
                return
            raise ValueError(f'Conflicting output for {relative}: {old["generator"]} / {self.owner}')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.paths[relative] = {'sha256': digest, 'generator': self.owner}

    def report(self):
        files = sorted(p for p in self.root.rglob('*') if p.is_file())
        groups = defaultdict(list)
        for p in files:
            relative = p.relative_to(self.root).as_posix()
            if '__pycache__' in p.parts or p.suffix in ('.pyc', '.zip', '.log'):
                raise ValueError('Prohibited deployment artifact: ' + relative)
            groups[hashlib.sha256(p.read_bytes()).hexdigest()].append(relative)
        result = {
            'files': len(files), 'bytes': sum(p.stat().st_size for p in files),
            'by_type': dict(Counter(p.suffix or '[none]' for p in files)),
            'by_section': dict(Counter('/'.join(p.relative_to(self.root).parts[:2]) if p.relative_to(self.root).parts[0] in ('en','hi') else p.relative_to(self.root).parts[0] for p in files)),
            'by_generator': dict(Counter(self.paths.get(p.relative_to(self.root).as_posix(),{}).get('generator') or ('image_pipeline' if p.relative_to(self.root).parts[0]=='images' else 'sitemaps' if p.suffix=='.xml' else 'publisher_brand_assets') for p in files)),
            'identical_write_attempts': self.identical_writes,
            'duplicate_groups': [v for v in groups.values() if len(v) > 1],
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
        return result
