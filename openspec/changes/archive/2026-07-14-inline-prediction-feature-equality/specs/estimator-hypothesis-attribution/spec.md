# estimator-hypothesis-attribution Delta Specification

## ADDED Requirements

### Requirement: Prediction Features SHALL Accept Equality String Shorthand In Config Files
The config JSON/YAML loader SHALL accept each `prediction_features` mapping
value in one of two forms: the explicit object form `{actual, baseline, label?}`
or a shorthand string whose parsed top-level expression is exactly one equality
`actual == baseline`. The shorthand SHALL be accepted only in config loading;
after parsing, both forms SHALL normalize to the same internal
`PredictionFeature(actual, baseline, label)` representation used by the
estimator. The feature name from the mapping key SHALL remain the variable name
used by `prediction_expr` binding.

#### Scenario: Equality shorthand parses as a feature
- **WHEN** a config declares `"class_sf_correct": "col('Class SF') == col('GT SF')"` under `prediction_features`
- **THEN** the loader accepts the config and constructs an internal prediction feature whose `actual` expression is `col('Class SF')` and whose `baseline` expression is `col('GT SF')`

#### Scenario: Mixed shorthand and explicit features coexist
- **WHEN** one prediction feature uses the shorthand string form and another uses the explicit `{actual, baseline, label}` object form
- **THEN** the loader accepts both in the same config and the estimator evaluates them identically after normalization

#### Scenario: Shorthand is limited to top-level equality
- **WHEN** a string-valued prediction feature is declared as `col('Class SF') != col('GT SF')`, `col('Class BW') < col('GT BW')`, or `col('A') == col('B') and col('C') == col('D')`
- **THEN** loading fails with a validation error explaining that string shorthand is allowed only for a top-level `==` equality

#### Scenario: Labeled equality feature still uses explicit object form
- **WHEN** a caller wants an equality-based feature with a custom `label`
- **THEN** the caller declares it with the explicit object form rather than the string shorthand, and the loader preserves the provided label

## MODIFIED Requirements

### Requirement: Hypotheses SHALL Be Declared As A Flat List Of Conditions
The system SHALL declare every caller-authored hypothesis through one `AttributionSpec.hypotheses` list, where each entry is constructed from a single public `Hypothesis` type carrying a boolean `condition` DSL string and an optional `name`/`label`. The system SHALL treat `Hypothesis` as the only public hypothesis type for callers. The system SHALL NOT require callers to declare regimes, binary tests, mismatch groups, or a specific subtype. In addition to the flat list, the system SHALL accept optional `factorials` declarations whose crossings expand into generated regime hypotheses at assessment time; generated hypotheses SHALL be internal `Hypothesis` instances that join the same regime-analysis pipeline as declared hypotheses, and callers SHALL NOT construct cell hypotheses by hand to obtain factorial analysis. Shapley formula features SHALL be declared separately through `prediction_features`, not inferred from hypothesis condition shape.

#### Scenario: One condition list describes the regime analysis
- **WHEN** a caller builds an `AttributionSpec` with `prediction_expr`, `target`, `prediction`, and a flat `hypotheses` list of conditions
- **THEN** the hypothesis list fully describes the regime side of the analysis with no `regimes`, `binary_tests`, or callable predicate inputs

#### Scenario: Factorial expansion feeds the same regime pipeline
- **WHEN** a spec declares a `factorials` crossing alongside a flat `hypotheses` list
- **THEN** the generated cell hypotheses are analysed by the same regime pipeline as declared hypotheses, and any Shapley features still come only from `prediction_features`

#### Scenario: Equality condition in hypotheses remains a regime
- **WHEN** a hypothesis condition is `col('Class SF') == col('GT SF')`
- **THEN** the estimator evaluates that hypothesis as a regime selector and does not synthesize a prediction feature from it

### Requirement: assess SHALL Privately Classify Each Condition
The primary hypotheses a caller declares are contributing-condition hypotheses — directional or conditional boolean expressions describing a suspected regime. The system SHALL evaluate each declared hypothesis condition only as a regime selector, regardless of whether the condition uses `==`, `!=`, or any other supported comparison. The system SHALL NOT infer Shapley features from hypothesis condition shape. Formula features SHALL instead be declared explicitly through `prediction_features`, whose config loader MAY accept the equality-string shorthand `actual == baseline` as a convenience syntax for exact-match features. A feature SHALL be routed to feature analysis because it is declared under `prediction_features`, not because its expression text resembles a condition.

#### Scenario: Equality and non-equality hypotheses share regime routing
- **WHEN** one hypothesis condition uses `==` and another uses `<`
- **THEN** both hypotheses are evaluated as regimes, based on where they are declared rather than on the operator they contain

#### Scenario: Equality feature is declared in prediction_features
- **WHEN** the config declares `class_sf_correct` under `prediction_features` using either the explicit object form or the equality-string shorthand
- **THEN** the estimator includes `class_sf_correct` in Shapley attribution as a formula feature

#### Scenario: Compound boolean feature shorthand is rejected
- **WHEN** a caller places a compound boolean string under `prediction_features`
- **THEN** validation fails instead of treating the string as either a regime or a feature

### Requirement: Public API SHALL Document The Single Classification Rule
The system SHALL document, in both the `contribution-kit` README and the public `Hypothesis` docstring, one canonical routing rule: entries declared in `prediction_features` are formula features, and entries declared in `hypotheses` are regimes. The documentation SHALL state that config files may use a top-level `actual == baseline` shorthand only inside `prediction_features`, while every hypothesis condition — including equality conditions — remains a regime. The documentation SHALL present `Hypothesis` as the single public hypothesis type and the explicit `PredictionFeature(actual, baseline)` form as the canonical feature representation.

#### Scenario: README and docstring separate feature and regime declarations
- **WHEN** a reader consults the README quick start or the `Hypothesis` docstring
- **THEN** they find that `prediction_features` declares formula features, `hypotheses` declares regimes, and `==` shorthand is mentioned only for config-loaded prediction features

#### Scenario: CLI builds the canonical types from config
- **WHEN** the CLI loads a config whose `prediction_features` entries mix explicit objects and equality-string shorthand and whose `hypotheses` entries declare regime conditions
- **THEN** the CLI constructs canonical `PredictionFeature` and `Hypothesis` instances directly, and routing depends on the declaration site rather than condition-shape inference