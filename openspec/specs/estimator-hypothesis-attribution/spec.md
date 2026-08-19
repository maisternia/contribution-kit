# estimator-hypothesis-attribution Specification

## Purpose

Define a single, unified estimator-hypothesis attribution capability for the
contribution-kit. Callers declare every hypothesis through a name-keyed
mapping of boolean `condition` DSL strings, while formula features are declared
separately through `prediction_features`, with config-file support for a
top-level equality shorthand. The estimator is constructed one way and
assessed with a single `assess()` call that returns one unified
per-hypothesis result.
## Requirements
### Requirement: Hypotheses SHALL Be Declared As A Named Mapping Of Conditions
The system SHALL declare every caller-authored hypothesis through one `AttributionSpec.hypotheses` collection whose config representation is a name-keyed **mapping** (`{name -> value}`), where the map key is the hypothesis name and each value is either (a) a boolean `condition` DSL string, or (b) an object with a required `condition` DSL string and an optional `label`. A string value SHALL be equivalent to an object whose `condition` is that string and whose `label` defaults to the key. Each entry SHALL be materialized as the single public `Hypothesis` type carrying `name` (the key), `condition`, and an optional `label`. The system SHALL treat `Hypothesis` as the only public hypothesis type for callers. The system SHALL NOT require callers to declare regimes, binary tests, mismatch groups, or a specific subtype. Mapping insertion order SHALL be preserved for rendering. The list form of `hypotheses` SHALL NOT be accepted in config files. In addition to the mapping, the system SHALL accept optional `factorials` declarations whose crossings expand into generated regime hypotheses at assessment time; generated hypotheses SHALL be internal `Hypothesis` instances that join the same regime-analysis pipeline as declared hypotheses, and callers SHALL NOT construct cell hypotheses by hand to obtain factorial analysis. Shapley formula features SHALL be declared separately through `prediction_features`, not inferred from hypothesis condition shape.

#### Scenario: One condition mapping describes the regime analysis
- **WHEN** a caller builds a config with `prediction_expr`, `target`, `prediction`, and a `hypotheses` mapping of name → condition
- **THEN** the hypothesis mapping fully describes the regime side of the analysis with no `regimes`, `binary_tests`, or callable predicate inputs, and no repeated `name` field inside entries

#### Scenario: String shorthand is equivalent to an object with a defaulted label
- **WHEN** an entry is written as `"class_sf_mismatch": "col('Class SF') != col('GT SF')"`
- **THEN** it materializes as a `Hypothesis` with `name` = `class_sf_mismatch`, `condition` = that string, and `label` = `class_sf_mismatch`, identical to writing `"class_sf_mismatch": { "condition": "col('Class SF') != col('GT SF')" }`

#### Scenario: Object form carries an explicit label
- **WHEN** an entry is written as `"class_sf_mismatch": { "label": "Nominal class SF wrong", "condition": "col('Class SF') != col('GT SF')" }`
- **THEN** it materializes as a `Hypothesis` with `name` = `class_sf_mismatch`, that `label`, and that `condition`

#### Scenario: Object missing condition is rejected
- **WHEN** a `hypotheses` entry value is an object without a `condition` key
- **THEN** the loader raises a configuration error naming the offending hypothesis key

#### Scenario: Redundant name key is rejected
- **WHEN** a `hypotheses` entry object includes a `name` field
- **THEN** the loader raises a configuration error, because the mapping key already supplies the name

#### Scenario: Mapping order is preserved
- **WHEN** a `hypotheses` mapping declares entries in a given order
- **THEN** the materialized hypotheses and their report rows follow that declared order

#### Scenario: Estimator is constructed and assessed one way
- **WHEN** a caller runs an attribution analysis
- **THEN** the caller constructs the estimator once (e.g. `Estimator.from_csv(input, spec=spec)`) and invokes a single `assess()` method, with no alternate construction or estimation paths

#### Scenario: Single public Hypothesis type is sufficient
- **WHEN** a caller declares every hypothesis using only the `Hypothesis` type with a `name` and `condition`
- **THEN** the estimator produces correct feature attributions, regime summaries, and mismatch-risk results with no other hypothesis type required

#### Scenario: Factorial expansion feeds the same regime pipeline
- **WHEN** a spec declares a `factorials` crossing alongside a `hypotheses` mapping
- **THEN** the generated cell hypotheses are analysed by the same regime pipeline as declared hypotheses, and any Shapley features still come only from `prediction_features`

#### Scenario: Equality condition in hypotheses remains a regime
- **WHEN** a hypothesis condition is `col('Class SF') == col('GT SF')`
- **THEN** the estimator evaluates that hypothesis as a regime selector and does not synthesize a prediction feature from it

### Requirement: Prediction Features SHALL Accept Equality String Shorthand In Config Files
The config JSON/YAML loader SHALL accept each `prediction_features` mapping
value in one of two forms: the explicit object form `{actual, baseline, label?}`
or a shorthand string whose parsed top-level expression is exactly one equality
`actual == baseline`. The shorthand SHALL be accepted only in config loading;
after parsing, both forms SHALL normalize to the same internal
`PredictionFeature(actual, baseline, label)` representation used by the
estimator. The feature name from the mapping key SHALL remain the variable name
used by `prediction_expr` binding. The right-hand side of the shorthand MAY
contain sibling feature references, which are validated and resolved on the same
terms as a `baseline` declared through the object form; the left-hand side SHALL
be subject to the same row-only restriction as any `actual` expression.

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

#### Scenario: Shorthand right-hand side may carry a sibling reference
- **WHEN** a config declares `"class_sf": "col('Class SF') == col('GT SF') - round(2 * log2(col('GT BW') / class_bw))"` under `prediction_features`
- **THEN** the loader normalizes it to a `PredictionFeature` whose `baseline` references `class_bw`, and the reference is validated and coalition-resolved identically to the object form

#### Scenario: Shorthand left-hand side may not carry a sibling reference
- **WHEN** a config declares a shorthand string whose left-hand side references another declared feature name
- **THEN** loading or assessment fails with the row-only `actual` validation error naming the feature and variable

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

### Requirement: assess SHALL Return One Unified Per-Hypothesis Result
The system SHALL return from `assess` an `AssessmentResult` whose `hypotheses` list holds exactly one `HypothesisAssessment` per declared hypothesis, in declaration order, and SHALL expose `feature_attributions`, `regime_summaries`, and `binary_results` as derived read-only views.

#### Scenario: One assessment per declared hypothesis
- **WHEN** a caller invokes `assess` with a flat condition list
- **THEN** `result.hypotheses` has one entry per declared hypothesis in declaration order, each carrying only the analysis (`feature` or `regime`) sub-results that apply

#### Scenario: Derived views preserve legacy table shapes
- **WHEN** a caller reads `feature_attributions`, `regime_summaries`, or `binary_results`
- **THEN** each view returns the corresponding sub-results (feature attributions ranked by net contribution share) without requiring the caller to inspect the unified list

### Requirement: Regime Hypotheses SHALL Share The Observed Error And Compare Against The Rest
The system SHALL attribute to each regime hypothesis the same per-row observed error used by the feature attribution (derived from `prediction_expr` versus `target_expr`), and SHALL compute its mismatch risk by comparing the matching rows against the rest of the population using the spec-level `mismatch_expr`. The reported risk-ratio and odds-ratio confidence intervals SHALL use Koopman asymptotic-score and Baptista-Pike exact methods as the primary default methods; when either primary method yields a non-finite or unordered interval for a finite point estimate, the system SHALL automatically use Katz (risk ratio) or Haldane-Anscombe (odds ratio) for that result.

#### Scenario: Compute requested class BW regime contributions
- **WHEN** a caller declares regime conditions including `class_bw < gt_bw (beyond tol)`, `class_bw > gt_bw (beyond tol)`, `class_bw within tol & sf wrong`, `class_bw & sf ok, measured_bw off`, and the baseline regime
- **THEN** the estimator returns regime summaries with `name`, `count`, `mean_contribution`, `total_contribution`, and `contribution_share_pct`, where the contribution totals are derived from the spec's `prediction_expr` versus `target_expr`

#### Scenario: Compute condition-vs-rest mismatch risk
- **WHEN** a regime hypothesis is evaluated and `mismatch_expr` is set
- **THEN** the estimator returns a binary result comparing the matching rows (group A) against the rest of the population (group B) with mismatch rates, risk ratio, and odds ratio with confidence intervals

#### Scenario: Default output avoids non-finite bounds for finite-point rows
- **WHEN** a finite risk-ratio or odds-ratio point estimate is computed and the primary default inversion yields a non-finite or unordered confidence interval
- **THEN** the corresponding confidence interval in reported output is computed using the paper-cited fallback method for that effect size and rendered as an ordered finite interval

#### Scenario: Markdown reports include confidence-interval ranges
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk rows
- **THEN** the report table labels the effect-size columns as `risk ratio (95% CI)` and `odds ratio (95% CI)` and formats each as `value (low to high)`

### Requirement: Mismatch-Risk Confidence Intervals SHALL Use Small-Sample Score And Exact Methods
The system SHALL compute mismatch-risk confidence intervals using the Koopman asymptotic-score interval for risk ratio and the Baptista-Pike exact interval for odds ratio as the default primary methods, selected for small-sample behavior as recommended by Fagerland, Lydersen & Laake (2015, 2017). If a primary default interval output is non-finite or unordered for a finite point estimate, the system SHALL automatically apply the corresponding paper-cited fallback method (Katz for risk ratio, Haldane-Anscombe for odds ratio) for that result. The system SHALL retain explicit opt-in fallback selection through the existing method-selection option, and selecting a confidence-interval method SHALL NOT change risk-ratio or odds-ratio point estimates. The mismatch-risk reference footnotes SHALL continue to cite Koopman (1984) and Baptista & Pike (1977), with the small-sample recommendation attributed to Fagerland, Lydersen & Laake (2015/2017). The system SHALL document the explicit fallback methods and selection path exactly once in the `contribution-kit` README.

#### Scenario: Risk-ratio and odds-ratio CIs use default primary methods
- **WHEN** a mismatch-risk result is computed without a caller specifying a confidence-interval method
- **THEN** risk-ratio confidence intervals are computed with Koopman asymptotic-score and odds-ratio confidence intervals are computed with Baptista-Pike exact, except for per-result automatic guardrail fallback when default inversion output is non-finite or unordered for a finite point estimate

#### Scenario: Automatic guardrail fallback is method-specific
- **WHEN** a finite risk-ratio default interval is invalid and the odds-ratio default interval is valid for the same table
- **THEN** the system applies Katz only to the risk-ratio interval and keeps Baptista-Pike for the odds-ratio interval

#### Scenario: Opt-in fallback methods remain selectable
- **WHEN** a caller selects fallback confidence-interval methods on the binary-hypothesis evaluation path
- **THEN** risk-ratio confidence intervals are produced by Katz and odds-ratio confidence intervals by Haldane-Anscombe regardless of whether automatic guardrail fallback would have been triggered

#### Scenario: Point estimates are independent of CI method
- **WHEN** the same 2x2 mismatch table is evaluated with default methods and with fallback methods
- **THEN** reported risk-ratio and odds-ratio point estimates are identical across both, and only confidence-interval bounds differ

#### Scenario: Sparse finite-point tables produce finite ordered intervals
- **WHEN** a sparse mismatch table with a finite risk-ratio point estimate is evaluated and the default inversion cannot produce a finite ordered confidence interval
- **THEN** the reported risk-ratio confidence interval is finite and ordered via method-specific fallback rather than `n/a` or `to inf`

#### Scenario: CI methods reject invalid confidence-level z input
- **WHEN** any confidence-interval routine is called with a non-finite or non-positive z value
- **THEN** the routine fails fast with a clear validation error instead of returning a malformed interval

#### Scenario: Footnotes cite default primary methods and README documents fallback once
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk footnotes and a reader checks the `contribution-kit` README
- **THEN** the footnotes cite Koopman (1984) and Baptista & Pike (1977) with Fagerland, Lydersen & Laake (2015/2017), and the README contains one section describing fallback availability and selection

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

### Requirement: Public API SHALL Document The Single Classification Rule
The system SHALL document, in both the `contribution-kit` README and the public `Hypothesis` docstring, one canonical routing rule: entries declared in `prediction_features` are formula features, and entries declared in `hypotheses` are regimes. The documentation SHALL state that config files may use a top-level `actual == baseline` shorthand only inside `prediction_features`, while every hypothesis condition — including equality conditions — remains a regime. The documentation SHALL present `Hypothesis` as the single public hypothesis type and the explicit `PredictionFeature(actual, baseline)` form as the canonical feature representation.

#### Scenario: README and docstring separate feature and regime declarations
- **WHEN** a reader consults the README quick start or the `Hypothesis` docstring
- **THEN** they find that `prediction_features` declares formula features, `hypotheses` declares regimes, and `==` shorthand is mentioned only for config-loaded prediction features

#### Scenario: CLI builds the canonical types from config
- **WHEN** the CLI loads a config whose `prediction_features` entries mix explicit objects and equality-string shorthand and whose `hypotheses` entries declare regime conditions
- **THEN** the CLI constructs canonical `PredictionFeature` and `Hypothesis` instances directly, and routing depends on the declaration site rather than condition-shape inference

### Requirement: Factorial-Only Specs SHALL Be Valid Without Declared Regimes
The estimator SHALL accept an attribution spec that declares zero caller-authored regimes when at least one factorial crossing is declared. The estimator SHALL continue to reject specs that declare neither regimes nor factorials.

#### Scenario: Factorial-only spec validates
- **WHEN** a spec declares at least one factorial crossing and no regimes
- **THEN** spec validation succeeds and assessment executes without raising a regime-required validation error

#### Scenario: Spec without regimes and factorials is rejected
- **WHEN** a spec declares no regimes and no factorial crossings
- **THEN** validation fails with an explicit configuration error indicating that at least one analysis surface is required

#### Scenario: Regime-based specs remain valid
- **WHEN** a spec declares one or more regimes and no factorial crossings
- **THEN** validation succeeds and regime/risk analysis behavior remains unchanged

### Requirement: Prediction Feature Baselines SHALL Support Coalition-Resolved References To Sibling Features
The system SHALL allow a `prediction_features` entry's `baseline` expression to reference other declared prediction feature names as free variables. When scoring a Shapley coalition, each referenced feature SHALL be bound to its **coalition-resolved** value: its `actual` value when that feature is a member of the coalition, and its own resolved `baseline` value otherwise. The system SHALL resolve features in dependency order so that a referenced feature is resolved before any feature referencing it. A `baseline` expression that references no sibling feature SHALL behave exactly as it does today.

#### Scenario: Baseline reference resolves to actual when the referenced feature is in the coalition
- **WHEN** `class_sf.baseline` is `col('GT SF') - round(2 * log2(col('GT BW') / class_bw))` and a coalition contains `class_bw` but not `class_sf`
- **THEN** `class_bw` binds to its `actual` expression value for that row when evaluating `class_sf`'s baseline

#### Scenario: Baseline reference resolves to baseline when the referenced feature is outside the coalition
- **WHEN** the same `class_sf.baseline` is evaluated for a coalition containing neither `class_sf` nor `class_bw`
- **THEN** `class_bw` binds to its own `baseline` expression value for that row when evaluating `class_sf`'s baseline

#### Scenario: Empty coalition reproduces the target for a dependent baseline
- **WHEN** the continuous-LoRa spec declares `prediction_expr` as `class_sf + round(2 * log2(measured_bw / class_bw))` with `class_sf.baseline` referencing `class_bw`, and all baselines are ground-truth-derived
- **THEN** the empty-coalition prediction equals `target` on every row, the empty-coalition score is `0`, and the per-feature net contribution shares sum to 100%

#### Scenario: Fully compensated misclassification scores zero
- **WHEN** the coalition contains only `class_bw`, so the nominal class bandwidth is the detector-produced value while the class SF and measured bandwidth are at their baselines
- **THEN** the coalition prediction equals `target` and the coalition score is `0`, reflecting that the prediction formula fully compensates a scaled class assignment

#### Scenario: Sibling-free baselines are unaffected
- **WHEN** every declared `baseline` expression references only `col(...)` columns and no sibling feature
- **THEN** the resolved feature values, Shapley attributions, and reported shares are identical to those produced before dependent baselines were supported

### Requirement: Free Variables In Feature Expressions SHALL Resolve By A Declared Precedence
The DSL permits a bare identifier to reference an input column directly (for example `Height * 2`), in addition to the `col('Height')` form. The system SHALL therefore resolve each free variable of a `prediction_features` expression in this order: within the expressions of a feature named `f`, the identifier `f` SHALL bind to an input column of that name when one exists, because a feature can never usefully reference itself and naming a feature after the column it reads is an established idiom; otherwise a name matching a declared prediction feature SHALL bind to that feature; otherwise a name matching an input column SHALL bind to that column; otherwise the name SHALL be rejected as unknown, naming the feature and the variable. This preserves every currently-valid expression that uses bare column names. When a name other than the owner's matches both a declared feature and an input column, the feature SHALL win, matching the existing precedence by which `prediction_expr` feature bindings override row values.

#### Scenario: Bare column reference remains valid
- **WHEN** a feature expression is `Height * 2` and `Height` is an input column with no declared feature of that name
- **THEN** the expression binds `Height` to the column value and is neither rejected nor treated as a sibling reference

#### Scenario: A feature named after the column it reads is valid
- **WHEN** a feature named `x` declares `actual` as the bare identifier `x` and the input has an `x` column
- **THEN** `x` binds to the input column, the expression is accepted, and it is not treated as a self-reference

#### Scenario: Unknown free variable is rejected
- **WHEN** a feature expression references a bare identifier that matches neither a declared feature nor an input column
- **THEN** `assess` fails with a validation error naming the feature and the unknown identifier

#### Scenario: Ambiguous baseline reference is reported
- **WHEN** one feature's `baseline` references a name that is both another declared feature and an input column
- **THEN** the feature binding wins and the estimator emits a shadowing diagnostic naming the ambiguous identifier

### Requirement: Prediction Feature Actual Expressions SHALL NOT Reference Sibling Features
The system SHALL reject a `prediction_features` entry whose `actual` expression contains a free variable that resolves to another declared prediction feature. Permitting sibling references in `actual` would prevent the full coalition from reproducing the observed prediction and would break Shapley efficiency at the full-coalition endpoint. Free variables that resolve to input columns SHALL remain permitted. The validation error SHALL name the offending feature and variable.

#### Scenario: Sibling reference in an actual expression is rejected
- **WHEN** a spec declares `class_sf` with `actual` set to `class_bw + 1` and `class_bw` is a declared prediction feature
- **THEN** `assess` fails with a validation error naming `class_sf` and the variable `class_bw` as an unsupported reference in an `actual` expression

#### Scenario: Column reference in an actual expression is permitted
- **WHEN** a spec declares an `actual` expression referencing an input column, whether as `col('Height')` or as bare `Height`
- **THEN** the expression is accepted and evaluated against the row

### Requirement: Baseline Feature References SHALL Be Validated As An Acyclic Graph Over Declared Features
The system SHALL extract the sibling-reference set of each `baseline` expression as the subset of its free variables that resolve to declared prediction features under the declared precedence, and SHALL require the resulting dependency graph to be acyclic. Free variables resolving to input columns SHALL NOT be treated as dependency edges. A cycle SHALL fail fast at assessment time with an error naming the offending features in declaration order.

#### Scenario: Baseline referencing an undeclared, non-column name is an error
- **WHEN** `class_sf.baseline` references a variable `nominal_bw` that is neither a declared prediction feature nor an input column
- **THEN** `assess` fails with a validation error naming `class_sf` and the unknown reference `nominal_bw`

#### Scenario: Column references do not create dependency edges
- **WHEN** `class_sf.baseline` is `col('GT SF') - round(2 * log2(col('GT BW') / class_bw))` with `class_bw` a declared feature
- **THEN** the dependency graph records exactly one edge, `class_sf -> class_bw`, and the ground-truth column references contribute no edges

#### Scenario: Cyclic baseline references are an error
- **WHEN** `class_sf.baseline` references `class_bw` and `class_bw.baseline` references `class_sf`
- **THEN** `assess` fails with a validation error reporting the cycle and the participating feature names

#### Scenario: Self-referencing baseline with no matching column is an error
- **WHEN** a feature's `baseline` expression references its own name and no input column carries that name
- **THEN** `assess` fails with a validation error reporting the unknown reference or cycle

#### Scenario: Acyclic multi-level references resolve in dependency order
- **WHEN** feature `a` has a baseline referencing `b`, and `b` has a baseline referencing `c`, with `c` referencing no sibling
- **THEN** resolution evaluates `c`, then `b`, then `a` for each coalition, and `assess` completes without error

### Requirement: The Estimator SHALL Report When Baselines Do Not Reproduce The Target
The system SHALL evaluate the empty-coalition prediction against `target` for every row and SHALL emit a diagnostic when they differ on any row, because in that case the per-feature contributions do not sum to the observed contribution and the reported shares are unsound. The diagnostic SHALL report the number of violating rows and identify at least one violating row.

#### Scenario: Baselines that reproduce the target produce no diagnostic
- **WHEN** every row's empty-coalition prediction equals its `target`
- **THEN** `assess` completes with no empty-coalition diagnostic and the reported net contribution shares sum to 100%

#### Scenario: Baselines that miss the target produce a diagnostic
- **WHEN** a spec pins a dependent baseline to an observed column such as `col('Class BW')` instead of the coalition-resolved sibling, so the empty-coalition prediction differs from `target` on some rows
- **THEN** `assess` emits a diagnostic reporting the count of violating rows and an example row, rather than silently reporting net contribution shares that do not sum to 100%

### Requirement: Prediction Features MAY Be Declared Independent To Forbid Dependency Edges
The system SHALL accept an optional boolean `independent` key on a `prediction_features` entry, defaulting to `false`. A feature declared `independent` SHALL participate in no dependency edge in either direction: no other feature's `baseline` may reference it, and its own `baseline` may not reference any other feature. Either violation SHALL fail fast at assessment time. Because the key name does not itself carry direction, the validation error SHALL state which direction was violated and name both features involved. The key SHALL be available only in the explicit object form; the equality string shorthand SHALL NOT be able to declare it. Omitting the key SHALL leave a feature referenceable, so existing specs and specs that declare no `independent` feature are unaffected.

#### Scenario: Referencing an independent feature is rejected
- **WHEN** `measured_bw` is declared `"independent": true` and `class_sf.baseline` references `measured_bw`
- **THEN** `assess` fails with a validation error stating that `class_sf` references `measured_bw`, which is declared independent and may not be referenced by another feature's baseline

#### Scenario: An independent feature may not depend on others
- **WHEN** a feature declared `"independent": true` has a `baseline` expression referencing another declared feature
- **THEN** `assess` fails with a validation error stating that the independent feature may not reference another feature from its own baseline, naming both

#### Scenario: Independent features may still reference input columns
- **WHEN** a feature declared `"independent": true` has a `baseline` of `col('GT BW')` and an `actual` of `col('Measured BW')`
- **THEN** the spec is valid and the feature is resolved exactly as an unflagged feature with the same expressions

#### Scenario: Default leaves features referenceable
- **WHEN** a spec declares no `independent` key on any feature
- **THEN** every feature is referenceable, and results are identical to a spec that predates the key

#### Scenario: Independent is rejected in the equality string shorthand
- **WHEN** a caller wants an equality-shorthand feature declared independent
- **THEN** the caller must use the explicit object form, and the loader rejects any attempt to express `independent` within the shorthand string

### Requirement: The Estimator SHALL Report When A Baseline Absorbs The Prediction Formula
The system SHALL detect, for each declared prediction feature `f` **whose baseline references at least one sibling feature**, whether the coalition of all other features scores zero on every row. A feature whose baseline references no sibling SHALL NOT be checked: it has no formula to absorb, and on small inputs its all-but-one coalition can score zero by coincidence. When it does, the baseline of `f` has absorbed the prediction formula: every feature referenced by that baseline becomes attributable only in interaction with `f`, and the reported attribution is degenerate. The system SHALL emit a diagnostic naming `f` and the features whose contributions are affected. A single zero-scoring coalition smaller than the all-but-one coalition SHALL NOT trigger the diagnostic, because a fully compensated feature is a legitimate and intended finding. The diagnostic SHALL be a warning rather than a hard error.

#### Scenario: Over-referenced baseline is detected
- **WHEN** `class_sf.baseline` references both `class_bw` and `measured_bw` such that it inverts `prediction_expr`, so the coalition `{class_bw, measured_bw}` scores zero on every row
- **THEN** `assess` emits a diagnostic naming `class_sf` as absorbing the prediction formula and identifying `class_bw` and `measured_bw` as degenerately attributed

#### Scenario: A sibling-free spec is never flagged
- **WHEN** a spec declares only baselines that reference input columns, and some all-but-one coalition happens to score zero on every row of a small input
- **THEN** `assess` emits no absorption diagnostic

#### Scenario: A single fully compensated feature is not flagged
- **WHEN** `class_sf.baseline` references only `class_bw`, so `{class_bw}` scores zero on every row but `{measured_bw}` and `{class_bw, measured_bw}` do not
- **THEN** `assess` emits no absorption diagnostic, because the zero-scoring coalition is not the all-but-one coalition

#### Scenario: Detection covers the sampling path
- **WHEN** a spec declares more features than `max_exact_features`, so Shapley values are estimated by permutation sampling rather than exhaustive coalition evaluation
- **THEN** the estimator still evaluates each all-but-one coalition explicitly and applies the same absorption detection

### Requirement: Specs Without Sibling References SHALL Produce Unchanged Results
The system SHALL produce, for any spec in which no `baseline` expression references a declared prediction feature, feature attributions and every other assessment output identical to those produced before dependent baselines were supported. Dependency-ordered resolution SHALL reduce to the prior behaviour when the dependency graph has no edges, and the new validations SHALL NOT reject any expression that was previously valid.

#### Scenario: Existing configs are unaffected
- **WHEN** the bundled `examples/continuous_lora/config.json` is assessed with its original sibling-free baselines
- **THEN** the per-feature `mean_abs_shapley`, `mean_signed_shapley`, `total_signed_shapley`, and `net_contribution_share_pct` values equal those produced before this change, and the shares sum to 100%

#### Scenario: Previously valid expressions are still accepted
- **WHEN** an existing spec uses bare column identifiers, `col(...)` references, or the equality string shorthand in any feature expression, with no sibling references anywhere
- **THEN** the new reference, acyclicity, and row-only validations accept the spec unchanged, and no new diagnostic is emitted

### Requirement: Dependent Baselines SHALL NOT Alter Target, Mismatch, Or Burden Results
The system SHALL confine the effect of dependent baselines to Shapley feature decomposition. The `target` expression, the observed `prediction` expression, the mismatch predicate `prediction != target`, regime summaries, factorial matrices, contrasts, and the attributable burden ranking SHALL be unchanged by the presence or absence of sibling references in `baseline` expressions.

#### Scenario: Mismatch-derived results are identical across baseline forms
- **WHEN** the same spec is assessed once with a sibling-free `class_sf` baseline and once with a dependent one, all else equal
- **THEN** the total mismatch count, observed accuracy, regime summaries, factorial cell counts and rates, contrasts, and burden ranking entries are identical between the two runs, and only the feature attributions differ

