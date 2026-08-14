# Proposal: add-factorial-regimes

## Why

Diagnosing a correction formula requires crossing independent error axes (e.g. class-BW deviation direction × measured-BW box quality), but today each factorial cell must be hand-written as a composite hypothesis, duplicating threshold formulas across conditions (the BW-matrix example repeats the same 10% tolerance expression twelve times) and offering no partition guarantees, no matrix rendering, and no statistically clean cell-vs-cell comparison — every regime is only ever tested against "rest".

## What Changes

- Add an optional `factors` block to the attribution config and `AttributionSpec`: named axes, each a mapping of level name → boolean condition DSL string. Conditions are declared once per level; no duplication in cells.
- Add an optional `factorials` block: a list of `{rows: <axis>, columns: <axis>}` crossings. Each crossing expands into generated regime hypotheses (one per cell, condition = AND of the two level conditions, name = `"<row> & <col>"`).
- Generated cells flow through the existing regime/risk machinery unchanged (contribution share, Koopman risk-ratio CI, Baptista-Pike odds-ratio CI vs rest).
- Validate each axis as a partition against the loaded data: warn when levels overlap or do not exhaust the rows.
- Render each factorial as a matrix table in the markdown report (per-cell count, mismatch rate, risk ratio) with row/column marginals.
- Add within-stratum contrasts: for each factorial, compare sibling cells inside a row/column stratum (group B = sibling cell instead of "rest") using the existing Koopman/Baptista-Pike interval machinery.
- The flat `hypotheses` list is kept exactly as-is, including automatic Shapley routing (top-level equality → feature, anything else → ad-hoc regime). `factors`/`factorials` are additive and optional; configs without them behave identically.

Out of scope:

- A `params` block for shared scalar constants (e.g. `tol = 0.10`) — deferred as an independent decision.
- The 18.92% rounding-cliff banding of the LoRa example — domain analysis; it belongs to the research paper (`paper/Proposal`), not the toolkit spec.
- Renaming `hypotheses` (e.g. to `features`/`players`) — explicitly rejected; automatic routing stays.

## Capabilities

### New Capabilities

- `factorial-regime-declaration`: declaring factor axes and factorial crossings; expansion of crossings into generated regime hypotheses; axis partition validation; factorial matrix rendering with marginals in reports; within-stratum sibling-cell contrasts.

### Modified Capabilities

- `estimator-hypothesis-attribution`: `AttributionSpec` gains optional `factors`/`factorials` inputs whose expansion produces regime hypotheses alongside the flat `hypotheses` list; the flat list and its equality-routing rule remain the only way to declare Shapley features and ad-hoc regimes.

## Impact

- `external/contribution-kit/src/contribution/spec.py`: `AttributionSpec` fields, config JSON parsing.
- `external/contribution-kit/src/contribution/estimator.py`: factorial expansion, partition validation, sibling contrasts.
- `external/contribution-kit/src/contribution/results.py`: matrix table + marginals rendering, contrast results in `run.json`/`report.md`.
- `external/contribution-kit/src/contribution/cli.py`: accept the new config blocks.
- `external/contribution-kit/examples/continuous_lora/config_bw_matrix.json`: rewrite using `factors`/`factorials` (removes the six hand-written composite cells).
- Backward compatible: no changes to existing configs, outputs for factor-free configs are byte-identical.
