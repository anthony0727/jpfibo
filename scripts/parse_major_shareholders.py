"""Parse MajorShareholders table from extracted EDINET JSON into structured rows.

EDINET reports the major-shareholders disclosure as an iXBRL HTML table inside
a single text-block fact. We preserve the inner HTML at extraction time
(scripts/extract_xbrl_facts.py) so we can parse the table cells here without
heuristics on collapsed whitespace.

Output: ``data/edinet/major_shareholders/<docID>.json``::

    {
      "doc_id": "...",
      "edinet_code": "E02144",
      "filer_name_ja": "...",
      "fy_end": "2025-03-31",
      "rows": [
        {"rank": 1, "name": "...", "address": "...", "shares": 1805605000,
         "shares_unit": "shares", "ownership_pct": 13.84,
         "holder_role": "Trustee"},
        ...
      ],
      "shares_unit": "shares"  # already normalized
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from lxml import html as lh

REPO = Path(__file__).resolve().parents[1]
EXTRACTED = REPO / "data" / "edinet" / "extracted"
OUT_DIR = REPO / "data" / "edinet" / "major_shareholders"

HEADER_KEYS = ("氏名", "名称")
ADDRESS_KEYS = ("住所",)
SHARES_KEYS = ("所有株式数", "保有株式数")
PCT_KEYS = ("割合",)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _parse_int(cell: str) -> int | None:
    if not cell:
        return None
    cell = re.sub(r"[\s,，]", "", cell)
    if not cell or not re.fullmatch(r"\d+", cell):
        return None
    return int(cell)


def _parse_pct(cell: str) -> float | None:
    if not cell:
        return None
    cell = re.sub(r"[\s,，％%]", "", cell)
    try:
        return float(cell)
    except ValueError:
        return None


def _shares_unit_from_header(header: list[str]) -> tuple[str, int]:
    """Inspect header row to determine units. Returns (unit_label, multiplier)."""
    text = "".join(header)
    if "千株" in text:
        return ("shares", 1000)
    if "百株" in text:
        return ("shares", 100)
    return ("shares", 1)


def _classify_holder(name: str, address: str) -> str:
    n = _norm(name)
    if "信託口" in n or "信託銀行" in n:
        return "Trustee"
    if "カストディ銀行" in n:
        return "Trustee"
    if "預託" in n or "DEPOSITARY" in n.upper() or "デポジタリ" in n:
        return "ADRDepositary"
    if "常任代理人" in n or "STATE STREET" in n.upper() or "JP MORGAN" in n.upper() or "BANK OF NEW YORK" in n.upper() or "HSBC" in n.upper() or "BNYM" in n.upper() or "CITIBANK" in n.upper():
        return "CustodyBank"
    if re.search(r"^[一-龥々ヵヶ]{1,4}\s+[一-龥々ヵヶ]{1,4}$", name.strip()):
        return "IndividualShareholder"
    return "RegisteredHolder"


def parse(extracted: dict) -> dict | None:
    blocks = extracted["text_blocks"].get("major_shareholders_text") or []
    if not blocks:
        return None
    html = blocks[0].get("html") or ""
    if not html:
        return None
    try:
        doc = lh.fragment_fromstring(html, create_parent="div")
    except Exception:
        doc = lh.fragment_fromstring(re.sub(r"xmlns:[^=]+=\"[^\"]+\"", "", html), create_parent="div")

    tables = doc.xpath(".//table")
    if not tables:
        return None
    table = tables[0]
    raw_rows = []
    for tr in table.xpath(".//tr"):
        cells = [(c.text_content() or "").strip() for c in tr.xpath(".//td|.//th")]
        if cells:
            raw_rows.append(cells)
    if len(raw_rows) < 2:
        return None
    header_idx = None
    for i, cells in enumerate(raw_rows):
        text = "".join(cells)
        if any(k in text for k in HEADER_KEYS) and any(k in text for k in SHARES_KEYS):
            header_idx = i
            break
    if header_idx is None:
        return None
    header = raw_rows[header_idx]
    unit_label, multiplier = _shares_unit_from_header(header)

    # Map columns by header keywords.
    def find_col(keys: tuple[str, ...]) -> int | None:
        for i, h in enumerate(header):
            for k in keys:
                if k in h:
                    return i
        return None

    name_col = find_col(HEADER_KEYS)
    address_col = find_col(ADDRESS_KEYS)
    shares_col = find_col(SHARES_KEYS)
    pct_col = find_col(PCT_KEYS)
    if name_col is None or shares_col is None:
        return None

    rows: list[dict] = []
    rank = 0
    for cells in raw_rows[header_idx+1:]:
        # Skip footer total rows (label '計') and empty rows.
        first = (cells[0] if cells else "").strip()
        if not first or first in ("計", "合計"):
            continue
        if len(cells) <= max(name_col, shares_col):
            continue
        name = cells[name_col].strip()
        address = cells[address_col].strip() if address_col is not None and address_col < len(cells) else ""
        shares_raw = cells[shares_col].strip() if shares_col < len(cells) else ""
        pct_raw = cells[pct_col].strip() if pct_col is not None and pct_col < len(cells) else ""
        shares = _parse_int(shares_raw)
        if shares is None:
            continue
        shares *= multiplier
        pct = _parse_pct(pct_raw)
        rank += 1
        rows.append({
            "rank": rank,
            "name": name,
            "address": address,
            "shares": shares,
            "shares_unit": unit_label,
            "ownership_pct": pct,
            "holder_role": _classify_holder(name, address),
        })

    return {
        "doc_id": extracted["doc_id"],
        "edinet_code": extracted["dei"]["edinet_code"]["value"],
        "filer_name_ja": extracted["dei"]["filer_name_ja"]["value"],
        "fy_end": extracted["dei"]["fy_end"]["value"],
        "rows": rows,
        "shares_unit": unit_label,
        "shares_multiplier": multiplier,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc_id", nargs="?")
    args = ap.parse_args()
    docs = [args.doc_id] if args.doc_id else sorted(p.stem for p in EXTRACTED.glob("*.json"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for doc_id in docs:
        p = EXTRACTED / f"{doc_id}.json"
        if not p.exists():
            print(f"missing {p}", file=sys.stderr); continue
        ex = json.loads(p.read_text())
        out = parse(ex)
        if out is None:
            print(f"{doc_id}: no MajorShareholders table found", file=sys.stderr); continue
        op = OUT_DIR / f"{doc_id}.json"
        op.write_text(json.dumps(out, ensure_ascii=False, indent=2))
        print(f"{doc_id}: {len(out['rows'])} major-shareholder rows -> {op.relative_to(REPO)}")
        total += len(out["rows"])
    print(f"total rows: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
