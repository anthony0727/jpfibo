"""Confirm that the EDINET taxonomy elements cited in benchmark cases and
registry actually exist in the downloaded official taxonomy."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
FOCUS = REPO / "data" / "derived" / "edinet_taxonomy_focus.json"
REGISTRY = REPO / "registry" / "terms.yaml"
CASES = REPO / "benchmark" / "cases"


def _focus_elements() -> set[str]:
    if not FOCUS.exists():
        pytest.skip("edinet_taxonomy_focus.json not present; run scripts/build_edinet_focus.py")
    data = json.loads(FOCUS.read_text())
    return {f"{e['prefix']}:{e['element']}" for e in data["elements"]}


def _qnames_from_registry() -> set[str]:
    registry = yaml.safe_load(REGISTRY.read_text())
    qnames: set[str] = set()
    for term in registry["terms"]:
        for q in term.get("edinet_elements", []):
            qnames.add(q)
    return qnames


def _qnames_from_cases() -> set[str]:
    qnames: set[str] = set()
    for p in CASES.glob("*.yaml"):
        case = yaml.safe_load(p.read_text())
        for q in case.get("edinet_elements", []):
            qnames.add(q)
    return qnames


def test_registry_cited_edinet_elements_in_taxonomy() -> None:
    focus = _focus_elements()
    if not focus:
        pytest.skip("focus list empty; nothing to compare")
    missing = _qnames_from_registry() - focus
    assert not missing, f"registry cites EDINET elements not present in focus list: {missing}"


def test_cases_cited_edinet_elements_in_taxonomy() -> None:
    focus = _focus_elements()
    missing = _qnames_from_cases() - focus
    assert not missing, f"benchmark cases cite EDINET elements not present in focus list: {missing}"
