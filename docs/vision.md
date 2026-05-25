# J-FIBO Vision

J-FIBO is a Japanese-finance extension of FIBO whose immediate goal is to make
Japanese corporate disclosures *auditable across the information boundary* —
not just structurally mapped.

## North star

> EDINET tells us what was disclosed.
> FIBO tells us what formal financial object it refers to.
> J-FIBO tells us what Japanese institutional status the claim has — legal
> obligation, accounting disclosure, governance relationship, institutional
> expectation, or inferred hypothesis — and whether the claim sits inside
> the information boundary.

## Why not just use FIBO

Vanilla FIBO types financial objects (Share, Bank, LegalEntity). Japanese
securities reports encode several semantic fields that are structurally
absent from FIBO classes:

1. **Holding purpose** (保有目的) — disclosed verbatim per policy shareholding.
2. **Non-pure-investment status** (純投資目的以外) — a regulatory class.
3. **Reciprocal-holding marker** (株式の相互保有) — a boolean-bearing concept.
4. **Quantitative effects of shareholding** (定量的な保有効果) — narrative.
5. **Reason for share-count change** (株式数が増加した理由) — narrative.
6. **Holder role** (信託口 / カストディ / 常任代理人 / ADR預託機関 / 個人株主) —
   the trustee-vs-beneficial-vs-custody distinction that vanilla FIBO erases.
7. **Information status** — observed / disclosed / evidence-backed inferred /
   hypothesized / counterfactual / predicted / outside information boundary.
8. **Normative status** — legal obligation / accounting disclosure /
   governance disclosure / institutional expectation / inferred hypothesis.
9. **Reporting regime** — Companies Act / FIEL / JPX listing rules /
   Cabinet-office ordinance / Japan CG Code / Banking Act.
10. **Document type** — annual / quarterly / semi-annual / governance /
    large-shareholding / extraordinary, mapped to EDINET document codes.
11. **Evidence locator** — the EDINET XBRL element underlying the claim.
12. **Reporting period validity** — the fiscal year the claim refers to.

A naïve FIBO mapping silently drops most of these and lets the consumer
mistake a *narrative policy holding* for a *bare ownership edge*.

## Why the `jpfibo:` prefix

The EDINET vocabulary family uses `jpcrp / jpdei / jppfs / jpigp / jpsps /
jplvh / jpaud / jpctl`. An FSA or Digital Agency engineer reading Turtle
decides "native vs foreign" in the first five seconds based on the prefix.
`jpfibo:` reads as a member of that family.

The brand "J-FIBO" stays (matches EDM Council Profile-naming conventions);
the Japanese formal name 金融意味基盤・日本版 stays. Only the RDF prefix
changed from `jfibo:` to `jpfibo:` for ecosystem affinity.

## Quantification: semantic-loss benchmark

We score two coverage numbers on each claim:

* `vanilla_coverage` = fraction of the expected semantic fields representable
  natively in vanilla FIBO.
* `jfibo_coverage`   = fraction representable in J-FIBO + EDINET alignment.

Running v0.2 on real EDINET FY2024 disclosures (Toyota, ITOCHU, MUFG,
SoftBank Group) over **217 materialized claims** (176 PolicyShareholding +
40 MajorShareholderClaim + 1 triangulated CrossShareholdingClaim):

```
mean vanilla FIBO coverage:  0.285
mean J-FIBO coverage:        0.975
mean J-FIBO gain:            0.690
```

Curated benchmark (15 cases): vanilla `0.34` → J-FIBO `1.00` → gain `0.66`.

## Building-trajectory layer

Every minted term carries `prov:wasAttributedTo` (a contributor) and
`prov:wasGeneratedBy` (a session). The aggregate Turtle is queryable as RDF,
and `scripts/build_trajectory.py` renders a human-readable timeline at
`docs/building-trajectory.md`. This is the seed for a future J-FIBO Working
Group governance layer — explicit attribution of vocabulary contributions,
so that future merges, splits, and ratifications can be traced like
FIBO/EDM Council should but doesn't.

Provisional contributor: `jfibo-wg-bootstrap`. Names of institutional
contributors (Digital Agency, FSA, JPX, EDM Council Japan Chapter / FDUA /
FISC) replace it as the working group formalizes.

## Scope of v0.2

Modules:

```
ontology/jpfibo-core.ttl
ontology/jpfibo-information-status.ttl
ontology/jpfibo-normative-status.ttl
ontology/jpfibo-reporting-regime.ttl
ontology/jpfibo-document-type.ttl
ontology/jpfibo-holder-role.ttl
ontology/jpfibo-disclosure-claim.ttl
ontology/jpfibo-institutional-context.ttl
ontology/jpfibo-edinet-alignment.ttl
```

Claim families: `PolicyShareholding`, `MajorShareholderClaim`,
`BorrowingsClaim`, `CrossShareholdingClaim`, `MainBankCandidate`,
`InstitutionalRelationshipHypothesis`. All subclasses of `DisclosureClaim`.

Pipelines:

```
scripts/download_edinet_taxonomy.py     # FSA taxonomy
scripts/build_edinet_focus.py           # focused taxonomy view
scripts/edinet_client.py                # EDINET v2 API (uses EDINET_API_KEY)
scripts/find_target_filings.py
scripts/extract_xbrl_facts.py           # XBRL -> per-filing JSON
scripts/parse_major_shareholders.py     # MajorShareholders HTML -> rows
scripts/materialize_claims.py           # JSON -> J-FIBO RDF + triangulation
scripts/build_ontology.py               # registry -> modular OWL/TTL
scripts/validate.py                     # SHACL validation
scripts/build_trajectory.py             # Mermaid timeline
benchmark/semantic_loss.py              # curated benchmark
benchmark/real_data_loss.py             # real-EDINET benchmark
```

## What v0.2 deliberately does not do

* No hard-asserted main-bank or keiretsu relations.
* No prediction layer; explanation/audit-first.
* No entity resolution against the National Tax Agency 法人番号 registry's
  full master list; the curated `registry/entities.yaml` covers the
  ~20 entities that the current benchmark corpus touches.
* No automated OWL-RL materialization layer (rdflib supports it; v0.2
  validates with SHACL only).
