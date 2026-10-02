## MODIFIED Requirements

### Requirement: Regime Hypotheses SHALL Share The Observed Error And Compare Against The Rest
The system SHALL attribute to each regime hypothesis the same per-row observed error used by the feature attribution (derived from `prediction_expr` versus `target_expr`), and SHALL compute its mismatch risk by comparing the matching rows against the rest of the population using the spec-level `mismatch_expr`. The reported risk-ratio and odds-ratio confidence intervals SHALL use the Koopman asymptotic-score interval and the Baptista-Pike exact conditional interval as the primary default methods. When either primary method fails numerically to produce a finite ordered interval for a finite point estimate, the system SHALL use Katz (risk ratio) or Haldane-Anscombe (odds ratio) for that result, and SHALL record and report that the fallback was used.

#### Scenario: Compute requested class BW regime contributions
- **WHEN** a caller declares regime conditions including `class_bw < gt_bw (beyond tol)`, `class_bw > gt_bw (beyond tol)`, `class_bw within tol & sf wrong`, `class_bw & sf ok, measured_bw off`, and the baseline regime
- **THEN** the estimator returns regime summaries with `name`, `count`, `mean_contribution`, `total_contribution`, and `contribution_share_pct`, where the contribution totals are derived from the spec's `prediction_expr` versus `target_expr`

#### Scenario: Compute condition-vs-rest mismatch risk
- **WHEN** a regime hypothesis is evaluated and `mismatch_expr` is set
- **THEN** the estimator returns a binary result comparing the matching rows (group A) against the rest of the population (group B) with mismatch rates, risk ratio, and odds ratio with confidence intervals, and with the method that produced each interval recorded as `rr_ci_method` and `or_ci_method`

#### Scenario: Fallback intervals are flagged in reported output
- **WHEN** a primary method fails numerically for a finite point estimate and the fallback interval is reported
- **THEN** the reported interval is finite and ordered, the result's `rr_ci_method` or `or_ci_method` names the fallback method, and the Markdown report marks that row and explains the marker in a footnote

#### Scenario: Markdown reports include confidence-interval ranges
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk rows
- **THEN** the report table labels the effect-size columns as `risk ratio (95% CI)` and `odds ratio (95% CI)` and formats each as `value (low to high)`

### Requirement: Mismatch-Risk Confidence Intervals SHALL Use Small-Sample Score And Exact Methods
The system SHALL compute mismatch-risk confidence intervals using the Koopman asymptotic-score interval for risk ratio and the Baptista-Pike exact conditional interval for odds ratio as the default primary methods, selected for small-sample behavior as recommended by Fagerland, Lydersen & Laake (2015, 2017).

The Koopman interval SHALL invert the score statistic `(p̂1 − φ·p̂0) / sqrt(p̃1(1−p̃1)/n1 + φ²·p̃0(1−p̃0)/n0)` at the restricted maximum-likelihood estimates `p̃1 = φ·p̃0`.

The Baptista-Pike interval SHALL be the hull of the set of odds ratios θ whose conditional minimum-likelihood p-value exceeds α. That p-value is the sum of the noncentral-hypergeometric probabilities of all tables, with the observed margins, that are no more probable than the observed table, with a relative tie tolerance of 1e-7.

The system SHALL offer two opt-in odds-ratio intervals through an `or_interval` option on `evaluate_binary_hypothesis`, `assess` and the CLI (`--or-interval`):
- `baptista-pike-midp`: the same p-value minus half the observed table's probability.
- `cornfield`: the Cornfield exact conditional interval, inverting each one-sided conditional tail at α/2.

`or_interval` SHALL default to `baptista-pike`, SHALL apply to the `score-exact` method, and SHALL be rejected with a clear error when a non-default value is combined with `ci_method="wald"`.

If a primary method fails numerically to produce a finite ordered interval for a finite point estimate, the system SHALL apply the corresponding fallback method (Katz for risk ratio, Haldane-Anscombe for odds ratio) for that result and SHALL record which method produced the bounds. The system SHALL retain explicit opt-in fallback selection through the existing method-selection option. Selecting any confidence-interval method SHALL NOT change risk-ratio or odds-ratio point estimates.

The mismatch-risk reference footnotes SHALL cite Koopman (1984) and Baptista & Pike (1977), with the small-sample recommendation attributed to Fagerland, Lydersen & Laake (2015/2017). When a non-default odds-ratio interval is used, they SHALL name it and cite its source instead. The system SHALL document the explicit fallback methods, the odds-ratio interval options and the selection path exactly once in the `contribution-kit` README.

#### Scenario: Risk-ratio and odds-ratio CIs use default primary methods
- **WHEN** a mismatch-risk result is computed without a caller specifying a confidence-interval method
- **THEN** risk-ratio confidence intervals are computed with Koopman asymptotic-score and odds-ratio confidence intervals with Baptista-Pike exact conditional, and the results record `koopman` and `baptista-pike` as their CI methods unless a numerical fallback was applied

#### Scenario: Koopman interval matches the reference implementation
- **WHEN** `koopman_risk_ratio` is evaluated on sparse, zero-event-reference, all-event and large-n tables
- **THEN** its bounds agree with R `PropCIs::riskscoreci` within the documented tolerance

#### Scenario: Zero-event reference group yields an open-ended interval with a correct lower bound
- **WHEN** group B has no mismatches and group A has at least one, for example `(248, 746, 0, 6002)`
- **THEN** the risk-ratio point estimate is infinite, the upper bound is infinite, and the lower bound equals the `riskscoreci` lower bound (390.1 for this table) within tolerance

#### Scenario: Baptista-Pike interval is the minimum-likelihood inversion
- **WHEN** `baptista_pike_odds_ratio(22, 1, 291, 12963)` is evaluated
- **THEN** the interval is approximately 162.5 to 19,952, agreeing with R `exact2x2(tsmethod = "minlike")` and with the independent high-precision reference within the documented tolerance

#### Scenario: Baptista-Pike mid-p interval is selectable
- **WHEN** the `baptista-pike-midp` odds-ratio interval is selected for the table `(22, 1, 291, 12963)`
- **THEN** the interval is approximately 162.51 to 10,184.32, agreeing with the independent high-precision reference within the documented tolerance, and the result records `or_ci_method = "baptista-pike-midp"`

#### Scenario: Cornfield exact interval is selectable
- **WHEN** the `cornfield` odds-ratio interval is selected
- **THEN** the interval inverts each one-sided conditional tail at α/2, agrees with the independent high-precision reference within the documented tolerance, and the result records `or_ci_method = "cornfield"`

#### Scenario: Odds-ratio interval option conflicts with wald
- **WHEN** a caller combines `ci_method="wald"` with a non-default `or_interval`
- **THEN** the call fails with a validation error naming both options

#### Scenario: Primary methods do not need the fallback on small tables
- **WHEN** every 2x2 table with cells in 0..7, at least one mismatch in each group and non-empty groups is evaluated with Koopman and with each odds-ratio interval option
- **THEN** no result uses a fallback CI method

#### Scenario: Automatic guardrail fallback is method-specific
- **WHEN** a finite risk-ratio primary interval fails numerically and the odds-ratio primary interval is valid for the same table
- **THEN** the system applies Katz only to the risk-ratio interval, records `rr_ci_method = "katz"`, and keeps the selected odds-ratio interval with its own method label

#### Scenario: Opt-in fallback methods remain selectable
- **WHEN** a caller selects fallback confidence-interval methods on the binary-hypothesis evaluation path
- **THEN** risk-ratio confidence intervals are produced by Katz and odds-ratio confidence intervals by Haldane-Anscombe regardless of whether automatic guardrail fallback would have been triggered

#### Scenario: Point estimates are independent of CI method
- **WHEN** the same 2x2 mismatch table, including a table with a zero cell such as `(91, 385, 0, 11972)`, is evaluated with the default methods, with each odds-ratio interval option and with the fallback methods
- **THEN** reported risk-ratio and odds-ratio point estimates are identical across all of them, and only confidence-interval bounds and CI-method labels differ

#### Scenario: CI methods reject invalid confidence-level z input
- **WHEN** any confidence-interval routine is called with a non-finite or non-positive z value
- **THEN** the routine fails fast with a clear validation error instead of returning a malformed interval

#### Scenario: Footnotes cite default primary methods and README documents fallback once
- **WHEN** `AssessmentResult.to_markdown()` renders mismatch-risk footnotes with the default methods and a reader checks the `contribution-kit` README
- **THEN** the footnotes cite Koopman (1984) and Baptista & Pike (1977) with Fagerland, Lydersen & Laake (2015/2017), and the README contains one section describing fallback availability, the odds-ratio interval options, their selection and how fallback rows are marked

#### Scenario: Footnotes name a non-default odds-ratio interval
- **WHEN** the report was produced with `or_interval` set to `baptista-pike-midp` or `cornfield`
- **THEN** the odds-ratio footnote names that interval and cites its source (Baptista & Pike 1977 with the mid-p modification of Lancaster 1961, or Cornfield 1956)
