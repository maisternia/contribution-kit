## 1. Public API Rename

- [x] 1.1 Add `RegimeHypothesis` and `FeatureHypothesis` to the public hypothesis module and export them from the package entry points.
- [x] 1.2 Keep `ContinuousHypothesis` and `CategoricalHypothesis` working as compatibility aliases that preserve existing behavior.

## 2. Documentation and Examples

- [x] 2.1 Update the README and inline API docs to describe hypotheses using regime/feature terminology instead of continuous/categorical terminology.
- [x] 2.2 Update example snippets and any user-facing text that demonstrates the old class names so the new names are the default.

## 3. Tests and Validation

- [x] 3.1 Add or update tests to verify that both the new names and the legacy aliases construct the same hypothesis objects and produce identical estimator output.
- [x] 3.2 Run the focused validation used by this repository for the estimator-attribution path and confirm the rename does not change runtime behavior.