# Semantic-Loss Benchmark

## Purpose

To quantitatively justify J-FIBO over vanilla FIBO by measuring what
fraction of disclosed Japanese-finance semantics each ontology can
represent natively, per claim and per domain.

## Inputs

### Curated cases

`benchmark/cases/*.yaml` (13 cases) — each names the disclosed semantic
fields, the vanilla-FIBO mapping (and the fields it cannot represent
without extension), and the J-FIBO mapping.

### Real EDINET claims

`data/edinet/claims/*.ttl` — every PolicyShareholding row extracted from a
real annual securities report and materialized as a J-FIBO RDF claim.

## Metrics

* `vanilla_coverage`        — `|vanilla.represents| / |expected|`
* `jfibo_coverage`          — `|jfibo.represents|   / |expected|`
* `semantic_loss_rate`      — fields vanilla FIBO cannot represent
                              natively
* `jfibo_gain`              — `jfibo_coverage − vanilla_coverage`
* `evidence_traceability`   — share of claims that cite an evidence
                              locator
* `information_boundary_marked` — share of claims with explicit
                                  information status

## Run

```bash
uv run python benchmark/semantic_loss.py       # curated cases
uv run python benchmark/real_data_loss.py      # real EDINET claims
```

Outputs land in `benchmark/results/`.

## Results (v0.1)

Curated cases (n=13):

```
mean vanilla FIBO coverage:  0.321
mean J-FIBO coverage:        1.000
mean semantic-loss rate:     0.621
mean J-FIBO gain:            0.679
```

Real EDINET FY2024 disclosures (n=176 PolicyShareholding claims from
Toyota Motor Corporation, Mitsubishi Corporation, Mitsubishi UFJ Financial
Group):

```
mean vanilla FIBO coverage:  0.294
mean J-FIBO coverage:        0.966
mean semantic-loss rate:     0.706
mean J-FIBO gain:            0.672
```

The 3 percentage points the real-data benchmark is below 1.0 reflect
Toyota's choice to omit some narrative purpose fields and the
sequential-numbers-axis structure of MUFG's largest-holding-company
disclosures; both are legitimate disclosure variants that J-FIBO records
faithfully rather than papering over.
