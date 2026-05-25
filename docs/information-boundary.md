# Information boundary — application-layer note

> **Scope note.** This document describes a *discipline a consumer of
> J-FIBO can adopt*. It is **not** part of the ontology's stated
> purpose. The ontology stays at the dictionary layer (roles,
> responsibilities, regimes, relationships); whether a consumer applies
> information-boundary reasoning, causal-discovery techniques,
> backtracing, or pure summarization is the consumer's choice and lives
> outside the ontology. See [`vision.md`](vision.md) for the ontology's
> actual scope.

## The discipline

A J-FIBO consumer that wants to keep disclosed facts auditably separate
from inferences can use the closed `jfibo:informationStatus` vocabulary
on every claim:

```
observed | disclosed | evidence-backed inferred |
hypothesized | counterfactual | predicted | outside information boundary
```

The SHACL shape enforces *that the field is present and drawn from the
closed vocabulary*; it does **not** enforce that the consumer chose the
right value. That judgement, and the broader discipline it serves, is
on the consumer side.

## Why `jfibo:MainBankCandidate` forbids `Disclosed` / `Observed`

Main-bank relationships are inferred, not disclosed. The SHACL shape
forbids `jfibo:MainBankCandidate` from carrying `jfibo:Disclosed` or
`jfibo:Observed` and requires at least two distinct evidence sources.
This is the strongest example of an *ontology-level* rule serving the
information-boundary discipline — and it exists because conflating
"plausibly true based on borrowings + shareholder data" with "the filer
disclosed this" would be a category error in *any* consumer
application, not just one.

## Cross-shareholding triangulation as an example consumer

`scripts/materialize_claims.py` ships a small application that
materializes `jfibo:CrossShareholdingClaim` records when filer A's
policy-shareholding disclosures include filer B and filer B's
major-shareholder table includes filer A. The result is marked
`informationStatus = EvidenceBackedInferred` and
`normativeStatus = InferredHypothesis` — because the *triangulation* is
the consumer's inference, even though the *underlying disclosures* are
disclosed facts.

That is the pattern: J-FIBO gives you the vocabulary to be honest about
which layer a claim lives at; what you do with that honesty is yours.
