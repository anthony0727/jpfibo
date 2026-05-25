# J-FIBO Building Trajectory

Derived from `registry/terms.yaml` (per-term `contributed_by` + `session`) and `registry/contributors.yaml`. Every minted term carries the same attribution as `prov:wasAttributedTo` + `prov:wasGeneratedBy` triples in `ontology/jpfibo.ttl`, so this view is also queryable via SPARQL.

> **Governance status**: J-FIBO is currently a single-author research seed. No Japanese institutional body has endorsed, reviewed, or participated. See [governance-status.md](governance-status.md).

## Sessions

### 2026-05-25-v0.1-bootstrap

- date: 2026-05-25
- goal: Bootstrap J-FIBO v0.1 with EDINET alignment and information-status vocabulary.
- terms contributed: 30
- modules: information-status=12, disclosure-claim=8, core=4, edinet-alignment=3, institutional-context=3
- kinds: class=14, individual=7, object_property=6, datatype_property=3

### 2026-05-25-v0.2-finalize

- date: 2026-05-25
- goal: Finalize ontology with normative-status / reporting-regime / document-type / holder-role vocab, atomic claim types, and the EDINET-family `jpfibo:` prefix.
- terms contributed: 40
- modules: holder-role=9, reporting-regime=8, document-type=8, normative-status=7, disclosure-claim=7, core=1
- kinds: individual=24, class=7, object_property=7, datatype_property=2

## Contributors

### jfibo-wg-bootstrap

- role: editor
- organization: J-FIBO Working Group (provisional)
- terms attributed: 70

> Provisional, single-author editorial seed for v0.x. NO Japanese
institutional body has endorsed, reviewed, or participated in J-FIBO.
The contributor / session model exists so that, if a working group
ever forms, term-level attribution can be added without restructuring
the ontology. The bodies that could plausibly play stewardship roles
(Digital Agency, FSA, JPX, FISC, FDUA, an EDM Council Japan Chapter)
are mentioned only as examples of where such attribution could go;
none have been contacted.

## Mermaid timeline

```mermaid
timeline
    title J-FIBO contribution timeline
    2026-05-25
        : 2026-05-25-v0.1-bootstrap (+30 terms)
        : 2026-05-25-v0.2-finalize (+40 terms)
```
