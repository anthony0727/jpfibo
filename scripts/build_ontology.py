"""Build J-FIBO OWL/RDFS modules from the controlled registry.

Discipline:
  * No string-templated Turtle. Triples flow through rdflib.Graph.add(...).
  * Official vocabularies are explicit prefixes; J-FIBO mints only local terms
    listed in registry/terms.yaml.
  * Every minted term has bilingual labels, definition, source, status, and
    proposed terms have scope notes.
  * Properties may declare domain/range; these become rdfs:domain / rdfs:range.
  * Every term may declare contributed_by and session, which become PROV
    attribution (prov:wasAttributedTo / prov:wasGeneratedBy) so the J-FIBO
    building trajectory is queryable as RDF.

Run:
    uv run python scripts/build_ontology.py
"""
from __future__ import annotations

import datetime as dt
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
CONTRIBUTORS = REPO / "registry" / "contributors.yaml"
AGGREGATE_OUT = REPO / "ontology" / "jfibo.ttl"

# Official / upstream prefix table.
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
    "foaf": Namespace("http://xmlns.com/foaf/0.1/"),
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

JPFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")
CONTRIBUTOR_BASE = "https://w3id.org/jfibo/contributor/"
SESSION_BASE = "https://w3id.org/jfibo/session/"


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


def contributor_iri(cid: str) -> URIRef:
    return URIRef(f"{CONTRIBUTOR_BASE}{cid}")


def session_iri(sid: str) -> URIRef:
    return URIRef(f"{SESSION_BASE}{sid}")


def add_common_metadata(
    g: Graph,
    iri: URIRef,
    term: dict[str, Any],
    ontology_iri: URIRef,
    registry: dict[str, Any],
    contributors: dict[str, dict[str, Any]],
    sessions: dict[str, dict[str, Any]],
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
    g.add((iri, JPFIBO.status, Literal(term.get("status", "proposed"))))
    g.add((iri, JPFIBO.level, Literal(term["level"])))
    if term.get("edinet_elements"):
        for element in term["edinet_elements"]:
            eiri = edinet_element_iri(element)
            g.add((iri, JPFIBO.mapsToEdinetElement, eiri))
    # Building-trajectory provenance
    if term.get("contributed_by"):
        cid = term["contributed_by"]
        require(cid in contributors, f"{term['id']}: unknown contributor {cid!r}")
        g.add((iri, PROV.wasAttributedTo, contributor_iri(cid)))
    if term.get("session"):
        sid = term["session"]
        require(sid in sessions, f"{term['id']}: unknown session {sid!r}")
        g.add((iri, PROV.wasGeneratedBy, session_iri(sid)))


def add_edinet_concepts(g: Graph, registry: dict[str, Any], ontology_iri: URIRef, elements: set[str]) -> None:
    for element in sorted(elements):
        prefix, local = element.split(":", 1)
        iri = edinet_element_iri(element)
        g.add((iri, RDF.type, SKOS.Concept))
        g.add((iri, RDF.type, JPFIBO.EDINETTaxonomyElement))
        g.add((iri, SKOS.notation, Literal(element)))
        g.add((iri, RDFS.isDefinedBy, ontology_iri))
        g.add((iri, DCTERMS.source, URIRef(EDINET_XBRL_NAMESPACES[prefix])))
        g.add((iri, SKOS.prefLabel, Literal(local, lang="en")))


def validate_registry(
    registry: dict[str, Any],
    contributors: dict[str, dict[str, Any]],
    sessions: dict[str, dict[str, Any]],
) -> None:
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
            edinet_element_iri(e)
        if term.get("contributed_by"):
            require(term["contributed_by"] in contributors, f"{tid}: unknown contributor {term['contributed_by']!r}")
        if term.get("session"):
            require(term["session"] in sessions, f"{tid}: unknown session {term['session']!r}")

    for term in registry["terms"]:
        if term.get("parent"):
            resolve_identifier(term["parent"], registry, ids)
        if term.get("type"):
            resolve_identifier(term["type"], registry, ids)
        if term.get("domain"):
            resolve_identifier(term["domain"], registry, ids)
        if term.get("range"):
            resolve_identifier(term["range"], registry, ids)


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


def emit_contributors_and_sessions(
    g: Graph,
    contributors: dict[str, dict[str, Any]],
    sessions: dict[str, dict[str, Any]],
    ontology_iri: URIRef,
) -> None:
    foaf = PREFIX_TABLE["foaf"]
    for cid, c in contributors.items():
        iri = contributor_iri(cid)
        g.add((iri, RDF.type, PROV.Agent))
        g.add((iri, RDF.type, foaf.Agent))
        g.add((iri, RDFS.isDefinedBy, ontology_iri))
        g.add((iri, SKOS.prefLabel, Literal(c["label_en"], lang="en")))
        if c.get("label_ja"):
            g.add((iri, SKOS.prefLabel, Literal(c["label_ja"], lang="ja")))
        if c.get("organization"):
            g.add((iri, foaf.member, Literal(c["organization"])))
        if c.get("role"):
            g.add((iri, JPFIBO.contributorRole, Literal(c["role"])))
        if c.get("note"):
            g.add((iri, SKOS.scopeNote, Literal(c["note"].strip(), lang="en")))
    for sid, s in sessions.items():
        iri = session_iri(sid)
        g.add((iri, RDF.type, PROV.Activity))
        g.add((iri, RDFS.isDefinedBy, ontology_iri))
        if s.get("goal"):
            g.add((iri, SKOS.definition, Literal(s["goal"], lang="en")))
        if s.get("date"):
            g.add((iri, PROV.startedAtTime, Literal(f"{s['date']}T00:00:00+09:00", datatype=XSD.dateTime)))
            g.add((iri, DCTERMS.date, Literal(str(s["date"]), datatype=XSD.date)))
        for cid in s.get("contributors", []):
            g.add((iri, PROV.wasAssociatedWith, contributor_iri(cid)))


def build(
    registry: dict[str, Any],
    contributors_doc: dict[str, Any],
) -> dict[str, Graph]:
    contributors = {c["id"]: c for c in contributors_doc.get("contributors", [])}
    sessions = {s["id"]: s for s in contributors_doc.get("sessions", [])}
    validate_registry(registry, contributors, sessions)
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
        else:  # pragma: no cover
            raise AssertionError(kind)

        if term.get("domain"):
            g.add((iri, RDFS.domain, resolve_identifier(term["domain"], registry, known_terms)))
        if term.get("range"):
            g.add((iri, RDFS.range, resolve_identifier(term["range"], registry, known_terms)))

        add_common_metadata(g, iri, term, ontology_iri, registry, contributors, sessions)
        for e in term.get("edinet_elements", []):
            edinet_elements_by_module["edinet-alignment"].add(e)

    if "edinet-alignment" in graphs:
        add_edinet_concepts(
            graphs["edinet-alignment"],
            registry,
            ontology_iris["edinet-alignment"],
            edinet_elements_by_module["edinet-alignment"],
        )

    # Emit contributors / sessions into the core module for stable findability.
    emit_contributors_and_sessions(
        graphs["core"], contributors, sessions, ontology_iris["core"]
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
    print(f"wrote {AGGREGATE_OUT.relative_to(REPO)} ({len(aggregate)} triples)")


def main() -> int:
    registry = yaml.safe_load(REGISTRY.read_text())
    contributors_doc = yaml.safe_load(CONTRIBUTORS.read_text())
    graphs = build(registry, contributors_doc)
    write_outputs(graphs, registry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
