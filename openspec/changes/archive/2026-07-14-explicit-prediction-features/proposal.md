# Explicit Prediction Features

## Why

Shapley feature routing in the contribution-kit is currently derived from
condition syntax: any hypothesis whose `condition` is a top-level `==` silently
becomes a Shapley feature, and its left/right operands become the actual and
baseline values. This has three silent failure modes: (1) `==` is commutative
to a reader but the operand split is not, so swapping sides silently flips
attribution direction; (2) misrouting is silent in both directions (a
non-equality condition intended as a feature becomes a regime; an equality
intended as a regime becomes a zero-effect feature when its name is not in
`prediction_expr`); (3) the documented rule that a feature name must appear in
`prediction_expr` is not enforced in code.

## What Changes

- **BREAKING**: Add a `prediction_features` declaration to `AttributionSpec`
  (and the JSON config): a mapping of feature name to explicit
  `{actual, baseline}` expression pairs. This becomes the only way to declare
  Shapley features.
- **BREAKING**: Remove syntax-shape routing — hypotheses are no longer
  classified as features via top-level `==` conditions. Every entry in
  `hypotheses` is a regime (equality conditions included).
- Add cross-validation between `prediction_expr` and `prediction_features`:
  every free variable of `prediction_expr` must be a declared feature name, and
  every declared feature must be referenced by `prediction_expr`; either
  violation fails fast with a clear error.
- Require `actual` and `baseline` keys on each feature entry; missing or extra
  keys fail fast.
- Update the CLI config loader, README classification-rule documentation, and
  the `examples/continuous_lora` configs to the new declaration.
- Result types (`FeatureAttribution`, `analysis="feature"`) and report shapes
  are unchanged.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `estimator-hypothesis-attribution`: Shapley features are declared explicitly
  via `prediction_features` `{actual, baseline}` pairs instead of being
  privately classified from top-level `==` condition shape; `hypotheses`
  entries are always regimes; `prediction_expr` variables and declared feature
  names must match exactly, enforced by validation.

## Impact

- `external/contribution-kit/src/contribution/spec.py`: new
  `PredictionFeature`/`prediction_features` on `AttributionSpec`.
- `external/contribution-kit/src/contribution/estimator.py`: `_formula_features`
  reads `prediction_features` instead of splitting `==` conditions; new
  validation in `_validate_spec`.
- `external/contribution-kit/src/contribution/expr.py`: `split_equality` no
  longer used for routing (may be removed or kept for internal use).
- `external/contribution-kit/src/contribution/cli.py`: config loader parses
  `prediction_features`.
- `external/contribution-kit/examples/continuous_lora/*.json`: configs migrate
  equality hypotheses to `prediction_features`.
- `external/contribution-kit/README.md`: classification-rule section rewritten.
- Tests under `external/contribution-kit/tests/` and ResearchData integration
  tests that declare equality hypotheses.
- Breaking for any external config still using `==` hypotheses as features;
  such configs now treat those entries as regimes and fail validation if
  `prediction_expr` references undeclared variables.
