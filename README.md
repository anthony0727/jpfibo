# J-FIBO (金融意味基盤・日本版)

J-FIBO is a Japanese-finance extension of FIBO that adds the institutional
status, evidence provenance, holder-role, and information-boundary semantics
needed to make Japanese securities-report disclosures auditable.

RDF prefix is `jpfibo:` (matches the EDINET vocabulary family
`jpcrp/jpdei/jppfs/jpigp/...`). Brand name remains **J-FIBO**.

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

With an `EDINET_API_KEY` in `~/.env`:

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

* [docs/vision.md](docs/vision.md)
* [docs/modeling-principles.md](docs/modeling-principles.md)
* [docs/information-boundary.md](docs/information-boundary.md)
* [docs/semantic-loss-benchmark.md](docs/semantic-loss-benchmark.md)
* [docs/building-trajectory.md](docs/building-trajectory.md)

## Layout

```
jfibo/
  registry/terms.yaml           -- controlled term registry
  registry/entities.yaml        -- curated entity / 法人番号 resolver input
  registry/contributors.yaml    -- contributors + sessions (PROV)
  ontology/jpfibo-*.ttl         -- generated OWL/TTL modules
  shapes/jpfibo-shapes.ttl      -- SHACL shapes
  scripts/                      -- builders, extractors, materializers
  benchmark/                    -- curated + real-data benchmarks
  examples/                     -- conformance / non-conformance fixtures
  data/                         -- gitignored; reproducible via scripts
  tests/                        -- pytest suite (30 tests)
  docs/                         -- design + benchmark + trajectory docs
```

## License

MIT.
