## 1. Unify the public type in `spec.py`

- [x] 1.1 Make `Hypothesis` the canonical dataclass and update its docstring to state the single classification rule (top-level `==` with `name` in `prediction_expr` → feature; otherwise → regime)
- [x] 1.2 Remove `RegimeHypothesis`, `FeatureHypothesis`, `ContinuousHypothesis`, and `CategoricalHypothesis`
- [x] 1.3 Remove the `kind` field and the `HypothesisKind` type from `spec.py`

## 2. Update exports and CLI

- [x] 2.1 Export only `Hypothesis` from `__init__.py` (drop the alias names)
- [x] 2.2 Update `cli.py` to construct `Hypothesis` directly from config entries

## 3. Update documentation

- [x] 3.1 Rewrite the README quick start to use the single `Hypothesis` type
- [x] 3.2 Add the canonical classification-rule sentence to the README and align module docstrings
- [x] 3.3 Remove all references to the subtype classes and `kind` from docs

## 4. Update examples and configs

- [x] 4.1 Verify `examples/*/config.json` still validate after removing `kind`
- [x] 4.2 Remove `kind` keys from all example configs

## 5. Tests

- [x] 5.1 Add a test asserting an equality condition declared via `Hypothesis` routes to a feature and produces Shapley attribution
- [x] 5.2 Add a test asserting a non-equality condition declared via `Hypothesis` routes to a regime
- [x] 5.3 Remove tests that referenced the deleted alias classes and `kind`
- [x] 5.4 Update `test_estimator.py` to use only `Hypothesis`
- [x] 5.5 Retain a behavior-preserving test asserting identical `feature_attributions` and `regime_summaries` for the bundled example

## 6. Validate

- [x] 6.1 Run the affected `error-attribution-kit` tests for the changed modules
- [x] 6.2 Run `openspec validate "unify-hypothesis-type"` and confirm it passes
