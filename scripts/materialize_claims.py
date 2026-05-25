"""Materialize J-FIBO disclosure claims from extracted EDINET facts.

Sources:
  * data/edinet/extracted/<docID>.json  (PolicyShareholding rows + DEI)
  * data/edinet/major_shareholders/<docID>.json (parsed top-N table rows)

Outputs:
  * data/edinet/claims/<docID>.ttl
      - jpfibo:PolicyShareholding claims (one per disclosed holding)
      - jpfibo:MajorShareholderClaim claims (one per major-shareholders row)
      - jpfibo:CrossShareholdingClaim claims when triangulation detects
        an issuer/holder pair that appears as a holding on one side and a
        major-shareholder row on the other side within the loaded corpus.

Entity resolution uses registry/entities.yaml; resolved entities use the
``https://w3id.org/jpfibo/entity/jcn/<JCN>`` URN, unresolved fall back to
``urn:jpfibo:issuer-fallback:<sha1-16>``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS, XSD

from entity_resolver import resolve as resolve_entity

REPO = Path(__file__).resolve().parents[1]
EXTRACTED_DIR = REPO / "data" / "edinet" / "extracted"
MS_DIR = REPO / "data" / "edinet" / "major_shareholders"
CLAIMS_DIR = REPO / "data" / "edinet" / "claims"

JPFIBO = Namespace("https://w3id.org/jpfibo/ontology/JP/core/")
JPCRP_COR = Namespace("http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor#")

EDINET_FILING_BASE = "https://disclosure2.edinet-fsa.go.jp/WEEK0030.aspx?docID="
EDINET_FILER_BASE = "https://w3id.org/jpfibo/entity/edinet/"
CLAIM_BASE = "urn:jpfibo:claim:"

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


def filer_iri(edinet_code: str) -> URIRef:
    return URIRef(f"{EDINET_FILER_BASE}{edinet_code}")


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


def bind_prefixes(g: Graph) -> None:
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)
    g.bind("xsd", XSD)
    g.bind("dcterms", DCTERMS)
    g.bind("prov", PROV)
    g.bind("jpfibo", JPFIBO)
    g.bind("jpcrp_cor", JPCRP_COR)


def add_actor(g: Graph, iri: URIRef, name: str) -> None:
    if (iri, SKOS.prefLabel, None) in g:
        return
    g.add((iri, SKOS.prefLabel, Literal(name, lang="ja")))


def claim_iri(doc_id: str, kind: str, suffix: str) -> URIRef:
    safe = re.sub(r"[^A-Za-z0-9]+", "-", suffix).strip("-") or "x"
    return URIRef(f"{CLAIM_BASE}{doc_id}/{kind}/{safe}")


def materialize(
    extracted: dict,
    major_shareholders: dict | None,
) -> tuple[Graph, dict[str, int]]:
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

    g.add((filer, RDF.type, JPFIBO.KabushikiKaisha))
    g.add((filer, SKOS.prefLabel, Literal(filer_name_ja, lang="ja")))
    # Bridge EDINET-coded filer to JCN-resolved entity when registry knows it.
    resolved_filer_iri, src = resolve_entity(filer_name_ja)
    if src == "jcn":
        g.add((filer, OWL.sameAs, URIRef(resolved_filer_iri)))
    g.add((document_iri, RDF.type, JPFIBO.EDINETDisclosureDocument))
    g.add((document_iri, DCTERMS.identifier, Literal(doc_id)))
    g.add((document_iri, DCTERMS.source, URIRef("https://disclosure2.edinet-fsa.go.jp/")))

    counts = defaultdict(int)
    grouped = group_rows(extracted["typed_rows"])
    issuer_iris_by_filer: dict[str, set[URIRef]] = defaultdict(set)
    for idx, (dim, row) in enumerate(grouped.items()):
        name = row.get("name")
        if not name:
            continue
        issuer_iri, _ = resolve_entity(name)
        issuer = URIRef(issuer_iri)
        add_actor(g, issuer, name)

        dim_key = "-".join(f"{k.split(':')[-1]}={v.split(':')[-1]}" for k, v in dim) or f"row{idx}"
        claim = claim_iri(doc_id, "policy-shareholding", dim_key)
        g.add((claim, RDF.type, JPFIBO.PolicyShareholding))
        g.add((claim, JPFIBO.hasInvestor, filer))
        g.add((claim, JPFIBO.hasIssuer, issuer))
        g.add((claim, PROV.wasDerivedFrom, document_iri))
        g.add((claim, JPFIBO.informationStatus, JPFIBO.Disclosed))
        g.add((claim, JPFIBO.normativeStatus, JPFIBO.GovernanceDisclosure))
        g.add((claim, PROV.generatedAtTime, Literal(generated.isoformat(), datatype=XSD.dateTime)))
        g.add((claim, DCTERMS.valid, Literal(fy_end, datatype=XSD.date)))
        g.add((
            claim,
            JPFIBO.hasEvidenceElement,
            JPCRP_COR["DetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompanyTable"],
        ))
        for c in row.get("concepts", []):
            g.add((claim, JPFIBO.hasEvidenceElement, JPCRP_COR[c]))
        if row.get("shares_value") is not None:
            g.add((claim, JPFIBO.hasShareCount, Literal(row["shares_value"], datatype=XSD.integer)))
        if row.get("book_value") is not None:
            g.add((claim, JPFIBO.hasCarryingAmount, Literal(row["book_value"], datatype=XSD.decimal)))
        if row.get("purpose_value"):
            g.add((claim, JPFIBO.hasHoldingPurpose, Literal(row["purpose_value"], lang="ja")))
        if row.get("reciprocal_value"):
            g.add((claim, SKOS.note, Literal(f"reciprocal-holding-disclosure: {row['reciprocal_value']}", lang="ja")))
        issuer_iris_by_filer[str(filer)].add(issuer)
        counts["policy_shareholding"] += 1

    holder_iris_by_filer: dict[str, set[URIRef]] = defaultdict(set)
    if major_shareholders:
        for row in major_shareholders["rows"]:
            holder_iri_str, _ = resolve_entity(row["name"])
            holder_iri = URIRef(holder_iri_str)
            add_actor(g, holder_iri, row["name"])

            claim = claim_iri(doc_id, "major-shareholder", f"rank{row['rank']:02d}")
            g.add((claim, RDF.type, JPFIBO.MajorShareholderClaim))
            g.add((claim, JPFIBO.hasIssuer, filer))
            g.add((claim, JPFIBO.hasHolder, holder_iri))
            g.add((claim, JPFIBO.holderRole, JPFIBO[row["holder_role"]]))
            g.add((claim, JPFIBO.hasShareholderRank, Literal(row["rank"], datatype=XSD.integer)))
            g.add((claim, JPFIBO.hasShareCount, Literal(row["shares"], datatype=XSD.integer)))
            if row.get("ownership_pct") is not None:
                g.add((claim, JPFIBO.hasOwnershipPercentage, Literal(row["ownership_pct"], datatype=XSD.decimal)))
            g.add((claim, JPFIBO.hasEvidenceElement, JPCRP_COR["MajorShareholdersTextBlock"]))
            g.add((claim, PROV.wasDerivedFrom, document_iri))
            g.add((claim, JPFIBO.informationStatus, JPFIBO.Disclosed))
            g.add((claim, JPFIBO.normativeStatus, JPFIBO.AccountingDisclosure))
            g.add((claim, PROV.generatedAtTime, Literal(generated.isoformat(), datatype=XSD.dateTime)))
            g.add((claim, DCTERMS.valid, Literal(fy_end, datatype=XSD.date)))
            holder_iris_by_filer[str(filer)].add(holder_iri)
            counts["major_shareholder"] += 1

    return g, dict(counts), issuer_iris_by_filer, holder_iris_by_filer


def triangulate_cross_shareholdings(
    issuer_iris_by_filer: dict[URIRef, set[URIRef]],
    holder_iris_by_filer: dict[URIRef, set[URIRef]],
    filer_to_doc: dict[URIRef, URIRef],
    filer_jcn_iri: dict[URIRef, URIRef],
    generated_at: str,
) -> Graph:
    """Detect filer pairs (A, B) where A's policy-shareholdings include B's
    filer entity and B's major-shareholders include A's filer entity."""
    g = Graph()
    bind_prefixes(g)
    pairs_seen: set[tuple[str, str]] = set()
    for filer_a, a_issuers in issuer_iris_by_filer.items():
        for filer_b, b_holders in holder_iris_by_filer.items():
            if filer_a == filer_b:
                continue
            jcn_a = filer_jcn_iri.get(URIRef(filer_a), URIRef(filer_a))
            jcn_b = filer_jcn_iri.get(URIRef(filer_b), URIRef(filer_b))
            b_issuers = issuer_iris_by_filer.get(filer_b, set())
            policy_x_policy = jcn_b in a_issuers and jcn_a in b_issuers
            policy_x_major  = jcn_b in a_issuers and jcn_a in b_holders
            if not (policy_x_policy or policy_x_major):
                continue
            key = tuple(sorted((str(filer_a), str(filer_b))))
            if key in pairs_seen:
                continue
            pairs_seen.add(key)
            triangulation_kind = "policy_x_policy" if policy_x_policy else "policy_x_major"
            claim = URIRef(
                f"{CLAIM_BASE}cross-shareholding/{key[0].split('/')[-1]}-{key[1].split('/')[-1]}"
            )
            g.add((claim, RDF.type, JPFIBO.CrossShareholdingClaim))
            g.add((claim, JPFIBO.hasInvestor, URIRef(filer_a)))
            g.add((claim, JPFIBO.hasIssuer, URIRef(filer_b)))
            g.add((claim, PROV.wasDerivedFrom, filer_to_doc[URIRef(filer_a)]))
            g.add((claim, PROV.wasDerivedFrom, filer_to_doc[URIRef(filer_b)]))
            g.add((claim, JPFIBO.informationStatus, JPFIBO.EvidenceBackedInferred))
            g.add((claim, JPFIBO.normativeStatus, JPFIBO.InferredHypothesis))
            g.add((claim, SKOS.note, Literal(f"triangulation: {triangulation_kind}", lang="en")))
            g.add((claim, PROV.generatedAtTime, Literal(generated_at, datatype=XSD.dateTime)))
            g.add((claim, DCTERMS.valid, Literal(dt.date.today().isoformat(), datatype=XSD.date)))
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc_id", nargs="?")
    args = ap.parse_args()
    docs = [args.doc_id] if args.doc_id else sorted(p.stem for p in EXTRACTED_DIR.glob("*.json"))
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    total = defaultdict(int)
    all_issuers: dict[URIRef, set[URIRef]] = defaultdict(set)
    all_holders: dict[URIRef, set[URIRef]] = defaultdict(set)
    filer_to_doc: dict[URIRef, URIRef] = {}
    filer_jcn_iri: dict[URIRef, URIRef] = {}
    for doc_id in docs:
        p = EXTRACTED_DIR / f"{doc_id}.json"
        if not p.exists():
            print(f"missing {p}", file=sys.stderr)
            continue
        extracted = json.loads(p.read_text())
        ms_path = MS_DIR / f"{doc_id}.json"
        major = json.loads(ms_path.read_text()) if ms_path.exists() else None
        g, counts, iss, hol = materialize(extracted, major)
        out = CLAIMS_DIR / f"{doc_id}.ttl"
        g.serialize(destination=out, format="turtle")
        for k, v in counts.items():
            total[k] += v
        print(
            f"{doc_id}: policy={counts.get('policy_shareholding',0)} "
            f"major_shareholder={counts.get('major_shareholder',0)} -> {out.relative_to(REPO)} ({len(g)} triples)"
        )
        for k, v in iss.items(): all_issuers[URIRef(k)].update(v)
        for k, v in hol.items(): all_holders[URIRef(k)].update(v)
        filer_iri_v = URIRef(EDINET_FILER_BASE + extracted["dei"]["edinet_code"]["value"])
        filer_to_doc[filer_iri_v] = URIRef(EDINET_FILING_BASE + doc_id)
        from entity_resolver import resolve as _resolve
        jcn_iri, src = _resolve(extracted["dei"]["filer_name_ja"]["value"])
        if src == "jcn":
            filer_jcn_iri[filer_iri_v] = URIRef(jcn_iri)
    print(f"total: policy={total['policy_shareholding']} major_shareholder={total['major_shareholder']}")

    # Triangulate cross-shareholding claims from the loaded corpus.
    cs = triangulate_cross_shareholdings(
        all_issuers, all_holders, filer_to_doc, filer_jcn_iri,
        dt.datetime.now(dt.UTC).isoformat(),
    )
    cs_out = CLAIMS_DIR / "_cross_shareholding.ttl"
    cs.serialize(destination=cs_out, format="turtle")
    n_pairs = len(set(cs.subjects(RDF.type, JPFIBO.CrossShareholdingClaim)))
    print(f"cross-shareholding triangulation: {n_pairs} pairs -> {cs_out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
