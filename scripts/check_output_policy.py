"""Reject recurrence of generated commits, duplicate jobs, and global middleware."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def check(root=ROOT, tracked=None):
    if tracked is None:tracked=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
    errors=[]
    for p in tracked:
        if p.startswith(('dist/','build/')) or '__pycache__' in Path(p).parts or p.endswith('.pyc'):
            errors.append('Generated file tracked: '+p)
    signatures={};duplicates=[]
    for path in sorted((root/'.github/workflows').glob('*.yml')):
        text=path.read_text()
        if re.search(r'git add[^\n]*\bdist\b',text):errors.append('Workflow commits deployment output: '+path.name)
        if 'safe threshold is 19000' in text:errors.append('Workflow bypasses build guard: '+path.name)
        if 'experiment/article-delivery-safe-preview' in text:errors.append('Workflow uses obsolete experimental build: '+path.name)
        signature=hashlib.sha256(text.encode()).hexdigest()
        if signature in signatures:duplicates.append([signatures[signature],path.name])
        signatures[signature]=path.name
    if duplicates:errors.append('Duplicated workflows: '+repr(duplicates))
    for path in ('functions/_middleware.js','functions/_middleware.ts','dist/_worker.js'):
        if (root/path).exists():errors.append('Global middleware prohibited: '+path)
    if errors:raise ValueError('\n'.join(errors[:40]))
    return {'tracked_files':len(tracked),'workflow_count':len(signatures),'duplicate_workflows':duplicates,'errors':0}

if __name__=='__main__':print(json.dumps(check()))
