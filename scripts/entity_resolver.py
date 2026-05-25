"""Entity resolver against registry/entities.yaml.

Returns a stable J-FIBO entity URN when a disclosed name (with arbitrary
trustee-suffix noise) matches a registered alias; falls back to a SHA-1
hash URN otherwise. The resolver is intentionally conservative: when an
alias appears as a substring of a disclosed name we prefer the longer
match.
"""
from __future__ import annotations

import functools
import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
ENTITIES = REPO / "registry" / "entities.yaml"

ENTITY_BASE = "urn:jpfibo:entity:"
JCN_BASE = "https://w3id.org/jpfibo/entity/jcn/"
FALLBACK_BASE = "urn:jpfibo:issuer-fallback:"

TRUSTEE_SUFFIXES = ["（信託口）", "(信託口)", "信託口", "（証券口）"]


@functools.lru_cache(maxsize=1)
def _registry() -> list[dict[str, Any]]:
    return yaml.safe_load(ENTITIES.read_text())["entities"]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def resolve(name: str) -> tuple[str, str]:
    """Return (iri, source) where source is 'jcn' or 'fallback'."""
    if not name:
        return _fallback(name), "fallback"
    needle = _norm(name)
    best: dict[str, Any] | None = None
    best_len = 0
    for entity in _registry():
        candidates = [entity["labels"]["ja"]] + entity.get("aliases", [])
        for alias in candidates:
            alias_n = _norm(alias)
            if not alias_n:
                continue
            if alias_n in needle or needle in alias_n:
                if len(alias_n) > best_len:
                    best = entity
                    best_len = len(alias_n)
    if best is not None:
        return f"{JCN_BASE}{best['jcn']}", "jcn"
    return _fallback(name), "fallback"


def _fallback(name: str) -> str:
    canonical = _norm(name)
    h = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{FALLBACK_BASE}{h}"
