# Semantic-Loss Benchmark

## Purpose

Quantitatively justify J-FIBO over vanilla FIBO by measuring what fraction
of disclosed Japanese-finance semantics each ontology can represent
natively, per claim and per claim kind.

## Inputs

### Curated cases

`benchmark/cases/*.yaml` (15 cases). Each names the disclosed semantic
fields, the vanilla-FIBO mapping (and the fields it cannot represent
without extension), and the J-FIBO mapping.

### Real EDINET claims

`data/edinet/claims/*.ttl` — materialized from FY2024 securities reports:

* PolicyShareholding   (176 claims)
* MajorShareholderClaim (40 claims)
* CrossShareholdingClaim (1 triangulated claim — Toyota Motor Corp ↔ MUFG)

## Metrics

* `vanilla_coverage`   — fraction of expected fields representable in
  vanilla FIBO
* `jfibo_coverage`     — fraction representable in J-FIBO
* `jfibo_gain`         — `jfibo_coverage − vanilla_coverage`

## Run

```bash
uv run python benchmark/semantic_loss.py    # curated cases
uv run python benchmark/real_data_loss.py   # real EDINET claims
```

## Results (v0.2)

Curated cases (n=15):

```
mean vanilla FIBO coverage:  0.338
mean J-FIBO coverage:        1.000
mean J-FIBO gain:            0.662
```

Real EDINET FY2024 disclosures (n=217 claims):

```
mean vanilla FIBO coverage:  0.285
mean J-FIBO coverage:        0.975
mean J-FIBO gain:            0.690

by claim kind:
  CrossShareholdingClaim   claims=  1  vanilla=0.286  jfibo=1.000  gain=0.714
  MajorShareholderClaim    claims= 40  vanilla=0.364  jfibo=1.000  gain=0.636
  PolicyShareholding       claims=176  vanilla=0.268  jfibo=0.969  gain=0.701
```
