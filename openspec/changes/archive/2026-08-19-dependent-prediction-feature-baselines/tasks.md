# Tasks: Dependent Prediction Feature Baselines

## 1. Reference Extraction And Validation

- [x] 1.1 Add a resolver that classifies each free variable of a feature expression as declared-feature, input-column, or unknown, using the row keys as the column set; return the sibling-reference set and the unknown names
- [x] 1.2 Extend `Estimator._validate_spec` to reject a free variable in a `PredictionFeature.actual` expression that resolves to a declared feature, naming the feature and variable; column references (bare or `col(...)`) stay valid
- [x] 1.3 Extend `_validate_spec` to reject a free variable resolving to neither a declared feature nor an input column, naming the feature and the unknown reference; emit a shadowing diagnostic when a feature name also matches a column
- [x] 1.4 Build the baseline dependency graph in `_validate_spec`, detect cycles (including self-reference), and raise naming the participating features in declaration order
- [x] 1.5 Compute and cache the topological resolution order for later use by feature resolution
- [x] 1.6 Add unit tests in `tests/unit/test_estimator.py` for sibling-reference-in-`actual`, unknown reference, two-feature cycle, and self-reference; run only these selected tests
- [x] 1.7 Add a regression test that a bare column identifier (e.g. `Height * 2`) in a feature expression is accepted and creates no dependency edge; run only this selected test
- [x] 1.8 Add `independent: bool = False` to `PredictionFeature` in `src/contribution/spec.py`, documenting in the docstring that it forbids dependency edges in **both** directions
- [x] 1.9 Enforce `independent` in `_validate_spec`: reject any baseline referencing an independent feature, and reject an independent feature's own baseline referencing another feature; each error must state the direction violated and name both features
- [x] 1.10 Accept the optional `independent` boolean in the object form of a feature entry in `src/contribution/cli.py`, keeping unknown-key rejection and leaving the equality shorthand unable to express it
- [x] 1.11 Add unit tests for both `independent` violation directions, for an independent feature with plain column expressions being valid, and for the shorthand rejecting the key; run only these selected tests

## 2. Coalition-Aware Feature Resolution

- [x] 2.1 Replace `Estimator._feature_values` with dependency-ordered resolution that accepts the coalition and builds each feature's value as actual-if-in-coalition else baseline-evaluated-with-resolved-siblings, via `build_row_context(row, extra)`
- [x] 2.2 Rewrite `_coalition_score` to hoist the coalition-independent `actual` map to once per row and resolve baselines per coalition, memoized for the duration of that coalition's scoring
- [x] 2.3 Verify `_exact_shapley` and `_sample_shapley` need no change beyond the new `_coalition_score` contract
- [x] 2.4 Add unit tests asserting resolved binding at both endpoints: sibling binds to actual when in coalition, to its own baseline when not; and that a spec with no sibling references produces byte-identical attributions to the previous implementation; run only these selected tests

## 3. Empty-Coalition Diagnostic

- [x] 3.1 Evaluate the empty-coalition prediction against `target` per row during `assess`, and record violating row count plus one example row index
- [x] 3.2 Surface the diagnostic through the existing warning/result-metadata path used by partition warnings, and render it in `report.md`
- [x] 3.3 Add a unit test that a baseline pinned to `col('Class BW')` instead of the resolved sibling triggers the diagnostic, and that the corrected config does not; run only these selected tests

## 4. Formula-Absorption Detection

- [x] 4.1 Accumulate per-coalition all-rows-zero flags during the exact Shapley pass at no extra scoring cost, and evaluate the `n` all-but-one coalitions explicitly on the sampling path
- [x] 4.2 Emit a diagnostic when the all-but-one coalition `N \ {f}` scores zero on every row, naming `f` and the features its baseline references; do not fire for smaller zero-scoring coalitions
- [x] 4.3 Surface the diagnostic through the same path as the D5 empty-coalition warning and render it in `report.md`
- [x] 4.4 Add unit tests: over-referenced baseline (`class_sf.baseline` reading `measured_bw`) fires the diagnostic; the correct dependent baseline does not despite `{class_bw}` being zero; run only these selected tests

## 5. Acceptance Case From The Paper

- [x] 5.1 Add a test fixture encoding the three rows of the manuscript's geometric-regression table for true signal `(812, 8)`: nominal classes `(1000, 8)`, `(1000, 9)`, `(500, 7)`
- [x] 5.2 Assert the dependent baseline scores `(1000, 8)` as a `class_sf` error and `(1000, 9)` / `(500, 7)` as correct, matching the formula outputs `7`, `8`, `8` against `GT SF = 8`
- [x] 5.3 Assert `v(empty) == 0` and `v({class_bw}) == 0` on that fixture; run only these selected tests

## 6. Example And Documentation Migration

- [x] 6.1 Update `examples/continuous_lora/config.json`: `class_sf.baseline` becomes `col('GT SF') - round(2 * log2(col('GT BW') / class_bw))`, and mark `measured_bw` with `"independent": true` to encode that box-geometry estimation is causally independent of the detector's class decision
- [x] 6.2 Run `contrib run` against the migrated config and `measurements.csv`; confirm the burden ranking, mismatch total, and observed accuracy are unchanged and only feature attributions move
- [x] 6.3 Update the README "How it works" bullet to document sibling references in `baseline`, the row-only `actual` restriction, and acyclicity
- [x] 6.4 Update the README Quick start snippet and any reported feature-attribution figures to the regenerated values
- [x] 6.5 Document the two interpretation notes in the README: negative shares mean a feature compensates for others, and over-referencing a baseline collapses the referenced feature's attribution to zero
- [x] 6.6 Document `independent` in the README as the opt-in guard against over-referencing, noting it is symmetric and that omitting it leaves a feature referenceable
- [x] 6.7 Add a unit test in `tests/unit/test_cli.py` covering the equality-shorthand right-hand side carrying a sibling reference; run only this selected test

## 7. Verification

- [x] 7.1 Pin backward compatibility: capture the current `assess()` feature attributions for the unmodified `examples/continuous_lora/config.json` as a golden fixture BEFORE any resolution changes land, and assert byte-equality after
- [x] 7.2 Run the full `pytest` suite for the kit and confirm no regressions
- [x] 7.3 Confirm the mismatch-invariance requirement by assessing the example spec with a sibling-free and a dependent `class_sf` baseline and diffing everything except feature attributions
