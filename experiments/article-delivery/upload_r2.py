#!/usr/bin/env python3
"""Safe, resumable article HTML copy from dist to private R2. Never deletes local or remote objects."""
import argparse
import hashlib
import json
import os
from pathlib import Path

def articles(root):
    for lang in ("en", "hi"):
        for p in sorted((root / lang / "news").glob("*/*/index.html")):
            if p.is_file():
                yield p.relative_to(root).as_posix(), p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--manifest", default="article-r2-manifest.json")
    ap.add_argument("--upload", action="store_true", help="Explicit opt-in; default is dry run")
    ap.add_argument("--verify", action="store_true", help="HEAD check every object after upload")
    args = ap.parse_args()
    root = Path(args.dist).resolve()
    if not root.is_dir():
        ap.error("dist directory missing; build site first")
    entries = []
    for key, path in articles(root):
        data = path.read_bytes()
        if b"<html" not in data.lower() or b"</html" not in data.lower():
            raise ValueError(f"Not valid HTML: {key}")
        entries.append({"key":key, "sha256":hashlib.sha256(data).hexdigest(), "bytes":len(data)})
    if not entries:
        raise SystemExit("No articles found; refusing empty upload")
    Path(args.manifest).write_text(json.dumps({"count":len(entries),"files":entries},indent=2)+"\n")
    print(f"Manifest: {len(entries)} article HTML files; bytes={sum(e['bytes'] for e in entries)}")
    if not args.upload:
        print("DRY RUN ONLY: no remote writes. Pass --upload to copy.")
        return
    try:
        import boto3
    except ImportError:
        raise SystemExit("Install boto3 before --upload")
    account = os.environ["CF_ACCOUNT_ID"]
    bucket = os.environ["R2_BUCKET"]
    client = boto3.client("s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],region_name="auto")
    copied = skipped = 0
    for entry in entries:
        key = entry["key"]
        try:
            old = client.head_object(Bucket=bucket,Key=key)
            if old.get("Metadata",{}).get("sha256") == entry["sha256"]:
                skipped += 1
                continue
        except client.exceptions.ClientError as ex:
            if ex.response.get("ResponseMetadata",{}).get("HTTPStatusCode") != 404:
                raise
        client.put_object(Bucket=bucket,Key=key,Body=(root/key).read_bytes(),
            ContentType="text/html; charset=utf-8",CacheControl="public, max-age=60, s-maxage=300",
            Metadata={"sha256":entry["sha256"]})
        copied += 1
    print(f"Uploaded={copied} unchanged={skipped} total={len(entries)}")
    if args.verify:
        for entry in entries:
            head = client.head_object(Bucket=bucket,Key=entry["key"])
            if head.get("Metadata",{}).get("sha256") != entry["sha256"]:
                raise RuntimeError(f"Verification failed: {entry['key']}")
        print("Verified all manifest keys")

if __name__ == "__main__":
    main()
