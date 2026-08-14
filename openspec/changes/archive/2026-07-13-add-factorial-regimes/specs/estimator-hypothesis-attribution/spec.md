# estimator-hypothesis-attribution Delta Specification

## MODIFIED Requirements

### Requirement: Hypotheses SHALL Be Declared As A Flat List Of Conditions
The system SHALL declare every caller-authored hypothesis through one `AttributionSpec.hypotheses` list, where each entry is constructed from a single public `Hypothesis` type carrying a boolean `condition` DSL string and an optional `name`/`label`. The system SHALL treat `Hypothesis` as the only public hypothesis type for callers. The system SHALL NOT require callers to declare regimes, binary tests, mismatch groups, separate actual/baseline expressions, or a specific subtype. In addition to the flat list, the system SHALL accept optional `factors`/`factorials` declarations whose crossings expand into generated regime hypotheses at assessment time; generated hypotheses SHALL be internal `Hypothesis` instances that join the same classification and analysis pipeline as declared hypotheses, and callers SHALL NOT construct cell hypotheses by hand to obtain factorial analysis.

#### Scenario: One condition list describes the whole analysis
- **WHEN** a caller builds an `AttributionSpec` with `prediction_expr`, `target_expr`, an optional `mismatch_expr`, and a flat `hypotheses` list of conditions
- **THEN** the spec fully describes the analysis with no `regimes`, `binary_tests`, or callable predicate inputs

#### Scenario: Estimator is constructed and assessed one way
- **WHEN** a caller runs an attribution analysis
- **THEN** the caller constructs the estimator once (e.g. `Estimator.from_csv(input, spec=spec)`) and invokes a single `assess()` method, with no alternate construction or estimation paths

#### Scenario: Single public Hypothesis type is sufficient
- **WHEN** a caller declares every hypothesis using only the `Hypothesis` type with a `name` and `condition`
- **THEN** the estimator produces correct feature attributions, regime summaries, and mismatch-risk results with no other hypothesis type required

#### Scenario: Factorial expansion feeds the same hypothesis pipeline
- **WHEN** a spec declares `factors` and a `factorials` crossing alongside a flat `hypotheses` list
- **THEN** the generated cell hypotheses are routed by the same private classification rule as declared hypotheses (their conjunction conditions are non-equality, so all cells are regimes), and declared equality hypotheses still become Shapley features unchanged
