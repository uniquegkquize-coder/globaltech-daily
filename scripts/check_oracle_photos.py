"""Check published article photos against the GitHub source Oracle is serving."""
import hashlib
import io
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from PIL import Image

SITE = "https://globewiredaily.org"
MIGRATION = "e19ff8aa03bb1237450d77493466739cca6c4ca7"
CONFIG_VERSION = "2"
PHOTO_KINDS = {
    "licensed_photo", "publisher_source", "source_original", "manual_original", "licensed_source"
}


def git(*args):
    return subprocess.check_output(["git", *args])


def get(url):
    response = requests.get(url, timeout=(5, 20))
    response.raise_for_status()
    return response


def deployed_source(release):
    for sha in git("log", "-60", "--format=%H", "--first-parent").decode().splitlines():
        release_key = f"{sha}:{MIGRATION}:{CONFIG_VERSION}".encode()
        if hashlib.sha256(release_key).hexdigest()[:20] == release:
            return sha
    raise RuntimeError(f"Oracle release {release!r} does not match recent main history")


def published_articles():
    pending = [f"{SITE}/sitemap.xml"]
    seen = set()
    routes = {}
    while pending:
        url = pending.pop()
        if url in seen:
            continue
        if urlsplit(url).netloc != urlsplit(SITE).netloc:
            raise ValueError(f"Unexpected sitemap host: {url}")
        seen.add(url)
        tree = ET.fromstring(get(url).content)
        links = [node.text.strip() for node in tree.findall("./*/{*}loc") if node.text]
        if tree.tag.endswith("sitemapindex"):
            pending.extend(links)
            continue
        for link in links:
            if not link.startswith(f"{SITE}/en/news/"):
                continue
            match = re.search(r"-([a-f0-9]{10})/?$", urlsplit(link).path)
            if match:
                routes[match[1]] = link
    return routes


def deployed_photos(sha, articles):
    featured = git("ls-tree", "-r", "--name-only", sha, "--", "content/featured").decode().splitlines()
    available = set(featured)
    recent = git("log", "-20", "--format=", "--name-only", sha, "--", "content/featured").decode().splitlines()
    for path in dict.fromkeys(recent + featured):
        if path not in available or not path.endswith(".json"):
            continue
        ident = PurePosixPath(path).stem
        image = f"content/featured/{ident}.jpg"
        if ident[:10] not in articles or image not in available:
            continue
        metadata = json.loads(git("show", f"{sha}:{path}"))
        if not isinstance(metadata, dict) or metadata.get("kind") not in PHOTO_KINDS:
            continue
        if str(metadata.get("review_status", "")).lower() in {"replace", "rejected", "needs_replacement"}:
            continue
        yield articles[ident[:10]], metadata, git("show", f"{sha}:{image}")


def verify(url, metadata, expected, release):
    page = get(url)
    if page.headers.get("x-globewire-release") != release:
        raise ValueError("Oracle release changed during the audit")
    soup = BeautifulSoup(page.content, "html.parser")
    hero = soup.select_one("img.hero")
    social = soup.select_one('meta[property="og:image"]')
    if not hero or not hero.get("alt") or (hero.get("width"), hero.get("height")) != ("1280", "720"):
        raise ValueError("Missing hero photo attributes")
    image_url = urljoin(url, hero["src"])
    if not social or social.get("content") != image_url:
        raise ValueError("Hero and social image URLs differ")
    image = get(image_url).content
    if image != expected:
        raise ValueError("Live photo bytes differ from the deployed source")
    with Image.open(io.BytesIO(image)) as photo:
        if (photo.format, photo.size) != ("JPEG", (1280, 720)):
            raise ValueError("Unexpected photo format or dimensions")
    if metadata.get("source_image") not in {link["href"] for link in soup.select("a[href]")}:
        raise ValueError("Photo source credit is missing")
    license_name = metadata.get("license_name")
    if license_name and license_name not in soup.get_text(" ", strip=True):
        raise ValueError("Photo license is missing")


def main():
    release = get(f"{SITE}/deployment.json").headers.get("x-globewire-release")
    sha = deployed_source(release)
    print(f"Auditing Oracle release {release} from main commit {sha}", flush=True)
    failures = []
    checked = 0
    for url, metadata, expected in deployed_photos(sha, published_articles()):
        checked += 1
        try:
            verify(url, metadata, expected, release)
            print(f"Verified {url}", flush=True)
        except (requests.RequestException, ValueError, OSError, KeyError) as error:
            failures.append(url)
            print(f"::error::{url}: {error}", flush=True)
        if checked == 12:
            break
    if not checked:
        raise SystemExit("No published photos found for the live release")
    print(f"Verified {checked - len(failures)}/{checked} photos")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
