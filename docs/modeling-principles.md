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
`rdflib.Graph.add(...)`. The serializer owns prefix / escape consistency.

## Information status × normative status are orthogonal

A single claim may be:

* `informationStatus = Disclosed` (a regulator-disclosed fact)
* `normativeStatus   = AccountingDisclosure` (because the disclosure rule is
  the financial-statement-regulation, not corporate governance)

J-FIBO requires explicit information status; normative status is optional
but encouraged.

## Disclosure claims, not ownership edges

Every shareholding/borrowing/relationship is **a claim about disclosed
evidence**, not a bare structural edge. Concrete subclasses of
`jpfibo:DisclosureClaim`:

* `PolicyShareholding` — 政策保有株式
* `MajorShareholderClaim` — 大株主の状況
* `BorrowingsClaim` — 借入金等明細表
* `CrossShareholdingClaim` — triangulated from two underlying claims
* `MainBankCandidate` — hypothesis-only
* `InstitutionalRelationshipHypothesis` — hypothesis-only

## Holder role is mandatory on major-shareholder claims

Japanese MajorShareholders tables are dominated by trust banks (信託口) and
custody banks acting as registered holders. SHACL requires every
`MajorShareholderClaim` to carry one of:

```
BeneficialHolder | RegisteredHolder | Trustee | CustodyBank |
StandingProxy   | ADRDepositary    | IndividualShareholder
```

This is the single biggest semantic distinction vanilla FIBO erases.

## SHACL enforces the discipline

* every `DisclosureClaim` has provenance, validity, generated-at, and an
  `informationStatus` from the closed vocabulary;
* `PolicyShareholding` requires investor, issuer, and an EDINET evidence
  element;
* `MajorShareholderClaim` requires issuer, holder, holderRole, and rank;
* `BorrowingsClaim` requires lender and borrower;
* `MainBankCandidate` cannot use `Disclosed`/`Observed` status and must
  cite ≥2 evidence items;
* `CrossShareholdingClaim` requires ≥2 evidence items.

## Building-trajectory provenance

Every minted term may carry `contributed_by` (id from
`registry/contributors.yaml`) and `session` (id of a session). The builder
emits these as `prov:wasAttributedTo` + `prov:wasGeneratedBy`. The
trajectory is queryable as RDF and renderable as a Mermaid timeline via
`scripts/build_trajectory.py`.
