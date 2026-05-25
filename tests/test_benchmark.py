from __future__ import annotations

from pathlib import Path

from semantic_loss import compute_case, cohort_summary, load_cases, run

REPO = Path(__file__).resolve().parents[1]


def test_cases_load() -> None:
    cases = load_cases()
    assert cases, "no benchmark cases found"
    for c in cases:
        assert {"id", "domain", "expected_semantic_fields", "vanilla_fibo_mapping", "jfibo_mapping"}.issubset(c.keys()), c["id"]


def test_per_case_metrics_invariants() -> None:
    cases = load_cases()
    for c in cases:
        m = compute_case(c)
        assert 0.0 <= m.vanilla_coverage <= 1.0
        assert 0.0 <= m.jfibo_coverage <= 1.0
        assert 0.0 <= m.semantic_loss_rate <= 1.0
        assert m.jfibo_coverage >= m.vanilla_coverage, c["id"]
        assert m.expected > 0, c["id"]


def test_cohort_jfibo_beats_vanilla_on_average() -> None:
    cases = load_cases()
    metrics = [compute_case(c) for c in cases]
    summary = cohort_summary(metrics)
    assert summary["mean_jfibo_coverage"] > summary["mean_vanilla_coverage"] + 0.3
    assert summary["mean_jfibo_gain"] > 0.3


def test_summary_serializes() -> None:
    summary = run()
    out = REPO / "benchmark" / "results" / "summary.json"
    assert out.exists()
    assert summary["cohort"]["cases"] >= 10
