## 1. Estimator Hypothesis API

- [x] 1.1 Audit existing `Estimator` hypothesis entry points and identify non-estimator regime logic to consolidate.
- [x] 1.2 Define and implement a single unified estimator hypothesis input contract that supports arbitrary attribution and predicate-based hypotheses.
- [x] 1.3 Add estimator-level validation and deterministic ordering for user-provided hypothesis sets and output fields.

## 2. Single-Spec Unification

- [x] 2.1 Declare feature, regime, and binary hypotheses on one `AttributionSpec` using DSL string expressions (`regimes`, `binary_tests`, `mismatch_expr`).
- [x] 2.2 Make `Estimator.assess` the single door that returns `feature_attributions`, `regime_summaries`, and `binary_results` in one `AssessmentResult`.
- [x] 2.3 Derive regime error shares from the spec's shared per-row observed error (`prediction_expr` vs `target_expr`).
- [x] 2.4 Remove callable-based `assess_hypotheses` / `assess_error_regimes` / `assess_binary_hypotheses` so estimation flows only through the spec.

## 3. Regime Contribution Support

- [x] 3.1 Implement estimator-managed contribution/error-share computation for predicate-based regime hypotheses.
- [x] 3.2 Add first-class support for `class_bw < gt_bw (beyond tol)`, `class_bw > gt_bw (beyond tol)`, `class_bw within tol & sf wrong`, `class_bw & sf ok, measured_bw off`, and the baseline regime.
- [x] 3.3 Remove split estimation paths so hypothesis estimation is performed only through the unified estimator interface.

## 5. Single-Condition Public API

- [x] 5.1 Collapse the spec to one flat `hypotheses` list where each `Hypothesis` carries a single boolean `condition`; remove `RegimeHypothesis`, `BinaryHypothesis`, `regimes`, `binary_tests`, and `actual_expr`/`baseline_expr`.
- [x] 5.2 Add `split_equality` so the estimator privately classifies a condition as a formula feature (top-level `==`) or an error regime, deriving Shapley actual/baseline from the equality operands.
- [x] 5.3 Return one `HypothesisAssessment` per declared hypothesis from `assess`, exposing `feature_attributions`, `regime_summaries`, and `binary_results` as derived views.
- [x] 5.4 Compute regime mismatch risk as condition-vs-rest using the spec-level `mismatch_expr`.
- [x] 5.5 Update `__init__`, CLI spec loading, the sample config, and the kit's own unit tests to the condition-based API.
- [x] 5.6 Rewrite the integration test to build one flat condition spec and assert the unified output, regime shares, and condition-vs-rest risk independently from the source CSV.
