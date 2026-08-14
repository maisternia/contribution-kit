## ADDED Requirements

### Requirement: Factorial-Only Specs SHALL Be Valid Without Declared Regimes
The estimator SHALL accept an attribution spec that declares zero caller-authored regimes when at least one factorial crossing is declared. The estimator SHALL continue to reject specs that declare neither regimes nor factorials.

#### Scenario: Factorial-only spec validates
- **WHEN** a spec declares at least one factorial crossing and no regimes
- **THEN** spec validation succeeds and assessment executes without raising a regime-required validation error

#### Scenario: Spec without regimes and factorials is rejected
- **WHEN** a spec declares no regimes and no factorial crossings
- **THEN** validation fails with an explicit configuration error indicating that at least one analysis surface is required

#### Scenario: Regime-based specs remain valid
- **WHEN** a spec declares one or more regimes and no factorial crossings
- **THEN** validation succeeds and regime/risk analysis behavior remains unchanged
