# J-FIBO Vision (v0.1)

J-FIBO is a Japanese-finance extension of FIBO whose immediate goal is to
make Japanese corporate disclosures *auditable across the information
boundary* — not just structurally mapped.

## North star

> EDINET tells us what was disclosed.
> FIBO tells us what formal financial object it refers to.
> J-FIBO tells us what Japanese institutional status the claim has — legal
> obligation, accounting disclosure, governance relationship, institutional
> expectation, or inferred hypothesis — and whether the claim sits inside
> the information boundary.

## Why not just use FIBO

Vanilla FIBO is excellent at typing *objects* (Share, Bank, LegalEntity).
But Japanese securities reports encode several semantic fields that are
structurally absent from FIBO classes:

1. **Holding purpose** (保有目的) — disclosed verbatim for every policy
   shareholding.
2. **Non-pure-investment status** (純投資目的以外) — a regulatory class.
3. **Reciprocal holding marker** (株式の相互保有) — disclosed as a
   boolean-bearing concept.
4. **Quantitative effects of shareholding** (定量的な保有効果) — narrative.
5. **Reason for share-count change** (株式数が増加した理由) — narrative.
6. **Information status** — observed, disclosed, evidence-backed inferred,
   hypothesized, counterfactual, predicted, outside information boundary.
7. **Evidence locator** — the EDINET XBRL element underlying the claim.
8. **Reporting period validity** — the fiscal year the claim refers to.

A naïve FIBO mapping silently drops 7 of these 8 fields and lets the
consumer mistake a *narrative policy holding* for a *bare ownership edge*.

## Quantification: semantic-loss benchmark

We score two coverage numbers on each claim:

* `vanilla_coverage` = fraction of the 10 expected semantic fields that
  can be represented natively in vanilla FIBO.
* `jfibo_coverage`   = fraction representable in J-FIBO + EDINET alignment.

Running the benchmark on real EDINET FY2024 disclosures (Toyota, Mitsubishi
Corporation, MUFG) over 176 PolicyShareholding claims:

```
mean vanilla FIBO coverage:  0.294
mean J-FIBO coverage:        0.966
mean semantic-loss rate:     0.706
mean J-FIBO gain:            0.672
```

The curated benchmark (13 cases spanning policy shareholding, cross-
shareholding, main-bank candidacy, borrowings evidence, institutional
relationship hypothesis) reports comparable numbers (`vanilla=0.32,
jfibo=1.00, gain=0.68`).

## Scope of v0.1

Modules:

```
ontology/jfibo-core.ttl
ontology/jfibo-information-status.ttl
ontology/jfibo-disclosure-claim.ttl
ontology/jfibo-institutional-context.ttl
ontology/jfibo-edinet-alignment.ttl
```

Pipelines:

```
scripts/download_edinet_taxonomy.py   # FSA-published EDINET taxonomy
scripts/build_edinet_focus.py         # focused taxonomy view (JSON)
scripts/edinet_client.py              # EDINET v2 API client
scripts/find_target_filings.py        # locate annual securities reports
scripts/extract_xbrl_facts.py         # extract focused XBRL facts
scripts/materialize_claims.py         # extracted -> J-FIBO RDF claims
scripts/build_ontology.py             # registry -> modular OWL/TTL
scripts/validate.py                   # SHACL validation of any data graph
benchmark/semantic_loss.py            # curated-case benchmark
benchmark/real_data_loss.py           # real-EDINET claim benchmark
```

## What we deliberately do not do yet

* No hard-asserted main-bank or keiretsu relations.
* No prediction layer; explanation/audit-first.
* No entity resolution to corporate-number registry (planned).
* No automated OWL-RL materialization layer (rdflib supports it; not needed
  for v0.1 SHACL-only validation).
