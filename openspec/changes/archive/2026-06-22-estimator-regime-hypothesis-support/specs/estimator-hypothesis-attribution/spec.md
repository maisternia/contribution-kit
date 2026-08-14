## ADDED Requirements

### Requirement: Hypotheses SHALL Be Declared As A Flat List Of Conditions
The system SHALL declare every hypothesis through one `AttributionSpec.hypotheses` list, where each `Hypothesis` carries a single boolean `condition` DSL string and an optional `name`/`label`/`kind`. The system SHALL NOT require callers to declare regimes, binary tests, mismatch groups, or separate actual/baseline expressions.

#### Scenario: One condition list describes the whole analysis
- **WHEN** a caller builds an `AttributionSpec` with `prediction_expr`, `target_expr`, an optional `mismatch_expr`, and a flat `hypotheses` list of conditions
- **THEN** the spec fully describes the analysis with no `regimes`, `binary_tests`, or callable predicate inputs

#### Scenario: Estimator is constructed and assessed one way
- **WHEN** a caller runs an attribution analysis
- **THEN** the caller constructs the estimator once (e.g. `Estimator.from_csv(input, spec=spec)`) and invokes a single `assess()` method, with no alternate construction or estimation paths

### Requirement: assess SHALL Privately Classify Each Condition
The primary hypotheses a caller declares are **contributing-condition** hypotheses — directional or conditional boolean expressions describing a suspected error regime (for example "detected BW falls below GT BW" or "detected BW is within tolerance but detected SF is wrong"). The system SHALL also accept **exact-match** hypotheses written as a top-level equality (`actual == baseline`) as an extra capability. The system SHALL decide privately how to analyse each hypothesis from the shape of its `condition`: a top-level equality SHALL be a formula feature whose equality operands provide the Shapley actual and baseline values, and any other condition SHALL be an error regime.

#### Scenario: Directional and conditional regimes are the primary use case
- **WHEN** a caller declares the contributing-condition hypotheses `col('Detected BW (Hz)') < col('GT BW (Hz)') * (1 - 0.10)` (detected BW under GT BW), `col('Detected BW (Hz)') > col('GT BW (Hz)') * (1 + 0.10)` (detected BW over GT BW), `abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 and col('Detected SF') != col('GT SF')` (detected BW within tolerance but SF wrong), and `abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 and col('Detected SF') == col('GT SF') and abs(col('Measured BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') > 0.10` (detected BW and SF correct but measured BW off GT BW)
- **THEN** the estimator treats each as an error regime and reports its error share and condition-vs-rest mismatch risk without the caller declaring any regime/binary-test machinery

#### Scenario: Exact-match equality condition is an extra formula feature
- **WHEN** a hypothesis condition is a top-level equality such as `col('Detected SF') == col('GT SF')` or `col('Detected BW (Hz)') == col('GT BW (Hz)')`
- **THEN** the estimator treats the left operand as the model-produced value and the right operand as the ground-truth baseline and includes the feature in the Shapley attribution of the prediction-formula error

### Requirement: assess SHALL Return One Unified Per-Hypothesis Result
The system SHALL return from `assess` an `AssessmentResult` whose `hypotheses` list holds exactly one `HypothesisAssessment` per declared hypothesis, in declaration order, and SHALL expose `feature_attributions`, `regime_summaries`, and `binary_results` as derived read-only views.

#### Scenario: One assessment per declared hypothesis
- **WHEN** a caller invokes `assess` with a flat condition list
- **THEN** `result.hypotheses` has one entry per declared hypothesis in declaration order, each carrying only the analysis (`feature` or `regime`) sub-results that apply

#### Scenario: Derived views preserve legacy table shapes
- **WHEN** a caller reads `feature_attributions`, `regime_summaries`, or `binary_results`
- **THEN** each view returns the corresponding sub-results (feature attributions ranked by net error share) without requiring the caller to inspect the unified list

### Requirement: Regime Hypotheses SHALL Share The Observed Error And Compare Against The Rest
The system SHALL attribute to each regime hypothesis the same per-row observed error used by the feature attribution (derived from `prediction_expr` versus `target_expr`), and SHALL compute its mismatch risk by comparing the matching rows against the rest of the population using the spec-level `mismatch_expr`.

#### Scenario: Compute requested class BW regime contributions
- **WHEN** a caller declares regime conditions including `class_bw < gt_bw (beyond tol)`, `class_bw > gt_bw (beyond tol)`, `class_bw within tol & sf wrong`, `class_bw & sf ok, measured_bw off`, and the baseline regime
- **THEN** the estimator returns regime summaries with `name`, `count`, `mean_error`, `total_error`, and `error_share_pct`, where the error totals are derived from the spec's `prediction_expr` versus `target_expr`

#### Scenario: Compute condition-vs-rest mismatch risk
- **WHEN** a regime hypothesis is evaluated and `mismatch_expr` is set
- **THEN** the estimator returns a binary result comparing the matching rows (group A) against the rest of the population (group B) with mismatch rates, risk ratio, and odds ratio with confidence intervals

### Requirement: Legacy Scripts SHALL Remain Unchanged
The system SHALL implement unified estimator hypothesis estimation without modifying existing scripts in `scripts/` that document historical, single-use analyses.

#### Scenario: Unified estimator capability added without script edits
- **WHEN** the new estimator hypothesis feature is implemented
- **THEN** legacy scripts remain unchanged and continue serving as prior-reference analysis artifacts

### Requirement: Integration Tests SHALL Verify Single-Condition Hypothesis Estimation
The system SHALL include integration tests that construct the estimator exactly one way from a single flat condition spec and assert the unified per-hypothesis output, the regime error shares, and the condition-vs-rest mismatch risk from one `assess` call.

#### Scenario: Integration test validates the single-condition flow
- **WHEN** the integration suite runs against the combined measurements fixture
- **THEN** tests build one `AttributionSpec` from a flat condition list, call `assess` once, and assert that the unified `hypotheses` list, `feature_attributions`, `regime_summaries`, and condition-vs-rest `binary_results` match values derived from the source data
