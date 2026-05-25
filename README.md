# J-FIBO (金融意味基盤・日本版)

> **Governance status — read first.** J-FIBO is an **independent single-author research artifact**. It is **not** endorsed by, affiliated with, or reviewed by the FSA, Digital Agency, JPX, BOJ, FISC, FDUA, EDM Council, OMG, or any other Japanese or international body. The `J-FIBO` brand and the `jfibo:` prefix are provisional. See [`docs/governance-status.md`](docs/governance-status.md).

J-FIBO is a Japanese-finance extension of [FIBO](https://spec.edmcouncil.org/fibo/) — a **canonical OWL/SHACL dictionary** of the roles, responsibilities, reporting regimes, and relationships specific to the Japanese securities-disclosure system, with verbatim alignment to the FSA-published EDINET XBRL taxonomy.

J-FIBO is a dictionary, not an application. It says what a 政策保有株式 disclosure means, who is the holder of record vs the beneficial holder, which regime (FIEL / Companies Act / JPX Listing Rules / Corporate Governance Code) governs which disclosure, and which EDINET XBRL element is the official source of which fact. **It does not say anything about how a consumer should reason, summarize, score, or back-trace those facts.** Information-flow / information-boundary / causal-discovery applications belong to consumers; the ontology gives them the canonical vocabulary to build on. ([why](docs/vision.md))

## Status (v0.5)

| Metric | Value |
|---|---:|
| Triples | 1,740 |
| Minted J-FIBO terms | 82 |
| Aligned EDINET concepts (verbatim FSA labels) | 56 |
| Real EDINET FY2024 claims materialized | 223 |
| Claim families | PolicyShareholding · MajorShareholderClaim · BorrowingsClaim · CommercialPaperClaim · CrossShareholdingClaim · MainBankCandidate |
| Cross-shareholding triangulations (real) | 1 (Toyota Motor ↔ MUFG) |
| Vanilla-FIBO coverage on real claims | 0.280 |
| J-FIBO coverage on real claims | 0.973 |
| **Gain (real, 223 claims)** | **+0.693** |
| Gain (curated, 19 cases) | +0.703 |
| Tests | 40 / 40 passing |

Real filings processed: Toyota Motor Corp, ITOCHU, Mitsubishi UFJ FG, SoftBank Group (FY2024 有価証券報告書).

## EDINET translation fidelity

Every aligned EDINET concept now carries the FSA's published 標準ラベル in 日本語 **and** English, the 冗長ラベル, the XBRL `periodType`, the XBRL item `type`, the abstract flag, and the EDINET prefix family — verbatim. No camelCase URI-derived English is fabricated. When the FSA leaves a Japanese cell blank, J-FIBO leaves it blank too. ([test](tests/test_v05_coverage.py))

## Naming conventions

J-FIBO follows the **J-REIT / J-GAAP / J-SOX** family of Japan-localized standards:

| Surface | Form | Audience |
|---|---|---|
| Brand (papers, slides, prose) | **J-FIBO** | Humans — pattern-matches J-REIT / J-GAAP / J-SOX |
| Repo URL | **`j-fibo`** | Humans clicking links — brand visible at the click |
| Python package | **`jfibo`** | Python devs — `import jfibo` |
| RDF prefix | **`jfibo:`** | SPARQL / Turtle authors — short, brand-direct |
| IRI base | **`https://w3id.org/jfibo/`** | URI resolvers |

EDINET filings are **XBRL**; J-FIBO is **OWL/RDF**. XBRL↔RDF interoperability is achieved by URI mapping (`owl:equivalentClass` between full IRIs), not by prefix-letter rhyme; we therefore default to the shorter brand-direct `jfibo:` prefix. A `jpfibo:` alias namespace remains an option if a future EDINET-bridge use case justifies it.

## Quick start

```bash
uv sync
uv run python scripts/build_ontology.py
uv run python scripts/validate.py examples/policy-shareholding-valid.ttl
uv run python scripts/validate.py examples/policy-shareholding-invalid.ttl --expect-fail
uv run python scripts/validate.py examples/borrowings-valid.ttl
uv run python scripts/validate.py examples/commercial-paper-valid.ttl
uv run python benchmark/semantic_loss.py
uv run python scripts/build_trajectory.py
uv run python -m pytest
```

With an `EDINET_API_KEY` in `~/.env` (never committed):

```bash
uv run python scripts/download_edinet_taxonomy.py
uv run python scripts/build_edinet_focus.py
uv run python scripts/find_target_filings.py --days 400
uv run python scripts/edinet_client.py download <docID> --type 1
uv run python scripts/extract_xbrl_facts.py
uv run python scripts/parse_major_shareholders.py
uv run python scripts/parse_borrowings.py
uv run python scripts/materialize_claims.py
uv run python benchmark/real_data_loss.py
```

## Documentation

* [`docs/governance-status.md`](docs/governance-status.md) — **read first**: what J-FIBO is and is not
* [`docs/vision.md`](docs/vision.md) — design rationale; ontology-as-dictionary framing
* [`docs/modeling-principles.md`](docs/modeling-principles.md) — how new terms are added
* [`docs/semantic-loss-benchmark.md`](docs/semantic-loss-benchmark.md)
* [`docs/building-trajectory.md`](docs/building-trajectory.md) — auto-generated PROV view
* [`docs/information-boundary.md`](docs/information-boundary.md) — *application-layer* note: a discipline a consumer can adopt on top of `informationStatus`; not part of the ontology's purpose

## Layout

```
j-fibo/
  registry/terms.yaml           -- controlled term registry
  registry/entities.yaml        -- curated entity / 法人番号 resolver input
  registry/contributors.yaml    -- contributors + sessions (PROV)
  ontology/jfibo-*.ttl          -- generated OWL/TTL modules
  shapes/jfibo-shapes.ttl       -- SHACL shapes
  scripts/                      -- builders, extractors, materializers
  benchmark/                    -- curated + real-data benchmarks
  examples/                     -- conformance / non-conformance fixtures
  data/                         -- gitignored; reproducible via scripts
  tests/                        -- pytest suite (40 tests)
  docs/                         -- design, benchmark, trajectory, governance
```

## License

[MIT](LICENSE) — both code and ontology. This matches upstream FIBO, which the EDM Council also distributes under the MIT License.
