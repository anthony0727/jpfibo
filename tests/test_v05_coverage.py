"""v0.5 coverage tests:

  * EDINET alignment concepts carry official FSA bilingual labels and XBRL metadata.
  * BorrowingsClaim materialization from MUFG's real consolidated 借入金等明細表.
  * CommercialPaperClaim materialization from MUFG's CP parenthetical.
  * No element silently fabricates English from a URI local name.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS

REPO = Path(__file__).resolve().parents[1]
ALIGNMENT = REPO / "ontology" / "jfibo-edinet-alignment.ttl"
CLAIMS = REPO / "data" / "edinet" / "claims"
FOCUS = REPO / "data" / "derived" / "edinet_taxonomy_focus.json"

JPFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")
JPCRP = Namespace("http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor#")


@pytest.fixture(scope="module")
def alignment_graph() -> Graph:
    g = Graph()
    g.parse(ALIGNMENT)
    return g


def test_alignment_concept_count_meets_v05_floor(alignment_graph: Graph) -> None:
    """v0.5 commits to >= 40 minted EDINET concepts (v0.4 emitted ~15)."""
    concepts = set(alignment_graph.subjects(RDF.type, JPFIBO.EDINETTaxonomyElement))
    assert len(concepts) >= 40, f"alignment regressed: only {len(concepts)} concepts"


def test_alignment_concepts_carry_official_bilingual_labels(alignment_graph: Graph) -> None:
    """For every concept that exists in the FSA focus file, both en and ja
    standard labels must be present — except when the FSA itself leaves the
    Japanese cell blank (intentional gaps preserved)."""
    focus = {f"{r['prefix']}:{r['element']}": r
             for r in json.loads(FOCUS.read_text())["elements"]}
    checked = 0
    for c in alignment_graph.subjects(RDF.type, JPFIBO.EDINETTaxonomyElement):
        notation = alignment_graph.value(c, SKOS.notation)
        if notation is None:
            continue
        key = str(notation)
        row = focus.get(key)
        if row is None:
            continue
        labels_en = [str(o) for o in alignment_graph.objects(c, SKOS.prefLabel)
                     if isinstance(o, Literal) and o.language == "en"]
        labels_ja = [str(o) for o in alignment_graph.objects(c, SKOS.prefLabel)
                     if isinstance(o, Literal) and o.language == "ja"]
        if row.get("standard_label_en"):
            assert row["standard_label_en"] in labels_en, key
        if row.get("standard_label_ja"):
            assert row["standard_label_ja"] in labels_ja, key
        checked += 1
    assert checked >= 10, f"expected to verify >= 10 alignment labels; only {checked}"


def test_xbrl_metadata_carried_on_aligned_elements(alignment_graph: Graph) -> None:
    """Major Shareholders text block should carry its XBRL periodType, type,
    and abstract flag verbatim from the FSA taxonomy."""
    iri = JPCRP.MajorShareholdersTextBlock
    period_types = list(alignment_graph.objects(iri, JPFIBO.xbrlPeriodType))
    types = list(alignment_graph.objects(iri, JPFIBO.xbrlType))
    abstracts = list(alignment_graph.objects(iri, JPFIBO.xbrlAbstract))
    assert period_types and str(period_types[0]) in {"instant", "duration"}
    assert types
    assert abstracts and str(abstracts[0]) in {"true", "false"}


def test_borrowings_claim_present_for_mufg() -> None:
    p = CLAIMS / "S100W4FB.ttl"
    g = Graph().parse(p)
    claims = list(g.subjects(RDF.type, JPFIBO.BorrowingsClaim))
    assert len(claims) >= 4, f"expected MUFG to materialize >= 4 BorrowingsClaim, got {len(claims)}"
    # Spot-check one row: 借入金 (general aggregate) with the known closing balance.
    found_borrowings = False
    for c in claims:
        label = g.value(c, JPFIBO.hasBorrowingsClassLabel)
        closing = g.value(c, JPFIBO.hasClosingBalance)
        if str(label) == "借入金" and closing is not None and int(float(str(closing))) == 22101954:
            found_borrowings = True
            assert g.value(c, JPFIBO.hasBorrower) is not None
            assert g.value(c, JPFIBO.informationStatus) == JPFIBO.Disclosed
            evidence = list(g.objects(c, JPFIBO.hasEvidenceElement))
            assert any(JPCRP.AnnexedConsolidatedDetailedScheduleOfBorrowingsTextBlock in evidence for _ in [0])
    assert found_borrowings, "could not locate the 借入金 closing-balance 22,101,954 百万円 row"


def test_commercial_paper_claim_distinct_from_borrowings() -> None:
    p = CLAIMS / "S100W4FB.ttl"
    g = Graph().parse(p)
    cps = list(g.subjects(RDF.type, JPFIBO.CommercialPaperClaim))
    bcs = list(g.subjects(RDF.type, JPFIBO.BorrowingsClaim))
    assert cps, "expected MUFG to materialize a CommercialPaperClaim"
    # CP and borrowings must be disjoint subject sets so totals are not double-counted.
    assert set(cps).isdisjoint(set(bcs))
    cp = cps[0]
    closing = g.value(cp, JPFIBO.hasClosingBalance)
    assert closing is not None and int(float(str(closing))) == 3475042


def test_no_fabricated_english_for_focus_elements(alignment_graph: Graph) -> None:
    """For elements present in the focus JSON, the English prefLabel must match
    the FSA-published ``standard_label_en`` exactly (not the camelCase local
    name we used to silently mint). When the FSA label *happens* to equal the
    local name (e.g. "Assets"), that's fine because it came from the FSA."""
    focus = {f"{r['prefix']}:{r['element']}": r
             for r in json.loads(FOCUS.read_text())["elements"]
             if r.get("standard_label_en")}
    # Pick the richest row per key (same dedup logic as the builder).
    canonical: dict[str, str] = {}
    for key, row in focus.items():
        prev = canonical.get(key)
        new_en = row["standard_label_en"]
        if prev is None or len(new_en) > len(prev):
            canonical[key] = new_en
    bad: list[tuple[str, list[str], str]] = []
    for c in alignment_graph.subjects(RDF.type, JPFIBO.EDINETTaxonomyElement):
        notation = alignment_graph.value(c, SKOS.notation)
        if notation is None or str(notation) not in canonical:
            continue
        expected = canonical[str(notation)]
        labels_en = [str(o) for o in alignment_graph.objects(c, SKOS.prefLabel)
                     if isinstance(o, Literal) and o.language == "en"]
        if expected not in labels_en:
            bad.append((str(notation), labels_en, expected))
    assert not bad, f"FSA English label missing for: {bad[:5]}"
