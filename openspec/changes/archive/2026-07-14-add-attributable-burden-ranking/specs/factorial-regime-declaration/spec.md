# factorial-regime-declaration Delta Specification

## MODIFIED Requirements

### Requirement: Factorial Axes SHALL Be Declared Inline Per Crossing
The system SHALL accept each entry of the optional `factorials` list, both in the config JSON/YAML and on `AttributionSpec`, as a self-contained crossing object whose `rows` and `columns` keys are each an ordered mapping of level name to a boolean `condition` DSL string. Each axis mapping SHALL declare at least one level, and every level condition SHALL be a non-empty string. Each level condition SHALL be declared exactly once; the system SHALL NOT require the caller to repeat a level condition inside any cell or hypothesis. Level ordering SHALL be preserved for rendering. The only keys accepted on a crossing object SHALL be `rows`, `columns`, `label`, and `baseline`; any other key SHALL raise a configuration error. There SHALL be no top-level `factors` declaration.

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
