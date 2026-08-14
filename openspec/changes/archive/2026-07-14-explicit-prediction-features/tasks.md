# Tasks: Explicit Prediction Features

## 1. Spec Types And Validation (contribution-kit)

- [x] 1.1 Add `PredictionFeature` dataclass (`actual: str`, `baseline: str`, `label: str | None = None`) and `AttributionSpec.prediction_features: dict[str, PredictionFeature]` in `src/contribution/spec.py`; update the `Hypothesis`/`AttributionSpec` docstrings to describe regimes-only hypotheses and explicit features
- [x] 1.2 Add `free_variables(expression)` helper to `src/contribution/expr.py` returning `ast.Name` identifiers minus `_ALLOWED_FUNCTIONS` keys and `col`
- [x] 1.3 Extend `Estimator._validate_spec` with bidirectional `prediction_expr` ↔ `prediction_features` checks and feature/hypothesis name-collision check, with errors naming each offending variable/feature
- [x] 1.4 Add unit tests for the new validation in `tests/unit/test_spec.py` (undeclared formula variable) and `tests/unit/test_estimator.py` (unused feature, name collision); run only these selected tests

## 2. Feature Routing Replacement

- [x] 2.1 Rewrite `Estimator._formula_features` to compile `_Feature` objects from `spec.prediction_features` (declaration order) instead of splitting `==` hypothesis conditions
- [x] 2.2 Emit `analysis="feature"` assessments from `prediction_features` and `analysis="regime"` assessments for every `hypotheses` entry (equality conditions included) in `assess()`, preserving `AssessmentResult` shape
- [x] 2.3 Remove `split_equality` from `src/contribution/expr.py` and its uses; migrate `tests/unit/test_expr.py` cases to `free_variables` coverage
- [x] 2.4 Update `tests/unit/test_estimator.py` feature-attribution cases to declare `prediction_features` pairs and assert equality-condition hypotheses are analysed as regimes; run only the two most representative selected tests

## 3. CLI Config And Examples

- [x] 3.1 Parse `prediction_features` (object with required `actual`/`baseline`, optional `label`) in the CLI config loader in `src/contribution/cli.py`, failing fast on missing/unknown keys
- [x] 3.2 Migrate `examples/continuous_lora/config.json` and `config_factorial.json`: move equality hypotheses (`class_sf`, `class_bw`, `measured_bw`) into `prediction_features` pairs, keep regime conditions in `hypotheses`
- [x] 3.3 Update `tests/unit/test_cli.py` config-loading cases for the new key; run only the selected new/changed tests
- [x] 3.4 Verify `contrib validate` and `contrib run` end-to-end against `examples/continuous_lora/config_factorial.json` and `measurements.csv`, confirming unchanged report shape

## 4. Documentation

- [x] 4.1 Rewrite the classification-rule sections of `external/contribution-kit/README.md`: explicit `prediction_features` declaration, regimes-only hypotheses, validation errors, and a before/after migration example for `==` feature-hypotheses

## 5. ResearchData Integration

- [x] 5.1 Update ResearchData integration tests that declare equality hypotheses (`tests/test_error_attribution_kit_integration.py`, `tests/integration/test_contribution_baseline_accuracy.py`) to `prediction_features` pairs; run only the selected affected tests
- [x] 5.2 Add fail-fast integration assertions (undeclared formula variable, unused feature, name collision) per the delta spec; run only the selected new tests
