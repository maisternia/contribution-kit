## 1. Koopman risk-ratio CI (stats)

- [ ] 1.1 Add `koopman_risk_ratio(a, b, c, d, z=1.96)` to [external/contribution-kit/src/contribution/stats.py](external/contribution-kit/src/contribution/stats.py) returning a `RiskRatioResult`, computing the point estimate as today and the CI by inverting the asymptotic score statistic via bisection on each side of the estimate
- [ ] 1.2 Handle degenerate/boundary tables (zero cells, empty margins) with defined limits (0 / +∞) and validated inputs via `_validate_2x2_counts`, keeping `ci_low`/`ci_high` typed `float | None`
- [ ] 1.3 Add unit tests in [external/contribution-kit/tests/test_stats.py](external/contribution-kit/tests/test_stats.py) covering a known-value case (expected bounds precomputed from R `ratesci`), a single-zero-cell case that still yields a defined interval, and a boundary case

## 2. Baptista-Pike odds-ratio CI (stats)

- [ ] 2.1 Add `baptista_pike_odds_ratio(a, b, c, d, z=1.96)` to `stats.py` returning an `OddsRatioResult`, computing exact two-sided limits by inverting the noncentral-hypergeometric conditional test over the support of `a` given fixed margins
- [ ] 2.2 Handle degenerate/boundary tables (zero-cell odds ratio at 0 or +∞) with defined limits and root-find convergence caps
- [ ] 2.3 Add unit tests in `test_stats.py` covering a known-value case (expected bounds precomputed from R `exact2x2`), a sparse-cell case, and monotonic-bounds assertions

## 3. Method selection on the evaluation path

- [ ] 3.1 Add a CI-method selector to `evaluate_binary_hypothesis` / `evaluate_binary_hypotheses` in [external/contribution-kit/src/contribution/hypothesis.py](external/contribution-kit/src/contribution/hypothesis.py) defaulting to the score/exact pair (Koopman + Baptista-Pike) with a legacy Wald-type option (Katz + Haldane-Anscombe)
- [ ] 3.2 Dispatch to the selected RR and OR functions, keeping point estimates identical across methods and leaving `BinaryHypothesisResult` fields unchanged
- [ ] 3.3 Thread the selector through any estimator/assess call site so `assess()` uses the default methods without requiring caller changes

## 4. Exports and reporting references

- [ ] 4.1 Export `koopman_risk_ratio` and `baptista_pike_odds_ratio` from [external/contribution-kit/src/contribution/__init__.py](external/contribution-kit/src/contribution/__init__.py) and add them to `__all__`
- [ ] 4.2 Update the mismatch-risk reference footnotes in [external/contribution-kit/src/contribution/results.py](external/contribution-kit/src/contribution/results.py) so the RR CI cites Koopman (1984) and the OR CI cites Baptista & Pike (1977), attributing the small-sample recommendation to Fagerland, Lydersen & Laake (2015/2017) (footnotes do not list the fallback methods)
- [ ] 4.3 Update [external/contribution-kit/README.md](external/contribution-kit/README.md) binary-effect-sizes and mismatch-risk sections plus the reference list to present Koopman and Baptista-Pike as the methods (citing Fagerland et al.), and add a single note stating the Katz / Haldane-Anscombe fallbacks exist and how to select them

## 5. Verification

- [ ] 5.1 Run the two new stats test methods (Koopman and Baptista-Pike known-value tests) to confirm they pass
- [ ] 5.2 Run the mismatch-risk / hypothesis test methods that render the markdown table to confirm reports use Koopman and Baptista-Pike and cite them
- [ ] 5.3 Confirm the opt-in fallback selector reproduces the prior Katz + Haldane-Anscombe interval values via a targeted test
