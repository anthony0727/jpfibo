"""Scan EDINET document lists for the user-requested anchor filings.

Targets (by EDINET code):
  Toyota Motor Corp     -> E02144
  Mitsubishi UFJ FG     -> E03606  (holding company)
  SoftBank Group Corp   -> E02778
  Mitsubishi Corp       -> E02497
  Honda Motor Co. Ltd.  -> E02165

For each, we scan back N days and return securities reports (docTypeCode 120).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
LIST_DIR = REPO / "data" / "edinet" / "lists"
USER_AGENT = "jfibo/0.1 (+https://github.com/) python-requests"
API_BASE = "https://api.edinet-fsa.go.jp/api/v2"

TARGETS = {
    "Toyota Motor Corporation": "E02144",
    "Mitsubishi UFJ Financial Group, Inc.": "E03606",
    "SoftBank Group Corp.": "E02778",
    "Mitsubishi Corporation": "E02497",
    "Honda Motor Co., Ltd.": "E02165",
}
SECURITIES_REPORT = "120"


def fetch_day(date: str, key: str) -> dict:
    out = LIST_DIR / f"list-{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return json.loads(out.read_text())
    r = requests.get(
        f"{API_BASE}/documents.json",
        params={"date": date, "type": 2, "Subscription-Key": key},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    r.raise_for_status()
    out.write_bytes(r.content)
    time.sleep(0.3)
    return r.json()


def main() -> int:
    key = os.environ.get("EDINET_API_KEY")
    if not key:
        print("EDINET_API_KEY not set", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=400, help="days back from --end-date")
    ap.add_argument("--end-date", default=None, help="YYYY-MM-DD (defaults to today)")
    ap.add_argument("--doc-type", default=SECURITIES_REPORT, help="EDINET docTypeCode")
    ap.add_argument("--out", type=Path, default=REPO / "data" / "edinet" / "target_filings.json")
    args = ap.parse_args()

    end = dt.date.fromisoformat(args.end_date) if args.end_date else dt.date.today()
    targets_remaining = dict(TARGETS)
    hits: dict[str, list[dict]] = {name: [] for name in TARGETS}

    for i in range(args.days):
        if not targets_remaining:
            break
        date = (end - dt.timedelta(days=i)).isoformat()
        try:
            day = fetch_day(date, key)
        except requests.HTTPError as e:
            print(f"{date}: HTTP {e.response.status_code}", file=sys.stderr)
            continue
        for r in day.get("results", []):
            if r.get("docTypeCode") != args.doc_type:
                continue
            ec = r.get("edinetCode")
            for name, code in list(targets_remaining.items()):
                if ec == code:
                    hits[name].append(r)
                    targets_remaining.pop(name, None)
        if i % 30 == 0:
            print(f"scanned through {date} | remaining: {list(targets_remaining)}", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"targets": TARGETS, "hits": hits}, ensure_ascii=False, indent=2))
    for name, ms in hits.items():
        if ms:
            m = ms[0]
            print(f"FOUND  {name:42s} {m['docID']}  {m['submitDateTime']}  {m['docDescription']}")
        else:
            print(f"MISS   {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
