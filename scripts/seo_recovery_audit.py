#!/usr/bin/env python3
"""Read-only, resumable SEO audit. Never edits articles, URLs, or deployment files."""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

SITE = "https://globewiredaily.org"
class Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canon = []
        self.alt = {}
        self.robots = ""
        self.title = ""
        self.desc = ""
        self.ld = []
        self._tag = None
        self._buf = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and a.get("rel") == "canonical":
            self.canon.append(a.get("href", ""))
        if tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.alt[a["hreflang"]] = a.get("href", "")
        if tag == "meta" and a.get("name", "").lower() == "robots":
            self.robots = a.get("content", "")
        if tag == "meta" and a.get("name", "").lower() == "description":
            self.desc = a.get("content", "")
        if tag in ("title", "script"):
            if tag == "title" or a.get("type") == "application/ld+json":
                self._tag, self._buf = tag, []
    def handle_data(self, data):
        if self._tag:
            self._buf.append(data)
    def handle_endtag(self, tag):
        if self._tag == tag:
            value = "".join(self._buf)
            if tag == "title":
                self.title = value.strip()
            else:
                try:
                    self.ld.append(json.loads(value))
                except (ValueError, TypeError):
                    self.ld.append(None)
            self._tag = None

def nodes(value):
    if isinstance(value, list):
        for v in value:
            yield from nodes(v)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from nodes(value["@graph"])

def audit(out, max_pages=0):
    issues = []
    counts = Counter()
    paths = sorted(out.rglob("index.html"))
    if max_pages:
        paths = paths[:max_pages]
    for path in paths:
        rel = path.relative_to(out).as_posix()
        url = SITE + "/" + rel.removesuffix("index.html")
        try:
            data = path.read_text(encoding="utf-8")
            head = Head()
            head.feed(data.split("</head>", 1)[0])
        except (OSError, UnicodeError, ValueError) as exc:
            issues.append({"url": url, "issue": "unreadable_html", "detail": str(exc)})
            continue
        counts["html"] += 1
        redirect = 'http-equiv="refresh"' in data[:3000].lower()
        if redirect or "noindex" in head.robots.lower():
            counts["excluded"] += 1
            continue
        counts["indexable"] += 1
        if head.canon != [url]:
            issues.append({"url": url, "issue": "canonical", "detail": head.canon})
        if not head.title:
            issues.append({"url": url, "issue": "missing_title"})
        if not head.desc:
            issues.append({"url": url, "issue": "missing_description"})
        if rel.startswith(("en/", "hi/")):
            lang = rel[:2]
            if head.alt.get(lang) != url:
                issues.append({"url": url, "issue": "self_hreflang", "detail": head.alt.get(lang)})
            for code, target in head.alt.items():
                if code not in ("en", "hi", "x-default") or not target.startswith(SITE + "/"):
                    issues.append({"url": url, "issue": "invalid_hreflang", "detail": [code, target]})
        if "/news/" in url and not re.search(r'<nav[^>]*|BreadcrumbList', data, re.I):
            issues.append({"url": url, "issue": "missing_breadcrumb"})
        if "/news/" in url and not any(
            n.get("@type") in ("NewsArticle", "Article")
            for ld in head.ld for n in nodes(ld)
        ):
            issues.append({"url": url, "issue": "missing_article_schema"})
    sitemap = out / "sitemap.xml"
    if sitemap.exists():
        try:
            root = ET.parse(sitemap).getroot()
            locs = [x.text for x in root.iter() if x.tag.endswith("}loc") or x.tag == "loc"]
            counts["sitemap_urls"] = len(locs)
            if len(locs) != len(set(locs)):
                issues.append({"issue": "duplicate_sitemap_urls"})
            for loc in locs:
                if not loc or not loc.startswith(SITE + "/"):
                    issues.append({"issue": "off_domain_sitemap_url", "detail": loc})
        except ET.ParseError as exc:
            issues.append({"issue": "invalid_sitemap", "detail": str(exc)})
    else:
        issues.append({"issue": "missing_sitemap"})
    redirects = out / "_redirects"
    if redirects.exists():
        lines = [x for x in redirects.read_text().splitlines() if x.strip() and not x.startswith("#")]
        counts["redirect_rules"] = len(lines)
        if len(lines) > 2000:
            issues.append({"issue": "cloudflare_redirect_limit", "detail": len(lines)})
    news = out / "news-sitemap.xml"
    if news.exists():
        try:
            ET.parse(news)
            counts["news_sitemap_valid"] = 1
        except ET.ParseError as exc:
            issues.append({"issue": "invalid_news_sitemap", "detail": str(exc)})
    else:
        issues.append({"issue": "missing_news_sitemap"})
    return {"counts": dict(counts), "issues": issues[:1000], "issue_total": len(issues)}

def gsc_opportunities(csv_path):
    """Optional GSC Pages export; no fabricated impressions or CTR."""
    if not csv_path:
        return []
    opportunities = []
    with open(csv_path, encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            try:
                url = row.get("Top pages") or row.get("Page") or row.get("Pages") or ""
                impressions = int(str(row.get("Impressions", "0")).replace(",", ""))
                clicks = int(str(row.get("Clicks", "0")).replace(",", ""))
                ctr = clicks / impressions if impressions else 0
                if url.startswith(SITE + "/") and impressions >= 100 and ctr < .03:
                    opportunities.append({"url": url, "impressions": impressions, "clicks": clicks, "ctr": round(ctr, 4)})
            except (ValueError, TypeError):
                continue
    return sorted(opportunities, key=lambda x: x["impressions"], reverse=True)[:200]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dist", default="dist")
    p.add_argument("--report", default="seo-recovery-report.json")
    p.add_argument("--gsc-pages")
    p.add_argument("--max-pages", type=int, default=0)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    dist = Path(args.dist)
    if not dist.is_dir():
        p.error("Build directory missing; run build before audit")
    report = audit(dist, args.max_pages)
    report["gsc_low_ctr_pages"] = gsc_opportunities(args.gsc_pages)
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"counts": report["counts"], "issues": report["issue_total"], "gsc_opportunities": len(report["gsc_low_ctr_pages"])}))
    if args.strict and report["issue_total"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
