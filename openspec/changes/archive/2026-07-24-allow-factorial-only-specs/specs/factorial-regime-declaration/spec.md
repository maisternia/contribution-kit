## ADDED Requirements

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
