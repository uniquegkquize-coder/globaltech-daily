"""Native Oracle output; leave the Pages output and source content untouched."""
from pathlib import Path
import shutil


def output_directory(root: Path, render_only: bool) -> Path:
    if not render_only:
        return root / 'dist'
    build = root / 'build'
    out = build / 'rendered'
    if build.is_symlink() or out.is_symlink():
        raise ValueError('Oracle build output must not be a symlink')
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    return out
