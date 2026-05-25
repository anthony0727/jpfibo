from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXTRACTED = REPO / "data" / "edinet" / "extracted"


def _files() -> list[Path]:
    return sorted(EXTRACTED.glob("*.json"))


def test_dei_metadata_present() -> None:
    files = _files()
    if not files:
        pytest.skip("no extracted EDINET filings")
    for p in files:
        d = json.loads(p.read_text())
        for k in ("edinet_code", "filer_name_ja", "fy_start", "fy_end", "document_type"):
            assert d["dei"].get(k), f"{p.name} missing DEI.{k}"


def test_at_least_one_text_block() -> None:
    files = _files()
    if not files:
        pytest.skip("no extracted EDINET filings")
    for p in files:
        d = json.loads(p.read_text())
        assert any(d["text_blocks"].values()), f"{p.name} has no text blocks"
