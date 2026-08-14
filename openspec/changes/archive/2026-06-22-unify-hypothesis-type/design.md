## Context

`error-attribution-kit` exposes `Hypothesis` plus subclasses `RegimeHypothesis`
and `FeatureHypothesis` (and aliases `ContinuousHypothesis` /
`CategoricalHypothesis`). The only thing the subclasses change is the default
`kind` value. The estimator never reads `kind` or the class: `Estimator._formula_features`
calls `split_equality(compile_expression(hypothesis.condition))` and treats any
top-level equality as a Shapley feature; the `assess` loop then routes a
hypothesis to `analysis="feature"` iff its `name` is in the derived feature set,
otherwise `analysis="regime"`. Classification is therefore already a pure
function of `condition` shape and `prediction_expr` membership.

The kit is consumed as a git submodule (the code lives under
`external/error-attribution-kit/`) but has not been shared with anyone, so the
extra type names and the `kind` field can be removed outright without
compatibility concerns.

## Goals / Non-Goals

**Goals:**
- Make `Hypothesis` the one and only type callers construct.
- State the classification rule once, in code docs and README: top-level `==`
  condition whose `name` is in `prediction_expr` → feature; otherwise → regime.
- Preserve exact analysis behavior and output schemas.
- Remove the redundant subclass names and the `kind` field entirely.

**Non-Goals:**
- Changing Shapley math, regime metrics, or mismatch-risk computation.
- Changing the `AssessmentResult` shape or any derived view.

## Decisions

**Decision: Single canonical `Hypothesis`; subclasses and `kind` removed.**
`RegimeHypothesis`, `FeatureHypothesis`, `ContinuousHypothesis`, and
`CategoricalHypothesis` are deleted, and the `kind` field is dropped from the
dataclass and configs.
- *Why over keeping aliases:* the submodule has not been shared, so there is no
  downstream to migrate; removing the dead surface keeps the API minimal.

**Decision: CLI builds `Hypothesis` directly.**
`cli.py` constructs `Hypothesis(...)` directly from config entries.

**Decision: Documentation states the rule verbatim.**
README and `spec.py` docstring carry the same sentence so there is one canonical
description: "A hypothesis whose `condition` is a top-level equality (`==`) and
whose `name` appears in `prediction_expr` becomes a Shapley feature; every other
hypothesis is an error regime."

## Risks / Trade-offs

- [Behavioral drift during refactor] → Retain tests asserting identical
  `feature_attributions` and `regime_summaries` for the bundled example so the
  refactor is provably behavior-preserving.
