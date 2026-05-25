"""Build J-FIBO OWL/RDFS modules from the controlled registry.

Design constraints:
  * No string-templated Turtle. Triples are created with rdflib.Graph.add(...).
  * Official vocabularies are explicit prefixes; J-FIBO only mints local terms
    listed in registry/terms.yaml.
  * Every minted term has bilingual labels, definition, source, status, and
    proposed terms have scope notes.
  * EDINET XBRL concepts are represented as alignment handles while preserving
    the official EDINET namespace URI in source metadata.

Run:
    uv run python scripts/build_ontology.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS, XSD

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "registry" / "terms.yaml"
AGGREGATE_OUT = REPO / "ontology" / "jfibo.ttl"
LEGACY_AGGREGATE_OUT = REPO / "ontology" / "fibo-jp-core.ttl"

# Official / upstream prefix table. Add only stable namespace IRIs here.
PREFIX_TABLE: dict[str, Namespace] = {
    "rdf": Namespace(str(RDF)),
    "rdfs": Namespace(str(RDFS)),
    "owl": Namespace(str(OWL)),
    "skos": Namespace(str(SKOS)),
    "xsd": Namespace(str(XSD)),
    "dcterms": Namespace(str(DCTERMS)),
    "prov": Namespace(str(PROV)),
    "time": Namespace("http://www.w3.org/2006/time#"),
    "sh": Namespace("http://www.w3.org/ns/shacl#"),
    "cmns-org": Namespace("https://www.omg.org/spec/Commons/Organizations/"),
    "fibo-be-le-cb": Namespace(
        "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/CorporateBodies/"
    ),
    "fibo-be-le-lp": Namespace(
        "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/"
    ),
    "fibo-fbc-fct-fse": Namespace(
        "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialServicesEntities/"
    ),
    "fibo-fbc-fi-fi": Namespace(
        "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/"
    ),
    "fibo-sec-eq-eq": Namespace(
        "https://spec.edmcouncil.org/fibo/ontology/SEC/Equities/EquityInstruments/"
    ),
}

# XBRL element handles: XBRL names are (namespace URI, local name).  In RDF we
# mint stable alignment URIs using namespace + '#' + local name, while preserving
# the source namespace in dcterms:source and docs.
EDINET_XBRL_NAMESPACES: dict[str, str] = {
    "jpdei_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jpdei/2013-08-31/jpdei_cor",
    "jpcrp_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor",
    "jppfs_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2025-11-01/jppfs_cor",
}
EDINET_RDF_PREFIXES: dict[str, Namespace] = {
    p: Namespace(ns + "#") for p, ns in EDINET_XBRL_NAMESPACES.items()
}

VALID_LOCAL = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
VALID_QNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*:[A-Za-z_][A-Za-z0-9_\-.]*$")
VALID_STATUS = {"proposed", "reviewed", "stable"}
VALID_LEVEL = {"reuse", "align", "propose"}
VALID_KIND = {"class", "object_property", "datatype_property", "annotation_property", "individual"}

JFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"registry violation: {message}")


def bind_all(g: Graph, registry: dict[str, Any]) -> None:
    for prefix, ns in PREFIX_TABLE.items():
        g.bind(prefix, ns)
    for prefix, ns in EDINET_RDF_PREFIXES.items():
        g.bind(prefix, ns)
    g.bind(registry["prefix"], Namespace(registry["prefix_iri"]))


def module_iri(module: dict[str, Any], registry: dict[str, Any]) -> URIRef:
    return URIRef(module["iri"])


def term_iri(term_id: str, registry: dict[str, Any]) -> URIRef:
    return URIRef(str(Namespace(registry["prefix_iri"])) + term_id)


def edinet_element_iri(qname: str) -> URIRef:
    require(VALID_QNAME.match(qname), f"bad EDINET element QName {qname!r}")
    prefix, local = qname.split(":", 1)
    require(prefix in EDINET_RDF_PREFIXES, f"unknown EDINET prefix {prefix!r}")
    return URIRef(str(EDINET_RDF_PREFIXES[prefix]) + local)


def resolve_identifier(identifier: str, registry: dict[str, Any], known_terms: set[str]) -> URIRef:
    """Resolve upstream QName or local J-FIBO id. Never invent prefixes."""
    if ":" not in identifier:
        require(identifier in known_terms, f"unknown local J-FIBO id {identifier!r}")
        return term_iri(identifier, registry)
    prefix, local = identifier.split(":", 1)
    if prefix in PREFIX_TABLE:
        return URIRef(str(PREFIX_TABLE[prefix]) + local)
    if prefix in EDINET_RDF_PREFIXES:
        return edinet_element_iri(identifier)
    raise ValueError(
        f"unknown prefix {prefix!r}; add it to PREFIX_TABLE / EDINET_XBRL_NAMESPACES before using"
    )


def add_common_metadata(
    g: Graph,
    iri: URIRef,
    term: dict[str, Any],
    ontology_iri: URIRef,
    registry: dict[str, Any],
) -> None:
    labels = term["labels"]
    g.add((iri, RDFS.isDefinedBy, ontology_iri))
    g.add((iri, SKOS.prefLabel, Literal(labels["en"], lang="en")))
    g.add((iri, SKOS.prefLabel, Literal(labels["ja"], lang="ja")))
    g.add((iri, SKOS.definition, Literal(term["definition_en"].strip(), lang="en")))
    if term.get("scope_note_en"):
        g.add((iri, SKOS.scopeNote, Literal(term["scope_note_en"].strip(), lang="en")))
    for src in term["sources"]:
        g.add((iri, DCTERMS.source, URIRef(src)))
    g.add((iri, JFIBO.status, Literal(term.get("status", "proposed"))))
    g.add((iri, JFIBO.level, Literal(term["level"])))
    if term.get("edinet_elements"):
        for element in term["edinet_elements"]:
            eiri = edinet_element_iri(element)
            g.add((iri, JFIBO.mapsToEdinetElement, eiri))


def add_edinet_concepts(g: Graph, registry: dict[str, Any], ontology_iri: URIRef, elements: set[str]) -> None:
    for element in sorted(elements):
        prefix, local = element.split(":", 1)
        iri = edinet_element_iri(element)
        g.add((iri, RDF.type, SKOS.Concept))
        g.add((iri, RDF.type, JFIBO.EDINETTaxonomyElement))
        g.add((iri, SKOS.notation, Literal(element)))
        g.add((iri, RDFS.isDefinedBy, ontology_iri))
        g.add((iri, DCTERMS.source, URIRef(EDINET_XBRL_NAMESPACES[prefix])))
        g.add((iri, SKOS.prefLabel, Literal(local, lang="en")))


def validate_registry(registry: dict[str, Any]) -> None:
    require("modules" in registry and registry["modules"], "missing modules")
    ids: set[str] = set()
    for term in registry["terms"]:
        tid = term["id"]
        require(VALID_LOCAL.match(tid), f"local name {tid!r} is not a SPARQL-safe QName")
        require(tid not in ids, f"duplicate id {tid!r}")
        ids.add(tid)

        kind = term.get("kind", "class")
        level = term.get("level")
        status = term.get("status", "proposed")
        module = term.get("module")
        require(kind in VALID_KIND, f"{tid}: bad kind {kind!r}")
        require(level in VALID_LEVEL, f"{tid}: bad level {level!r}")
        require(status in VALID_STATUS, f"{tid}: bad status {status!r}")
        require(module in registry["modules"], f"{tid}: unknown module {module!r}")
        require("labels" in term and "ja" in term["labels"] and "en" in term["labels"], f"{tid}: must carry both ja and en labels")
        require("definition_en" in term and term["definition_en"].strip(), f"{tid}: missing English definition")
        require(term.get("sources"), f"{tid}: must cite at least one source")
        if level == "propose":
            require(term.get("scope_note_en"), f"{tid}: proposed term must include scope_note_en")
        if kind == "individual":
            require("type" in term, f"{tid}: individual missing type")
        else:
            require("parent" in term, f"{tid}: missing parent")
        for e in term.get("edinet_elements", []):
            edinet_element_iri(e)  # validates

    for term in registry["terms"]:
        if term.get("parent"):
            resolve_identifier(term["parent"], registry, ids)
        if term.get("type"):
            resolve_identifier(term["type"], registry, ids)


def ontology_header(g: Graph, mod_name: str, mod: dict[str, Any], registry: dict[str, Any]) -> URIRef:
    iri = module_iri(mod, registry)
    version_iri = URIRef(str(iri).rstrip("/") + f"/{registry['version']}/")
    g.add((iri, RDF.type, OWL.Ontology))
    g.add((iri, OWL.versionIRI, version_iri))
    g.add((iri, OWL.versionInfo, Literal(registry["version"])))
    g.add((iri, RDFS.label, Literal(mod["label_en"], lang="en")))
    g.add((iri, RDFS.label, Literal(mod["label_ja"], lang="ja")))
    g.add((iri, DCTERMS.license, URIRef("https://opensource.org/licenses/MIT")))
    g.add((iri, DCTERMS.source, URIRef("https://spec.edmcouncil.org/fibo/")))
    if mod_name == "edinet-alignment":
        g.add((iri, DCTERMS.source, URIRef("https://www.fsa.go.jp/search/20251111.html")))
    return iri


def build(registry: dict[str, Any]) -> dict[str, Graph]:
    validate_registry(registry)
    known_terms = {t["id"] for t in registry["terms"]}

    graphs: dict[str, Graph] = {}
    ontology_iris: dict[str, URIRef] = {}
    for mod_name, mod in registry["modules"].items():
        g = Graph()
        bind_all(g, registry)
        ontology_iris[mod_name] = ontology_header(g, mod_name, mod, registry)
        graphs[mod_name] = g

    edinet_elements_by_module: dict[str, set[str]] = defaultdict(set)

    for term in registry["terms"]:
        mod_name = term["module"]
        g = graphs[mod_name]
        ontology_iri = ontology_iris[mod_name]
        tid = term["id"]
        iri = term_iri(tid, registry)
        kind = term.get("kind", "class")

        if kind == "class":
            parent = resolve_identifier(term["parent"], registry, known_terms)
            g.add((iri, RDF.type, OWL.Class))
            g.add((iri, RDFS.subClassOf, parent))
        elif kind == "object_property":
            parent = resolve_identifier(term["parent"], registry, known_terms)
            g.add((iri, RDF.type, OWL.ObjectProperty))
            g.add((iri, RDFS.subPropertyOf, parent))
        elif kind == "datatype_property":
            parent = resolve_identifier(term["parent"], registry, known_terms)
            g.add((iri, RDF.type, OWL.DatatypeProperty))
            g.add((iri, RDFS.subPropertyOf, parent))
        elif kind == "annotation_property":
            parent = resolve_identifier(term["parent"], registry, known_terms)
            g.add((iri, RDF.type, OWL.AnnotationProperty))
            g.add((iri, RDFS.subPropertyOf, parent))
        elif kind == "individual":
            typ = resolve_identifier(term["type"], registry, known_terms)
            g.add((iri, RDF.type, OWL.NamedIndividual))
            g.add((iri, RDF.type, typ))
        else:  # pragma: no cover - guarded above
            raise AssertionError(kind)

        add_common_metadata(g, iri, term, ontology_iri, registry)
        for e in term.get("edinet_elements", []):
            edinet_elements_by_module["edinet-alignment"].add(e)

    # Add explicit EDINET element SKOS concepts to the alignment module.
    if "edinet-alignment" in graphs:
        add_edinet_concepts(
            graphs["edinet-alignment"],
            registry,
            ontology_iris["edinet-alignment"],
            edinet_elements_by_module["edinet-alignment"],
        )

    return graphs


def write_outputs(graphs: dict[str, Graph], registry: dict[str, Any]) -> None:
    ontology_dir = REPO / "ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    aggregate = Graph()
    bind_all(aggregate, registry)

    for mod_name, g in graphs.items():
        out = REPO / registry["modules"][mod_name]["path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        g.serialize(destination=out, format="turtle")
        print(f"wrote {out.relative_to(REPO)} ({len(g)} triples)")
        for triple in g:
            aggregate.add(triple)

    aggregate.serialize(destination=AGGREGATE_OUT, format="turtle")
    # Compatibility for the original scaffold path; now an aggregate, not just core.
    aggregate.serialize(destination=LEGACY_AGGREGATE_OUT, format="turtle")
    print(f"wrote {AGGREGATE_OUT.relative_to(REPO)} ({len(aggregate)} triples)")
    print(f"wrote {LEGACY_AGGREGATE_OUT.relative_to(REPO)} ({len(aggregate)} triples; compatibility aggregate)")


def main() -> int:
    registry = yaml.safe_load(REGISTRY.read_text())
    graphs = build(registry)
    write_outputs(graphs, registry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
