# J-FIBO (金融意味基盤・日本版)

> **Independent research artifact** — not endorsed by FSA, Digital Agency, JPX, BOJ, FISC, FDUA, EDM Council, or OMG. The `J-FIBO` brand and `jfibo:` prefix are provisional. See [`docs/governance-status.md`](docs/governance-status.md).

J-FIBO is a Japanese-finance extension of [FIBO](https://spec.edmcouncil.org/fibo/): a canonical OWL/SHACL dictionary of the roles, responsibilities, reporting regimes, and relationships specific to the Japanese securities-disclosure system, with verbatim alignment to the FSA-published EDINET XBRL taxonomy.

## Status (v0.5)

| Metric | Value |
|---|---:|
| Triples | 1,740 |
| Aligned EDINET concepts (verbatim FSA labels) | 56 |
| Real EDINET FY2024 claims materialized | 223 |
| Claim families | PolicyShareholding · MajorShareholderClaim · BorrowingsClaim · CommercialPaperClaim · CrossShareholdingClaim · MainBankCandidate |
| Cross-shareholding triangulations (real) | 1 (Toyota Motor ↔ MUFG) |
| Vanilla-FIBO vs J-FIBO coverage on real claims | 0.280 → 0.973 (**gain +0.693**) |
| Curated benchmark gain (19 cases) | +0.703 |
| Tests | 40 / 40 |

Real filings: Toyota Motor Corp, ITOCHU, Mitsubishi UFJ FG, SoftBank Group (FY2024 有価証券報告書).

## Naming

| Surface | Form |
|---|---|
| Brand | **J-FIBO** (J-REIT / J-GAAP / J-SOX family) |
| Repo / package / prefix / IRI | `j-fibo` / `jfibo` / `jfibo:` / `https://w3id.org/jfibo/` |

## Quick start

```bash
uv sync
uv run python scripts/build_ontology.py
uv run python scripts/validate.py examples/policy-shareholding-valid.ttl
uv run python benchmark/semantic_loss.py
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

## Layout

```
registry/         -- term / entity / contributor YAML (source of truth)
ontology/         -- generated OWL/TTL modules
shapes/           -- SHACL shapes
scripts/          -- builders, extractors, materializers
benchmark/        -- curated + real-data benchmarks
examples/         -- conformance / non-conformance fixtures
tests/            -- pytest suite (40 tests)
docs/             -- governance-status (read first)
data/             -- mostly gitignored; reproducible via scripts/
```

## License

[MIT](LICENSE) — both code and ontology. Matches upstream FIBO.
