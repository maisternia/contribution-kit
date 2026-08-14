## ADDED Requirements

### Requirement: Reports SHALL Title Each Analysis Section
The system SHALL render, in `AssessmentResult.to_markdown()`, a titled heading for
every analysis section naming the analysis it presents (for example a Shapley-value
contributions section, an error-regimes section, and a mismatch-risk section). Each
section title SHALL be distinct so a reader can identify which analysis a table
belongs to without interpreting the numbers.

#### Scenario: Shapley table has a named title
- **WHEN** `to_markdown()` renders the feature attribution table
- **THEN** the table is preceded by a heading that names it as the Shapley-value contribution analysis

#### Scenario: Each analysis table is individually titled
- **WHEN** the report contains a Shapley table, a regime table, and a mismatch-risk table
- **THEN** each table is preceded by its own distinct titled heading naming that analysis

### Requirement: Reports SHALL Describe Each Analysis In Plain Language
The system SHALL render, directly under each analysis section title, a one-line
plain-language description stating what the analysis does and referencing the inputs
it used. The description SHALL avoid unexplained jargon so a reader who is not
comfortable with statistics can understand the purpose of the section.

#### Scenario: Shapley section is described
- **WHEN** `to_markdown()` renders the Shapley-value section
- **THEN** a one-line description explains that it apportions the prediction-versus-target outcome across the declared features

#### Scenario: Regime and mismatch-risk sections are described
- **WHEN** `to_markdown()` renders the error-regime and mismatch-risk sections
- **THEN** each has a one-line description explaining, respectively, how much of the observed outcome each condition accounts for and how much more often matching rows mismatch than the rest

### Requirement: Reports SHALL Echo The Analysis Inputs
The system SHALL render the inputs that produced the report so the report is
reproducible on its own. The system SHALL show the prediction/target formula used
for the Shapley attribution and SHALL echo the `target`, `prediction`, and
`prediction_expr` inputs. To make these available at render time, `Estimator.assess()`
SHALL populate `AssessmentResult.metadata` with `target`, `prediction`,
`prediction_expr`, and `score_mode`. When an input is absent from `metadata`, the
system SHALL omit only that input's line rather than fail.

#### Scenario: assess records the spec inputs in metadata
- **WHEN** a caller runs `assess()` with a spec carrying `target`, `prediction`, `prediction_expr`, and `score_mode`
- **THEN** the returned `AssessmentResult.metadata` contains those four values

#### Scenario: Report shows the Shapley formula and expressions
- **WHEN** `to_markdown()` renders a report whose metadata carries the spec inputs
- **THEN** the report shows the prediction-versus-target formula used for the Shapley attribution and echoes the `target`, `prediction`, and `prediction_expr` values

#### Scenario: Missing input is skipped, not fatal
- **WHEN** `to_markdown()` renders a report whose metadata lacks `prediction_expr`
- **THEN** the report omits only that input line and still renders the remaining inputs and tables without error

### Requirement: Framework SHALL Derive Regime Outcome And Mismatch From Observed Inputs
The system SHALL define observed regime outcomes and mismatch risk from
`target` and `prediction`, not from `prediction_expr`. Regime contributions SHALL
be computed from `score(prediction, target, score_mode)`, and mismatch risk SHALL
use a fixed mismatch definition `prediction != target`.

#### Scenario: Regime outcomes use observed prediction and target
- **WHEN** `Estimator.assess()` computes observed contribution rows for regimes
- **THEN** each row contribution is computed from `prediction` vs `target` under `score_mode`

#### Scenario: Mismatch risk uses fixed definition
- **WHEN** `Estimator.assess()` computes mismatch risk for a regime
- **THEN** mismatch is evaluated as `prediction != target` for each row

### Requirement: Report Tables SHALL Use Human-Readable Column Names
The system SHALL render report table columns using concise, widely-used
human-readable names instead of raw dataclass field identifiers. In particular the
Shapley table SHALL label `mean_abs_shapley` as a "Mean absolute" column,
`mean_signed_shapley` as a "Mean signed" column, `total_signed_shapley` as a "Total
signed" column, and `net_contribution_share_pct` as a net-share percentage column.
The machine-readable `contribution.csv` and `run.json` outputs SHALL keep their
existing raw field names unchanged.

#### Scenario: Shapley columns are human-readable
- **WHEN** `to_markdown()` renders the Shapley table header
- **THEN** the columns read as human-readable terms such as "Mean absolute", "Mean signed", and "Total signed" rather than `mean_abs_shapley` or `total_signed_shapley`

#### Scenario: Machine outputs keep raw field names
- **WHEN** the same result is exported via `to_csv()` and `to_json()`
- **THEN** the CSV headers and JSON keys retain the original field names (e.g. `mean_abs_shapley`, `net_contribution_share_pct`)

### Requirement: Report Tables SHALL Include A Plain-Language Conclusion
The system SHALL render, directly below each report table, a one-sentence
plain-language conclusion summarising that table's headline takeaway derived from the
rendered rows (for example which feature carries the largest net share, which regime
accounts for the largest share, or which condition carries the highest mismatch
risk). Conclusions SHALL be phrased descriptively and SHALL NOT assert causation.

#### Scenario: Shapley table has a conclusion
- **WHEN** `to_markdown()` renders the Shapley table
- **THEN** a one-sentence conclusion below the table names the feature with the largest net contribution share

#### Scenario: Regime and mismatch tables have conclusions
- **WHEN** `to_markdown()` renders the regime table and the mismatch-risk table
- **THEN** each has a one-sentence descriptive conclusion identifying, respectively, the largest-share regime and the highest-mismatch-risk condition

### Requirement: The report Command SHALL Reuse The Accessible Layout
The system SHALL make the `contrib report` command regenerate the report from
`run.json` using the same accessible presentation produced by
`AssessmentResult.to_markdown()`, so the regenerated report has the same titles,
descriptions, input echoes, human-readable columns, and conclusions as the report
written by `save`.

#### Scenario: Regenerated report matches the saved layout
- **WHEN** a caller runs `contrib report` against a `run.json` produced by `run`
- **THEN** the regenerated markdown contains the same section titles, descriptions, human-readable column names, and per-table conclusions as the `report.md` written by `save`

### Requirement: Accessible Presentation SHALL Preserve Existing Report Guarantees
The system SHALL preserve the mismatch-risk effect-size column labels
`risk ratio (95% CI)` and `odds ratio (95% CI)`, their `value (low to high)`
formatting, and the existing reference footnotes when adding the accessible
presentation layer.

#### Scenario: CI columns and footnotes are unchanged
- **WHEN** `to_markdown()` renders the mismatch-risk section under the new accessible layout
- **THEN** the effect-size columns are still labelled `risk ratio (95% CI)` and `odds ratio (95% CI)` formatted as `value (low to high)`, and the Koopman / Baptista-Pike / Fagerland reference footnotes are still present
