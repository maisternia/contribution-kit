# estimator-hypothesis-attribution Delta Specification

## REMOVED Requirements

### Requirement: Hypotheses SHALL Be Declared As A Named Mapping Of Conditions

**Reason**: Renamed to "Regimes SHALL Be Declared As A Named Mapping Of Conditions" — the declared objects are regimes; "hypothesis" is reserved for statistical tests and the human claim motivating an analysis.

### Requirement: assess SHALL Return One Unified Per-Hypothesis Result

**Reason**: Renamed to "assess SHALL Return One Unified Per-Regime Result" with the result surface renamed accordingly.

### Requirement: Regime Hypotheses SHALL Share The Observed Error And Compare Against The Rest

**Reason**: Renamed to "Regimes SHALL Share The Observed Error And Compare Against The Rest" (vocabulary only).

### Requirement: Integration Tests SHALL Verify Single-Condition Hypothesis Estimation

**Reason**: Renamed to "Integration Tests SHALL Verify Single-Condition Regime Estimation" (vocabulary only).

## ADDED Requirements

### Requirement: Regimes SHALL Be Declared As A Named Mapping Of Conditions
The system SHALL declare every caller-authored regime through one `AttributionSpec.regimes` collection whose config representation is a name-keyed **mapping** (`{name -> value}`), where the map key is the regime name and each value is either (a) a boolean `condition` DSL string, or (b) an object with a required `condition` DSL string and an optional `label`. A string value SHALL be equivalent to an object whose `condition` is that string and whose `label` defaults to the key. Each entry SHALL be materialized as the single public `Regime` type carrying `name` (the key), `condition`, and an optional `label`. The system SHALL treat `Regime` as the only public regime type for callers, and SHALL keep `Hypothesis`, `CategoricalHypothesis`, and `ContinuousHypothesis` importable as backward-compatible aliases of `Regime`. The system SHALL NOT require callers to declare binary tests, mismatch groups, or a specific subtype. Mapping insertion order SHALL be preserved for rendering. The list form of `regimes` SHALL NOT be accepted in config files. A config file containing the legacy `hypotheses` key SHALL be rejected with a configuration error stating that the key was renamed to `regimes`. In addition to the mapping, the system SHALL accept optional `factorials` declarations whose crossings expand into generated regimes at assessment time; generated regimes SHALL be internal `Regime` instances that join the same regime-analysis pipeline as declared regimes, and callers SHALL NOT construct cell regimes by hand to obtain factorial analysis. Shapley formula features SHALL be declared separately through `prediction_features`, not inferred from regime condition shape.

#### Scenario: One condition mapping describes the regime analysis
- **WHEN** a caller builds a config with `prediction_expr`, `target`, `prediction`, and a `regimes` mapping of name → condition
- **THEN** the regime mapping fully describes the regime side of the analysis with no `binary_tests` or callable predicate inputs, and no repeated `name` field inside entries

#### Scenario: String shorthand is equivalent to an object with a defaulted label
- **WHEN** an entry is written as `"class_sf_mismatch": "col('Class SF') != col('GT SF')"`
- **THEN** it materializes as a `Regime` with `name` = `class_sf_mismatch`, `condition` = that string, and `label` = `class_sf_mismatch`, identical to writing `"class_sf_mismatch": { "condition": "col('Class SF') != col('GT SF')" }`

#### Scenario: Object form carries an explicit label
- **WHEN** an entry is written as `"class_sf_mismatch": { "label": "Nominal class SF wrong", "condition": "col('Class SF') != col('GT SF')" }`
- **THEN** it materializes as a `Regime` with `name` = `class_sf_mismatch`, that `label`, and that `condition`

#### Scenario: Object missing condition is rejected
- **WHEN** a `regimes` entry value is an object without a `condition` key
- **THEN** the loader raises a configuration error naming the offending regime key

#### Scenario: Redundant name key is rejected
- **WHEN** a `regimes` entry object includes a `name` field
- **THEN** the loader raises a configuration error, because the mapping key already supplies the name

#### Scenario: Legacy hypotheses key is rejected with a migration error
- **WHEN** a config file declares a top-level `hypotheses` key
- **THEN** loading fails with a configuration error stating that `hypotheses` was renamed to `regimes`

#### Scenario: Mapping order is preserved
- **WHEN** a `regimes` mapping declares entries in a given order
- **THEN** the materialized regimes and their report rows follow that declared order

#### Scenario: Estimator is constructed and assessed one way
- **WHEN** a caller runs an attribution analysis
- **THEN** the caller constructs the estimator once (e.g. `Estimator.from_csv(input, spec=spec)`) and invokes a single `assess()` method, with no alternate construction or estimation paths

#### Scenario: Single public Regime type is sufficient
- **WHEN** a caller declares every regime using only the `Regime` type with a `name` and `condition`
- **THEN** the estimator produces correct feature attributions, regime summaries, and mismatch-risk results with no other regime type required

#### Scenario: Legacy type names remain importable aliases
- **WHEN** existing code imports `Hypothesis` from the package root and constructs it
- **THEN** the import succeeds and the constructed object is a `Regime`

#### Scenario: Factorial expansion feeds the same regime pipeline
- **WHEN** a spec declares a `factorials` crossing alongside a `regimes` mapping
- **THEN** the generated cell regimes are analysed by the same regime pipeline as declared regimes, and any Shapley features still come only from `prediction_features`

#### Scenario: Equality condition in regimes remains a regime
- **WHEN** a regime condition is `col('Class SF') == col('GT SF')`
- **THEN** the estimator evaluates that regime as a row selector and does not synthesize a prediction feature from it

### Requirement: assess SHALL Return One Unified Per-Regime Result
The system SHALL return from `assess` an `AssessmentResult` whose `regimes` list holds exactly one `RegimeAssessment` per declared regime, in declaration order, and SHALL expose `feature_attributions`, `regime_summaries`, and `binary_results` as derived read-only views. `HypothesisAssessment` SHALL remain importable as a backward-compatible alias of `RegimeAssessment`. The JSON output SHALL carry the per-regime entries under a `regimes` key; `contrib report` SHALL additionally accept the legacy `hypotheses` key when reading a previously saved `run.json`, while the write path SHALL emit only `regimes`.

#### Scenario: One assessment per declared regime
- **WHEN** a caller invokes `assess` with a flat condition spec
- **THEN** `result.regimes` has one entry per declared regime in declaration order, each carrying only the analysis (`feature` or `regime`) sub-results that apply

#### Scenario: Derived views preserve legacy table shapes
- **WHEN** a caller reads `feature_attributions`, `regime_summaries`, or `binary_results`
- **THEN** each view returns the corresponding sub-results (feature attributions ranked by net contribution share) without requiring the caller to inspect the unified list

#### Scenario: JSON writes the new key and report reads the legacy key
- **WHEN** `run.json` is written by `save()` and an older `run.json` containing a `hypotheses` payload key is passed to `contrib report`
- **THEN** the new file carries the entries under `regimes`, and the older file still renders a report

### Requirement: Regimes SHALL Share The Observed Error And Compare Against The Rest
The system SHALL attribute to each regime the same per-row observed error used by the feature attribution (derived from `prediction_expr` versus `target_expr`), and SHALL compute its mismatch risk by comparing the matching rows against the rest of the population using the spec-level `mismatch_expr`. The reported risk-ratio and odds-ratio confidence intervals SHALL use Koopman asymptotic-score and Baptista-Pike exact methods as the primary default methods; when either primary method yields a non-finite or unordered interval for a finite point estimate, the system SHALL automatically use Katz (risk ratio) or Haldane-Anscombe (odds ratio) for that result.

#### Scenario: Compute requested class BW regime contributions
- **WHEN** a caller declares regime conditions including `class_bw < gt_bw (beyond tol)`, `class_bw > gt_bw (beyond tol)`, `class_bw within tol & sf wrong`, `class_bw & sf ok, measured_bw off`, and the baseline regime
- **THEN** the estimator returns regime summaries with `name`, `count`, `mean_contribution`, `total_contribution`, and `contribution_share_pct`, where the contribution totals are derived from the spec's `prediction_expr` versus `target_expr`

#### Scenario: Compute condition-vs-rest mismatch risk
- **WHEN** a regime is evaluated and `mismatch_expr` is set
- **THEN** the estimator returns a binary result comparing the matching rows (group A) against the rest of the population (group B) with mismatch rates, risk ratio, and odds ratio with confidence intervals

#### Scenario: Default output avoids non-finite bounds for finite-point rows
- **WHEN** a finite risk-ratio or odds-ratio point estimate is computed and the primary default inversion yields a non-finite or unordered confidence interval
- **THEN** the corresponding confidence interval in reported output is computed using the paper-cited fallback method for that effect size and rendered as an ordered finite interval

#### Scenario: Markdown reports include confidence-interval ranges
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk rows
- **THEN** the report table labels the first column `Regime`, labels the effect-size columns as `risk ratio (95% CI)` and `odds ratio (95% CI)`, and formats each as `value (low to high)`

### Requirement: Integration Tests SHALL Verify Single-Condition Regime Estimation
The system SHALL include integration tests that construct the estimator exactly one way from a single flat condition spec and assert the unified per-regime output, the regime error shares, and the condition-vs-rest mismatch risk from one `assess` call.

#### Scenario: Integration test validates the single-condition flow
- **WHEN** the integration suite runs against the combined measurements fixture
- **THEN** tests build one `AttributionSpec` from a flat condition spec, call `assess` once, and assert that the unified `regimes` list, `feature_attributions`, `regime_summaries`, and condition-vs-rest `binary_results` match values derived from the source data

## MODIFIED Requirements

### Requirement: assess SHALL Privately Classify Each Condition
The primary regimes a caller declares are contributing-condition regimes — directional or conditional boolean expressions describing a suspected failure mode. The system SHALL evaluate each declared regime condition only as a row selector, regardless of whether the condition uses `==`, `!=`, or any other supported comparison. The system SHALL NOT infer Shapley features from regime condition shape. Formula features SHALL instead be declared explicitly through `prediction_features`, whose config loader MAY accept the equality-string shorthand `actual == baseline` as a convenience syntax for exact-match features. A feature SHALL be routed to feature analysis because it is declared under `prediction_features`, not because its expression text resembles a condition.

#### Scenario: Equality and non-equality regimes share regime routing
- **WHEN** one regime condition uses `==` and another uses `<`
- **THEN** both regimes are evaluated as row selectors, based on where they are declared rather than on the operator they contain

#### Scenario: Equality feature is declared in prediction_features
- **WHEN** the config declares `class_sf_correct` under `prediction_features` using either the explicit object form or the equality-string shorthand
- **THEN** the estimator includes `class_sf_correct` in Shapley attribution as a formula feature

#### Scenario: Compound boolean feature shorthand is rejected
- **WHEN** a caller places a compound boolean string under `prediction_features`
- **THEN** validation fails instead of treating the string as either a regime or a feature

### Requirement: Public API SHALL Document The Single Classification Rule
The system SHALL document, in both the `contribution-kit` README and the public `Regime` docstring, one canonical routing rule: entries declared in `prediction_features` are formula features, and entries declared in `regimes` are regimes. The documentation SHALL state that config files may use a top-level `actual == baseline` shorthand only inside `prediction_features`, while every regime condition — including equality conditions — remains a regime. The documentation SHALL present `Regime` as the single public regime type and the explicit `PredictionFeature(actual, baseline)` form as the canonical feature representation.

#### Scenario: README and docstring separate feature and regime declarations
- **WHEN** a reader consults the README quick start or the `Regime` docstring
- **THEN** they find that `prediction_features` declares formula features, `regimes` declares regimes, and `==` shorthand is mentioned only for config-loaded prediction features

#### Scenario: CLI builds the canonical types from config
- **WHEN** the CLI loads a config whose `prediction_features` entries mix explicit objects and equality-string shorthand and whose `regimes` entries declare regime conditions
- **THEN** the CLI constructs canonical `PredictionFeature` and `Regime` instances directly, and routing depends on the declaration site rather than condition-shape inference
