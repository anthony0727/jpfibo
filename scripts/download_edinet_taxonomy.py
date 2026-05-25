"""Reproducible EDINET taxonomy fetch.

Downloads:
  * 1c_Taxonomy.zip           -- the XBRL taxonomy (schemas, label/linkbases)
  * 1e_ElementList.xlsx       -- human-readable element list
  * 1f_AccountList.xlsx       -- jpfr-pfs account-line element list

Files are written under data/sources/edinet-taxonomy-<YYYY>/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://www.fsa.go.jp/search/20251111"
DEFAULT_NAMES = ["1c_Taxonomy.zip", "1e_ElementList.xlsx", "1f_AccountList.xlsx"]


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"exists: {dest.relative_to(REPO)}")
        return
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"wrote:  {dest.relative_to(REPO)} ({dest.stat().st_size:,} bytes)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year-tag", default="2026", help="year tag for the local directory")
    ap.add_argument("--base", default=DEFAULT_BASE, help="FSA publication base URL")
    args = ap.parse_args()
    out_dir = REPO / "data" / "sources" / f"edinet-taxonomy-{args.year_tag}"
    for n in DEFAULT_NAMES:
        fetch(f"{args.base}/{n}", out_dir / n)
    print(out_dir.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
