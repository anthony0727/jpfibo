"""Run SHACL validation. Loads the J-FIBO ontology (closed vocabulary needs it)
and all *.ttl shapes under shapes/. Returns non-zero on conformance failure
unless --expect-fail is passed."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

REPO = Path(__file__).resolve().parents[1]


def load_shapes(shape_paths: list[Path]) -> Graph:
    g = Graph()
    for p in shape_paths:
        g.parse(p)
    return g


def load_ontology(extra_paths: list[Path] | None = None) -> Graph:
    g = Graph()
    onto_dir = REPO / "ontology"
    for ttl in sorted(onto_dir.glob("jfibo-*.ttl")):
        g.parse(ttl)
    if extra_paths:
        for p in extra_paths:
            g.parse(p)
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("data", type=Path)
    ap.add_argument(
        "--shapes",
        type=Path,
        action="append",
        default=None,
        help="SHACL shapes file; may be passed multiple times. Defaults to shapes/*.ttl",
    )
    ap.add_argument("--expect-fail", action="store_true")
    args = ap.parse_args()

    shape_paths = args.shapes or sorted((REPO / "shapes").glob("*.ttl"))
    if not shape_paths:
        print("no SHACL shapes found", file=sys.stderr)
        return 2

    data = Graph().parse(args.data)
    shapes = load_shapes(shape_paths)
    ontology = load_ontology()

    conforms, _report_graph, report_text = validate(
        data_graph=data,
        shacl_graph=shapes,
        ont_graph=ontology,
        inference="rdfs",
        meta_shacl=False,
        advanced=True,
    )
    print(f"data: {args.data.name}")
    print(f"shapes: {', '.join(p.name for p in shape_paths)}")
    print(f"conforms: {conforms}")
    print(report_text.rstrip())

    if args.expect_fail:
        return 0 if not conforms else 1
    return 0 if conforms else 1


if __name__ == "__main__":
    sys.exit(main())
