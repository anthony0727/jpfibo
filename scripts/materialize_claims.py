"""Materialize J-FIBO disclosure claims from extracted EDINET facts.

Reads ``data/edinet/extracted/<docID>.json`` produced by
``scripts/extract_xbrl_facts.py`` and emits Turtle under
``data/edinet/claims/<docID>.ttl``. Each PolicyShareholding row in the
specified-investment-equity table becomes one ``jfibo:PolicyShareholding``
claim with:

  * jfibo:hasInvestor   -> the filer (urn:edinet:<EDINETCode>)
  * jfibo:hasIssuer     -> a stable URN derived from the disclosed name
  * jfibo:hasShareCount -> integer number of shares
  * jfibo:hasCarryingAmount -> reported book value (yen, decimal)
  * jfibo:hasHoldingPurpose -> disclosed combined-purpose narrative (preserved
                                verbatim, language tag ``ja``)
  * jfibo:hasEvidenceElement -> the EDINET XBRL concept QName
  * prov:wasDerivedFrom -> EDINET document URI
  * jfibo:informationStatus -> jfibo:Disclosed
  * prov:generatedAtTime  -> extraction time
  * dcterms:valid         -> reporting fiscal-year-end (xsd:date)

The result is then SHACL-validated by ``scripts/validate.py``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS, XSD

REPO = Path(__file__).resolve().parents[1]
EXTRACTED_DIR = REPO / "data" / "edinet" / "extracted"
CLAIMS_DIR = REPO / "data" / "edinet" / "claims"

JFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")
EDINET_FILING_BASE = "https://disclosure2.edinet-fsa.go.jp/WEEK0030.aspx?docID="
ISSUER_BASE = "urn:jfibo:issuer:"
FILER_BASE = "urn:jfibo:edinet:"
CLAIM_BASE = "urn:jfibo:claim:"

JPCRP_COR = Namespace("http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor#")

# Concept families we recognize as PolicyShareholding rows.
PURPOSE_LOCAL = (
    "PurposeOfShareholdingOverviewOfBusinessAllianceQuantitativeEffectsOfShareholdingAndReasonForIncreaseInNumberOfShares"
)
NAME_LOCAL_PREFIXES = (
    "NameOfSecuritiesDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestment",
    "NameOfSecuritiesDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestment",
)
SHARES_LOCAL_PREFIXES = (
    "NumberOfSharesHeldDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestment",
    "NumberOfSharesHeldDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestment",
)
BOOK_LOCAL_PREFIXES = (
    "BookValueDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestment",
    "BookValueDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestment",
)
PURPOSE_LOCAL_PREFIXES = (
    f"{PURPOSE_LOCAL}DetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestment",
    f"{PURPOSE_LOCAL}DetailsOfDeemedHoldingsOfSharesHeldForPurposesOtherThanPureInvestment",
)
RECIPROCAL_LOCAL_PREFIXES = (
    "WhetherIssuerOfAforementionedSharesHoldsReportingCompanysSharesDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestment",
    "WhetherIssuerOfAforementionedSharesHoldsReportingCompanysSharesDetailsOfDeemedHoldingsOfSharesHeldForPurposesOtherThanPureInvestment",
)


def starts_with_any(s: str, prefixes: tuple[str, ...]) -> bool:
    return any(s.startswith(p) for p in prefixes)


def issuer_iri(name: str) -> URIRef:
    canonical = re.sub(r"\s+", "", name)
    h = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return URIRef(f"{ISSUER_BASE}{h}")


def filer_iri(edinet_code: str) -> URIRef:
    return URIRef(f"{FILER_BASE}{edinet_code}")


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    v = value.replace(",", "").strip()
    try:
        return int(v)
    except ValueError:
        return None


def parse_amount(value: str | None) -> float | None:
    if not value:
        return None
    v = value.replace(",", "").strip()
    try:
        return float(v)
    except ValueError:
        return None


def group_rows(typed_rows: list[dict]) -> dict:
    grouped: dict[tuple[tuple[str, str], ...], dict] = defaultdict(dict)
    for row in typed_rows:
        dim = tuple(sorted(row["dimensions"].items()))
        c = row["concept"]
        if starts_with_any(c, NAME_LOCAL_PREFIXES):
            grouped[dim]["name"] = row["value"]
            grouped[dim].setdefault("concepts", set()).add(c)
        elif starts_with_any(c, SHARES_LOCAL_PREFIXES):
            grouped[dim]["shares_concept"] = c
            grouped[dim]["shares_value"] = parse_int(row["value"])
            grouped[dim].setdefault("concepts", set()).add(c)
        elif starts_with_any(c, BOOK_LOCAL_PREFIXES):
            grouped[dim]["book_concept"] = c
            grouped[dim]["book_value"] = parse_amount(row["value"])
            grouped[dim].setdefault("concepts", set()).add(c)
        elif starts_with_any(c, PURPOSE_LOCAL_PREFIXES):
            grouped[dim]["purpose_concept"] = c
            grouped[dim]["purpose_value"] = row["value"]
            grouped[dim].setdefault("concepts", set()).add(c)
        elif starts_with_any(c, RECIPROCAL_LOCAL_PREFIXES):
            grouped[dim]["reciprocal_concept"] = c
            grouped[dim]["reciprocal_value"] = row["value"]
            grouped[dim].setdefault("concepts", set()).add(c)
    return grouped


def claim_iri(doc_id: str, dim_key: str) -> URIRef:
    return URIRef(f"{CLAIM_BASE}{doc_id}/{dim_key}")


def bind_prefixes(g: Graph) -> None:
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)
    g.bind("xsd", XSD)
    g.bind("dcterms", DCTERMS)
    g.bind("prov", PROV)
    g.bind("jfibo", JFIBO)
    g.bind("jpcrp_cor", JPCRP_COR)


def materialize(extracted: dict) -> Graph:
    g = Graph()
    bind_prefixes(g)
    edinet_code = extracted["dei"]["edinet_code"]["value"]
    filer_name_ja = extracted["dei"]["filer_name_ja"]["value"]
    fy_end = extracted["dei"]["fy_end"]["value"]
    doc_id = extracted["doc_id"]
    document_iri = URIRef(EDINET_FILING_BASE + doc_id)
    filer = filer_iri(edinet_code)
    generated = dt.datetime.fromisoformat(extracted["extracted_at"])
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=dt.UTC)

    g.add((filer, RDF.type, JFIBO.KabushikiKaisha))
    g.add((filer, SKOS.prefLabel, Literal(filer_name_ja, lang="ja")))
    g.add((document_iri, RDF.type, JFIBO.EDINETDisclosureDocument))
    g.add((document_iri, DCTERMS.identifier, Literal(doc_id)))
    g.add((document_iri, DCTERMS.source, URIRef("https://disclosure2.edinet-fsa.go.jp/")))

    grouped = group_rows(extracted["typed_rows"])

    n_claims = 0
    for idx, (dim, row) in enumerate(grouped.items()):
        name = row.get("name")
        if not name:
            continue
        issuer = issuer_iri(name)
        g.add((issuer, SKOS.prefLabel, Literal(name, lang="ja")))
        g.add((issuer, JFIBO.status, Literal("named-from-disclosure")))

        dim_key = "-".join(f"{k.split(':')[-1]}={v.split(':')[-1]}" for k, v in dim) or f"row{idx}"
        claim = claim_iri(doc_id, dim_key)
        g.add((claim, RDF.type, JFIBO.PolicyShareholding))
        g.add((claim, JFIBO.hasInvestor, filer))
        g.add((claim, JFIBO.hasIssuer, issuer))
        g.add((claim, PROV.wasDerivedFrom, document_iri))
        g.add((claim, JFIBO.informationStatus, JFIBO.Disclosed))
        g.add((claim, PROV.generatedAtTime, Literal(generated.isoformat(), datatype=XSD.dateTime)))
        g.add((claim, DCTERMS.valid, Literal(fy_end, datatype=XSD.date)))
        # Always cite the table-level evidence element so SHACL passes even if
        # only Number/Book facts were emitted (some filers omit purpose text).
        g.add((
            claim,
            JFIBO.hasEvidenceElement,
            JPCRP_COR["DetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompanyTable"],
        ))
        for c in row.get("concepts", []):
            g.add((claim, JFIBO.hasEvidenceElement, JPCRP_COR[c]))
        if row.get("shares_value") is not None:
            g.add((claim, JFIBO.hasShareCount, Literal(row["shares_value"], datatype=XSD.integer)))
        if row.get("book_value") is not None:
            g.add((claim, JFIBO.hasCarryingAmount, Literal(row["book_value"], datatype=XSD.decimal)))
        if row.get("purpose_value"):
            g.add((claim, JFIBO.hasHoldingPurpose, Literal(row["purpose_value"], lang="ja")))
        if row.get("reciprocal_value"):
            g.add((claim, SKOS.note, Literal(f"reciprocal-holding-disclosure: {row['reciprocal_value']}", lang="ja")))
        n_claims += 1
    return g, n_claims


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc_id", nargs="?")
    args = ap.parse_args()
    docs = [args.doc_id] if args.doc_id else sorted(p.stem for p in EXTRACTED_DIR.glob("*.json"))
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for doc_id in docs:
        p = EXTRACTED_DIR / f"{doc_id}.json"
        if not p.exists():
            print(f"missing {p}", file=sys.stderr)
            continue
        extracted = json.loads(p.read_text())
        g, n = materialize(extracted)
        out = CLAIMS_DIR / f"{doc_id}.ttl"
        g.serialize(destination=out, format="turtle")
        print(f"{doc_id}: {n} PolicyShareholding claims -> {out.relative_to(REPO)} ({len(g)} triples)")
        total += n
    print(f"total claims: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
