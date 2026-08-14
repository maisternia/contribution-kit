## 1. Parser and loader

- [x] 1.1 Add a helper in `external/contribution-kit/src/contribution/expr.py` or `external/contribution-kit/src/contribution/cli.py` that recognizes only a top-level `actual == baseline` DSL expression and returns normalized left/right expressions
- [x] 1.2 Update `_load_spec` in `external/contribution-kit/src/contribution/cli.py` so each `prediction_features` entry accepts either the current `{actual, baseline, label?}` object or the equality-string shorthand and normalizes both to `PredictionFeature`
- [x] 1.3 Keep the current strict validation for explicit feature objects and add targeted validation errors for shorthand strings that are not a single top-level `==` equality

## 2. Tests

- [x] 2.1 Extend `external/contribution-kit/tests/unit/test_cli.py` with a loader test that accepts a shorthand feature such as `"col('Class SF') == col('GT SF')"`
- [x] 2.2 Extend `external/contribution-kit/tests/unit/test_cli.py` with rejection tests for non-equality shorthand (`!=`, `<`, chained comparisons, compound boolean expressions)
- [x] 2.3 Add or update a focused estimator or smoke test to confirm mixed shorthand and explicit-object features coexist and bind into `prediction_expr` correctly after normalization

## 3. Docs and examples

- [x] 3.1 Update `external/contribution-kit/README.md` to document that `prediction_features` is canonical in explicit `{actual, baseline, label?}` form but also accepts a top-level `==` shorthand in config files only
- [x] 3.2 Update the public docstrings in `external/contribution-kit/src/contribution/spec.py` so they distinguish prediction-feature declarations from regime hypotheses and mention the config-only equality shorthand
- [x] 3.3 Update the continuous LoRa example configs to demonstrate one valid equality-string feature alongside existing explicit object features where labels are still needed

## 4. Validation

- [x] 4.1 Run the targeted contribution-kit unit tests covering loader acceptance and rejection of shorthand prediction features
- [x] 4.2 Run one focused config validation or smoke path against the updated example config to confirm the shorthand round-trips through `contrib validate` without changing downstream feature semantics