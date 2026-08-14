# factorial-regime-declaration Specification

## Purpose

Define optional inline factorial crossing declarations that generate internal
regime hypotheses, validate axis partitions, and render factorial-focused
report views without changing behavior for factor-free specifications.

## Requirements

### Requirement: Factorial Axes SHALL Be Declared Inline Per Crossing
The system SHALL accept each entry of the optional `factorials` list, both in the config JSON/YAML and on `AttributionSpec`, as a self-contained crossing object whose `rows` and `columns` keys are each an ordered mapping of level name to a boolean `condition` DSL string. Each axis mapping SHALL declare at least one level, and every level condition SHALL be a non-empty string. Each level condition SHALL be declared exactly once; the system SHALL NOT require the caller to repeat a level condition inside any cell or hypothesis. Level ordering SHALL be preserved for rendering. Unknown keys on a crossing object SHALL raise a configuration error. There SHALL be no top-level `factors` declaration.

#### Scenario: Crossing with inline directional levels is declared once
- **WHEN** a config declares a factorial whose `rows` map contains levels `class_ok`, `upscale`, and `downscale` and whose `columns` map contains levels `measured_ok` and `measured_off`, each with one condition string
- **THEN** the spec parses successfully and no composite cell conditions or separate axis declarations are required from the caller

#### Scenario: Level conditions appear exactly once in the config
- **WHEN** a factorial analysis uses a tolerance expression such as `abs(col('Class BW') - col('GT BW')) / col('GT BW') <= 0.10`
- **THEN** that expression is written once, in the level that defines it, and nowhere else in the config

#### Scenario: Empty axis is rejected
- **WHEN** a factorial declares `rows` as an empty mapping
- **THEN** loading fails with a configuration error identifying the crossing and the empty axis

#### Scenario: Unknown crossing key is rejected
- **WHEN** a factorial entry contains a key other than `rows`, `columns`, or `label`
- **THEN** loading fails with a configuration error naming the unknown key

### Requirement: Factorial Crossings SHALL Support An Optional Display Label
Each factorial crossing SHALL accept an optional `label` string used as its display identity. When `label` is absent, the system SHALL derive the fallback label `"Factorial <n>"` from the crossing's 1-based position in the `factorials` list. The effective label SHALL title the crossing's matrix section and contrast sections in the markdown report and SHALL identify the crossing in the JSON output.

#### Scenario: Declared label titles the report sections
- **WHEN** a crossing declares `"label": "Class BW vs measured BW quality"`
- **THEN** the report renders the matrix under the heading `Class BW vs measured BW quality` and its contrast sections are prefixed with the same label

#### Scenario: Unlabeled crossing falls back to position
- **WHEN** the second entry of `factorials` declares no `label`
- **THEN** its matrix and contrast sections are titled `Factorial 2` and the JSON output carries `Factorial 2` as the crossing label

### Requirement: Factorial Crossings SHALL Expand Into Generated Regime Hypotheses
At assessment time, each crossing in the `factorials` list SHALL expand into one generated regime hypothesis per (row level, column level) cell, whose condition is the conjunction of the two inline level conditions and whose name is `"<row_level> & <col_level>"`. Generated cells SHALL be analysed by the existing regime machinery (contribution share and mismatch risk vs rest) with no separate evaluation path. A generated cell name that collides with a declared hypothesis name or another generated name SHALL raise a validation error.

#### Scenario: Crossing two axes generates all cells
- **WHEN** a factorial crosses a 3-level `rows` axis with a 2-level `columns` axis
- **THEN** six regime hypotheses are generated with conjunction conditions and names such as `upscale & measured_off`, and each receives a regime summary and a mismatch-risk result

#### Scenario: Cell name collision is rejected
- **WHEN** a declared hypothesis is already named `upscale & measured_off` and a factorial would generate a cell with the same name
- **THEN** assessment raises a validation error instead of silently overriding either result

### Requirement: Axis Partitions SHALL Be Validated Against The Data
For each axis (`rows` and `columns`) of each factorial crossing, the system SHALL evaluate all level conditions over the loaded rows and SHALL emit a warning when any row matches more than one level (overlap) or no level (gap). The warning SHALL identify the axis by the crossing's effective label and the axis role (`rows` or `columns`) and SHALL report affected row counts. Partition violations SHALL NOT abort the run. Partition warnings SHALL be recorded in the JSON output metadata and noted in the markdown report.

#### Scenario: Overlapping levels produce a warning
- **WHEN** two levels of the `rows` axis of a crossing labelled `Class BW vs measured BW quality` both match 40 rows
- **THEN** the run completes and a warning identifies `Class BW vs measured BW quality: rows` with the 40 overlapping rows, and the warning is recorded in `run.json` and the report

#### Scenario: Clean partition produces no warning
- **WHEN** every row matches exactly one level of each factorial axis
- **THEN** no partition warning is emitted

### Requirement: Reports SHALL Render Each Factorial As A Matrix With Marginals
`to_markdown()` SHALL render, for each declared factorial, a matrix table titled by the crossing's effective label, with row-axis levels as rows and column-axis levels as columns, each cell reporting at least its row count, mismatch rate, and risk ratio vs rest. The table SHALL include a row-marginal column and a column-marginal row whose counts and mismatch rates are computed over the union of member rows (not by summing cell values), so overlapping levels cannot double-count. Generated cells SHALL also continue to appear in the flat regime and mismatch-risk tables.

#### Scenario: Matrix table is rendered for a crossing
- **WHEN** a factorial crosses a 3-level axis with a 2-level axis
- **THEN** the report contains a matrix table under the crossing's effective label with 3 data rows, 2 data columns, one marginal column, and one marginal row, each cell showing count, mismatch rate, and risk ratio

#### Scenario: Marginals are union-computed
- **WHEN** a row marginal is rendered for level `upscale`
- **THEN** its count and mismatch rate equal those computed directly over all rows matching the `upscale` condition

### Requirement: Within-Stratum Sibling-Cell Contrasts SHALL Be Reported
For each factorial, within each stratum (each fixed level of one axis), the system SHALL compare every unordered pair of distinct levels of the crossed axis as a 2x2 contrast where group A and group B are the two sibling cells (not "rest"). Contrasts SHALL reuse the existing Koopman risk-ratio and Baptista-Pike odds-ratio interval machinery, including the established guardrail fallbacks. Contrast results SHALL be exposed in the result object and JSON output, identifying the crossing by its effective label and the stratum by axis role and level (`rows=<level>` or `columns=<level>`), with level pair, counts, and effect sizes with CIs, and rendered as a titled report table.

#### Scenario: Directional contrast controlled for the other axis
- **WHEN** a factorial crosses a class axis with a measured axis and the stratum `columns=measured_ok` is examined
- **THEN** a contrast compares `upscale & measured_ok` directly against `downscale & measured_ok` with Koopman and Baptista-Pike intervals, answering the direction question without the baseline-dominated "rest" group

#### Scenario: Sparse sibling cells use guardrail fallbacks
- **WHEN** a contrast table is degenerate for the default interval methods but has a finite point estimate
- **THEN** the established guardrail fallbacks (Katz for risk ratio, Haldane-Anscombe for odds ratio) are applied to that contrast only

### Requirement: Factor-Free Configurations SHALL Be Unaffected
Configs and `AttributionSpec` instances that declare no `factorials` SHALL produce identical outputs to the current behavior, with no factorial sections in the report and no factorial fields in the JSON output.

#### Scenario: Existing flat config is byte-stable
- **WHEN** an existing config with only a flat `hypotheses` list is assessed
- **THEN** `report.md` and `run.json` contain no factorial content and are unchanged relative to the pre-factorial implementation

### Requirement: Factorial Analysis SHALL Run Without Caller-Authored Regimes
The factorial analysis pipeline SHALL run when a spec declares one or more factorial crossings even if the caller declares zero regimes. In this mode, factorial matrices, contrasts, and burden rankings SHALL still be produced according to existing factorial rules.

#### Scenario: Factorial report sections are emitted without regimes
- **WHEN** a spec includes factorial crossings and no caller-authored regimes
- **THEN** assessment output includes factorial matrices and related factorial outputs

#### Scenario: Factorial-generated regime and risk rows are preserved without placeholders
- **WHEN** a spec includes factorial crossings and no caller-authored regimes
- **THEN** generated cell regimes continue to appear in regime summary and mismatch-risk outputs, and no synthetic "all rows" placeholder regime is introduced

#### Scenario: Mixed specs remain fully supported
- **WHEN** a spec includes both caller-authored regimes and factorial crossings
- **THEN** the system renders both regime/risk analysis and factorial analysis in the same assessment result
