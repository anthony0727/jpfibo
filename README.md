# J-FIBO (金融意味基盤・日本版)

J-FIBO is a Japanese-finance extension of FIBO that adds the institutional
status, evidence provenance, and information-boundary semantics needed to
make Japanese securities-report disclosures auditable.

## Quick start

```bash
uv sync
uv run python scripts/build_ontology.py
uv run python scripts/validate.py examples/policy-shareholding-valid.ttl
uv run python scripts/validate.py examples/policy-shareholding-invalid.ttl --expect-fail
uv run python benchmark/semantic_loss.py
uv run python -m pytest
```

With an `EDINET_API_KEY` in `~/.env`:

```bash
uv run python scripts/download_edinet_taxonomy.py
uv run python scripts/build_edinet_focus.py
uv run python scripts/find_target_filings.py --days 400
uv run python scripts/edinet_client.py download <docID> --type 1
uv run python scripts/extract_xbrl_facts.py
uv run python scripts/materialize_claims.py
uv run python benchmark/real_data_loss.py
```

## Documentation

* [docs/vision.md](docs/vision.md)
* [docs/information-boundary.md](docs/information-boundary.md)
* [docs/modeling-principles.md](docs/modeling-principles.md)
* [docs/semantic-loss-benchmark.md](docs/semantic-loss-benchmark.md)

## Layout

```
jfibo/
  registry/terms.yaml                    -- controlled term registry
  ontology/jfibo-*.ttl                   -- generated OWL/TTL modules
  shapes/jfibo-shapes.ttl                -- SHACL shapes
  scripts/                               -- builders, extractors, materializers
  benchmark/                             -- curated and real-data benchmarks
  examples/                              -- conformance/non-conformance fixtures
  data/                                  -- gitignored; reproducible via scripts
  tests/                                 -- pytest suite
  docs/                                  -- design + benchmark docs
```

## License

MIT.
