# Tasks: add-factorial-regimes

## 1. Spec and config surface

- [x] 1.1 Add `Factor` dataclass and optional `factors`/`factorials` fields to `AttributionSpec` in `external/contribution-kit/src/contribution/spec.py`, preserving level order
- [x] 1.2 Parse optional top-level `factors` and `factorials` config keys in `external/contribution-kit/src/contribution/cli.py`, with clear errors for unknown axis references and empty axes
- [x] 1.3 Add spec validation: factorial axis names must exist; unused declared axes emit a warning

## 2. Factorial expansion in the estimator

- [x] 2.1 Implement crossing expansion in `estimator.py`: generate one regime `Hypothesis` per cell with conjunction condition `(<row_cond>) and (<col_cond>)` and name `"<row_level> & <col_level>"`, appended before routing
- [x] 2.2 Raise a validation error on cell-name collision with declared hypotheses or other generated cells
- [x] 2.3 Implement per-axis partition validation over loaded rows (overlap/gap counts), emitting `warnings.warn` and collecting entries for output metadata

## 3. Within-stratum contrasts

- [x] 3.1 Generalize `_regime_risk` (or add a sibling helper) to accept an explicit group-B row mask instead of the complement
- [x] 3.2 Compute contrasts for every unordered sibling-level pair within each stratum of each factorial, reusing Koopman/Baptista-Pike intervals and guardrail fallbacks
- [x] 3.3 Add a contrast result type (stratum, level pair, counts, RR/OR with CIs) and expose `contrast_results` on `AssessmentResult`

## 4. Rendering and serialization

- [x] 4.1 Render a "Factorial Matrices" report section: one matrix table per crossing with per-cell count, mismatch rate, RR vs rest, plus union-computed row/column marginals
- [x] 4.2 Render a titled "Within-stratum contrasts" report table grouped by stratum
- [x] 4.3 Include factorial cells, marginals, contrasts, and partition warnings in `run.json`; keep factor-free output unchanged
- [x] 4.4 Note partition warnings in the markdown report when present

## 5. Example migration and tests

- [x] 5.1 Rewrite `examples/continuous_lora/config_bw_matrix.json` using `factors`/`factorials` (drop the six hand-written cells and the stale sketch block; keep the three equality hypotheses)
- [x] 5.2 Add unit tests for expansion, name collisions, unknown-axis errors, and partition warnings
- [x] 5.3 Add unit tests for contrast effect sizes on a small fixture, including a guardrail-fallback case
- [x] 5.4 Add a regression test that a factor-free config produces `report.md`/`run.json` identical to pre-factorial output
- [x] 5.5 Run the migrated BW-matrix example end-to-end and verify cell metrics match the current hand-written run in `build/bw_matrix/`
- [x] 5.6 Update `external/contribution-kit/README.md` with the `factors`/`factorials` schema and the matrix/contrast report sections
