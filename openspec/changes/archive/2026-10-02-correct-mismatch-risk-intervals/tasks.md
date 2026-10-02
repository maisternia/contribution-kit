## 1. Independent baselines first (red before green)

- [x] 1.1 Create `tests/reference/effect_size_cases.csv` with the 4 legacy and 8 realistic tables from the baselines spec, plus `(91,385,0,11972)`, an all-event table with a non-zero reference (e.g. `(12,0,30,970)`), `(0,1,0,1)` (collapsed support), and small tables where the BP p-value is non-monotone (e.g. `(3,7,8,2)`, `(12,30,4,40)`)
- [x] 1.2 Write `tests/reference/generate_effect_size_baselines.R`: runnable from the repo root, with paths from `commandArgs()` and `conf.level = 0.95` explicit. Emit Koopman (`riskscoreci`), Katz and Haldane–Anscombe values plus the cross-check columns `exact2x2(tsmethod="minlike")` and `exact2x2(tsmethod="central")` to an intermediate JSON, with R and package versions
- [x] 1.3 Write `tests/reference/hp_exact_or.py`: an independent 60-digit `mpmath` implementation of BP exact, BP mid-p (hull of `{θ : p(θ) > α}`, tie tolerance 1e-7) and Cornfield central, importing nothing from `contribution`
- [x] 1.4 Write `tests/reference/generate_effect_size_baselines.py`: merge the R output with the high-precision values. Record the cross-checks: `exact2x2` minlike for BP exact; SciPy `odds_ratio(kind="conditional")` for Cornfield; and `contingencytables::BaptistaPike_midP_CI_2x2` for BP mid-p on the small tables where it converges. Write the `provenance` block and per-case `authority`
- [x] 1.5 Run the generators and commit `tests/reference/effect_size_baselines.json`. Check it reproduces the handoff table (Koopman `22,1,291,12963` → 35.32–49.49; `248,746,0,6002` → 390.1–∞; BP exact `22,1,291,12963` → 162.5–19,952; BP mid-p → 162.51–10,184.32)
- [x] 1.6 Add `tests/reference/README.md`: the files, the regeneration commands, the R and Python packages, why baselines must never be filled from kit output, and the `contingencytables` 3.1.0 caveat (its "exact" BP and Cornfield functions return mid-p results; NA on large n)
- [x] 1.7 Add `tests/accuracy/test_effect_size_baselines.py`: compare every method per case with the D6 tolerances; assert ∞/0/`None` structurally; assert the recorded cross-check agreement; fail on missing provenance or authority. Confirm it is collected by the default `pytest` run and **fails** on the current code

## 2. Koopman risk ratio

- [x] 2.1 Replace the `_rr_score_statistic` numerator with `p̂1 − φ·p̂0` (design D1), keeping the restricted-MLE quadratic
- [x] 2.2 Rework `koopman_risk_ratio` to solve `T(φ) = ±z` on `log φ` with a relative tolerance, deriving the zero-event and zero-exposed cases from the same statistic
- [x] 2.3 Return `ci_method` (`"koopman"` / `"katz"`) on `RiskRatioResult`
- [x] 2.4 All Koopman rows of the accuracy test pass
- [x] 2.5 Make the default `z` of every CI routine (`koopman`, `katz`, `haldane_anscombe`, the odds-ratio intervals, Miettinen–Nurminen, Agresti–Caffo) the exact 95% normal quantile `NormalDist().inv_cdf(0.975)` (1.959964…) instead of `1.96`, via one module constant (design D10)

## 3. Odds-ratio intervals

- [x] 3.1 Move the existing central-tail algorithm to `cornfield_exact_odds_ratio`, with a docstring citing Cornfield (1956), and switch its root-finding to `log θ` with a relative tolerance ≤ 1e-10 (design D4)
- [x] 3.2 Implement `baptista_pike_odds_ratio(a, b, c, d, z=1.96, *, mid_p=False)` per design D2: closed-form breakpoints in log space, evaluation at breakpoint limits and on a per-segment log grid, crossings refined by bisection on `log θ`, outermost crossings as the hull, and the boundary cases (`[L,∞)`, `[0,U]`, collapsed support). Docstring cites Baptista & Pike (1977) AS 115, Fagerland et al. (2017), and Lancaster (1961) for mid-p, and states the hull convention
- [x] 3.3 Return `ci_method` (`"baptista-pike"`, `"baptista-pike-midp"`, `"cornfield"`, `"haldane-anscombe"`) on `OddsRatioResult`. Katz and Haldane–Anscombe set their own labels
- [x] 3.4 Export `cornfield_exact_odds_ratio` from `contribution/__init__.py`
- [x] 3.5 All odds-ratio rows of the accuracy test pass for all three intervals

## 4. Hypothesis layer, estimator and CLI

- [x] 4.1 In `evaluate_binary_hypothesis`, compute the reported RR/OR point estimates from the raw table under every method choice. Keep the zero-OR → Haldane–Anscombe convention identical everywhere
- [x] 4.2 Add `or_interval` (default `"baptista-pike"`) to `evaluate_binary_hypothesis` and `ContributionEstimator.assess`, threaded through the regime, factorial-cell and within-stratum contrast paths. Reject a non-default value combined with `ci_method="wald"`. Record `or_interval` in `run.json` metadata beside `ci_method`
- [x] 4.3 Add `--or-interval {baptista-pike,baptista-pike-midp,cornfield}` to `cli.py` and update the `--ci-method` help text
- [x] 4.4 Add `rr_ci_method` / `or_ci_method` to `BinaryHypothesisResult` and the `results.py` result types, and serialise them into `run.json`
- [x] 4.5 In `to_markdown()`, mark fallback rows with one explanatory footnote. Make the OR footnote name the interval actually used (default text unchanged; mid-p adds Lancaster 1961; Cornfield cites Cornfield 1956)

## 5. Unit tests

- [x] 5.1 Rewrite the `tests/unit/test_stats.py` tests that encode fallback on tables where Koopman is finite (`test_koopman_sparse_finite_cases_*`, `test_sparse_fallback_keeps_point_estimate_*`) to assert the primary method and its labels. Keep a monkeypatched forced-failure test for each fallback path and its label
- [x] 5.2 Grid test: every table with cells 0..7, a>0, c>0 → no fallback for Koopman or for any OR interval
- [x] 5.3 BP tests: a jump-at-breakpoint case (`22,1,291,12963` lower bound), a non-monotone mid-p case where the hull, not the first crossing, is reported, and a randomized small-table sweep cross-checked against committed `exact2x2` minlike values within 1e-3
- [x] 5.4 Extend `tests/unit/test_hypothesis.py`: identical RR/OR point estimates across `score-exact` × each `or_interval` and `wald`, including `(91,385,0,11972)`; the CI-method labels; and the `wald` + non-default `or_interval` validation error
- [x] 5.5 CLI test for `--or-interval`; `to_markdown()` tests for the fallback marker and the per-interval OR footnotes

## 6. Docs and examples

- [x] 6.1 Update `README.md`: the Mismatch-risk bullet, the `stats.py` module line, the single fallback/options section (fallback marker, `*_ci_method` fields, `or_interval`), and the references (fix Baptista & Pike to "Algorithm AS 115"; add Cornfield 1956 and Lancaster 1961)
- [x] 6.2 Regenerate `examples/continuous_lora/runs/c18x2/` and `runs/c9x1/` with the documented commands. Re-check every README number quoted from those runs
- [x] 6.3 Regenerate the golden fixtures in `tests/fixtures/` whose CI values or fields change. Diff them and confirm only CI bounds and the new fields moved
- [x] 6.4 Bump `pyproject.toml` version to 0.3.0

## 7. Verification and hand-off

- [x] 7.1 Run the full `pytest` suite, including `tests/accuracy/`, and keep coverage at the level the `attribution-kit-unit-coverage` spec requires
- [x] 7.2 Re-run `Rscript build/handoff/compare_ci_with_r.R` against the kit on the eight handoff tables and record the agreement in the change notes
- [x] 7.3 Hand the user the superproject follow-ups, each to be approved as its own commit and none needing prose changes: (a) remove `ResearchData/tests/reference/effect_size_*` and the effect-size test in `tests/integration/test_contribution_baseline_accuracy.py`; (b) `paper/array-v3` §3: 24.3–32.4 → 24.2–32.3, 6.1–12.9 → 6.1–12.5, 1.36–3.86 → 1.59–2.25; (c) `paper/geom-v0` §3.2 and `table_sources.md`: 24.26–32.37 → 24.25–32.35, 6.05–12.91 → 6.13–12.52, 1.36–3.86 → 1.59–2.25; (d) `paper/methodsx` Table 1 RR and OR lower bounds from the regenerated run
