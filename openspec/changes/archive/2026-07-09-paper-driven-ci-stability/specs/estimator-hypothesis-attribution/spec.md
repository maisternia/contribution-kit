## MODIFIED Requirements

### Requirement: Regime Hypotheses SHALL Share The Observed Error And Compare Against The Rest
The system SHALL attribute to each regime hypothesis the same per-row observed error used by the feature attribution (derived from `prediction_expr` versus `target_expr`), and SHALL compute its mismatch risk by comparing the matching rows against the rest of the population using the spec-level `mismatch_expr`. The reported risk-ratio and odds-ratio confidence intervals SHALL use Koopman asymptotic-score and Baptista-Pike exact methods as the primary default methods; when either primary method yields a non-finite or unordered interval for a finite point estimate, the system SHALL automatically use Katz (risk ratio) or Haldane-Anscombe (odds ratio) for that result.

#### Scenario: Compute requested class BW regime contributions
- **WHEN** a caller declares regime conditions including `class_bw < gt_bw (beyond tol)`, `class_bw > gt_bw (beyond tol)`, `class_bw within tol & sf wrong`, `class_bw & sf ok, measured_bw off`, and the baseline regime
- **THEN** the estimator returns regime summaries with `name`, `count`, `mean_contribution`, `total_contribution`, and `contribution_share_pct`, where the contribution totals are derived from the spec's `prediction_expr` versus `target_expr`

#### Scenario: Compute condition-vs-rest mismatch risk
- **WHEN** a regime hypothesis is evaluated and `mismatch_expr` is set
- **THEN** the estimator returns a binary result comparing the matching rows (group A) against the rest of the population (group B) with mismatch rates, risk ratio, and odds ratio with confidence intervals

#### Scenario: Default output avoids non-finite bounds for finite-point rows
- **WHEN** a finite risk-ratio or odds-ratio point estimate is computed and the primary default inversion yields a non-finite or unordered confidence interval
- **THEN** the corresponding confidence interval in reported output is computed using the paper-cited fallback method for that effect size and rendered as an ordered finite interval

#### Scenario: Markdown reports include confidence-interval ranges
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk rows
- **THEN** the report table labels the effect-size columns as `risk ratio (95% CI)` and `odds ratio (95% CI)` and formats each as `value (low to high)`

### Requirement: Mismatch-Risk Confidence Intervals SHALL Use Small-Sample Score And Exact Methods
The system SHALL compute mismatch-risk confidence intervals using the Koopman asymptotic-score interval for risk ratio and the Baptista-Pike exact interval for odds ratio as the default primary methods, selected for small-sample behavior as recommended by Fagerland, Lydersen & Laake (2015, 2017). If a primary default interval output is non-finite or unordered for a finite point estimate, the system SHALL automatically apply the corresponding paper-cited fallback method (Katz for risk ratio, Haldane-Anscombe for odds ratio) for that result. The system SHALL retain explicit opt-in fallback selection through the existing method-selection option, and selecting a confidence-interval method SHALL NOT change risk-ratio or odds-ratio point estimates. The mismatch-risk reference footnotes SHALL continue to cite Koopman (1984) and Baptista & Pike (1977), with the small-sample recommendation attributed to Fagerland, Lydersen & Laake (2015/2017). The system SHALL document the explicit fallback methods and selection path exactly once in the `contribution-kit` README.

#### Scenario: Risk-ratio and odds-ratio CIs use default primary methods
- **WHEN** a mismatch-risk result is computed without a caller specifying a confidence-interval method
- **THEN** risk-ratio confidence intervals are computed with Koopman asymptotic-score and odds-ratio confidence intervals are computed with Baptista-Pike exact, except for per-result automatic guardrail fallback when default inversion output is non-finite or unordered for a finite point estimate

#### Scenario: Automatic guardrail fallback is method-specific
- **WHEN** a finite risk-ratio default interval is invalid and the odds-ratio default interval is valid for the same table
- **THEN** the system applies Katz only to the risk-ratio interval and keeps Baptista-Pike for the odds-ratio interval

#### Scenario: Opt-in fallback methods remain selectable
- **WHEN** a caller selects fallback confidence-interval methods on the binary-hypothesis evaluation path
- **THEN** risk-ratio confidence intervals are produced by Katz and odds-ratio confidence intervals by Haldane-Anscombe regardless of whether automatic guardrail fallback would have been triggered

#### Scenario: Point estimates are independent of CI method
- **WHEN** the same 2x2 mismatch table is evaluated with default methods and with fallback methods
- **THEN** reported risk-ratio and odds-ratio point estimates are identical across both, and only confidence-interval bounds differ

#### Scenario: Sparse finite-point tables produce finite ordered intervals
- **WHEN** a sparse mismatch table with a finite risk-ratio point estimate is evaluated and the default inversion cannot produce a finite ordered confidence interval
- **THEN** the reported risk-ratio confidence interval is finite and ordered via method-specific fallback rather than `n/a` or `to inf`

#### Scenario: CI methods reject invalid confidence-level z input
- **WHEN** any confidence-interval routine is called with a non-finite or non-positive z value
- **THEN** the routine fails fast with a clear validation error instead of returning a malformed interval

#### Scenario: Footnotes cite default primary methods and README documents fallback once
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk footnotes and a reader checks the `contribution-kit` README
- **THEN** the footnotes cite Koopman (1984) and Baptista & Pike (1977) with Fagerland, Lydersen & Laake (2015/2017), and the README contains one section describing fallback availability and selection
