# attributable-burden-ranking Specification

## Purpose

Define an opt-in attributable-burden ranking for factorial crossings with a
declared baseline cell so reports can prioritize which regimes contribute the
most recoverable mismatches while preserving baseline-free behavior.

## Requirements

### Requirement: A Factorial Crossing SHALL Accept An Optional Baseline Cell
The system SHALL accept an optional `baseline` key on each factorial crossing object, both in config JSON/YAML and on `AttributionSpec`, whose value is an object `{rows: <row_level>, columns: <col_level>}` naming one cell of that crossing as the reference for attributable-burden computation. Both named levels SHALL exist on their respective axes; a missing level SHALL raise a configuration error naming the crossing and the missing level. If the baseline cell matches zero rows at assessment time, the run SHALL fail with an error naming the crossing; a small-but-nonempty baseline cell SHALL be accepted with no minimum-count threshold. A crossing without `baseline` SHALL compute no burden ranking and SHALL behave exactly as before this capability, except that the CLI SHALL print a one-line hint to stderr naming the unbaselined crossing and suggesting the `baseline` key; the hint SHALL NOT appear in `report.md` or the JSON output.

#### Scenario: Baseline cell is declared structurally
- **WHEN** a crossing declares `"baseline": {"rows": "class_ok", "columns": "measured_ok"}`
- **THEN** the spec parses and the cell `class_ok & measured_ok` becomes the burden reference for that crossing

#### Scenario: Unknown baseline level is rejected
- **WHEN** a crossing declares `"baseline": {"rows": "class_good", "columns": "measured_ok"}` and the `rows` axis has no level `class_good`
- **THEN** loading fails with a configuration error naming the crossing and the missing `rows` level

#### Scenario: Baseline-free crossing is unchanged
- **WHEN** a crossing declares no `baseline` key
- **THEN** no burden ranking is computed or rendered for it, all other `report.md` and JSON outputs are identical to pre-capability behavior, and the CLI prints a stderr hint naming the crossing and suggesting the `baseline` key

#### Scenario: Empty baseline cell fails the run
- **WHEN** the declared baseline cell matches zero rows of the input data
- **THEN** the assessment fails with an error naming the crossing and the empty baseline cell

### Requirement: Attributable Burden SHALL Be Computed Per Non-Baseline Cell
For each crossing with a declared baseline, the system SHALL compute for every non-baseline cell the excess (recoverable) mismatches `n_cell * (p_cell - p_baseline)`, where `p` denotes the cell mismatch rate under the spec-level mismatch definition, together with the excess share of all observed mismatches and a cumulative accuracy trajectory in which, proceeding down the ranking, each cell's mismatches are replaced by `n_cell * p_baseline`. The accuracy trajectory SHALL use all dataset rows as its denominator, with rows outside all cells keeping their observed outcomes. Cells with equal excess SHALL be ordered by declaration order (rows axis first, then columns axis). Cells with non-positive excess SHALL rank after all positive-excess cells and SHALL be presented as non-recoverable rather than as negative recoveries.

#### Scenario: Excess mismatches rank the dominant cause first
- **WHEN** a crossing's cells include one with 170 rows at 97% mismatch and one with 464 rows at 17% mismatch, against a baseline rate of 0.2%
- **THEN** the burden ranking lists the 170-row cell first with approximately 165 recoverable mismatches and the 464-row cell second with approximately 78

#### Scenario: Cumulative accuracy trajectory is reported
- **WHEN** the burden ranking is computed
- **THEN** each ranked row reports the overall prediction-vs-target accuracy that would result if that cell and all higher-ranked cells reverted to the baseline mismatch rate, computed over all dataset rows including any outside the crossing's cells

#### Scenario: Equal excess breaks ties by declaration order
- **WHEN** two non-baseline cells have equal recoverable mismatches
- **THEN** the cell whose levels appear earlier in the declared axis order (rows axis first, then columns axis) ranks first

#### Scenario: Better-than-baseline cell is not a negative recovery
- **WHEN** a non-baseline cell has a mismatch rate below the baseline rate
- **THEN** the cell appears after all positive-excess cells and its recoverable value is rendered as not recoverable, not as a negative count

### Requirement: Burden Rows SHALL Carry Risk-Difference Confidence Intervals
Each burden row SHALL report the risk difference `p_cell - p_baseline` with a 95% confidence interval computed by the Miettinen-Nurminen asymptotic score method as the primary default. When the primary interval is non-finite or unordered for a finite point estimate, the system SHALL automatically apply the Agresti-Caffo interval for that result only, following the kit's established primary-plus-guardrail pattern. The `--ci-method wald` opt-in SHALL NOT affect the risk-difference method. The report reference footnotes SHALL cite Miettinen & Nurminen (1985) and Agresti & Caffo (2000) when a burden table is rendered.

#### Scenario: Risk difference uses the score interval by default
- **WHEN** a burden row is computed for a cell with a finite risk-difference point estimate
- **THEN** its confidence interval is computed with the Miettinen-Nurminen asymptotic score method and rendered as `value (low to high)`

#### Scenario: Degenerate interval falls back per result
- **WHEN** the primary interval is non-finite or unordered for a finite risk-difference point estimate
- **THEN** the Agresti-Caffo interval is used for that row only, and other rows keep the primary method

#### Scenario: Reference footnotes cite the risk-difference methods
- **WHEN** a report containing a burden table is rendered
- **THEN** the references footnote block cites Miettinen & Nurminen (1985) and Agresti & Caffo (2000), and reports without a burden table do not include these entries

### Requirement: Burden Rankings SHALL Be Guarded For Statistical Honesty
The system SHALL render a burden ranking only when the crossing's axes produced no overlap partition warnings; rows outside all cells (coverage gaps) SHALL NOT block the ranking but their count SHALL be noted alongside the table as excluded. When any non-baseline cell has a mismatch rate strictly below the baseline cell's rate, the system SHALL emit a baseline-sanity warning recorded in the JSON output and noted in the report. Every rendered burden table SHALL be accompanied by a fixed counterfactual caveat stating that recoverable counts assume rows in a fixed regime revert to the baseline mismatch rate.

#### Scenario: Overlapping axes suppress the ranking
- **WHEN** a baselined crossing produced an overlap partition warning
- **THEN** no burden table is rendered for it and the report notes that the ranking was suppressed due to overlapping levels

#### Scenario: Coverage gap is excluded but reported
- **WHEN** 30 rows match no cell of a baselined crossing
- **THEN** the burden table renders with a note that 30 rows were excluded from the ranking

#### Scenario: Suspicious baseline triggers a warning
- **WHEN** the declared baseline cell's mismatch rate is higher than another cell's rate in the same crossing
- **THEN** a baseline-sanity warning is emitted, recorded in `run.json`, and noted next to the burden table

#### Scenario: Counterfactual caveat is always rendered
- **WHEN** any burden table is rendered
- **THEN** it is followed by the fixed caveat sentence about the revert-to-baseline assumption

### Requirement: Burden Rankings SHALL Be Rendered And Serialized
`to_markdown()` SHALL render, for each baselined crossing, a titled "Attributable burden" section (prefixed by the crossing's effective label) whose table reports per ranked cell: rank, cell name, row count, mismatch rate, baseline rate, recoverable mismatches, share of all observed mismatches, risk difference with confidence interval, and cumulative accuracy if eliminated. The cumulative-accuracy column label SHALL explicitly indicate accumulation (for example, `Accuracy if eliminated (accumulating)`). The table SHALL follow the accessible-reports conventions: plain-language column labels, confidence intervals formatted as `value (low to high)`, and the established footnote style. The JSON output SHALL carry a `burden_rankings` collection with the crossing label, baseline cell, per-cell entries, and guard outcomes. Baseline-free runs SHALL contain no `burden_rankings` content.

#### Scenario: Burden table renders ranked rows
- **WHEN** a baselined 3x2 crossing is assessed
- **THEN** the report contains an "Attributable burden" section for it with one row per non-baseline cell ordered by recoverable mismatches

#### Scenario: JSON exposes the ranking
- **WHEN** `run.json` is written for a baselined run
- **THEN** it contains `burden_rankings` entries with baseline cell identity, per-cell excess values, risk differences with CIs, and guard outcomes