## Why

The mismatch-risk intervals the kit reports do not reproduce independent implementations, and the manuscripts already print some of the wrong numbers (see `build/handoff/koopman-bp-ci.md`). The defects date from v0.2.0. They surfaced only now because the realistic tables from the rebased example were checked against R by hand, and because the baselines that should have caught them were never independent.

- **Koopman RR is computed from the wrong score statistic.** `_rr_score_statistic` uses the numerator `p̂1 − p̃1`, where Koopman's score is `p̂1 − φ·p̂0`. With the corrected numerator the kit matches `PropCIs::riskscoreci` on all 12 tables tried. With the current one, intervals are off by up to 30% on large tables and by 10–100× when the reference group has zero events.
- **The Katz fallback hid the bug.** Across all 3,136 tables with cells 0–7 and events in both groups, the current Koopman inversion fails on 2,401 (77%), and Katz silently stands in for it. With the corrected statistic the fallback fires on none of them. Zero-event rows (RR = ∞) never reached the fallback, so their wrong lower bounds went straight into the reports.
- **`baptista_pike_odds_ratio` computes the Cornfield exact conditional (central) interval, not Baptista–Pike.** Baptista–Pike inverts the minimum-likelihood conditional p-value, the sum of the conditional probabilities of all tables no more likely than the observed one. This is the interval R reports as `exact2x2(tsmethod = "minlike")`.
- **The "R baselines" were never produced by R.** `ResearchData/tests/reference/effect_size_baselines.json` holds the kit's own output. The committed generator cannot run, because it omits `conf.level` and calls `sys.frame(1)` under `Rscript`. Real R output differs on 3 of the 4 cases. The superproject comparison test has been failing since the Katz fallback landed, and no one noticed because it lives outside this repository's test run.
- **`--ci-method wald` changes the odds-ratio point estimate** (the Haldane–Anscombe-corrected 5,683 instead of ∞). This violates the existing scenario "Point estimates are independent of CI method".

The manuscripts (Array v3 under review, geom-v0, MethodsX) describe the methods as "Koopman" and "Baptista–Pike". This change makes the kit implement exactly those methods under those names, so the manuscript prose stays correct. Only printed interval values change.

## What Changes

- Correct the Koopman score statistic so that `koopman_risk_ratio` reproduces `PropCIs::riskscoreci`, including zero-event groups, all-event groups and large tables.
- Make `baptista_pike_odds_ratio` compute the Baptista–Pike exact conditional interval (Baptista & Pike 1977, Algorithm AS 115). The confidence set is reported as its hull, because the Baptista–Pike p-value function is discontinuous and not monotone.
- Add two opt-in odds-ratio intervals beside the default: the **Baptista–Pike mid-p** interval, and the **Cornfield exact conditional** interval, which is the current algorithm with tighter root-finding, kept under its correct name `cornfield_exact_odds_ratio`. Selection goes through a new `or_interval` option on `assess()`, `evaluate_binary_hypothesis()` and the CLI (`--or-interval`). It defaults to `baptista-pike` and applies only to `ci_method="score-exact"`.
- Keep the automatic Katz / Haldane–Anscombe guardrail only as a numerical-failure guard, and make it visible. Each result records which CI method produced its bounds, and the Markdown report marks fallback rows. A fallback never passes as primary-method output.
- **Output schema (additive)**: binary-hypothesis results and `run.json` gain `rr_ci_method` / `or_ci_method` (`contribution.csv` is the feature table and carries no mismatch-risk fields).
- Fix `evaluate_binary_hypothesis` so that the reported RR and OR point estimates are identical under every CI-method choice.
- Move the effect-size baselines into this repository: a generator that runs under `Rscript`, an independent high-precision reference for the exact odds-ratio intervals, committed JSON carrying the tool and package versions, and a comparison test. Cover at least the eight realistic tables from the handoff plus the edge cases, at tight documented tolerances.
- Regenerate `examples/continuous_lora/runs/{c18x2,c9x1}/` and every golden fixture whose CI values change. Fix the README's Baptista & Pike reference (it says Algorithm AS 64; the paper is AS 115).

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `estimator-hypothesis-attribution`: the primary OR interval becomes the actual Baptista–Pike exact interval, with Baptista–Pike mid-p and Cornfield exact selectable. The Koopman statistic is pinned. The automatic fallback is restated as a numerical guard that is recorded per result and flagged in reports, and the "Sparse finite-point tables" scenario now requires the primary method, not the fallback, to deliver finite ordered intervals. Point-estimate independence covers the odds ratio explicitly.
- `attribution-kit-statistical-baselines`: effect-size baselines, their generators and the comparison test move into `contribution-kit` (replacing "Integration tests reside in the parent repository" for effect sizes). Baselines must come from a runnable generator that records its provenance in the baseline file. Coverage extends to realistic large-n, sparse and zero-event tables. The authority is named per method, with an independent high-precision reference for the exact odds-ratio intervals.

## Impact

- **Code**: `src/contribution/stats.py` (Koopman statistic, Baptista–Pike exact and mid-p, Cornfield rename of the existing algorithm, root-finding), `hypothesis.py` (point estimates, `or_interval`, CI-method provenance), `estimator.py` and `cli.py` (the `or_interval` / `--or-interval` plumbing and help text), `results.py` (fallback marking, new fields, footnotes for the non-default OR intervals), `__init__.py` (exports), `README.md`.
- **Tests**: `tests/unit/test_stats.py`, `test_hypothesis.py`, `test_cli.py` and `test_results.py` change. Tests that asserted fallback behaviour on tables where Koopman is actually finite get rewritten. New `tests/reference/` and `tests/accuracy/`. Golden fixtures under `tests/fixtures/` are regenerated.
- **Bundled example**: both runs under `examples/continuous_lora/runs/` are regenerated, and README figures quoted from them are re-checked.
- **Dependencies**: regenerating the baselines needs R (`PropCIs`, `exact2x2`, `epitools`, `DescTools`, `jsonlite`) and Python `mpmath` and `scipy`. Running the tests stays offline and R-free. `mpmath` is a test-time dependency only if the accuracy test imports it. The design keeps it generator-only.
- **Manuscripts (superproject; separate user-approved commits, no prose changes needed)**:
  - `paper/array-v3` §3 (under review): "24.3–32.4" → "24.2–32.3", "6.1–12.9" → "6.1–12.5", "1.36–3.86" → "1.59–2.25".
  - `paper/geom-v0` §3.2 and `table_sources.md`: "24.26–32.37" → "24.25–32.35", "6.05–12.91" → "6.13–12.52", "1.36–3.86" → "1.59–2.25".
  - `paper/methodsx` Table 1: the RR and OR lower bounds change (e.g. RR 18.0 → 390.1). Its Method-validation sentences become true as written.
  - Every conclusion stands: each interval still excludes 1.
- **Superproject tests**: remove the obsolete effect-size baselines and comparison test from `ResearchData/tests/{reference,integration}/`. The Shapley baselines stay.
- **Out of scope**: the C9x1 example's status, and the legacy convention that blanks the RR CI when group A has zero mismatches.
