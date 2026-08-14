## Why

The current config loader only accepts `prediction_features` entries in the
explicit object form with `actual` and `baseline`, even for the common exact-
match case `lhs == rhs`. That removed a concise shorthand that remains useful
for boolean formula features, and it forces callers to spell the same equality
twice when the intended semantics are simply "treat this exact equality as a
feature".

## What Changes

- Add backward-compatible `prediction_features` shorthand support for a string
  value whose top-level expression is exactly `actual == baseline`.
- Keep the current explicit object form unchanged; both forms coexist in the
  same config surface.
- Reject any shorthand string that is not a top-level `==` equality; no other
  operators (`!=`, `<`, `>`, `<=`, `>=`) or compound boolean expressions are
  allowed in the shorthand path.
- Normalize the shorthand into the same internal `PredictionFeature`
  representation used by the current `actual`/`baseline` form so downstream
  estimator behavior and docs stay coherent.
- Update README, examples, and tests to document and validate the dual-form
  behavior.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `estimator-hypothesis-attribution`: `prediction_features` accepts either the
  existing explicit `{actual, baseline, label?}` object or a string shorthand
  that must be a top-level `actual == baseline` equality, with identical
  downstream feature semantics after parsing.

## Impact

- `external/contribution-kit/src/contribution/cli.py`: `_load_spec` must accept
  and validate the equality-string shorthand, converting it into
  `PredictionFeature(actual=..., baseline=...)`.
- `external/contribution-kit/src/contribution/expr.py` or adjacent parser code:
  likely needs a small helper to recognize only top-level `==` expressions
  without accepting other boolean conditions.
- `external/contribution-kit/src/contribution/spec.py`: public docs for
  `PredictionFeature` / `AttributionSpec` may need clarification on the two
  supported config forms.
- Tests: loader validation tests, estimator integration around parsed features,
  and example-config coverage.
- Docs/examples: `external/contribution-kit/README.md` and the continuous LoRa
  example configs.