#!/usr/bin/env python3
"""Copy generated site images to R2; never delete remote objects. Dry run by default."""
import argparse
import hashlib
import json
import os
from pathlib import Path

def image_files(root):
    for path in sorted((root / "images").rglob("*")):
        if path.is_file() and path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"):
            yield path.relative_to(root).as_posix(), path

def manifest(root):
    return [{"key":key, "bytes":p.stat().st_size,
             "sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for key,p in image_files(root)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", default="dist")
    parser.add_argument("--manifest", default="r2-image-manifest.json")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(args.dist)
    if not root.is_dir():
        parser.error("Missing dist directory; build the site first")
    entries = manifest(root)
    if not entries:
        raise SystemExit("No images found; refusing empty upload")
    Path(args.manifest).write_text(json.dumps({"count":len(entries), "files":entries},indent=2)+"\n")
    print(f"Images={len(entries)} total_bytes={sum(e['bytes'] for e in entries)}")
    if not args.upload:
        print("Dry run: no remote writes")
        return
    import boto3
    from botocore.exceptions import ClientError
    from mimetypes import guess_type
    client = boto3.client("s3", endpoint_url=f"https://{os.environ['CF_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    bucket = os.environ.get("R2_BUCKET","globewire-media")
    uploaded = skipped = 0
    for entry in entries:
        key = entry["key"]
        try:
            old = client.head_object(Bucket=bucket,Key=key)
            if old.get("Metadata",{}).get("sha256") == entry["sha256"]:
                skipped += 1
                continue
        except ClientError as exc:
            if exc.response.get("ResponseMetadata",{}).get("HTTPStatusCode") != 404:
                raise
        client.put_object(Bucket=bucket,Key=key,Body=(root/key).read_bytes(),
            ContentType=guess_type(key)[0] or "application/octet-stream",
            CacheControl="public, max-age=86400",Metadata={"sha256":entry["sha256"]})
        uploaded += 1
    if args.verify:
        for entry in entries:
            obj = client.head_object(Bucket=bucket,Key=entry["key"])
            if obj.get("Metadata",{}).get("sha256") != entry["sha256"] or obj.get("ContentLength") != entry["bytes"]:
                raise RuntimeError("R2 image verification failed: "+entry["key"])
    print(f"Uploaded={uploaded} skipped={skipped} verified={args.verify}")

if __name__ == "__main__":
    main()
