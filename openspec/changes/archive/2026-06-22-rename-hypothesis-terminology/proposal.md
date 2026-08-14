## Why

The current `ContinuousHypothesis` and `CategoricalHypothesis` names are misleading because both types are still boolean conditions, and neither maps cleanly to how the toolkit actually classifies them. The current behavior is really about analysis role: non-equality conditions act as regimes, while top-level equality conditions act as attribution features.

## What Changes

- **BREAKING** Rename the public hypothesis terminology to better match behavior:
  - `RegimeHypothesis` for non-equality conditions such as `<`, `>`, `and`, and `or`
  - `FeatureHypothesis` for top-level equality conditions such as `==`
- Update docs and examples to use the new terminology consistently.
- Preserve legacy names as compatibility aliases during the transition where practical.
- Align the README language and API descriptions with the actual routing behavior in the estimator.

## Capabilities

### New Capabilities
- `hypothesis-terminology`: clarify and standardize the public naming for boolean hypotheses based on their analysis role.

### Modified Capabilities
- `estimator-hypothesis-attribution`: rename the public hypothesis classes and adjust documentation/examples so the API terminology matches the analysis model.

## Impact

Affected code includes the public spec types, estimator-facing docs, README examples, and any tests or scripts that import the current hypothesis class names. The underlying analysis behavior should stay the same; this change is primarily about reducing ambiguity and making the API match the implementation.