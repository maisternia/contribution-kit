## MODIFIED Requirements

### Requirement: Hypotheses SHALL Be Declared As A Flat List Of Conditions
The system SHALL declare every hypothesis through one `AttributionSpec.hypotheses` list, where each entry is constructed from a single public `Hypothesis` type carrying a boolean `condition` DSL string and an optional `name`/`label`. The system SHALL treat `Hypothesis` as the only public hypothesis type for callers. The system SHALL NOT expose `RegimeHypothesis`, `FeatureHypothesis`, `ContinuousHypothesis`, `CategoricalHypothesis`, or a `kind` field. The system SHALL NOT require callers to declare regimes, binary tests, mismatch groups, separate actual/baseline expressions, or a specific subtype.

#### Scenario: One condition list describes the whole analysis
- **WHEN** a caller builds an `AttributionSpec` with `prediction_expr`, `target_expr`, an optional `mismatch_expr`, and a flat `hypotheses` list of conditions
- **THEN** the spec fully describes the analysis with no `regimes`, `binary_tests`, or callable predicate inputs

#### Scenario: Estimator is constructed and assessed one way
- **WHEN** a caller runs an attribution analysis
- **THEN** the caller constructs the estimator once (e.g. `Estimator.from_csv(input, spec=spec)`) and invokes a single `assess()` method, with no alternate construction or estimation paths

#### Scenario: Single public Hypothesis type is sufficient
- **WHEN** a caller declares every hypothesis using only the `Hypothesis` type with a `name` and `condition`
- **THEN** the estimator produces correct feature attributions, regime summaries, and mismatch-risk results with no other hypothesis type required

#### Scenario: kind does not influence classification
- **WHEN** two hypotheses share the same `condition`
- **THEN** the estimator classifies both identically based solely on the condition shape

### Requirement: assess SHALL Privately Classify Each Condition
The primary hypotheses a caller declares are **contributing-condition** hypotheses — directional or conditional boolean expressions describing a suspected error regime (for example "detected BW falls below GT BW" or "detected BW is within tolerance but detected SF is wrong"). The system SHALL also accept **exact-match** hypotheses written as a top-level equality (`actual == baseline`) as an extra capability. The system SHALL decide privately how to analyse each hypothesis from the shape of its `condition`, using one rule: a hypothesis whose `condition` is a top-level equality (`actual == baseline`) is a formula feature whose equality operands provide the Shapley actual and baseline values, and any other condition is an error regime. A feature meaningfully contributes to the prediction-formula Shapley attribution when its `name` appears in `prediction_expr`. The system SHALL NOT require any subtype declaration to perform this classification.

#### Scenario: Directional and conditional regimes are the primary use case
- **WHEN** a caller declares the contributing-condition hypotheses `col('Detected BW (Hz)') < col('GT BW (Hz)') * (1 - 0.10)` (detected BW under GT BW), `col('Detected BW (Hz)') > col('GT BW (Hz)') * (1 + 0.10)` (detected BW over GT BW), `abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 and col('Detected SF') != col('GT SF')` (detected BW within tolerance but SF wrong), and `abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 and col('Detected SF') == col('GT SF') and abs(col('Measured BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') > 0.10` (detected BW and SF correct but measured BW off GT BW)
- **THEN** the estimator treats each as an error regime and reports its error share and condition-vs-rest mismatch risk without the caller declaring any regime/binary-test machinery

#### Scenario: Exact-match equality condition is an extra formula feature
- **WHEN** a hypothesis condition is a top-level equality such as `col('Detected SF') == col('GT SF')` or `col('Detected BW (Hz)') == col('GT BW (Hz)')`
- **THEN** the estimator treats the left operand as the model-produced value and the right operand as the ground-truth baseline and includes the feature in the Shapley attribution of the prediction-formula error

#### Scenario: Classification depends only on the condition shape
- **WHEN** one hypothesis has an equality `condition` and another has a non-equality `condition`
- **THEN** the equality hypothesis is classified as a formula feature and the non-equality hypothesis is classified as an error regime, based solely on the condition shape

## ADDED Requirements

### Requirement: Public API SHALL Document The Single Classification Rule
The system SHALL document, in both the `error-attribution-kit` README and the public `Hypothesis` docstring, one canonical classification rule stating that a hypothesis whose `condition` is a top-level equality (`==`) and whose `name` appears in `prediction_expr` becomes a Shapley feature, and that every other hypothesis is an error regime. The documentation SHALL present `Hypothesis` as the single hypothesis type.

#### Scenario: README and docstring state the rule
- **WHEN** a reader consults the README quick start or the `Hypothesis` docstring
- **THEN** they find the single classification rule and a single-`Hypothesis` example, with no other hypothesis type referenced

#### Scenario: CLI builds the canonical type from config
- **WHEN** the CLI loads a config whose hypothesis entries declare `name`, `condition`, and optional `label`
- **THEN** the CLI constructs `Hypothesis` instances directly and classification of each entry depends only on its `condition`
