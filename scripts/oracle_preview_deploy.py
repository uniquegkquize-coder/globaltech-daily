#!/usr/bin/python3
"""Build, verify, and promote a loopback Oracle preview, with nginx rollback."""
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
from urllib.parse import quote

HOME = Path("/home/ubuntu")
CHECKOUT = HOME / "globewire-test"
PYTHON = CHECKOUT / ".venv/bin/python"
REPO = "https://github.com/uniquegkquize-coder/globaltech-daily.git"
MIGRATION = "e19ff8aa03bb1237450d77493466739cca6c4ca7"
ACTIVE = Path("/etc/nginx/conf.d/z-globewire-latest.conf")
CANDIDATE = Path("/etc/nginx/conf.d/zz-globewire-oracle-candidate.conf")
RELEASES = Path("/var/www/globewire-oracle-releases")
PREVIEW = 8081
TEST = 8082
SAFE_PATH = re.compile(r"/[A-Za-z0-9._~/%-]*")


def run(*args, capture=False, user=False, **kwargs):
    if user:
        args = ("runuser", "-u", "ubuntu", "--", "env", f"HOME={HOME}", *args)
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None, **kwargs)


def git(directory, *args, capture=False):
    return run("git", "-C", directory, *args, capture=capture, user=True).stdout


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".globewire-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def reload_nginx():
    run("nginx", "-t")
    run("systemctl", "reload", "nginx")


def read_routes(build):
    root = build / "rendered"
    redirects = json.loads((build / "redirects.json").read_text())
    redirects["/"] = ["/en/", "301"]
    for name in ("news-sitemap-1.xml", "news-sitemap-2.xml"):
        if not (root / name).exists():
            redirects.setdefault("/" + name, ["/news-sitemap.xml", "301"])
    for source, (target, status) in redirects.items():
        if int(status) != 301 or any(
            path.startswith("//") or not SAFE_PATH.fullmatch(path)
            for path in (source, target)
        ):
            raise ValueError(f"Unsupported redirect: {source!r} -> {target!r}")
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"Unexpected generated path: {path}")
        if not path.is_file() or path.name in {"_headers", "_redirects"}:
            continue
        relative = path.relative_to(root).as_posix()
        url = "/" + relative
        if url.endswith("/index.html"):
            url = url.removesuffix("index.html")
        if url not in redirects:
            files[url] = relative
    required = {"/en/", "/hi/", "/sitemap.xml", "/news-sitemap.xml"}
    if not required <= files.keys():
        raise ValueError("Build is missing required public routes")
    for source, (target, _) in redirects.items():
        seen = {source}
        while target in redirects:
            if target in seen:
                raise ValueError(f"Redirect loop: {source}")
            seen.add(target)
            target = redirects[target][0]
        if target not in files:
            raise ValueError(f"Missing redirect target: {source} -> {target}")
    return files, redirects


def config(port, release, site, redirects):
    name = f"globewire_oracle_{port}"
    rows = "\n".join(f'    "{source}" "{target}";' for source, (target, _) in redirects.items())
    return f'''map $uri ${name} {{
    default "";
{rows}
}}
server {{
    listen 127.0.0.1:{port};
    root {site};
    index index.html;
    absolute_redirect off;
    add_header X-Robots-Tag "noindex" always;
    add_header X-GlobeWire-Release "{release}" always;
    if (${name} != "") {{
        return 301 ${name}$is_args$args;
    }}
    location = /_headers {{ return 404; }}
    location = /_redirects {{ return 404; }}
    location / {{ try_files $uri $uri/ =404; }}
}}
'''.encode()


def fetch(conn, path):
    conn.request("GET", quote(path, safe="/%?=&"))
    response = conn.getresponse()
    return response.status, response.getheader("Location"), response.getheaders(), response.read()


def snapshot(port):
    with_connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        return fetch(with_connection, "/en/")
    finally:
        with_connection.close()


def await_page(port, predicate):
    for _ in range(20):
        try:
            if predicate(snapshot(port)):
                return
        except (OSError, http.client.HTTPException):
            pass
        time.sleep(1)
    raise RuntimeError("Preview did not serve the expected release")


def release_header(response):
    return {key.lower(): value for key, value in response[2]}.get("x-globewire-release")


def same_page(a, b):
    return (a[0], a[1], release_header(a), a[3]) == (b[0], b[1], release_header(b), b[3])


def check_candidate(release, site, files, redirects):
    conn = http.client.HTTPConnection("127.0.0.1", TEST, timeout=15)
    try:
        for path, relative in files.items():
            status, _, headers, body = fetch(conn, path)
            if status != 200 or body != (site / relative).read_bytes():
                raise RuntimeError(f"Candidate file failed: HTTP {status} {path}")
            header = {name.lower(): value for name, value in headers}
            if header.get("x-globewire-release") != release or header.get("x-robots-tag") != "noindex":
                raise RuntimeError(f"Candidate release headers failed: {path}")
        for path, (target, expected) in redirects.items():
            status, location, _, _ = fetch(conn, path)
            if status != int(expected) or location != target:
                raise RuntimeError(f"Candidate redirect failed: HTTP {status} {path} -> {location}")
        status, location, _, _ = fetch(conn, "/?preview=1")
        if (status, location) != (301, "/en/?preview=1"):
            raise RuntimeError("Candidate redirect lost its query string")
        if fetch(conn, "/missing-oracle-deploy-check")[0] != 404:
            raise RuntimeError("Candidate did not return 404 for an unknown path")
    finally:
        conn.close()
    print(f"CANDIDATE PASSED: {len(files)} files, {len(redirects)} redirects", flush=True)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run as root so nginx can be reloaded after verification")
    if shutil.disk_usage("/var/www").free < 4 * 1024**3:
        raise SystemExit("Less than 4 GiB free; preview kept in place")
    original = ACTIVE.read_bytes()
    old = snapshot(PREVIEW)
    if old[0] != 200 or CANDIDATE.exists():
        raise SystemExit("Expected a working preview and an unused candidate configuration")
    old_urls, old_redirects = read_routes(HOME / "globewire-latest/build")
    git(CHECKOUT, "-c", "pack.threads=1", "fetch", "--depth=40", REPO, "refs/heads/main")
    source = git(CHECKOUT, "rev-parse", "FETCH_HEAD", capture=True).strip()
    git(CHECKOUT, "cat-file", "-e", f"{MIGRATION}^{{commit}}")
    release = hashlib.sha256(f"{source}:{MIGRATION}".encode()).hexdigest()[:20]
    if release_header(old) == release:
        print(f"PREVIEW ALREADY CURRENT: {release}", flush=True)
        return

    work = Path(run("mktemp", "-d", str(HOME / "globewire-managed-build.XXXXXX"), capture=True, user=True).stdout.strip())
    try:
        git(CHECKOUT, "worktree", "add", "--detach", work, source)
        git(work, "-c", "user.name=GlobeWire Oracle Preview", "-c", "user.email=preview@localhost", "merge", "--no-edit", MIGRATION)
        epoch = git(work, "log", "-1", "--format=%ct", source, capture=True).strip()
        run("env", f"SOURCE_DATE_EPOCH={epoch}", PYTHON, "scripts/build.py", "--render-only", user=True, cwd=work)
        files, redirects = read_routes(work / "build")
        baseline = json.loads((work / "content/published-url-inventory.json").read_text())["urls"]
        missing = (old_urls.keys() | old_redirects.keys() | set(baseline)) - (files.keys() | redirects.keys())
        if missing:
            raise RuntimeError(f"Build lost {len(missing)} old URLs: {sorted(missing)[:10]}")
        RELEASES.mkdir(mode=0o755, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix=f"{release}-", dir=RELEASES))
        directory.chmod(0o755)
        site = directory / "site"
        shutil.copytree(work / "build/rendered", site)
    finally:
        if (work / ".git").is_file():
            git(CHECKOUT, "worktree", "remove", "--force", work)
        elif work.is_dir():
            work.rmdir()

    try:
        expected = (site / files["/en/"]).read_bytes()

        def is_new(response):
            return response[0] == 200 and response[3] == expected and release_header(response) == release

        atomic_write(CANDIDATE, config(TEST, release, site, redirects))
        reload_nginx()
        await_page(TEST, is_new)
        check_candidate(release, site, files, redirects)

        atomic_write(ACTIVE, config(PREVIEW, release, site, redirects))
        reload_nginx()
        await_page(PREVIEW, is_new)
        atomic_write(ACTIVE, original)
        reload_nginx()
        await_page(PREVIEW, lambda response: same_page(response, old))
        print("ROLLBACK CHECK PASSED", flush=True)

        atomic_write(ACTIVE, config(PREVIEW, release, site, redirects))
        CANDIDATE.unlink()
        reload_nginx()
        await_page(PREVIEW, is_new)
        print(f"ORACLE AUTOMATED PREVIEW DEPLOY PASSED: main={source} release={release}", flush=True)
    except (Exception, KeyboardInterrupt):
        atomic_write(ACTIVE, original)
        CANDIDATE.unlink(missing_ok=True)
        reload_nginx()
        await_page(PREVIEW, lambda response: same_page(response, old))
        print("PREVIOUS PREVIEW RESTORED", flush=True)
        raise


def stop(_signum, _frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    with open("/run/lock/globewire-oracle-preview.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
