"""Semantic-loss benchmark.

Given a controlled set of benchmark cases describing real Japanese finance
disclosures, compute coverage metrics for vanilla FIBO vs. J-FIBO mappings.

Each case YAML must include:
  expected_semantic_fields:    [list of named semantic fields]
  vanilla_fibo_mapping:
    primary_class:             str (FIBO/Commons QName)
    represents:                [subset of expected fields]
    cannot_represent_without_extension: [subset of expected fields]
  jfibo_mapping:
    primary_class:             str (J-FIBO QName)
    represents:                [subset of expected fields]

Metrics (per case):
  vanilla_coverage      = |vanilla.represents| / |expected|
  jfibo_coverage        = |jfibo.represents|   / |expected|
  semantic_loss_rate    = |vanilla.cannot_represent_without_extension| / |expected|
  jfibo_gain            = max(0, jfibo_coverage - vanilla_coverage)
  evidence_traceability = 1.0 if every represented field carries an evidence
                          locator (we require 'evidence_locator' field for full
                          score, partial credit otherwise)

Cohort metrics are arithmetic means.

Run:
    uv run python benchmark/semantic_loss.py
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
CASES_DIR = REPO / "benchmark" / "cases"
RESULTS_DIR = REPO / "benchmark" / "results"


def _ratio(num: int, den: int) -> float:
    return float(num) / float(den) if den else 0.0


@dataclass
class CaseMetrics:
    id: str
    domain: str
    expected: int
    vanilla_represents: int
    vanilla_missing: int
    jfibo_represents: int
    vanilla_coverage: float
    jfibo_coverage: float
    semantic_loss_rate: float
    jfibo_gain: float
    evidence_traceability: float
    information_boundary_marked: bool


def compute_case(case: dict[str, Any]) -> CaseMetrics:
    expected = set(case["expected_semantic_fields"])
    vanilla = case["vanilla_fibo_mapping"]
    jfibo = case["jfibo_mapping"]

    vrep = set(vanilla.get("represents", [])) & expected
    vmiss = set(vanilla.get("cannot_represent_without_extension", [])) & expected
    jrep = set(jfibo.get("represents", [])) & expected

    evidence_traceability = 1.0 if "evidence_locator" in jrep else 0.0
    info_marked = any(f.startswith("information_status") for f in jrep)

    return CaseMetrics(
        id=case["id"],
        domain=case["domain"],
        expected=len(expected),
        vanilla_represents=len(vrep),
        vanilla_missing=len(vmiss),
        jfibo_represents=len(jrep),
        vanilla_coverage=_ratio(len(vrep), len(expected)),
        jfibo_coverage=_ratio(len(jrep), len(expected)),
        semantic_loss_rate=_ratio(len(vmiss), len(expected)),
        jfibo_gain=max(0.0, _ratio(len(jrep), len(expected)) - _ratio(len(vrep), len(expected))),
        evidence_traceability=evidence_traceability,
        information_boundary_marked=info_marked,
    )


def cohort_summary(metrics: list[CaseMetrics]) -> dict[str, Any]:
    return {
        "cases": len(metrics),
        "mean_vanilla_coverage": statistics.fmean(m.vanilla_coverage for m in metrics),
        "mean_jfibo_coverage": statistics.fmean(m.jfibo_coverage for m in metrics),
        "mean_semantic_loss_rate": statistics.fmean(m.semantic_loss_rate for m in metrics),
        "mean_jfibo_gain": statistics.fmean(m.jfibo_gain for m in metrics),
        "share_with_evidence_traceability": statistics.fmean(m.evidence_traceability for m in metrics),
        "share_with_information_boundary_marked": statistics.fmean(
            1.0 if m.information_boundary_marked else 0.0 for m in metrics
        ),
        "by_domain": _by_domain(metrics),
    }


def _by_domain(metrics: list[CaseMetrics]) -> dict[str, dict[str, float]]:
    out: dict[str, list[CaseMetrics]] = {}
    for m in metrics:
        out.setdefault(m.domain, []).append(m)
    return {
        d: {
            "cases": len(ms),
            "mean_vanilla_coverage": statistics.fmean(m.vanilla_coverage for m in ms),
            "mean_jfibo_coverage": statistics.fmean(m.jfibo_coverage for m in ms),
            "mean_jfibo_gain": statistics.fmean(m.jfibo_gain for m in ms),
        }
        for d, ms in sorted(out.items())
    }


def load_cases(cases_dir: Path = CASES_DIR) -> list[dict[str, Any]]:
    cases = []
    for p in sorted(cases_dir.glob("*.yaml")):
        case = yaml.safe_load(p.read_text())
        case["_path"] = str(p.relative_to(REPO))
        cases.append(case)
    return cases


def run(cases_dir: Path = CASES_DIR, results_dir: Path = RESULTS_DIR) -> dict[str, Any]:
    cases = load_cases(cases_dir)
    metrics = [compute_case(c) for c in cases]
    summary = {
        "cases": [asdict(m) for m in metrics],
        "cohort": cohort_summary(metrics),
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    out = results_dir / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _fmt(v: float) -> str:
    return f"{v:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases-dir", type=Path, default=CASES_DIR)
    ap.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = ap.parse_args()
    summary = run(args.cases_dir, args.results_dir)

    print("J-FIBO semantic-loss benchmark")
    print("=" * 48)
    print(f"cases:                            {summary['cohort']['cases']}")
    print(f"mean vanilla FIBO coverage:       {_fmt(summary['cohort']['mean_vanilla_coverage'])}")
    print(f"mean J-FIBO coverage:             {_fmt(summary['cohort']['mean_jfibo_coverage'])}")
    print(f"mean semantic-loss rate:          {_fmt(summary['cohort']['mean_semantic_loss_rate'])}")
    print(f"mean J-FIBO gain:                 {_fmt(summary['cohort']['mean_jfibo_gain'])}")
    print(f"share w/ evidence traceability:   {_fmt(summary['cohort']['share_with_evidence_traceability'])}")
    print(f"share w/ info-boundary marked:    {_fmt(summary['cohort']['share_with_information_boundary_marked'])}")
    print()
    print("by domain:")
    for d, v in summary["cohort"]["by_domain"].items():
        print(f"  {d}: cases={v['cases']} vanilla={_fmt(v['mean_vanilla_coverage'])} jfibo={_fmt(v['mean_jfibo_coverage'])} gain={_fmt(v['mean_jfibo_gain'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
