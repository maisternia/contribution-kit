## ADDED Requirements

### Requirement: Mismatch-Risk Confidence Intervals SHALL Use Small-Sample Score And Exact Methods
The system SHALL compute the mismatch-risk confidence intervals using the Koopman asymptotic-score interval for the risk ratio and the Baptista-Pike exact interval for the odds ratio, chosen for their better small-sample coverage as recommended by Fagerland, Lydersen & Laake (2015, 2017). These SHALL be the methods used for all default reporting output. The system SHALL retain the Katz log-transform risk-ratio interval and the Haldane-Anscombe continuity-corrected odds-ratio interval as opt-in fallback methods, selectable through a single method-selection option on the binary-hypothesis evaluation path. Selecting a confidence-interval method SHALL NOT change the risk-ratio or odds-ratio point estimates. The mismatch-risk reference footnotes SHALL cite Koopman (1984) and Baptista & Pike (1977), with the small-sample recommendation attributed to Fagerland, Lydersen & Laake (2015/2017). The system SHALL document the availability of the opt-in fallback methods and how to select them exactly once in the `contribution-kit` README, and SHALL NOT otherwise present them as co-equal choices in default output.

#### Scenario: Risk-ratio CI uses Koopman
- **WHEN** a mismatch-risk result is computed without a caller specifying a confidence-interval method
- **THEN** the risk-ratio confidence interval is produced by the Koopman asymptotic-score method (Koopman 1984) and the odds-ratio confidence interval by the Baptista-Pike exact method (Baptista & Pike 1977)

#### Scenario: Opt-in fallback methods remain selectable
- **WHEN** a caller selects the fallback confidence-interval methods on the binary-hypothesis evaluation path
- **THEN** the risk-ratio confidence interval is produced by the Katz log-transform method (Katz et al. 1978) and the odds-ratio confidence interval by the Haldane-Anscombe continuity-corrected method (Haldane 1956; Anscombe 1956; Agresti 2013)

#### Scenario: Point estimates are independent of CI method
- **WHEN** the same 2×2 mismatch table is evaluated with the default methods and again with the fallback methods
- **THEN** the reported risk-ratio and odds-ratio point estimates are identical across both, and only the confidence-interval bounds differ

#### Scenario: Sparse tables still yield a risk-ratio interval
- **WHEN** a mismatch table with a single zero cell is evaluated with the default Koopman method
- **THEN** the risk-ratio confidence interval is defined and reported rather than collapsing to `n/a`, wherever the Koopman score interval is defined

#### Scenario: Footnotes cite the methods used and README documents the fallback once
- **WHEN** `AssessmentResult.to_markdown()` renders the mismatch-risk reference footnotes and a reader consults the `contribution-kit` README
- **THEN** the footnotes cite Koopman (1984) for the risk-ratio CI and Baptista & Pike (1977) for the odds-ratio CI (small-sample recommendation per Fagerland, Lydersen & Laake 2015/2017), and the README states in a single place that the Katz and Haldane-Anscombe fallbacks exist and how to select them

## MODIFIED Requirements

### Requirement: Regime Hypotheses SHALL Share The Observed Error And Compare Against The Rest
The system SHALL attribute to each regime hypothesis the same per-row observed error used by the feature attribution (derived from `prediction_expr` versus `target_expr`), and SHALL compute its mismatch risk by comparing the matching rows against the rest of the population using the spec-level `mismatch_expr`. The reported risk-ratio and odds-ratio confidence intervals SHALL use the Koopman asymptotic-score and Baptista-Pike exact methods respectively; the Katz and Haldane-Anscombe methods are available only as an opt-in fallback.

#### Scenario: Compute requested class BW regime contributions
- **WHEN** a caller declares regime conditions including `class_bw < gt_bw (beyond tol)`, `class_bw > gt_bw (beyond tol)`, `class_bw within tol & sf wrong`, `class_bw & sf ok, measured_bw off`, and the baseline regime
- **THEN** the estimator returns regime summaries with `name`, `count`, `mean_contribution`, `total_contribution`, and `contribution_share_pct`, where the contribution totals are derived from the spec's `prediction_expr` versus `target_expr`

#### Scenario: Compute condition-vs-rest mismatch risk
- **WHEN** a regime hypothesis is evaluated and `mismatch_expr` is set
- **THEN** the estimator returns a binary result comparing the matching rows (group A) against the rest of the population (group B) with mismatch rates, risk ratio, and odds ratio with confidence intervals computed by the active confidence-interval method

#### Scenario: Markdown reports include confidence-interval ranges
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk rows
- **THEN** the report table labels the effect-size columns as `risk ratio (95% CI)` and `odds ratio (95% CI)` and formats each as `value (low to high)`
