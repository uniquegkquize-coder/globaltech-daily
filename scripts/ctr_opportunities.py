#!/usr/bin/env python3
"""Prioritize Search Console page-query opportunities from a CSV export.

Input columns: page, query, clicks, impressions, position (optional: date).
No network calls, API keys, or website rebuilds.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def rank(rows, minimum=20):
    grouped = defaultdict(lambda: {"clicks": 0, "impressions": 0, "weighted_position": 0.0, "queries": []})
    for row in rows:
        url = str(row.get("page", "")).strip()
        if url.startswith("https://www.globewiredaily.org/"):
            url = "https://globewiredaily.org/" + url.split("/", 3)[3]
        if not url.startswith("https://globewiredaily.org/") and not url.startswith("https://www.globewiredaily.org/"):
            continue
        try:
            impressions = int(float(row.get("impressions", 0) or 0))
            clicks = int(float(row.get("clicks", 0) or 0))
            position = float(row.get("position", 0) or 0)
        except (TypeError, ValueError):
            continue
        if impressions <= 0 or position <= 0:
            continue
        record = grouped[url]
        record["clicks"] += clicks
        record["impressions"] += impressions
        record["weighted_position"] += position * impressions
        record["queries"].append((impressions, str(row.get("query", ""))))
    result = []
    for url, item in grouped.items():
        n = item["impressions"]
        if n < minimum:
            continue
        position = item["weighted_position"] / n
        ctr = item["clicks"] / n
        if position <= 3:
            group = "top-3"
        elif position <= 10:
            group = "position-4-10"
        elif position <= 20:
            group = "position-11-20"
        else:
            group = "position-21+"
        # Heuristic for review order, not a predicted click uplift.
        score = n * max(0.0, 0.05 - ctr) / max(1.0, position / 5.0)
        result.append({
            "page": url,
            "query": max(item["queries"], default=(0, ""))[1],
            "clicks": item["clicks"],
            "impressions": n,
            "ctr": round(ctr, 5),
            "position": round(position, 2),
            "segment": group,
            "review_score": round(score, 2),
            "status": "needs-editorial-review",
        })
    return sorted(result, key=lambda x: (-x["review_score"], -x["impressions"], x["page"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Search Console page-query CSV")
    parser.add_argument("--output", type=Path, default=Path("ctr-opportunities.json"))
    parser.add_argument("--minimum-impressions", type=int, default=20)
    args = parser.parse_args()
    with args.csv_path.open(encoding="utf-8-sig", newline="") as stream:
        results = rank(csv.DictReader(stream), args.minimum_impressions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CTR review candidates: {len(results)}; output: {args.output}")
    print("Review query intent and actual snippets before changing titles.")


if __name__ == "__main__":
    main()
