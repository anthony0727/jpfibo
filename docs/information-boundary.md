# Information Boundary

J-FIBO uses **information boundary**, not **reasoning boundary**, as its
primary discipline term.

Inside the boundary:

```
observed | disclosed | evidence-backed inferred
```

Outside the boundary:

```
hypothesized | counterfactual | predicted | outside information boundary
```

## The principle

> Backtracer may reason beyond the information boundary, but must not
> present beyond-boundary reasoning as auditable explanation.

The SHACL shapes enforce this:

* `jfibo:DisclosureClaim` requires exactly one `jfibo:informationStatus`
  from the closed vocabulary above.
* `jfibo:MainBankCandidate` is forbidden from using `jfibo:Disclosed` or
  `jfibo:Observed`; it must use `Hypothesized`,
  `EvidenceBackedInferred`, `Counterfactual`, or
  `OutsideInformationBoundary`.

## Why explanation/audit-first

* Soros-style reflexivity makes prediction targets depend on beliefs about
  predictions; modeling latent beliefs as observed data is incorrect.
* Hidden confounders (negotiation rooms, regulatory bargaining, board
  succession) are unobservable from filings.
* Tracking every agent's beliefs is infeasible and undesirable; restricting
  to disclosed evidence is sufficient and honest.

When prediction is required, predicted claims must be tagged with
`jfibo:Predicted` so consumers cannot conflate them with disclosed facts.
