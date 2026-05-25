"""Real-EDINET semantic-loss benchmark for the J-FIBO v0.5 claim families.

Scores three claim families against fixed expected-field schemas:

  * PolicyShareholding    (investor, issuer, share_count, carrying_amount,
                           holding_purpose, reciprocal_holding_marker,
                           evidence_element, information_status,
                           normative_status, evidence_locator,
                           reporting_period_validity)
  * MajorShareholderClaim (issuer, holder, holder_role, share_count,
                           ownership_percentage, shareholder_rank,
                           evidence_element, information_status,
                           normative_status, evidence_locator,
                           reporting_period_validity)
  * CrossShareholdingClaim (investor, issuer, dual_evidence_traceability,
                            jcn_identity_resolution, information_status,
                            evidence_locator, reporting_period_validity)

Vanilla FIBO is scored as representing only the structural object fields
(parties + counts); the institutional/role/provenance fields are J-FIBO-only.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, SKOS, XSD

REPO = Path(__file__).resolve().parents[1]
CLAIMS_DIR = REPO / "data" / "edinet" / "claims"
RESULTS_DIR = REPO / "benchmark" / "results"

JPFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")

POLICY_EXPECTED = [
    "investor", "issuer", "share_count", "carrying_amount", "holding_purpose",
    "reciprocal_holding_marker", "evidence_element", "information_status",
    "normative_status", "evidence_locator", "reporting_period_validity",
]
POLICY_VANILLA = {"investor", "issuer", "share_count"}

MAJOR_EXPECTED = [
    "issuer", "holder", "holder_role", "share_count", "ownership_percentage",
    "shareholder_rank", "evidence_element", "information_status",
    "normative_status", "evidence_locator", "reporting_period_validity",
]
MAJOR_VANILLA = {"issuer", "holder", "share_count", "ownership_percentage"}

CROSS_EXPECTED = [
    "investor", "issuer", "dual_evidence_traceability",
    "jcn_identity_resolution", "information_status", "evidence_locator",
    "reporting_period_validity",
]
CROSS_VANILLA = {"investor", "issuer"}

BORROWINGS_EXPECTED = [
    "borrower", "borrowings_class_label", "opening_balance",
    "closing_balance", "average_rate", "repayment_deadline",
    "unit_label", "evidence_element", "information_status",
    "normative_status", "evidence_locator", "reporting_period_validity",
]
BORROWINGS_VANILLA = {"borrower"}

COMMERCIAL_PAPER_EXPECTED = [
    "borrower", "borrowings_class_label", "opening_balance",
    "closing_balance", "average_rate", "unit_label",
    "evidence_element", "information_status", "normative_status",
    "evidence_locator", "reporting_period_validity",
]
COMMERCIAL_PAPER_VANILLA = {"borrower"}


def _ratio(a: int, b: int) -> float:
    return float(a) / float(b) if b else 0.0


def policy_metrics(g: Graph) -> list[dict]:
    out: list[dict] = []
    for c in g.subjects(RDF.type, JPFIBO.PolicyShareholding):
        f: set[str] = set()
        if g.value(c, JPFIBO.hasInvestor): f.add("investor")
        if g.value(c, JPFIBO.hasIssuer): f.add("issuer")
        if g.value(c, JPFIBO.hasShareCount) is not None: f.add("share_count")
        if g.value(c, JPFIBO.hasCarryingAmount) is not None: f.add("carrying_amount")
        if g.value(c, JPFIBO.hasHoldingPurpose): f.add("holding_purpose")
        if any(g.objects(c, SKOS.note)): f.add("reciprocal_holding_marker")
        if any(g.objects(c, JPFIBO.hasEvidenceElement)): f.add("evidence_element")
        if g.value(c, JPFIBO.informationStatus): f.add("information_status")
        if g.value(c, JPFIBO.normativeStatus): f.add("normative_status")
        if g.value(c, PROV.wasDerivedFrom): f.add("evidence_locator")
        if g.value(c, DCTERMS.valid): f.add("reporting_period_validity")
        v = f & POLICY_VANILLA
        out.append({
            "claim": str(c), "kind": "PolicyShareholding",
            "fields": sorted(f),
            "vanilla_coverage": _ratio(len(v), len(POLICY_EXPECTED)),
            "jfibo_coverage":   _ratio(len(f), len(POLICY_EXPECTED)),
        })
    return out


def major_metrics(g: Graph) -> list[dict]:
    out: list[dict] = []
    for c in g.subjects(RDF.type, JPFIBO.MajorShareholderClaim):
        f: set[str] = set()
        if g.value(c, JPFIBO.hasIssuer): f.add("issuer")
        if g.value(c, JPFIBO.hasHolder): f.add("holder")
        if g.value(c, JPFIBO.holderRole): f.add("holder_role")
        if g.value(c, JPFIBO.hasShareCount) is not None: f.add("share_count")
        if g.value(c, JPFIBO.hasOwnershipPercentage) is not None: f.add("ownership_percentage")
        if g.value(c, JPFIBO.hasShareholderRank) is not None: f.add("shareholder_rank")
        if any(g.objects(c, JPFIBO.hasEvidenceElement)): f.add("evidence_element")
        if g.value(c, JPFIBO.informationStatus): f.add("information_status")
        if g.value(c, JPFIBO.normativeStatus): f.add("normative_status")
        if g.value(c, PROV.wasDerivedFrom): f.add("evidence_locator")
        if g.value(c, DCTERMS.valid): f.add("reporting_period_validity")
        v = f & MAJOR_VANILLA
        out.append({
            "claim": str(c), "kind": "MajorShareholderClaim",
            "fields": sorted(f),
            "vanilla_coverage": _ratio(len(v), len(MAJOR_EXPECTED)),
            "jfibo_coverage":   _ratio(len(f), len(MAJOR_EXPECTED)),
        })
    return out


def cross_metrics(g: Graph) -> list[dict]:
    out: list[dict] = []
    for c in g.subjects(RDF.type, JPFIBO.CrossShareholdingClaim):
        f: set[str] = set()
        if g.value(c, JPFIBO.hasInvestor): f.add("investor")
        if g.value(c, JPFIBO.hasIssuer): f.add("issuer")
        derived = list(g.objects(c, PROV.wasDerivedFrom))
        if len(derived) >= 2: f.add("dual_evidence_traceability")
        if g.value(c, JPFIBO.hasInvestor) and g.value(c, JPFIBO.hasIssuer):
            f.add("jcn_identity_resolution")
        if g.value(c, JPFIBO.informationStatus): f.add("information_status")
        if g.value(c, PROV.wasDerivedFrom): f.add("evidence_locator")
        if g.value(c, DCTERMS.valid): f.add("reporting_period_validity")
        v = f & CROSS_VANILLA
        out.append({
            "claim": str(c), "kind": "CrossShareholdingClaim",
            "fields": sorted(f),
            "vanilla_coverage": _ratio(len(v), len(CROSS_EXPECTED)),
            "jfibo_coverage":   _ratio(len(f), len(CROSS_EXPECTED)),
        })
    return out



def borrowings_metrics(g: Graph) -> list[dict]:
    out: list[dict] = []
    for c in g.subjects(RDF.type, JPFIBO.BorrowingsClaim):
        f: set[str] = set()
        if g.value(c, JPFIBO.hasBorrower): f.add("borrower")
        if g.value(c, JPFIBO.hasBorrowingsClassLabel): f.add("borrowings_class_label")
        if g.value(c, JPFIBO.hasOpeningBalance) is not None: f.add("opening_balance")
        if g.value(c, JPFIBO.hasClosingBalance) is not None: f.add("closing_balance")
        if g.value(c, JPFIBO.hasAverageRate) is not None: f.add("average_rate")
        if g.value(c, JPFIBO.hasRepaymentDeadline): f.add("repayment_deadline")
        if g.value(c, JPFIBO.hasUnitLabel): f.add("unit_label")
        if any(g.objects(c, JPFIBO.hasEvidenceElement)): f.add("evidence_element")
        if g.value(c, JPFIBO.informationStatus): f.add("information_status")
        if g.value(c, JPFIBO.normativeStatus): f.add("normative_status")
        if g.value(c, PROV.wasDerivedFrom): f.add("evidence_locator")
        if g.value(c, DCTERMS.valid): f.add("reporting_period_validity")
        v = f & BORROWINGS_VANILLA
        out.append({
            "claim": str(c), "kind": "BorrowingsClaim",
            "fields": sorted(f),
            "vanilla_coverage": _ratio(len(v), len(BORROWINGS_EXPECTED)),
            "jfibo_coverage":   _ratio(len(f), len(BORROWINGS_EXPECTED)),
        })
    return out


def commercial_paper_metrics(g: Graph) -> list[dict]:
    out: list[dict] = []
    for c in g.subjects(RDF.type, JPFIBO.CommercialPaperClaim):
        f: set[str] = set()
        if g.value(c, JPFIBO.hasBorrower): f.add("borrower")
        if g.value(c, JPFIBO.hasBorrowingsClassLabel): f.add("borrowings_class_label")
        if g.value(c, JPFIBO.hasOpeningBalance) is not None: f.add("opening_balance")
        if g.value(c, JPFIBO.hasClosingBalance) is not None: f.add("closing_balance")
        if g.value(c, JPFIBO.hasAverageRate) is not None: f.add("average_rate")
        if g.value(c, JPFIBO.hasUnitLabel): f.add("unit_label")
        if any(g.objects(c, JPFIBO.hasEvidenceElement)): f.add("evidence_element")
        if g.value(c, JPFIBO.informationStatus): f.add("information_status")
        if g.value(c, JPFIBO.normativeStatus): f.add("normative_status")
        if g.value(c, PROV.wasDerivedFrom): f.add("evidence_locator")
        if g.value(c, DCTERMS.valid): f.add("reporting_period_validity")
        v = f & COMMERCIAL_PAPER_VANILLA
        out.append({
            "claim": str(c), "kind": "CommercialPaperClaim",
            "fields": sorted(f),
            "vanilla_coverage": _ratio(len(v), len(COMMERCIAL_PAPER_EXPECTED)),
            "jfibo_coverage":   _ratio(len(f), len(COMMERCIAL_PAPER_EXPECTED)),
        })
    return out

def run(claims_dir: Path = CLAIMS_DIR) -> dict:
    per_doc: dict[str, list[dict]] = {}
    all_claims: list[dict] = []
    for p in sorted(claims_dir.glob("*.ttl")):
        g = Graph().parse(p)
        m = (policy_metrics(g) + major_metrics(g) + cross_metrics(g) + borrowings_metrics(g) + commercial_paper_metrics(g))
        per_doc[p.stem] = m
        for x in m:
            x["doc_id"] = p.stem
        all_claims.extend(m)

    if not all_claims:
        return {"claims": 0}

    by_kind = defaultdict(list)
    for c in all_claims:
        by_kind[c["kind"]].append(c)

    summary = {
        "claims": len(all_claims),
        "mean_vanilla_coverage": statistics.fmean(c["vanilla_coverage"] for c in all_claims),
        "mean_jfibo_coverage":   statistics.fmean(c["jfibo_coverage"]   for c in all_claims),
        "mean_jfibo_gain":       statistics.fmean(c["jfibo_coverage"] - c["vanilla_coverage"] for c in all_claims),
        "by_kind": {
            k: {
                "claims": len(ms),
                "mean_vanilla_coverage": statistics.fmean(m["vanilla_coverage"] for m in ms),
                "mean_jfibo_coverage":   statistics.fmean(m["jfibo_coverage"]   for m in ms),
                "mean_jfibo_gain":       statistics.fmean(m["jfibo_coverage"] - m["vanilla_coverage"] for m in ms),
            }
            for k, ms in sorted(by_kind.items())
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
        print("no claims found"); return 0
    print("J-FIBO real-EDINET semantic-loss benchmark (v0.5)")
    print("=" * 52)
    print(f"claims:                          {summary['claims']}")
    print(f"mean vanilla FIBO coverage:      {summary['mean_vanilla_coverage']:.3f}")
    print(f"mean J-FIBO coverage:            {summary['mean_jfibo_coverage']:.3f}")
    print(f"mean J-FIBO gain:                {summary['mean_jfibo_gain']:.3f}")
    print()
    print("by claim kind:")
    for k, v in summary["by_kind"].items():
        print(
            f"  {k:24s} claims={v['claims']:>3}  "
            f"vanilla={v['mean_vanilla_coverage']:.3f}  "
            f"jfibo={v['mean_jfibo_coverage']:.3f}  "
            f"gain={v['mean_jfibo_gain']:.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
