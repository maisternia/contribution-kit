## Why

From the user's perspective, the main thing they need to set up are **contributing-condition** hypotheses — directional or conditional regimes such as "detected BW falls below GT BW", "detected BW rises above GT BW", or "detected BW is within tolerance but detected SF is wrong". Exact-match hypotheses (`detected == GT`) are useful extras, not the primary goal. The current error-attribution flow does not make it clear how to express and estimate these regime-style hypotheses directly through `Estimator`, which causes duplicated logic in integration code and makes capability gaps hard to identify.

## What Changes

- Declare every hypothesis through one flat `AttributionSpec.hypotheses` list, where each `Hypothesis` carries a single boolean `condition` DSL string. Callers never declare regimes, binary tests, or mismatch groups directly.
- Let the estimator privately classify each condition: a top-level equality (`actual == baseline`) becomes a formula feature (Shapley); any other condition becomes an error regime whose error share and mismatch risk (versus the rest of the population) are reported.
- Make `Estimator.assess` the single door that returns a unified `AssessmentResult` whose `hypotheses` list holds one `HypothesisAssessment` per declared hypothesis, with `feature_attributions`, `regime_summaries`, and `binary_results` exposed as derived convenience views.
- Derive regime error shares from the spec's shared per-row observed error (`prediction_expr` vs `target_expr`) so one prediction/target definition drives every hypothesis.
- Remove the separate `regimes`, `binary_tests`, `RegimeHypothesis`, `BinaryHypothesis`, and `actual_expr`/`baseline_expr` inputs so the public surface is just conditions.
- Update integration tests to build one spec from a flat condition list, construct the estimator once, and assert all outputs from a single `assess` call.


## Capabilities

### New Capabilities
- `estimator-hypothesis-attribution`: Unified estimator-driven attribution and contribution analysis for both feature and regime hypotheses.

### Modified Capabilities
- None.

## Impact

- Affected code in `external/error-attribution-kit/src/error_attribution` (`Estimator`, hypothesis models, and assessment APIs).
- Affected integration coverage in `tests/test_error_attribution_kit_integration.py`.
- Legacy scripts under `scripts/` are intentionally left unchanged as historical, single-use analysis references.
