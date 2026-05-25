# J-FIBO Vision

J-FIBO is a **Japanese-finance extension of FIBO**: a canonical OWL/SHACL
dictionary of the roles, responsibilities, reporting regimes, and
relationships specific to the Japanese securities-disclosure system, with
verbatim alignment to the FSA-published EDINET XBRL taxonomy.

J-FIBO is a **dictionary**, not an application. It says what a 政策保有株式
disclosure means, who is the holder of record vs the beneficial holder,
which regime (FIEL / Companies Act / JPX Listing Rules / Corporate
Governance Code) governs which disclosure, and which EDINET XBRL element
is the official source of which fact. It does not say anything about how
a consumer should reason, summarize, score, or back-trace those facts.

## What J-FIBO is

* **A canonical dictionary.** Roles, responsibilities, regimes,
  relationships, instrument types, holder-role distinctions
  (信託口 / カストディ / 常任代理人 / ADR預託機関 / 個人株主), and
  atomic disclosure-claim types (`MajorShareholderClaim`,
  `BorrowingsClaim`, `CommercialPaperClaim`, `PolicyShareholding`,
  `CrossShareholdingClaim`, `MainBankCandidate`).

* **A faithful alignment layer over the FSA EDINET XBRL taxonomy.**
  Every aligned element carries the FSA-published 標準ラベル in 日本語
  AND English, the 冗長ラベル, the XBRL `periodType`, the XBRL item
  `type`, the abstract flag, and the EDINET prefix family — verbatim,
  no fabrication, no silent translation. When the FSA leaves a cell
  blank, J-FIBO leaves it blank too.

* **A claim-level provenance + SHACL discipline.** Every claim carries
  `prov:wasDerivedFrom`, `prov:generatedAtTime`, `dcterms:valid`, an
  `informationStatus` from a closed vocabulary, and may carry a
  `normativeStatus`. SHACL shapes enforce these as guarantees so a
  downstream consumer can rely on them.

## What J-FIBO is NOT

* J-FIBO is **not** an information-flow framework, an audit framework,
  a backtracer, a causal-discovery engine, or a hallucination guard.
  These are *applications* a consumer can build *on top of* J-FIBO. The
  ontology stays out of that layer so different consumers can wire
  different applications to the same canonical facts.

* J-FIBO is **not** an interpretation of what a disclosure *means*
  economically. It states what the disclosure *says*, who the named
  parties are, which regime requires it, and what the FSA's official
  label is. Whether a particular 主要株主 entry indicates a strategic
  alliance or a pure-investment position is a downstream judgement.

* J-FIBO is **not** endorsed by the FSA, Digital Agency, JPX, BOJ,
  FISC, FDUA, EDM Council, or OMG. It is a single-author research
  artifact. See [`governance-status.md`](governance-status.md).

## What an application built on J-FIBO might do

Examples — **not** part of the ontology, deliberately outside scope:

* Information-flow / information-boundary reasoning: distinguishing
  disclosed facts from analyst inferences from counterfactuals; this is
  exactly the kind of consumer-side discipline `informationStatus`
  exists to *enable*, but the ontology does not enforce which boundary
  a consumer draws.
* Cross-shareholding triangulation across filers (our materializer
  ships one such application as a demo).
* Backtracing from a market event to candidate causal disclosures.
* LLM grounding / hallucination control.
* Translation QA against EDINET English filings.

## Why the `jfibo:` prefix and J-FIBO brand

* Brand `J-FIBO` follows the J-REIT / J-GAAP / J-SOX pattern: instantly
  legible to a Japanese finance audience as "the Japan version of FIBO".
* Technical prefix `jfibo:` is short and brand-direct. Pre-v0.4 we
  briefly used `jpfibo:` to rhyme with EDINET XBRL prefixes
  (`jpcrp` / `jpdei` / `jppfs`), but those rhyme inside the XBRL/XML
  layer; J-FIBO is OWL/RDF; XBRL ↔ RDF interoperability is achieved by
  URI mapping (`owl:equivalentClass` between full IRIs), not prefix
  letters. The shorter, brand-direct `jfibo:` wins on every surface
  that actually matters.

## Semantic-loss benchmark — what it measures

The benchmark scores **per-claim semantic-field coverage** of vanilla
FIBO vs J-FIBO. It does **not** benchmark any LLM, agent, or pipeline.
It measures *what fraction of the disclosed semantic content can be
represented at all* in each ontology.

```
vanilla_coverage  = |fields representable in FIBO|        / |expected fields|
jfibo_coverage    = |fields representable in J-FIBO|      / |expected fields|
jfibo_gain        = jfibo_coverage − vanilla_coverage
```

Latest curated benchmark (19 cases):
```
mean vanilla FIBO coverage:  0.297
mean J-FIBO coverage:        1.000
mean J-FIBO gain:            0.703
```

Latest real-EDINET benchmark (223 materialized claims across Toyota /
ITOCHU / MUFG / SoftBank FY2024 annual securities reports):
```
mean vanilla FIBO coverage:  0.280
mean J-FIBO coverage:        0.973
mean J-FIBO gain:            0.693
```

By claim kind (real-data):
```
PolicyShareholding       176  vanilla 0.268  jfibo 0.969  gain 0.701
MajorShareholderClaim     40  vanilla 0.364  jfibo 1.000  gain 0.636
CrossShareholdingClaim     1  vanilla 0.286  jfibo 1.000  gain 0.714
BorrowingsClaim            5  vanilla 0.083  jfibo 0.900  gain 0.817
CommercialPaperClaim       1  vanilla 0.091  jfibo 1.000  gain 0.909
```

## Building-trajectory PROV

Every minted term carries `prov:wasAttributedTo <contributor>` and
`prov:wasGeneratedBy <session>` so the J-FIBO trajectory is queryable
as RDF and the markdown view at
[`docs/building-trajectory.md`](building-trajectory.md) is generated
from the same triples.

Provisional contributor: `jfibo-wg-bootstrap` (a single-author
editorial seed). See `registry/contributors.yaml`.

## Modules

```
ontology/jfibo-core.ttl
ontology/jfibo-information-status.ttl
ontology/jfibo-normative-status.ttl
ontology/jfibo-reporting-regime.ttl
ontology/jfibo-document-type.ttl
ontology/jfibo-holder-role.ttl
ontology/jfibo-disclosure-claim.ttl
ontology/jfibo-institutional-context.ttl
ontology/jfibo-edinet-alignment.ttl
ontology/jfibo.ttl                    # aggregate, generated
shapes/jfibo-shapes.ttl               # SHACL discipline
```

## Pipeline modules

```
scripts/build_ontology.py             # registry YAML → OWL/TTL modules
scripts/build_edinet_focus.py         # EDINET XBRL XLSX → focused JSON view
scripts/download_edinet_taxonomy.py   # fetch FSA taxonomy zip + xlsx
scripts/find_target_filings.py        # EDINET API → target docID list
scripts/edinet_client.py              # EDINET API helper
scripts/extract_xbrl_facts.py         # iXBRL → typed rows + text blocks
scripts/parse_major_shareholders.py   # 大株主の状況 → JSON
scripts/parse_borrowings.py           # 借入金等明細表 → JSON
scripts/materialize_claims.py         # JSON → J-FIBO RDF + cross-shareholding triangulation
scripts/build_trajectory.py           # RDF → Markdown/Mermaid view
```
