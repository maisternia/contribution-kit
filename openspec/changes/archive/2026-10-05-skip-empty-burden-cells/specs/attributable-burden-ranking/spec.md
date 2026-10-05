## MODIFIED Requirements

### Requirement: Attributable Burden SHALL Be Computed Per Non-Baseline Cell
For each crossing with a declared baseline, the system SHALL compute for every non-empty non-baseline cell the excess (recoverable) mismatches `n_cell * (p_cell - p_baseline)`, where `p` denotes the cell mismatch rate under the spec-level mismatch definition, together with the excess share of all observed mismatches and a cumulative accuracy trajectory in which, proceeding down the ranking, each cell's mismatches are replaced by `n_cell * p_baseline`. The accuracy trajectory SHALL use all dataset rows as its denominator, with rows outside all cells keeping their observed outcomes. Cells with equal excess SHALL be ordered by declaration order (rows axis first, then columns axis). Cells with non-positive excess SHALL rank after all positive-excess cells and SHALL be presented as non-recoverable rather than as negative recoveries. A non-baseline cell that matches zero rows SHALL NOT be ranked and SHALL NOT fail the run; its name SHALL be recorded in the ranking's `empty_cells` list in declaration order (rows axis first, then columns axis), and the report SHALL list it in a note alongside the burden table.

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

#### Scenario: Empty non-baseline cell is skipped, not fatal
- **WHEN** a non-baseline cell of a baselined crossing matches zero rows of the input data
- **THEN** the assessment completes, the cell has no burden entry, its name appears in the ranking's `empty_cells` list in `run.json`, and the report notes it beside the burden table

### Requirement: Burden Rankings SHALL Be Guarded For Statistical Honesty
The system SHALL render a burden ranking only when the crossing's axes produced no overlap partition warnings; rows outside all cells (coverage gaps) SHALL NOT block the ranking but their count SHALL be noted alongside the table as excluded. When any non-empty non-baseline cell has a mismatch rate strictly below the baseline cell's rate, the system SHALL emit a baseline-sanity warning recorded in the JSON output and noted in the report; empty cells have no mismatch rate and SHALL NOT trigger the warning. Every rendered burden table SHALL be accompanied by a fixed counterfactual caveat stating that recoverable counts assume rows in a fixed regime revert to the baseline mismatch rate.

#### Scenario: Overlapping axes suppress the ranking
- **WHEN** a baselined crossing produced an overlap partition warning
- **THEN** no burden table is rendered for it and the report notes that the ranking was suppressed due to overlapping levels

#### Scenario: Coverage gap is excluded but reported
- **WHEN** 30 rows match no cell of a baselined crossing
- **THEN** the burden table renders with a note that 30 rows were excluded from the ranking

#### Scenario: Suspicious baseline triggers a warning
- **WHEN** the declared baseline cell's mismatch rate is higher than another cell's rate in the same crossing
- **THEN** a baseline-sanity warning is emitted, recorded in `run.json`, and noted next to the burden table

#### Scenario: Empty cell does not trigger the sanity warning
- **WHEN** the baseline cell has a non-zero mismatch rate, one non-baseline cell matches zero rows, and every non-empty non-baseline cell has a rate at or above the baseline rate
- **THEN** no baseline-sanity warning is emitted

#### Scenario: Counterfactual caveat is always rendered
- **WHEN** any burden table is rendered
- **THEN** it is followed by the fixed caveat sentence about the revert-to-baseline assumption
