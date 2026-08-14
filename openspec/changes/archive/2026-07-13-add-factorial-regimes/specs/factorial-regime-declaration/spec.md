# factorial-regime-declaration Delta Specification

## ADDED Requirements

### Requirement: Factors SHALL Be Declared As Named Axes Of Named Level Conditions
The system SHALL accept an optional `factors` declaration, both in the config JSON and on `AttributionSpec`, as a mapping of axis name to an ordered mapping of level name to a boolean `condition` DSL string. Each level condition SHALL be declared exactly once; the system SHALL NOT require the caller to repeat a level condition inside any cell or hypothesis. Level ordering SHALL be preserved for rendering.

#### Scenario: Axis with directional levels is declared once
- **WHEN** a config declares `factors` with axis `class_axis` containing levels `class_ok`, `upscale`, and `downscale`, each with one condition string
- **THEN** the spec parses successfully and no composite cell conditions need to be declared by the caller

#### Scenario: Level conditions appear exactly once in the config
- **WHEN** a factorial analysis uses a tolerance expression such as `abs(col('Class BW') - col('GT BW')) / col('GT BW') <= 0.10`
- **THEN** that expression is written once, in the level that defines it, and nowhere else in the config

### Requirement: Factorial Crossings SHALL Expand Into Generated Regime Hypotheses
The system SHALL accept an optional `factorials` list of `{rows: <axis>, columns: <axis>}` crossings referencing declared factor axes by name. At assessment time, each crossing SHALL expand into one generated regime hypothesis per (row level, column level) cell, whose condition is the conjunction of the two level conditions and whose name is `"<row_level> & <col_level>"`. Generated cells SHALL be analysed by the existing regime machinery (contribution share and mismatch risk vs rest) with no separate evaluation path. A generated cell name that collides with a declared hypothesis name or another generated name SHALL raise a validation error. A factorial referencing an undeclared axis SHALL raise a configuration error.

#### Scenario: Crossing two axes generates all cells
- **WHEN** a factorial crosses `class_axis` (3 levels) with `measured_axis` (2 levels)
- **THEN** six regime hypotheses are generated with conjunction conditions and names such as `upscale & measured_off`, and each receives a regime summary and a mismatch-risk result

#### Scenario: Unknown axis reference fails clearly
- **WHEN** a factorial references axis `speed_axis` that is not declared in `factors`
- **THEN** the run fails with a configuration error naming the missing axis

#### Scenario: Cell name collision is rejected
- **WHEN** a declared hypothesis is already named `upscale & measured_off` and a factorial would generate a cell with the same name
- **THEN** assessment raises a validation error instead of silently overriding either result

### Requirement: Axis Partitions SHALL Be Validated Against The Data
For each axis used by a factorial, the system SHALL evaluate all level conditions over the loaded rows and SHALL emit a warning when any row matches more than one level (overlap) or no level (gap). The warning SHALL report affected row counts per axis. Partition violations SHALL NOT abort the run. Partition warnings SHALL be recorded in the JSON output metadata and noted in the markdown report.

#### Scenario: Overlapping levels produce a warning
- **WHEN** two levels of one axis both match 40 rows
- **THEN** the run completes and a warning reports the axis name and the 40 overlapping rows, and the warning is recorded in `run.json` and the report

#### Scenario: Clean partition produces no warning
- **WHEN** every row matches exactly one level of each factorial axis
- **THEN** no partition warning is emitted

### Requirement: Reports SHALL Render Each Factorial As A Matrix With Marginals
`to_markdown()` SHALL render, for each declared factorial, a matrix table with row-axis levels as rows and column-axis levels as columns, each cell reporting at least its row count, mismatch rate, and risk ratio vs rest. The table SHALL include a row-marginal column and a column-marginal row whose counts and mismatch rates are computed over the union of member rows (not by summing cell values), so overlapping levels cannot double-count. Generated cells SHALL also continue to appear in the flat regime and mismatch-risk tables.

#### Scenario: Matrix table is rendered for a crossing
- **WHEN** a factorial crosses a 3-level axis with a 2-level axis
- **THEN** the report contains a matrix table with 3 data rows, 2 data columns, one marginal column, and one marginal row, each cell showing count, mismatch rate, and risk ratio

#### Scenario: Marginals are union-computed
- **WHEN** a row marginal is rendered for level `upscale`
- **THEN** its count and mismatch rate equal those computed directly over all rows matching the `upscale` condition

### Requirement: Within-Stratum Sibling-Cell Contrasts SHALL Be Reported
For each factorial, within each stratum (each fixed level of one axis), the system SHALL compare every unordered pair of distinct levels of the crossed axis as a 2×2 contrast where group A and group B are the two sibling cells (not "rest"). Contrasts SHALL reuse the existing Koopman risk-ratio and Baptista-Pike odds-ratio interval machinery, including the established guardrail fallbacks. Contrast results SHALL be exposed in the result object and JSON output (stratum, level pair, counts, effect sizes with CIs) and rendered as a titled report table.

#### Scenario: Directional contrast controlled for the other axis
- **WHEN** a factorial crosses `class_axis` with `measured_axis` and the stratum `measured_ok` is examined
- **THEN** a contrast compares `upscale & measured_ok` directly against `downscale & measured_ok` with Koopman and Baptista-Pike intervals, answering the direction question without the baseline-dominated "rest" group

#### Scenario: Sparse sibling cells use guardrail fallbacks
- **WHEN** a contrast table is degenerate for the default interval methods but has a finite point estimate
- **THEN** the established guardrail fallbacks (Katz for risk ratio, Haldane-Anscombe for odds ratio) are applied to that contrast only

### Requirement: Factor-Free Configurations SHALL Be Unaffected
Configs and `AttributionSpec` instances that declare no `factors`/`factorials` SHALL produce identical outputs to the current behavior, with no factorial sections in the report and no factorial fields in the JSON output.

#### Scenario: Existing flat config is byte-stable
- **WHEN** an existing config with only a flat `hypotheses` list is assessed
- **THEN** `report.md` and `run.json` contain no factorial content and are unchanged relative to the pre-factorial implementation
