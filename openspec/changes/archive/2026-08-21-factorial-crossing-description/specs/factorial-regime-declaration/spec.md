## ADDED Requirements

### Requirement: Factorial Crossings SHALL Support An Optional Description
Each factorial crossing SHALL accept an optional `description` string, in the config JSON/YAML and on `FactorialCrossing`, holding prose that explains the crossing's axes and what distinguishes their levels. When provided it SHALL be a non-empty string; a non-string or empty value SHALL raise a configuration error identifying the crossing. The description SHALL be display-only: it SHALL NOT affect level names, generated cell names, `baseline` resolution, partition validation, or any computed statistic. A crossing SHALL remain valid with no description.

#### Scenario: Description is declared alongside the axes
- **WHEN** a crossing declares `"description": "Rows split rows by whether the class decision alone caused error; columns by whether the BW measurement alone did."` together with its `rows` and `columns` maps
- **THEN** the spec parses successfully and the crossing carries that description

#### Scenario: Empty description is rejected
- **WHEN** a crossing declares `"description": ""`
- **THEN** loading fails with a configuration error identifying the crossing

#### Scenario: Description does not affect analysis
- **WHEN** a description is added to an existing crossing and nothing else changes
- **THEN** generated cell names, partition warnings, matrix counts, mismatch rates, risk ratios, contrast records, and burden ranking entries are all unchanged

### Requirement: Reports SHALL Render A Crossing Description With Its Matrix
`to_markdown()` SHALL render a crossing's description as prose directly beneath that crossing's matrix section heading and before the matrix table. The description SHALL NOT be rendered in the within-stratum contrast sections or the attributable-burden section, which remain anchored to the crossing by its effective label. A crossing that declares no description SHALL render no such prose, leaving its matrix section byte-identical to the pre-description output.

#### Scenario: Description precedes the matrix table
- **WHEN** a crossing labelled `Class decision × BW measurement` declares a description
- **THEN** the report renders the heading `Class decision × BW measurement`, then the description prose, then the matrix table

#### Scenario: Description-free crossing renders unchanged
- **WHEN** a crossing declares no description
- **THEN** its matrix section contains no description prose and is byte-identical to the output produced before this field existed

### Requirement: JSON Output SHALL Expose The Crossing Description
The factorial matrix record in the JSON output SHALL carry a `description` field holding the crossing's declared description, or null when none is declared. All existing matrix, contrast, and burden fields SHALL be unchanged.

#### Scenario: Declared description appears in the matrix record
- **WHEN** a crossing declares a description
- **THEN** that crossing's matrix record in `run.json` carries the description text and its cells, marginals, and label are unchanged

#### Scenario: Description-free run carries a null description
- **WHEN** no crossing declares a description
- **THEN** every matrix record in the JSON output carries a null description

## MODIFIED Requirements

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
- **WHEN** a factorial entry contains a key other than `rows`, `columns`, `label`, `description`, or `baseline`
- **THEN** loading fails with a configuration error naming the unknown key
