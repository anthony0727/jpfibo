"""Parse the 借入金等明細表 text block into structured borrowings rows.

Source:
    data/edinet/extracted/<docID>.json["text_blocks"]["borrowings_schedule_fs_text"]
    or                                 ["borrowings_schedule_consolidated_text"]

Output:
    data/edinet/borrowings/<docID>.json
    {
      "doc_id": "...",
      "edinet_code": "...",
      "filer_name_ja": "...",
      "kind": "consolidated" | "fs",
      "rows": [
        {
          "row_index": 0,
          "class_label_ja": "借入金",
          "opening_balance_million_jpy": 25955961,
          "closing_balance_million_jpy": 22101954,
          "average_rate_percent": 0.68,
          "repayment_deadline_ja": "2024年 1月～ 2051年 10月",
          "unit_label_ja": "百万円",
          "rate_unit_label_ja": "％"
        },
        ...
      ],
      "commercial_paper": [ ... same schema, classified separately ... ],
      "source_text_chars": 807
    }

The parser is deliberately conservative. We:
  * accept either the consolidated or unconsolidated text block;
  * tokenize the cells using the wide-character punctuation/spaces EDINET
    uses verbatim (do not normalize);
  * recognise lines whose first cell appears in a curated label list
    (借入金, 借用金, 再割引手形, リース債務, 短期借入金, 長期借入金,
    1年以内に返済予定の長期借入金, コマーシャル・ペーパー, etc.).
  * pull two numeric cells (opening / closing balance) and one
    percentage cell when present;
  * keep the verbatim 区分 string as ``class_label_ja`` for joinback;
  * classify "コマーシャル・ペーパー" rows into a separate list so they
    feed CommercialPaperClaim rather than BorrowingsClaim.

Anything unparseable is dropped with a warning; the input is preserved
on disk so a future stricter parser can re-run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EXTRACTED_DIR = REPO / "data" / "edinet" / "extracted"
BORROWINGS_DIR = REPO / "data" / "edinet" / "borrowings"

# Recognized 区分 labels. The disclosed text usually contains a small handful
# of these per filing; we list the common ones and accept any line whose
# first cell starts with one of them.
BORROWINGS_LABELS = [
    "短期借入金",
    "1年以内に返済予定の長期借入金",
    "１年以内に返済予定の長期借入金",
    "長期借入金",
    "借入金",
    "借用金",          # bank-industry borrowings
    "再割引手形",
    "リース債務",
    "社債",
]
CP_LABELS = [
    "コマーシャル・ペーパー",
    "コマーシャルペーパー",
]

# Numeric cell: digits with optional thousands separators
NUM = re.compile(r"-?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?")
PCT = re.compile(r"-?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?")


def _to_number(s: str) -> float | int | None:
    if s is None:
        return None
    s = s.replace(",", "")
    if not s:
        return None
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return None


def _split_after_label(label: str, line: str) -> list[str]:
    """Return cells after the label, splitting on whitespace runs (including
    full-width spaces). Empty cells are dropped."""
    tail = line[len(label):]
    parts = [p for p in re.split(r"[\s\u3000]+", tail.strip()) if p]
    return parts


def parse_text_block(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (borrowings_rows, commercial_paper_rows)."""
    borrowings: list[dict[str, Any]] = []
    cp: list[dict[str, Any]] = []
    # Split on \u3000 (ideographic space) and ordinary newlines/whitespace runs.
    # The XBRL textBlock is one long line; we split aggressively on whitespace
    # then look for marker labels.
    # Strategy: walk through known labels in order of length (longest first)
    # so "1年以内に返済予定の長期借入金" wins over "長期借入金".
    labels_sorted = sorted(BORROWINGS_LABELS + CP_LABELS, key=len, reverse=True)

    pos = 0
    while pos < len(text):
        next_hit_label: str | None = None
        next_hit_pos = len(text)
        for label in labels_sorted:
            hit = text.find(label, pos)
            if hit != -1 and hit < next_hit_pos:
                next_hit_pos = hit
                next_hit_label = label
        if next_hit_label is None:
            break
        # Capture a chunk after the label up to the next label or 200 chars.
        chunk_start = next_hit_pos + len(next_hit_label)
        # Find the next label hit to bound this chunk.
        further_hit = len(text)
        for label in labels_sorted:
            h = text.find(label, chunk_start)
            if h != -1 and h < further_hit:
                further_hit = h
        chunk_end = min(further_hit, chunk_start + 240)
        tail = text[chunk_start:chunk_end]
        # Try to pull two numbers (opening, closing) and an optional rate.
        nums = NUM.findall(tail)
        # Drop trivial year numbers like 2024, 2051 that follow 返済期限.
        # Heuristic: opening/closing balances are typically >= 1000.
        big = [n for n in nums if _to_number(n.replace(",", "")) and abs(_to_number(n.replace(",", ""))) >= 1000]
        opening = closing = avg_rate = None
        if len(big) >= 2:
            opening = _to_number(big[0])
            closing = _to_number(big[1])
        # Average rate: look for a small (<100) decimal number that is NOT a year.
        for n in nums:
            v = _to_number(n)
            if v is None or v >= 100 or v == 0:
                continue
            if "." in n:
                avg_rate = v
                break
        # Deadline: the trailing part often contains "YYYY年 M月～ YYYY年 M月".
        deadline = None
        m = re.search(r"(\d{4})\s*年\s*\d{1,2}\s*月\s*[～~〜\-]\s*(\d{4})\s*年\s*\d{1,2}\s*月", tail)
        if m:
            deadline = m.group(0).strip()

        row = {
            "row_index": len(borrowings) + len(cp),
            "class_label_ja": next_hit_label,
            "opening_balance_million_jpy": opening,
            "closing_balance_million_jpy": closing,
            "average_rate_percent": avg_rate,
            "repayment_deadline_ja": deadline,
            "unit_label_ja": "百万円",
            "rate_unit_label_ja": "％",
        }
        # Drop rows that carry no numeric content — these are echoes of
        # the same label inside narrative footnotes, not separate disclosure rows.
        empty = (opening is None) and (closing is None) and (avg_rate is None)
        if not empty:
            if next_hit_label in CP_LABELS:
                cp.append(row)
            else:
                borrowings.append(row)
        pos = chunk_end

    return borrowings, cp


def process(doc_id: str) -> dict[str, Any] | None:
    src = EXTRACTED_DIR / f"{doc_id}.json"
    if not src.exists():
        print(f"skip {doc_id}: no extracted facts at {src}", file=sys.stderr)
        return None
    data = json.loads(src.read_text())
    tbs = data.get("text_blocks", {})
    # Prefer consolidated (the bank/holdco form) if present; else fs.
    kind = None
    text = None
    for key in ("borrowings_schedule_consolidated_text", "borrowings_schedule_fs_text"):
        rows = tbs.get(key) or []
        for r in rows:
            t = r.get("text") or ""
            if t.strip():
                text = t
                kind = "consolidated" if "consolidated" in key else "fs"
                break
        if text:
            break
    if not text:
        # Nothing disclosed (common for non-banks with no borrowings schedule).
        return None

    borrowings, cp = parse_text_block(text)
    out = {
        "doc_id": doc_id,
        "edinet_code": data.get("dei", {}).get("edinet_code"),
        "filer_name_ja": (data.get("dei", {}).get("filer_name_ja") or {}).get("value")
                        if isinstance(data.get("dei", {}).get("filer_name_ja"), dict)
                        else data.get("dei", {}).get("filer_name_ja"),
        "kind": kind,
        "rows": borrowings,
        "commercial_paper": cp,
        "source_text_chars": len(text),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", action="append", help="docID(s) to parse (default: all in extracted/)")
    args = ap.parse_args()

    BORROWINGS_DIR.mkdir(parents=True, exist_ok=True)
    if args.doc:
        targets = args.doc
    else:
        targets = sorted(p.stem for p in EXTRACTED_DIR.glob("*.json"))

    summary = []
    for doc_id in targets:
        out = process(doc_id)
        if out is None:
            print(f"{doc_id}: no borrowings schedule disclosed")
            continue
        dest = BORROWINGS_DIR / f"{doc_id}.json"
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=2))
        summary.append((doc_id, len(out["rows"]), len(out["commercial_paper"])))
        print(f"{doc_id}: borrowings={len(out['rows'])} commercial_paper={len(out['commercial_paper'])} -> {dest.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
