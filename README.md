# J-FIBO (金融意味基盤・日本版)

> **Governance status — read first.** J-FIBO is an **independent single-author research artifact**. It is **not** endorsed by, affiliated with, or reviewed by the FSA, Digital Agency, JPX, BOJ, FISC, FDUA, EDM Council, OMG, or any other Japanese or international body. The `J-FIBO` brand and the `jfibo:` prefix are provisional. See [`docs/governance-status.md`](docs/governance-status.md).

J-FIBO is a Japanese-finance extension of [FIBO](https://spec.edmcouncil.org/fibo/) that models the **roles, responsibilities, reporting regimes, and relationships** specific to the Japanese securities-disclosure system — policy shareholdings (政策保有株式), main-bank relationships (メインバンク), cross-shareholdings (持合い), holder-role distinctions (信託口・カストディ・常任代理人・ADR預託機関), and the normative-status axis (legal obligation vs accounting disclosure vs governance disclosure vs institutional expectation vs inferred hypothesis) that vanilla FIBO is too general to capture.

Atomic disclosure claims (`MajorShareholderClaim`, `BorrowingsClaim`, `PolicyShareholding`, `CrossShareholdingClaim`, `MainBankCandidate`) carry PROV provenance and pass SHACL validation. Information-flow / information-boundary concerns belong to consumers of these claims, not to the ontology itself ([why](docs/information-boundary.md)).

## Status (v0.4)

| Metric | Value |
|---|---:|
| Triples | 996 |
| Minted terms | 70 |
| Real EDINET FY2024 claims materialized | 217 |
| Cross-shareholding triangulations (real) | 1 (Toyota Motor ↔ MUFG) |
| Vanilla-FIBO coverage on real claims | 0.285 |
| J-FIBO coverage on real claims | 0.975 |
| **Gain (real)** | **+0.690** |
| Gain (curated n=15) | +0.662 |
| Tests | 30 / 30 passing |

Real filings processed for v0.4: Toyota Motor Corp, ITOCHU, Mitsubishi UFJ FG, SoftBank Group.

## Naming conventions

J-FIBO follows the **J-REIT / J-GAAP / J-SOX** family of Japan-localized standards:

| Surface | Form | Audience |
|---|---|---|
| Brand (papers, slides, prose) | **J-FIBO** | Humans — pattern-matches J-REIT / J-GAAP / J-SOX |
| Repo URL | **`j-fibo`** | Humans clicking links — brand visible at the click |
| Python package | **`jfibo`** | Python devs — `import jfibo` |
| RDF prefix | **`jfibo:`** | SPARQL / Turtle authors — short, brand-direct |
| IRI base | **`https://w3id.org/jfibo/`** | URI resolvers |

### Note on EDINET compatibility

EDINET filings are **XBRL**, and the EDINET XBRL taxonomy declares **XML namespaces** prefixed `jpcrp / jpdei / jppfs / jpigp / jpsps / jpaud / jpctl / jplvh`. J-FIBO is **OWL/RDF**, a different technical layer — XBRL↔RDF interoperability is achieved by URI mapping (`owl:equivalentClass` between full IRIs), not by prefix-letter rhyme. We therefore default to the shorter, brand-direct `jfibo:` prefix.

If a future EDINET-bridge use case justifies it, a `jpfibo:` alias namespace pointing to the same IRI base may be registered as a parallel convenience for bridge-file authors. No technical compatibility depends on it today.

## Quick start

```bash
uv sync
uv run python scripts/build_ontology.py
uv run python scripts/validate.py examples/policy-shareholding-valid.ttl
uv run python scripts/validate.py examples/policy-shareholding-invalid.ttl --expect-fail
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
uv run python scripts/materialize_claims.py
uv run python benchmark/real_data_loss.py
```

## Documentation

* [`docs/governance-status.md`](docs/governance-status.md) — **read first**: what J-FIBO is and is not
* [`docs/vision.md`](docs/vision.md)
* [`docs/modeling-principles.md`](docs/modeling-principles.md)
* [`docs/information-boundary.md`](docs/information-boundary.md)
* [`docs/semantic-loss-benchmark.md`](docs/semantic-loss-benchmark.md)
* [`docs/building-trajectory.md`](docs/building-trajectory.md)

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
  tests/                        -- pytest suite (30 tests)
  docs/                         -- design, benchmark, trajectory, governance
```

## License

[MIT](LICENSE) — both code and ontology. This matches upstream FIBO, which the EDM Council also distributes under the MIT License.
