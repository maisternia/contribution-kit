## ADDED Requirements

### Requirement: Public Hypothesis Types SHALL Use Role-Based Names
The system SHALL expose `RegimeHypothesis` for boolean conditions that are analyzed as error regimes and `FeatureHypothesis` for top-level equality conditions that are analyzed as Shapley features. The system SHALL preserve `ContinuousHypothesis` and `CategoricalHypothesis` as compatibility aliases during the transition, with unchanged behavior.

#### Scenario: New names map to the existing analysis roles
- **WHEN** a caller imports `RegimeHypothesis` or `FeatureHypothesis`
- **THEN** the caller can declare the same flat list of boolean `condition` DSL strings and the estimator routes each hypothesis to the same regime or feature analysis it would have performed before

#### Scenario: Legacy names remain usable during migration
- **WHEN** a caller continues importing `ContinuousHypothesis` or `CategoricalHypothesis`
- **THEN** the caller gets the same analysis results and output shapes as before, without needing to change the underlying conditions

#### Scenario: Terminology aligns with boolean condition role
- **WHEN** a condition is a non-equality expression such as `<`, `>`, `and`, or `or`
- **THEN** the public type name reflects regime analysis rather than data cardinality or numeric continuity
- **WHEN** a condition is a top-level equality such as `==`
- **THEN** the public type name reflects feature attribution rather than categorical data modeling