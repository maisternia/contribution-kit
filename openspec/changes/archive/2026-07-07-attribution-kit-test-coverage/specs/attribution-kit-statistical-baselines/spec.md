## ADDED Requirements

### Requirement: Integration tests reside in the parent repository

The accuracy-focused integration tests and their reference baselines SHALL live in the
parent repository under `ResearchData/tests/` (integration tests under
`ResearchData/tests/integration/`, baselines and generator scripts under
`ResearchData/tests/reference/`). They MUST NOT be placed inside the
`external/contribution-kit/` submodule.

#### Scenario: Integration tests are located in the parent repo

- **WHEN** the repository is inspected after this change
- **THEN** the accuracy/integration tests for the `contribution` kit exist under
  `ResearchData/tests/`
- **AND** no such integration test exists inside `external/contribution-kit/`

### Requirement: Reported statistics are validated against independent baselines

Integration tests SHALL validate the statistics the project reports — risk ratio and odds
ratio point estimates and their confidence intervals (`katz_risk_ratio`,
`haldane_anscombe_odds_ratio`, `koopman_risk_ratio`, `baptista_pike_odds_ratio`), and the
Shapley feature-attribution and regime-contribution shares — against baselines produced by
an independent authority. Effect-size and CI baselines SHALL be generated with an
established statistical package (for example R's `PropCIs`, `exact2x2`, `epitools`, or
`DescTools`); Shapley and regime shares SHALL be validated against an independent
brute-force reference computed outside the kit's own code.

#### Scenario: Effect sizes and CIs match the R baseline

- **WHEN** an integration test compares a kit-computed risk ratio or odds ratio (with its
  CI) to the corresponding independently generated baseline value
- **THEN** the kit value agrees with the baseline within the documented tolerance for that
  statistic

#### Scenario: Shapley and regime shares match an independent reference

- **WHEN** an integration test compares the kit's feature-attribution or
  regime-contribution shares to the independent brute-force reference
- **THEN** the kit values agree with the reference within the documented tolerance

#### Scenario: Baseline authority is recorded

- **WHEN** a baseline artifact is inspected
- **THEN** the exact package, function, and version used to produce it are recorded in the
  accompanying generator script or README

### Requirement: Baselines are committed and the suite runs offline

The reference baselines SHALL be committed as data artifacts (CSV/JSON) alongside the
scripts that generate them, so that running the integration suite does NOT require R or
network access. Regenerating baselines MAY require the external tooling, but running the
tests MUST NOT.

#### Scenario: Integration tests run without R or network

- **WHEN** the integration suite is executed with only the committed baselines present and
  no R installation or network available
- **THEN** the tests read the committed baselines and complete without invoking external
  tooling

#### Scenario: Generator scripts are committed with the baselines

- **WHEN** a committed baseline file is inspected
- **THEN** the script that produced it is present in `ResearchData/tests/reference/`

### Requirement: Numeric tolerance contract is explicit

Each integration comparison SHALL assert closeness using a documented per-statistic
tolerance with a stated rationale, and structural edge cases (infinite, zero, or absent
confidence-interval bounds) SHALL be asserted structurally rather than numerically.

#### Scenario: Point estimates use a tight documented tolerance

- **WHEN** a point-estimate comparison is asserted
- **THEN** the assertion uses an explicit absolute or relative tolerance documented next to
  it with a one-line rationale

#### Scenario: Degenerate CI bounds are asserted structurally

- **WHEN** a statistic returns an infinite, zero, or `None` confidence-interval bound
- **THEN** the test asserts that structural outcome rather than comparing it numerically

### Requirement: Integration data spans numeric edge cases

The integration layer SHALL exercise the reported statistics across numeric edge cases in
addition to the existing measurement-derived data, including sparse cells, single or double
zero cells, boundary support where the exact interval collapses, single-group regimes where
mismatch risk is undefined, and both supported `ci_method` values (`score-exact` and
`wald`). Purpose-built small tables MAY be added for this coverage of edge cases.

#### Scenario: Edge-case tables are validated against baselines

- **WHEN** the integration suite runs over the edge-case tables
- **THEN** each edge case is compared to its independently generated baseline (or asserted
  structurally where a numeric baseline is undefined)

#### Scenario: Both CI methods are validated

- **WHEN** integration tests cover confidence-interval computation
- **THEN** both the `score-exact` and `wald` `ci_method` paths are validated against
  baselines

### Requirement: Existing cross-repo integration test remains green

The system SHALL keep the existing parent-repo integration test
`ResearchData/tests/test_error_attribution_kit_integration.py` in the parent repository, and
this test MUST continue to pass after this change.

#### Scenario: Existing integration test still passes

- **WHEN** the parent-repo test suite is run after this change
- **THEN** `test_error_attribution_kit_integration.py` passes unchanged in behavior
