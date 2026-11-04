#!/usr/bin/env python3
"""Read-only Google Search Console daily CTR audit. No website writes or deployments.

Requires GSC_CLIENT_ID, GSC_CLIENT_SECRET, GSC_REFRESH_TOKEN in environment.
The Google account must have access to GSC_PROPERTY.
"""
import csv
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from ctr_opportunities import rank


def request_json(url, payload, token=None):
    data = json.dumps(payload).encode() if token else urlencode(payload).encode()
    headers = {"Content-Type": "application/json" if token else "application/x-www-form-urlencoded"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, data=data, headers=headers), timeout=45) as response:
        return json.load(response)


def access_token():
    required = ("GSC_CLIENT_ID", "GSC_CLIENT_SECRET", "GSC_REFRESH_TOKEN")
    if any(not os.environ.get(key) for key in required):
        print("GSC credentials unavailable; skipping remote audit without failing publishing.")
        return None
    response = request_json("https://oauth2.googleapis.com/token", {
        "client_id": os.environ["GSC_CLIENT_ID"],
        "client_secret": os.environ["GSC_CLIENT_SECRET"],
        "refresh_token": os.environ["GSC_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    return response["access_token"]


def fetch(token, prop, start, end, dimensions):
    endpoint = "https://www.googleapis.com/webmasters/v3/sites/" + quote(prop, safe="") + "/searchAnalytics/query"
    rows = []
    for offset in range(0, 25000, 25000):
        response = request_json(endpoint, {
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": dimensions, "rowLimit": 25000, "startRow": offset,
            "dataState": "final",
        }, token)
        batch = response.get("rows", [])
        for item in batch:
            record = dict(zip(dimensions, item.get("keys", [])))
            record.update({key: item.get(key) for key in ("clicks", "impressions", "ctr", "position")})
            rows.append(record)
        if len(batch) < 25000:
            break
    return rows


def main():
    token = access_token()
    if not token:
        return
    prop = os.environ.get("GSC_PROPERTY", "sc-domain:globewiredaily.org")
    # Three-day buffer prevents treating fresh/incomplete data as final.
    end = dt.date.today() - dt.timedelta(days=3)
    start = end - dt.timedelta(days=6)
    previous_end = start - dt.timedelta(days=1)
    previous_start = previous_end - dt.timedelta(days=6)
    current = fetch(token, prop, start, end, ["page", "query"])
    previous = fetch(token, prop, previous_start, previous_end, ["date"])
    daily = fetch(token, prop, start, end, ["date"])
    output = Path(os.environ.get("GSC_REPORT_DIR", "/tmp/gsc-ctr-report"))
    output.mkdir(parents=True, exist_ok=True)
    candidates = rank(current, minimum=20)
    (output / "opportunities.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def totals(rows):
        clicks = sum(float(row.get("clicks") or 0) for row in rows)
        impressions = sum(float(row.get("impressions") or 0) for row in rows)
        return {"clicks": round(clicks), "impressions": round(impressions), "ctr": round(clicks / impressions, 5) if impressions else 0}
    summary = {
        "property": prop, "data_state": "final", "window_start": start.isoformat(),
        "window_end": end.isoformat(), "current": totals(daily),
        "previous_window_start": previous_start.isoformat(),
        "previous_window_end": previous_end.isoformat(), "previous": totals(previous),
        "candidates": len(candidates), "note": "Query-level rows may be anonymized or truncated by Google. No automatic article edits."
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
