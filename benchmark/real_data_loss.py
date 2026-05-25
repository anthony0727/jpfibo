"""Real-EDINET semantic-loss benchmark.

For every materialized PolicyShareholding claim, compare what vanilla FIBO
can represent natively (issuer, investor, share count) against what J-FIBO
represents (those plus holding purpose, evidence element, reciprocal-
holding marker, information status, evidence locator, validity).

A claim's vanilla-coverage and jfibo-coverage are computed against a fixed
expected-field schema; the gap is the per-claim semantic loss.

The benchmark also aggregates by filer (EDINET code) and emits
``benchmark/results/real_summary.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import statistics
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, SKOS, XSD

REPO = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO / "data" / "edinet" / "claims"
RESULTS_DIR = REPO / "benchmark" / "results"

JFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")

EXPECTED_FIELDS = [
    "investor",
    "issuer",
    "share_count",
    "carrying_amount",
    "holding_purpose",
    "reciprocal_holding_marker",
    "evidence_element",
    "information_status",
    "evidence_locator",
    "reporting_period_validity",
]
VANILLA_REPRESENTS = {"investor", "issuer", "share_count"}


def per_claim_metrics(g: Graph) -> list[dict]:
    out: list[dict] = []
    for claim in g.subjects(RDF.type, JFIBO.PolicyShareholding):
        fields = set()
        if g.value(claim, JFIBO.hasInvestor): fields.add("investor")
        if g.value(claim, JFIBO.hasIssuer): fields.add("issuer")
        if g.value(claim, JFIBO.hasShareCount) is not None: fields.add("share_count")
        if g.value(claim, JFIBO.hasCarryingAmount) is not None: fields.add("carrying_amount")
        if g.value(claim, JFIBO.hasHoldingPurpose): fields.add("holding_purpose")
        if any(g.objects(claim, SKOS.note)): fields.add("reciprocal_holding_marker")
        if any(g.objects(claim, JFIBO.hasEvidenceElement)): fields.add("evidence_element")
        if g.value(claim, JFIBO.informationStatus): fields.add("information_status")
        if g.value(claim, PROV.wasDerivedFrom): fields.add("evidence_locator")
        if g.value(claim, DCTERMS.valid): fields.add("reporting_period_validity")

        vanilla = fields & VANILLA_REPRESENTS
        jrep = fields
        out.append({
            "claim": str(claim),
            "fields": sorted(fields),
            "vanilla_coverage": len(vanilla) / len(EXPECTED_FIELDS),
            "jfibo_coverage": len(jrep) / len(EXPECTED_FIELDS),
            "semantic_loss_rate": (len(EXPECTED_FIELDS) - len(vanilla)) / len(EXPECTED_FIELDS),
            "jfibo_gain": (len(jrep) - len(vanilla)) / len(EXPECTED_FIELDS),
        })
    return out


def run(claims_dir: Path = CLAIMS_DIR) -> dict:
    per_doc: dict[str, list[dict]] = {}
    all_claims: list[dict] = []
    for p in sorted(claims_dir.glob("*.ttl")):
        g = Graph().parse(p)
        m = per_claim_metrics(g)
        per_doc[p.stem] = m
        for x in m:
            x["doc_id"] = p.stem
        all_claims.extend(m)

    if not all_claims:
        return {"claims": 0}

    summary = {
        "claims": len(all_claims),
        "mean_vanilla_coverage": statistics.fmean(c["vanilla_coverage"] for c in all_claims),
        "mean_jfibo_coverage": statistics.fmean(c["jfibo_coverage"] for c in all_claims),
        "mean_semantic_loss_rate": statistics.fmean(c["semantic_loss_rate"] for c in all_claims),
        "mean_jfibo_gain": statistics.fmean(c["jfibo_gain"] for c in all_claims),
        "by_doc": {
            d: {
                "claims": len(ms),
                "mean_jfibo_coverage": statistics.fmean(m["jfibo_coverage"] for m in ms),
                "mean_vanilla_coverage": statistics.fmean(m["vanilla_coverage"] for m in ms),
                "share_with_holding_purpose": statistics.fmean(
                    1.0 if "holding_purpose" in m["fields"] else 0.0 for m in ms
                ),
                "share_with_reciprocal_marker": statistics.fmean(
                    1.0 if "reciprocal_holding_marker" in m["fields"] else 0.0 for m in ms
                ),
            }
            for d, ms in per_doc.items() if ms
        },
    }
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims-dir", type=Path, default=CLAIMS_DIR)
    ap.add_argument("--out", type=Path, default=RESULTS_DIR / "real_summary.json")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary = run(args.claims_dir)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary or summary.get("claims", 0) == 0:
        print("no claims found")
        return 0
    print("J-FIBO real-EDINET semantic-loss benchmark")
    print("=" * 50)
    print(f"claims:                          {summary['claims']}")
    print(f"mean vanilla FIBO coverage:      {summary['mean_vanilla_coverage']:.3f}")
    print(f"mean J-FIBO coverage:            {summary['mean_jfibo_coverage']:.3f}")
    print(f"mean semantic-loss rate:         {summary['mean_semantic_loss_rate']:.3f}")
    print(f"mean J-FIBO gain:                {summary['mean_jfibo_gain']:.3f}")
    print()
    print("by document:")
    for d, v in summary["by_doc"].items():
        print(
            f"  {d}: claims={v['claims']:>3}  jfibo={v['mean_jfibo_coverage']:.3f}  "
            f"vanilla={v['mean_vanilla_coverage']:.3f}  "
            f"purpose={v['share_with_holding_purpose']:.2f}  "
            f"reciprocal={v['share_with_reciprocal_marker']:.2f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
