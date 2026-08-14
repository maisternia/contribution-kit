# estimator-hypothesis-attribution Delta Specification

## MODIFIED Requirements

### Requirement: Hypotheses SHALL Be Declared As A Named Mapping Of Conditions
The system SHALL declare every caller-authored hypothesis through one `AttributionSpec.hypotheses` collection whose config representation is a name-keyed **mapping** (`{name -> value}`), where the map key is the hypothesis name and each value is either (a) a boolean `condition` DSL string, or (b) an object with a required `condition` DSL string and an optional `label`. A string value SHALL be equivalent to an object whose `condition` is that string and whose `label` defaults to the key. Each entry SHALL be materialized as the single public `Hypothesis` type carrying `name` (the key), `condition`, and an optional `label`. The system SHALL treat `Hypothesis` as the only public hypothesis type for callers and SHALL NOT require callers to declare regimes, binary tests, mismatch groups, separate actual/baseline expressions, or a specific subtype. Mapping insertion order SHALL be preserved for rendering. The list form of `hypotheses` SHALL NOT be accepted. In addition to the mapping, the system SHALL accept optional `factors`/`factorials` declarations whose crossings expand into generated regime hypotheses at assessment time; generated hypotheses SHALL be internal `Hypothesis` instances that join the same classification and analysis pipeline as declared hypotheses, and callers SHALL NOT construct cell hypotheses by hand to obtain factorial analysis.

#### Scenario: One condition mapping describes the whole analysis
- **WHEN** a caller builds a config with `prediction_expr`, `target`, `prediction`, and a `hypotheses` mapping of name → condition
- **THEN** the spec fully describes the caller-authored hypotheses with no `regimes`, `binary_tests`, or callable predicate inputs, and no repeated `name` field inside entries

#### Scenario: String shorthand is equivalent to an object with a defaulted label
- **WHEN** an entry is written as `"class_bw": "col('Class BW') == col('GT BW')"`
- **THEN** it materializes as a `Hypothesis` with `name` = `class_bw`, `condition` = that string, and `label` = `class_bw`, identical to writing `"class_bw": { "condition": "col('Class BW') == col('GT BW')" }`

#### Scenario: Object form carries an explicit label
- **WHEN** an entry is written as `"class_sf": { "label": "Nominal class SF", "condition": "col('Class SF') == col('GT SF')" }`
- **THEN** it materializes as a `Hypothesis` with `name` = `class_sf`, that `label`, and that `condition`

#### Scenario: Object missing condition is rejected
- **WHEN** a `hypotheses` entry value is an object without a `condition` key
- **THEN** the loader raises a configuration error naming the offending hypothesis key

#### Scenario: Redundant name key is rejected
- **WHEN** a `hypotheses` entry object includes a `name` field
- **THEN** the loader raises a configuration error, because the mapping key already supplies the name

#### Scenario: Mapping order is preserved
- **WHEN** a `hypotheses` mapping declares entries in a given order
- **THEN** the materialized hypotheses and their report rows follow that declared order

#### Scenario: Factorial expansion feeds the same hypothesis pipeline
- **WHEN** a spec declares `factors` and a `factorials` crossing alongside a `hypotheses` mapping
- **THEN** the generated cell hypotheses are routed by the same private classification rule as declared hypotheses (their conjunction conditions are non-equality, so all cells are regimes), and declared equality hypotheses still become Shapley features unchanged
