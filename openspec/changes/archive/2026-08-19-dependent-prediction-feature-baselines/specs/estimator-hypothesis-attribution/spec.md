# Delta: estimator-hypothesis-attribution — dependent prediction feature baselines

## ADDED Requirements

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

## MODIFIED Requirements

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
