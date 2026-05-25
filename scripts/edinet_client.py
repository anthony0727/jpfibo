"""Thin client for the EDINET disclosure documents API (v2).

The client deliberately does *not* try to be a full XBRL parser. Its only
responsibilities are:

  1. List documents available for a given date / date range.
  2. Download the raw ZIP archive for a given docID and type.
  3. Cache responses on disk under data/edinet/raw/.

Requires an EDINET subscription key in the environment variable
``EDINET_API_KEY`` (the user can store it in ``~/.env``). The script will
exit cleanly with status 0 and a clear message when the key is missing, so
``uv run`` doesn't fail when the optional credential isn't present.

Reference: https://disclosure2.edinet-fsa.go.jp/weee0040.aspx
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "data" / "edinet" / "raw"
LIST_DIR = REPO / "data" / "edinet" / "lists"

API_BASE = "https://api.edinet-fsa.go.jp/api/v2"
USER_AGENT = "jfibo/0.1 (+https://github.com/) python-requests"


def _key() -> str | None:
    return os.environ.get("EDINET_API_KEY")


def list_documents(date: str, out_dir: Path = LIST_DIR) -> Path | None:
    key = _key()
    if not key:
        print("EDINET_API_KEY not set; skipping list", file=sys.stderr)
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"list-{date}.json"
    if out.exists():
        return out
    r = requests.get(
        f"{API_BASE}/documents.json",
        params={"date": date, "type": 2, "Subscription-Key": key},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    r.raise_for_status()
    out.write_bytes(r.content)
    return out


def download_document(doc_id: str, doc_type: int = 1, out_dir: Path = RAW_DIR) -> Path | None:
    key = _key()
    if not key:
        print("EDINET_API_KEY not set; skipping download", file=sys.stderr)
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = {1: "xbrl.zip", 2: "pdf.pdf", 5: "csv.zip"}[doc_type]
    out = out_dir / f"{doc_id}.{suffix}"
    if out.exists():
        return out
    r = requests.get(
        f"{API_BASE}/documents/{doc_id}",
        params={"type": doc_type, "Subscription-Key": key},
        headers={"User-Agent": USER_AGENT},
        timeout=180,
    )
    r.raise_for_status()
    out.write_bytes(r.content)
    time.sleep(0.5)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p_list = sp.add_parser("list", help="list filings on a given YYYY-MM-DD date")
    p_list.add_argument("date")
    p_get = sp.add_parser("download", help="download docID")
    p_get.add_argument("doc_id")
    p_get.add_argument("--type", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "list":
        p = list_documents(args.date)
        print(p or "(no key; skipped)")
    elif args.cmd == "download":
        p = download_document(args.doc_id, args.type)
        print(p or "(no key; skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
