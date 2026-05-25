# Modeling Principles

## REUSE / ALIGN / PROPOSE

Every term in the registry declares its level:

* `reuse`   — use the official IRI directly; no J-FIBO class minted.
* `align`   — Japanese specialization of a verified official parent
  (`cmns-org:FormalOrganization`, `fibo-be-le-cb:Corporation`,
  `fibo-sec-eq-eq:ListedShare`, …).
* `propose` — new term required because no official term fits; must carry a
  scope note and at least one source.

## Triples come from rdflib, not f-strings

`scripts/build_ontology.py` constructs every triple through
`rdflib.Graph.add(...)`. The serializer (`Graph.serialize`) owns prefix and
escape consistency. We do not template Turtle.

## Disclosure claims, not ownership edges

A policy shareholding is **a claim about disclosed evidence**, not a bare
ownership edge. A `jfibo:PolicyShareholding` carries investor, issuer,
share count, carrying amount, holding purpose, reciprocal-holding marker,
evidence element, information status, evidence locator, and reporting
period validity.

This separation lets J-FIBO represent disclosed *and* hypothesized
relationships in the same graph without conflating them.

## SHACL enforces the discipline

Shapes for `DisclosureClaim`, `PolicyShareholding`, `MainBankCandidate`,
`CrossShareholdingClaim`, and `EvidenceItem` ensure that:

* every claim cites at least one evidence locator;
* policy shareholdings carry investor, issuer, and an EDINET evidence
  element;
* main-bank candidates carry at least two distinct evidence items and
  cannot use disclosed/observed status;
* information status is from the closed vocabulary.
