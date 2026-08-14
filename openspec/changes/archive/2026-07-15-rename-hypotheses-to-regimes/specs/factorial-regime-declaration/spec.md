# factorial-regime-declaration Delta Specification

## REMOVED Requirements

### Requirement: Factorial Crossings SHALL Expand Into Generated Regime Hypotheses

**Reason**: Renamed to "Factorial Crossings SHALL Expand Into Generated Regimes" — generated cells are regimes; "hypothesis" is reserved for statistical tests.

## ADDED Requirements

### Requirement: Factorial Crossings SHALL Expand Into Generated Regimes
At assessment time, each crossing in the `factorials` list SHALL expand into one generated regime per (row level, column level) cell, whose condition is the conjunction of the two inline level conditions and whose name is `"<row_level> & <col_level>"`. Generated cells SHALL be analysed by the existing regime machinery (contribution share and mismatch risk vs rest) with no separate evaluation path. A generated cell name that collides with a declared regime name or another generated name SHALL raise a validation error.

#### Scenario: Crossing two axes generates all cells
- **WHEN** a factorial crosses a 3-level `rows` axis with a 2-level `columns` axis
- **THEN** six regimes are generated with conjunction conditions and names such as `upscale & measured_off`, and each receives a regime summary and a mismatch-risk result

#### Scenario: Cell name collision is rejected
- **WHEN** a declared regime is already named `upscale & measured_off` and a factorial would generate a cell with the same name
- **THEN** assessment raises a validation error instead of silently overriding either result

## MODIFIED Requirements

### Requirement: Factorial Axes SHALL Be Declared Inline Per Crossing
The system SHALL accept each entry of the optional `factorials` list, both in the config JSON/YAML and on `AttributionSpec`, as a self-contained crossing object whose `rows` and `columns` keys are each an ordered mapping of level name to a boolean `condition` DSL string. Each axis mapping SHALL declare at least one level, and every level condition SHALL be a non-empty string. Each level condition SHALL be declared exactly once; the system SHALL NOT require the caller to repeat a level condition inside any cell or regime. Level ordering SHALL be preserved for rendering. The only keys accepted on a crossing object SHALL be `rows`, `columns`, `label`, and `baseline`; any other key SHALL raise a configuration error. There SHALL be no top-level `factors` declaration.

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
- **WHEN** a factorial entry contains a key other than `rows`, `columns`, `label`, or `baseline`
- **THEN** loading fails with a configuration error naming the unknown key

### Requirement: Factor-Free Configurations SHALL Be Unaffected
Configs and `AttributionSpec` instances that declare no `factorials` SHALL produce identical outputs to the current behavior, with no factorial sections in the report and no factorial fields in the JSON output.

#### Scenario: Existing factorial-free config is byte-stable
- **WHEN** an existing config with only a `regimes` mapping and no `factorials` is assessed
- **THEN** `report.md` and `run.json` contain no factorial content and are unchanged relative to the pre-factorial implementation
