## Why

The public API exposes two hypothesis classes — `RegimeHypothesis` and
`FeatureHypothesis` (plus `ContinuousHypothesis`/`CategoricalHypothesis`
aliases) — but the estimator ignores the class and the `kind` field entirely. It
routes every hypothesis purely by inspecting the `condition`: a top-level
equality whose `name` appears in `prediction_expr` becomes a Shapley feature, and
everything else becomes an error regime. The two-class surface therefore implies
a choice that does not exist, which repeatedly confuses callers about which type
to use and what difference it makes.

## What Changes

- Promote `Hypothesis` to the single public type callers construct. A hypothesis
  is just a `name` + `condition` (+ optional `label`).
- Remove `RegimeHypothesis`, `FeatureHypothesis`, `ContinuousHypothesis`, and
  `CategoricalHypothesis`. The toolkit has not been shared, so no compatibility
  aliases are kept.
- Remove the `kind` field entirely. The estimator already ignores it; the public
  surface no longer implies it controls feature-vs-regime classification.
- Document the single routing rule explicitly: "A hypothesis whose `condition` is
  a top-level equality (`==`) and whose `name` appears in `prediction_expr`
  becomes a Shapley feature; every other hypothesis is an error regime."
- Update the README quick start, the `error-attribution-kit` docstrings, the CLI
  config loading, and the bundled example configs to use the single `Hypothesis`
  type and the documented rule.

No analysis behavior changes: identical specs produce identical
`feature_attributions`, `regime_summaries`, and `binary_results`.

## Capabilities

### New Capabilities
<!-- None: this change refines an existing capability's declaration surface. -->

### Modified Capabilities
- `estimator-hypothesis-attribution`: the hypothesis declaration surface becomes
  a single public `Hypothesis` type; the spec removes `kind` and the subtype
  classes and instead mandates that classification is derived solely from the
  `condition` shape and `prediction_expr` membership.

## Impact

- `external/error-attribution-kit/src/error_attribution/spec.py`: `Hypothesis`
  becomes the only type; subclasses/aliases and the `kind` field are removed.
- `external/error-attribution-kit/src/error_attribution/__init__.py`: export only
  `Hypothesis`.
- `external/error-attribution-kit/src/error_attribution/cli.py`: build
  `Hypothesis` directly from config entries.
- `external/error-attribution-kit/README.md` and module docstrings: single-type
  quick start plus the explicit routing-rule explanation.
- `external/error-attribution-kit/examples/*/config.json`: `kind` keys removed.
- `external/error-attribution-kit/tests/`: coverage asserting condition-based
  routing.
- No change to estimator analysis math or output schemas.
