# accessible-reports Delta Specification

## MODIFIED Requirements

### Requirement: Accessible Presentation SHALL Preserve Existing Report Guarantees
The system SHALL preserve the mismatch-risk effect-size column labels
`Risk ratio (95% CI)` and `Odds ratio (95% CI)`, their `value (low to high)`
formatting, and the existing reference footnotes when adding the accessible
presentation layer. The mismatch-risk table SHALL label its first column
`Regime`, SHALL label its percentage columns as `Regime mismatch rate` and
`Rest mismatch rate`, and SHALL format supporting counts in parentheses as
`mismatch:matched` (for example `22:1`). The mismatch-risk table SHALL omit
regimes whose matching rows contain zero mismatches, because those rows add no
positive mismatch signal to the risk-focused summary even if they still appear
in the regime-contribution table.

#### Scenario: CI columns and footnotes are unchanged
- **WHEN** `to_markdown()` renders the mismatch-risk section under the new accessible layout
- **THEN** the effect-size columns are still labelled `Risk ratio (95% CI)` and `Odds ratio (95% CI)` formatted as `value (low to high)`, and the Koopman / Baptista-Pike / Fagerland reference footnotes are still present

#### Scenario: Mismatch-rate columns and counts are explicit
- **WHEN** `to_markdown()` renders mismatch-risk rows
- **THEN** the table headers include `Regime`, `Regime mismatch rate`, and `Rest mismatch rate`
- **AND** each percentage includes counts in `mismatch:matched` form in parentheses

#### Scenario: Zero-mismatch baseline rows are omitted from mismatch risk
- **WHEN** `to_markdown()` renders mismatch-risk results for a regime whose matching rows have zero mismatches
- **THEN** that regime is omitted from the mismatch-risk table
- **AND** the same regime may still appear in the regime-contribution table if it has a regime summary
