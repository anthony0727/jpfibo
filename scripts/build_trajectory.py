"""Render the J-FIBO building trajectory as Markdown + Mermaid.

The trajectory is grounded in the PROV attribution emitted by the builder:
each term carries prov:wasGeneratedBy a session, and each session carries
prov:wasAssociatedWith one or more contributors. We summarize:

  * per-session term counts (by module and by kind)
  * per-contributor term counts
  * a Mermaid timeline diagram

Output: docs/building-trajectory.md
"""
from __future__ import annotations

import collections
from pathlib import Path

import yaml
from rdflib import Graph, Namespace
from rdflib.namespace import PROV, RDF

REPO = Path(__file__).resolve().parents[1]
ONT = REPO / "ontology" / "jpfibo.ttl"
CONTRIBUTORS = REPO / "registry" / "contributors.yaml"
REGISTRY = REPO / "registry" / "terms.yaml"
OUT = REPO / "docs" / "building-trajectory.md"

JPFIBO = Namespace("https://w3id.org/jfibo/ontology/JP/core/")


def main() -> int:
    registry = yaml.safe_load(REGISTRY.read_text())
    contributors_doc = yaml.safe_load(CONTRIBUTORS.read_text())
    contributors = {c["id"]: c for c in contributors_doc["contributors"]}
    sessions = {s["id"]: s for s in contributors_doc["sessions"]}

    by_session = collections.defaultdict(list)
    by_contributor = collections.defaultdict(list)
    by_module_in_session = collections.defaultdict(lambda: collections.Counter())
    by_kind_in_session = collections.defaultdict(lambda: collections.Counter())
    for term in registry["terms"]:
        s_id = term.get("session")
        c_id = term.get("contributed_by")
        if s_id:
            by_session[s_id].append(term)
            by_module_in_session[s_id][term["module"]] += 1
            by_kind_in_session[s_id][term.get("kind", "class")] += 1
        if c_id:
            by_contributor[c_id].append(term)

    lines = ["# J-FIBO Building Trajectory", ""]
    lines.append(
        "Derived from `registry/terms.yaml` (per-term `contributed_by` + `session`) "
        "and `registry/contributors.yaml`. Every minted term carries the same "
        "attribution as `prov:wasAttributedTo` + `prov:wasGeneratedBy` triples "
        "in `ontology/jpfibo.ttl`, so this view is also queryable via SPARQL."
    )
    lines.append("")
    lines.append(
        "> **Governance status**: J-FIBO is currently a single-author research "
        "seed. No Japanese institutional body has endorsed, reviewed, or "
        "participated. See [governance-status.md](governance-status.md).")
    lines.append("")
    lines.append("## Sessions")
    lines.append("")
    for s_id, s in sessions.items():
        n = len(by_session[s_id])
        lines.append(f"### {s_id}")
        lines.append("")
        lines.append(f"- date: {s.get('date')}")
        lines.append(f"- goal: {s.get('goal')}")
        lines.append(f"- terms contributed: {n}")
        if n:
            mods = ", ".join(f"{m}={c}" for m, c in by_module_in_session[s_id].most_common())
            kinds = ", ".join(f"{k}={c}" for k, c in by_kind_in_session[s_id].most_common())
            lines.append(f"- modules: {mods}")
            lines.append(f"- kinds: {kinds}")
        lines.append("")
    lines.append("## Contributors")
    lines.append("")
    for c_id, c in contributors.items():
        terms = by_contributor[c_id]
        lines.append(f"### {c_id}")
        lines.append("")
        lines.append(f"- role: {c.get('role')}")
        lines.append(f"- organization: {c.get('organization')}")
        lines.append(f"- terms attributed: {len(terms)}")
        lines.append("")
        if c.get("note"):
            lines.append(f"> {c['note'].strip()}")
            lines.append("")

    lines.append("## Mermaid timeline")
    lines.append("")
    lines.append("```mermaid")
    lines.append("timeline")
    lines.append("    title J-FIBO contribution timeline")
    by_date = collections.defaultdict(list)
    for s_id, s in sessions.items():
        by_date[str(s.get("date"))].append((s_id, len(by_session[s_id])))
    for d in sorted(by_date):
        lines.append(f"    {d}")
        for s_id, n in by_date[d]:
            lines.append(f"        : {s_id} (+{n} terms)")
    lines.append("```")
    lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    main()
