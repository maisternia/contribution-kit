## ADDED Requirements

### Requirement: Effect-size baselines reside in contribution-kit
The effect-size and confidence-interval baselines, their generator scripts and the accuracy test that compares the kit against them SHALL live in this repository: baselines and generators under `tests/reference/`, the comparison test under `tests/accuracy/`. The default `pytest` run of this repository SHALL collect and run that comparison. The Shapley and regime-share baselines and their integration tests SHALL remain in the parent repository under `ResearchData/tests/`.

#### Scenario: Effect-size accuracy test runs with the kit's own suite
- **WHEN** `pytest` is run from the `contribution-kit` repository root
- **THEN** the effect-size baseline comparison is collected and executed

#### Scenario: Shapley baselines stay in the parent repository
- **WHEN** the parent repository is inspected
- **THEN** the Shapley feature-attribution and regime-share integration tests and baselines remain under `ResearchData/tests/`

### Requirement: Baseline files record their provenance
Every committed effect-size baseline file SHALL carry a provenance block naming the generating tool and its version (R version and each package version, or Python and library versions), the exact function call used per method, and the generation timestamp. Each case SHALL name the authority that produced its values. The committed generator SHALL be runnable as documented, without editing, on a machine with the listed tooling.

#### Scenario: Missing provenance fails the suite
- **WHEN** the accuracy test loads a baseline file without a provenance block or a case without an authority
- **THEN** the test fails with a message naming the missing provenance

#### Scenario: Generator runs as documented
- **WHEN** the documented regeneration commands (`Rscript tests/reference/generate_effect_size_baselines.R`, then `python tests/reference/generate_effect_size_baselines.py`) are run from the repository root with the listed R and Python packages installed
- **THEN** they rewrite `tests/reference/effect_size_baselines.json` without error, and the result is identical to the committed file apart from the timestamp

## MODIFIED Requirements

### Requirement: Reported statistics are validated against independent baselines

Accuracy tests SHALL validate the statistics the project reports against baselines produced by an independent authority:
- risk ratio and odds ratio point estimates and their confidence intervals (`katz_risk_ratio`, `haldane_anscombe_odds_ratio`, `koopman_risk_ratio`, `baptista_pike_odds_ratio` in its exact and mid-p variants, and `cornfield_exact_odds_ratio`);
- the Shapley feature-attribution and regime-contribution shares.

Baselines SHALL NOT be derived from the kit's own output. The authority per method SHALL be:
- Koopman: R `PropCIs::riskscoreci`.
- Katz: R `epitools::riskratio.wald`.
- Haldane-Anscombe: R `DescTools::OddsRatio(method = "wald", correction = TRUE)`.
- Baptista-Pike exact, Baptista-Pike mid-p and Cornfield exact: an independent high-precision (at least 50 significant digits) implementation of each interval's definition, written without importing kit code. Its values SHALL be cross-checked against unrelated implementations, with the agreement recorded in the baseline file: R `exact2x2(tsmethod = "minlike")` for Baptista-Pike exact, `contingencytables::BaptistaPike_midP_CI_2x2` on the small tables where it converges for the mid-p variant, and SciPy `scipy.stats.contingency.odds_ratio(kind = "conditional")` for Cornfield.

Shapley and regime shares SHALL be validated against an independent brute-force reference computed outside the kit's own code.

#### Scenario: Effect sizes and CIs match the independent baseline
- **WHEN** an accuracy test compares a kit-computed risk ratio or odds ratio (with its CI) to the corresponding independently generated baseline value
- **THEN** the kit value agrees with the baseline within the documented tolerance for that statistic

#### Scenario: Shapley and regime shares match an independent reference
- **WHEN** an integration test compares the kit's feature-attribution or regime-contribution shares to the independent brute-force reference
- **THEN** the kit values agree with the reference within the documented tolerance

#### Scenario: Baseline authority is recorded
- **WHEN** a baseline artifact is inspected
- **THEN** the exact package, function, and version used to produce it are recorded in the baseline file itself and in the accompanying generator script or README

#### Scenario: High-precision odds-ratio reference is cross-checked
- **WHEN** the accuracy test loads the exact odds-ratio baselines
- **THEN** each case carries its recorded cross-check against the named unrelated implementation, and the test fails if any recorded agreement is outside that cross-check's documented tolerance

### Requirement: Baselines are committed and the suite runs offline

The reference baselines SHALL be committed as data artifacts (CSV/JSON) alongside the scripts that generate them, so that running the accuracy and integration suites does NOT require R or network access. Regenerating baselines MAY require the external tooling, but running the tests MUST NOT.

#### Scenario: Accuracy tests run without R or network
- **WHEN** the accuracy suite is executed with only the committed baselines present and no R installation or network available
- **THEN** the tests read the committed baselines and complete without invoking external tooling

#### Scenario: Generator scripts are committed with the baselines
- **WHEN** a committed effect-size baseline file is inspected
- **THEN** the script that produced it is present in `tests/reference/` of this repository

### Requirement: Numeric tolerance contract is explicit

Each accuracy comparison SHALL assert closeness using a documented per-statistic tolerance with a stated rationale. Confidence-interval bounds SHALL be compared with a relative tolerance, because bounds span several orders of magnitude. Structural edge cases (infinite, zero, or absent confidence-interval bounds) SHALL be asserted structurally rather than numerically.

#### Scenario: Point estimates use a tight documented tolerance
- **WHEN** a point-estimate comparison is asserted
- **THEN** the assertion uses an explicit tolerance documented next to it with a one-line rationale

#### Scenario: CI bounds use a documented relative tolerance
- **WHEN** a finite confidence-interval bound is compared to its baseline
- **THEN** the assertion uses an explicit relative tolerance documented next to it with a one-line rationale, and any case-specific looser tolerance names the reason

#### Scenario: Degenerate CI bounds are asserted structurally
- **WHEN** a statistic returns an infinite, zero, or `None` confidence-interval bound
- **THEN** the test asserts that structural outcome rather than comparing it numerically

### Requirement: Integration data spans numeric edge cases

The accuracy layer SHALL exercise the reported statistics across numeric edge cases and realistic tables, including sparse cells, single or double zero cells, a zero-event reference group with large n, an all-event exposed group, large-n tables with moderate effects, boundary support where the exact interval collapses, single-group regimes where mismatch risk is undefined, and both supported `ci_method` values (`score-exact` and `wald`). The case set SHALL include at least the tables `(22,1,291,12963)`, `(236,737,196,1333)`, `(15,14,482,8167)`, `(279,100,218,8081)`, `(248,746,0,6002)`, `(214,1348,0,6002)`, `(9,0,0,6002)` and `(26,85,0,6002)`, in addition to the legacy cases `(1,13,9,1)`, `(10,90,0,100)`, `(0,100,10,90)` and `(1,1,1,1)`.

#### Scenario: Edge-case and realistic tables are validated against baselines
- **WHEN** the accuracy suite runs over the case set
- **THEN** each case is compared to its independently generated baseline, or asserted structurally where a numeric baseline is undefined

#### Scenario: Both CI methods are validated
- **WHEN** accuracy tests cover confidence-interval computation
- **THEN** both the `score-exact` and `wald` `ci_method` paths are validated against baselines

## REMOVED Requirements

### Requirement: Integration tests reside in the parent repository
**Reason**: Keeping the effect-size baselines outside this repository meant the kit's own test run never compared it against an independent reference. The superproject copy was filled with kit output and has been failing unnoticed.
**Migration**: The effect-size baselines, generator and comparison test move to `tests/reference/` and `tests/accuracy/` in this repository (see "Effect-size baselines reside in contribution-kit"). The Shapley and regime-share integration tests stay in `ResearchData/tests/`. The obsolete superproject effect-size files are removed in a separate, user-approved superproject commit.
