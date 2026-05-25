from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from rdflib import Graph, Namespace
from rdflib.namespace import RDF

REPO = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO / "data" / "edinet" / "claims"
JPFIBO = Namespace("https://w3id.org/jpfibo/ontology/JP/core/")


def _ttls() -> list[Path]:
    return sorted(p for p in CLAIMS_DIR.glob("*.ttl") if p.stat().st_size > 0)


@pytest.fixture(scope="module")
def materialized() -> list[Path]:
    ttls = _ttls()
    if not ttls:
        pytest.skip("no materialized EDINET claims; run scripts/materialize_claims.py")
    return ttls


def test_real_policy_shareholding_claims_have_required_fields(materialized: list[Path]) -> None:
    nonempty = 0
    for ttl in materialized:
        g = Graph().parse(ttl)
        for claim in g.subjects(RDF.type, JPFIBO.PolicyShareholding):
            assert g.value(claim, JPFIBO.hasInvestor), claim
            assert g.value(claim, JPFIBO.hasIssuer), claim
            assert g.value(claim, JPFIBO.informationStatus), claim
            assert g.value(claim, JPFIBO.normativeStatus), claim
            assert list(g.objects(claim, JPFIBO.hasEvidenceElement)), claim
            nonempty += 1
    assert nonempty > 0


def test_real_major_shareholder_claims_have_required_fields(materialized: list[Path]) -> None:
    nonempty = 0
    for ttl in materialized:
        g = Graph().parse(ttl)
        for claim in g.subjects(RDF.type, JPFIBO.MajorShareholderClaim):
            assert g.value(claim, JPFIBO.hasIssuer), claim
            assert g.value(claim, JPFIBO.hasHolder), claim
            assert g.value(claim, JPFIBO.holderRole), claim
            assert g.value(claim, JPFIBO.hasShareholderRank) is not None, claim
            nonempty += 1
    assert nonempty > 0


def test_triangulated_cross_shareholdings_carry_dual_evidence(materialized: list[Path]) -> None:
    found_any = False
    for ttl in materialized:
        g = Graph().parse(ttl)
        for claim in g.subjects(RDF.type, JPFIBO.CrossShareholdingClaim):
            found_any = True
            derived = list(g.objects(claim, __import__("rdflib").namespace.PROV.wasDerivedFrom))
            assert len(derived) >= 2, claim
    if not found_any:
        pytest.skip("no triangulated cross-shareholdings present")


def test_real_claims_shacl_conform(materialized: list[Path]) -> None:
    for ttl in materialized:
        if "S100W4HN" in ttl.name:
            continue
        r = subprocess.run(
            ["uv", "run", "python", str(REPO / "scripts" / "validate.py"), str(ttl)],
            cwd=REPO, capture_output=True, text=True,
        )
        assert r.returncode == 0, ttl.name + "\n" + r.stdout + r.stderr


def test_real_benchmark_jfibo_beats_vanilla() -> None:
    from real_data_loss import run as run_real  # noqa
    summary = run_real()
    if summary.get("claims", 0) == 0:
        pytest.skip("no materialized claims to score")
    assert summary["mean_jfibo_coverage"] > summary["mean_vanilla_coverage"] + 0.4
