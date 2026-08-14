# Delta: estimator-hypothesis-attribution — explicit prediction features

## ADDED Requirements

### Requirement: Prediction Features SHALL Be Declared Explicitly As Actual/Baseline Pairs
The system SHALL accept a `prediction_features` declaration on `AttributionSpec` (and in the JSON config) as the only way to declare Shapley features: a mapping from feature name to an entry with required `actual` and `baseline` DSL expression strings and an optional `label`. The `actual` expression SHALL provide the model-produced value and the `baseline` expression SHALL provide the ground-truth baseline value for Shapley coalition evaluation of `prediction_expr`. The system SHALL NOT derive features from hypothesis condition syntax. Feature declaration order SHALL be preserved in results.

#### Scenario: Feature declared as an actual/baseline pair joins Shapley attribution
- **WHEN** a spec declares `prediction_features` with `class_sf: {actual: "col('Class SF')", baseline: "col('GT SF')"}` and `prediction_expr` references `class_sf`
- **THEN** the estimator evaluates `actual` as the model-produced value and `baseline` as the ground-truth value and includes `class_sf` in the Shapley attribution of the prediction-formula contribution

#### Scenario: Missing actual or baseline key fails fast
- **WHEN** a JSON config declares a `prediction_features` entry without an `actual` key or without a `baseline` key
- **THEN** spec loading fails with a validation error naming the feature and the missing key

#### Scenario: Operand direction is fixed by key names
- **WHEN** a caller declares a feature pair with `actual` and `baseline` keys in any textual order
- **THEN** the model-produced and ground-truth roles are bound by key name, and no operand-order swap is possible

### Requirement: Spec Validation SHALL Enforce Feature And Formula Consistency
The system SHALL validate at assessment time that the set of free variables of `prediction_expr` (its name nodes excluding built-in DSL functions and `col`) is exactly equal to the set of declared `prediction_features` names, and SHALL fail fast with an error naming each offending variable or feature when either direction is violated. The system SHALL also reject a `prediction_features` name that collides with a declared hypothesis name.

#### Scenario: Formula variable without a feature declaration is an error
- **WHEN** `prediction_expr` references a variable `measured_bw` that has no `prediction_features` entry
- **THEN** `assess` fails with a validation error identifying `measured_bw` as an undeclared prediction feature

#### Scenario: Declared feature not referenced by the formula is an error
- **WHEN** `prediction_features` declares `class_bw` but `prediction_expr` does not reference `class_bw`
- **THEN** `assess` fails with a validation error identifying `class_bw` as unused by `prediction_expr` instead of silently attributing zero

#### Scenario: Feature and hypothesis name collision is an error
- **WHEN** a spec declares a `prediction_features` entry and a `hypotheses` entry with the same name
- **THEN** `assess` fails with a validation error reporting the duplicate name

## MODIFIED Requirements

### Requirement: Hypotheses SHALL Be Declared As A Flat List Of Conditions
The system SHALL declare every caller-authored hypothesis through one `AttributionSpec.hypotheses` list, where each entry is constructed from a single public `Hypothesis` type carrying a boolean `condition` DSL string and an optional `name`/`label`. The system SHALL treat `Hypothesis` as the only public hypothesis type for callers, and SHALL analyse every hypothesis as an error regime regardless of condition shape (equality conditions included). The system SHALL NOT require callers to declare regimes, binary tests, mismatch groups, or a specific subtype; Shapley features SHALL be declared only through the separate `prediction_features` mapping. In addition to the flat list, the system SHALL accept optional `factors`/`factorials` declarations whose crossings expand into generated regime hypotheses at assessment time; generated hypotheses SHALL be internal `Hypothesis` instances that join the same regime analysis pipeline as declared hypotheses, and callers SHALL NOT construct cell hypotheses by hand to obtain factorial analysis.

#### Scenario: One spec describes the whole analysis
- **WHEN** a caller builds an `AttributionSpec` with `prediction_expr`, `target_expr`, an optional `mismatch_expr`, a `prediction_features` mapping, and a flat `hypotheses` list of regime conditions
- **THEN** the spec fully describes the analysis with no `regimes`, `binary_tests`, or callable predicate inputs

#### Scenario: Estimator is constructed and assessed one way
- **WHEN** a caller runs an attribution analysis
- **THEN** the caller constructs the estimator once (e.g. `Estimator.from_csv(input, spec=spec)`) and invokes a single `assess()` method, with no alternate construction or estimation paths

#### Scenario: Equality conditions are ordinary regimes
- **WHEN** a caller declares a hypothesis whose condition is a top-level equality such as `col('Class SF') == col('GT SF')`
- **THEN** the estimator analyses it as an error regime with an observed-contribution share and condition-vs-rest mismatch risk, and does not create a Shapley feature from it

#### Scenario: Factorial expansion feeds the same hypothesis pipeline
- **WHEN** a spec declares `factors` and a `factorials` crossing alongside a flat `hypotheses` list
- **THEN** the generated cell hypotheses join the same regime analysis pipeline as declared hypotheses, and declared `prediction_features` remain the only source of Shapley features

### Requirement: assess SHALL Return One Unified Per-Hypothesis Result
The system SHALL return from `assess` an `AssessmentResult` whose `hypotheses` list holds exactly one `HypothesisAssessment` per declared prediction feature (`analysis="feature"`, in feature declaration order) and one per declared hypothesis (`analysis="regime"`, in declaration order), and SHALL expose `feature_attributions`, `regime_summaries`, and `binary_results` as derived read-only views.

#### Scenario: One assessment per declared feature and hypothesis
- **WHEN** a caller invokes `assess` with a `prediction_features` mapping and a flat regime condition list
- **THEN** `result.hypotheses` has one `analysis="feature"` entry per declared prediction feature and one `analysis="regime"` entry per declared hypothesis, each carrying only the sub-results that apply

#### Scenario: Derived views preserve legacy table shapes
- **WHEN** a caller reads `feature_attributions`, `regime_summaries`, or `binary_results`
- **THEN** each view returns the corresponding sub-results (feature attributions ranked by net contribution share) without requiring the caller to inspect the unified list

### Requirement: Integration Tests SHALL Verify Single-Condition Hypothesis Estimation
The system SHALL include integration tests that construct the estimator exactly one way from a single spec carrying a `prediction_features` mapping and a flat regime condition list, and assert the unified per-hypothesis output, the regime error shares, the condition-vs-rest mismatch risk, and the feature attributions from one `assess` call. The tests SHALL also assert that inconsistent feature/formula declarations fail validation.

#### Scenario: Integration test validates the explicit-features flow
- **WHEN** the integration suite runs against the combined measurements fixture
- **THEN** tests build one `AttributionSpec` with `prediction_features` pairs and a flat regime condition list, call `assess` once, and assert that the unified `hypotheses` list, `feature_attributions`, `regime_summaries`, and condition-vs-rest `binary_results` match values derived from the source data

#### Scenario: Integration test validates fail-fast declarations
- **WHEN** the integration suite builds specs with an undeclared formula variable, an unused feature, or a feature/hypothesis name collision
- **THEN** each `assess` call fails with the corresponding validation error

## REMOVED Requirements

### Requirement: assess SHALL Privately Classify Each Condition
**Reason**: Syntax-shape routing (top-level `==` becomes a Shapley feature) is replaced by the explicit `prediction_features` declaration. The implicit rule allowed silent operand swaps, silent misrouting in both directions, and zero-effect features whose names were absent from `prediction_expr`.
**Migration**: Move each equality feature-hypothesis into `prediction_features` as `{actual: <left operand>, baseline: <right operand>}`. Keep genuinely subgroup-oriented equality conditions in `hypotheses`, where they are now analysed as regimes.
