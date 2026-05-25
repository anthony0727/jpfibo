from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

REPO = Path(__file__).resolve().parents[1]
ONTOLOGY_DIR = REPO / "ontology"
REGISTRY = REPO / "registry" / "terms.yaml"
JFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")


def load_aggregate() -> Graph:
    g = Graph()
    for ttl in sorted(ONTOLOGY_DIR.glob("jfibo-*.ttl")):
        g.parse(ttl)
    return g


@pytest.fixture(scope="module")
def aggregate() -> Graph:
    return load_aggregate()


def test_modules_present() -> None:
    expected = {
        "jfibo-core.ttl",
        "jfibo-information-status.ttl",
        "jfibo-disclosure-claim.ttl",
        "jfibo-institutional-context.ttl",
        "jfibo-edinet-alignment.ttl",
    }
    found = {p.name for p in ONTOLOGY_DIR.glob("jfibo-*.ttl")}
    assert expected.issubset(found), f"missing modules: {expected - found}"


def test_no_legacy_legalentity_parent(aggregate: Graph) -> None:
    bad_parent = URIRef(
        "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/LegalEntity"
    )
    for s, _, _ in aggregate.triples((None, RDFS.subClassOf, bad_parent)):
        if str(s).startswith(str(JFIBO)):
            pytest.fail(f"{s} still subClassOf placeholder fibo-be-le-lp:LegalEntity")


def test_information_status_individuals(aggregate: Graph) -> None:
    individuals = set()
    info_class = JFIBO.InformationStatus
    for s, _, _ in aggregate.triples((None, RDF.type, info_class)):
        individuals.add(s)
    expected_locals = {
        "Observed",
        "Disclosed",
        "EvidenceBackedInferred",
        "Hypothesized",
        "Counterfactual",
        "Predicted",
        "OutsideInformationBoundary",
    }
    found_locals = {str(i).split("/")[-1] for i in individuals}
    assert expected_locals == found_locals, found_locals


def test_every_jfibo_class_has_label_def_source(aggregate: Graph) -> None:
    for s, _, _ in aggregate.triples((None, RDF.type, OWL.Class)):
        if not str(s).startswith(str(JFIBO)):
            continue
        en_labels = [
            o for _, _, o in aggregate.triples((s, SKOS.prefLabel, None))
            if getattr(o, "language", None) == "en"
        ]
        ja_labels = [
            o for _, _, o in aggregate.triples((s, SKOS.prefLabel, None))
            if getattr(o, "language", None) == "ja"
        ]
        defs = list(aggregate.objects(s, SKOS.definition))
        sources = list(aggregate.objects(s, URIRef("http://purl.org/dc/terms/source")))
        assert en_labels, f"{s} missing en label"
        assert ja_labels, f"{s} missing ja label"
        assert defs, f"{s} missing definition"
        assert sources, f"{s} missing source"


def test_local_names_are_sparql_safe() -> None:
    registry = yaml.safe_load(REGISTRY.read_text())
    pat = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
    for term in registry["terms"]:
        assert pat.match(term["id"]), f"bad local name {term['id']!r}"


def test_proposed_terms_have_scope_notes() -> None:
    registry = yaml.safe_load(REGISTRY.read_text())
    for term in registry["terms"]:
        if term.get("level") == "propose":
            assert term.get("scope_note_en"), f"{term['id']!r}: proposed term missing scope_note_en"
