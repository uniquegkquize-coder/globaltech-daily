"""One-time, backed-up conversion of the existing Oracle deployer to native main.

Run as root on the Oracle host after the current deployment has finished.
Existing nginx verification, URL preservation, release promotion and rollback stay
in the deployer. This installer only replaces source fetching and merge assembly.
"""
import ast
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import time

TARGET = Path('/usr/local/sbin/globewire-oracle-preview-deploy')
MARKER = 'NATIVE_MAIN_DEPLOY_V1'


def transform(text):
    if MARKER in text:
        return text
    start = text.index('    shallow = git(CHECKOUT,')
    end = text.index('    if release_header(old) == release:', start)
    native = '''    # NATIVE_MAIN_DEPLOY_V1: build one main commit; never merge old history.
    shallow = git(CHECKOUT, "rev-parse", "--is-shallow-repository", capture=True).strip()
    history = ["--unshallow"] if shallow == "true" else []
    git(CHECKOUT, "-c", "pack.threads=1", "fetch", "--no-tags", *history, REPO, "refs/heads/main:refs/remotes/origin/main")
    source = git(CHECKOUT, "rev-parse", "refs/remotes/origin/main", capture=True).strip()
    builder = git(CHECKOUT, "show", f"{source}:scripts/build.py", capture=True)
    if "external=RENDER_ONLY" not in builder:
        raise RuntimeError("Main lacks native Oracle rendering; current release kept")
    git(CHECKOUT, "cat-file", "-e", f"{source}:scripts/oracle_render.py")
    git(CHECKOUT, "cat-file", "-e", f"{source}:content/published-url-inventory.json")
    release = hashlib.sha256(f"{source}:native-main-v1:{CONFIG_VERSION}".encode()).hexdigest()[:20]
'''
    text = text[:start] + native + text[end:]
    merge_call = 'git(work, "-c", "user.name=GlobeWire Oracle Preview"'
    wrapped = '        try:\n            ' + merge_call
    if wrapped in text:
        start = text.index(wrapped)
    else:
        start = text.index('        ' + merge_call)
    end = text.index('        epoch = git(work,', start)
    text = text[:start] + text[end:]
    # The old migration constant no longer controls any deployment operation.
    text = '\n'.join(line for line in text.split('\n') if not line.startswith('MIGRATION = '))
    ast.parse(text)
    if 'MIGRATION' in text:
        raise ValueError('Unrecognized migration references; no changes made')
    return text


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run this installer with sudo')
    state = subprocess.run(
        ['systemctl', 'show', 'globewire-oracle-preview.service', '-p', 'ActiveState', '--value'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if state not in {'inactive', 'failed'}:
        raise SystemExit('Deployment is running; wait for it to finish, then rerun installer')
    original = TARGET.read_text()
    updated = transform(original)
    if original == updated:
        print('Native main deployment already installed')
        return
    backup = TARGET.with_name(TARGET.name + '.before-native-' + str(time.time_ns()))
    shutil.copy2(TARGET, backup)
    with tempfile.NamedTemporaryFile(mode='w', dir=TARGET.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(updated)
    try:
        shutil.copystat(TARGET, temporary)
        os.replace(temporary, TARGET)
    finally:
        temporary.unlink(missing_ok=True)
    print('NATIVE MAIN INSTALLED. Backup:', backup)
    print('URL preservation, nginx checks and rollback retained. No release changed yet.')


if __name__ == '__main__':
    main()
