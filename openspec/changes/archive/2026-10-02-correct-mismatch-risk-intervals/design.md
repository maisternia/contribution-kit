## Context

`stats.py` provides four mismatch-risk interval routines. Katz RR and Haldane–Anscombe OR agree with R. The two primary methods do not:

- **Koopman RR.** `_rr_score_statistic` computes the restricted MLE `p̃0` correctly (the Miettinen–Nurminen quadratic), with `p̃1 = φ·p̃0`. It then returns `(p̂1 − p̃1)/se(p̃)`. The Koopman / Miettinen–Nurminen score without the `N/(N−1)` factor is `(p̂1 − φ·p̂0)/se(p̃)`. With `p̂0 = 0` the wrong numerator is ≈0 at every φ, so the inversion lands far too low (18 instead of 390).
- **"Baptista–Pike" OR.** The code inverts the two one-sided conditional tails at α/2 each, which is Cornfield's exact conditional central interval. Against a 50-digit `mpmath` evaluation it is accurate to about 1e-5 relative. The bisection stops on an absolute tolerance on the tail probability, which is loose where the tail is flat.
- **Fallbacks.** A finite point estimate with a non-finite or unordered interval falls back to Katz / Haldane–Anscombe, silently. An infinite point estimate returns early and never falls back.
- **Baselines.** The superproject's `effect_size_baselines.json` holds kit output, and its generator cannot run. The superproject spec required those baselines to live outside this repository, so the kit's own test suite never compared itself against anything independent.

Findings from exploration (scratch scripts, not committed):

| Check | Result |
|---|---|
| Koopman vs `riskscoreci`, 12 tables | current code differs on most; corrected statistic equal on all 12 to 4 significant digits |
| Katz fallback over all 3,136 tables with cells 0–7, a>0, c>0 | current code 2,401; corrected 0 |
| Baptista–Pike definition (Baptista & Pike 1977; Fagerland et al. 2017; `contingencytables` source) | `p(θ) = Σ_{x: f(x;θ) ≤ f(a;θ)} f(x;θ)`; mid-p subtracts `f(a;θ)/2`; confidence set `{θ : p(θ) > α}` |
| `22,1,291,12963`, 60-digit evaluation | BP exact 162.5–19,952 (= `exact2x2` minlike); BP mid-p 162.5–10,184; Cornfield 156.8–40,447 (= SciPy, = current kit) |
| BP p-value shape | jumps across α where a support point's probability crosses `f(a;θ)` (here at θ ≈ 162.51), and the mid-p set has a gap above it (p < 0.05 again near θ ≈ 172) |
| R `exact2x2(tsmethod = "central")` vs 50-digit Cornfield | off by up to 6% on small tables (`uniroot` tolerance); reports 2⁵² as an upper bound on extreme tables |
| `contingencytables` 3.1.0 (the Fagerland book's R package) | its "exact" Baptista–Pike and Cornfield functions return the mid-p results, because both files define the same internal `calculate_limit`. It also fails with NA on large n and searches only θ ∈ [1e-5, 1e5] |
| Effect on conclusions, all 52 tables in both example runs | no table changes "CI excludes 1" between Cornfield, BP exact and BP mid-p; median bound difference 2%, maximum 32% (a far bound on a sparse table) |

## Goals / Non-Goals

**Goals:**

- Koopman RR equals `PropCIs::riskscoreci` to a tight relative tolerance on sparse, zero-event, all-event and large-n tables.
- `baptista_pike_odds_ratio` is the Baptista–Pike exact interval, so the manuscripts' prose stays true. Mid-p and Cornfield are available and correctly named.
- A fallback can no longer stand in for a broken primary method unnoticed: provenance is recorded per result and visible in reports, and a test pins the fallback rate on a grid at zero.
- RR and OR point estimates do not depend on any CI-method choice.
- Baselines are independent, regenerable, carry their provenance, and run inside this repository's `pytest`.

**Non-Goals:**

- Changing manuscript prose. Only interval values are updated, in separate superproject commits.
- Changing the legacy convention that blanks the RR CI when group A has zero mismatches, or the convention that reports a zero OR via Haldane–Anscombe.
- Fixing or reporting the `contingencytables` bug upstream. That is the user's call, noted in `tests/reference/README.md`.
- Deciding the fate of the C9x1 example.

## Decisions

### D1. Koopman: fix the numerator and invert the score on log φ

Use `T(φ) = (p̂1 − φ·p̂0) / sqrt(p̃1(1−p̃1)/n1 + φ²·p̃0(1−p̃0)/n0)`, keeping the existing restricted-MLE quadratic, and solve `T(φ) = ±z` directly on `log φ` instead of inverting an `erfc` p-value. This avoids tail underflow at extreme φ. `T` is monotone decreasing in φ, so each bound is a single bracketed root. Zero-event and all-event groups follow from the same statistic, with no special-case branches.

*Alternative considered:* porting `riskscoreci`'s closed-form cubic. Rejected because it carries its own special-case branches and `acos` root picking, and copying the reference would make the baseline non-independent.

### D2. Baptista–Pike exact as the default OR interval, reported as the hull

For observed `a` with conditional support `x ∈ [lo, hi]` and noncentral hypergeometric `f(x; θ)`:

- `p(θ) = Σ f(x;θ)` over `x` with `f(x;θ) ≤ f(a;θ)·(1 + 1e-7)`. This is the relative tie tolerance `exact2x2` and `contingencytables` use. The mid-p variant subtracts `f(a;θ)/2`.
- Confidence set `S = {θ > 0 : p(θ) > α}`. The reported interval is the hull `[inf S, sup S]`, matching `exact2x2` minlike.
- `p` changes form only at breakpoints `θ_x` where `f(x;θ) = f(a;θ)`. These have a closed form: `θ_x = (C(n1,a)·C(n0,m1−a) / (C(n1,x)·C(n0,m1−x)))^{1/(x−a)}`. Between breakpoints the summed set is fixed and `p` is smooth.
- **Algorithm**: compute the breakpoints in log space; evaluate `p` at the breakpoints (both one-sided limits) and on a fine log grid within each segment; bracket every crossing of α; refine each crossing by bisection on `log θ` (relative tolerance 1e-12); and take the outermost crossings. Jumps across α at a breakpoint are resolved to the breakpoint itself (the 162.51 case).
- **Boundaries**: an infinite OR gives `[L, ∞)`, a zero OR gives `[0, U]`, and collapsed support gives `[0, ∞)`, as today.
- **Numerics**: work in log weights (`lgamma`), as `_tail_probability` already does, so n in the tens of thousands is fine.

`baptista_pike_odds_ratio(a, b, c, d, z=1.96, *, mid_p=False)` exposes both variants. `cornfield_exact_odds_ratio` holds the current central algorithm with D4's root-finding.

*Alternatives considered:*
- Mid-p as the default. It is Fagerland's recommended variant, but MethodsX says "Baptista–Pike *exact*" and "reproduce `exact2x2`", and only the exact variant keeps both statements true.
- Keeping Cornfield under the BP name. Rejected: the name would be false.

### D3. One selection option for the odds-ratio interval

Add `or_interval: Literal["baptista-pike", "baptista-pike-midp", "cornfield"] = "baptista-pike"` to `evaluate_binary_hypothesis`, `ContributionEstimator.assess`, and the CLI as `--or-interval`. It applies when `ci_method == "score-exact"`. Under `ci_method == "wald"` it is ignored, and passing a non-default value raises a `ValueError` naming the conflict. The footnote names the method actually used: Baptista & Pike (1977) for both BP variants, adding "mid-p (Lancaster 1961)" for that variant, and Cornfield (1956) for the third option. The default output is textually unchanged apart from the values.

*Alternative considered:* folding these into `ci_method` (`score-exact-midp`, ...). Rejected, because it multiplies combinations with the RR side.

### D4. Root-finding

Both the Cornfield and the Baptista–Pike bounds are solved on `log θ` with a relative tolerance on θ (≤1e-10) instead of an absolute tolerance on the probability.

### D5. Baseline authorities, per method

| Method | Tight authority (asserted at D6 tolerance) | Cross-check (recorded, looser) |
|---|---|---|
| Koopman RR | R `PropCIs::riskscoreci(x1, n1, x2, n2, conf.level = 0.95)` | — |
| BP exact OR | `tests/reference/hp_exact_or.py`: independent 60-digit `mpmath` implementation of D2's definition, written without importing kit code | R `exact2x2(tsmethod = "minlike")` (about 4 significant digits) |
| BP mid-p OR | the same script with `mid_p=True` | `contingencytables::BaptistaPike_midP_CI_2x2` on the small tables where it converges |
| Cornfield OR | the same script, central tails at α/2 | SciPy `odds_ratio(kind = "conditional")` |
| Katz RR | R `epitools::riskratio.wald` | — |
| Haldane–Anscombe OR | R `DescTools::OddsRatio(method = "wald", correction = TRUE)` | — |

The high-precision script is a second, independent implementation, so it is a legitimate authority only because the cross-check column agrees with it. The generator records each cross-check's agreement in the JSON, and the accuracy test asserts that the recorded agreement is within the cross-check tolerance. The JSON gets a top-level `provenance` block (R, Python, package versions, the call per method, timestamp) and a per-case `authority`. A missing block fails the test.

### D6. Tolerances

- Point estimates: `rel_tol = 1e-12`.
- Koopman bounds vs R: `rel_tol = 1e-7`. R's all-event branch iterates with step 1.0001, so those cases may get a documented `rel_tol = 1e-3`.
- Odds-ratio bounds vs the high-precision reference: `rel_tol = 1e-8`.
- Cross-checks, as recorded by the generator: `exact2x2` minlike `rel_tol = 1e-6`; `contingencytables` mid-p `rel_tol = 1e-4` (its `uniroot` stops on an absolute 1e-7); SciPy `rel_tol = 1e-6`. The direct sweep test against `exact2x2` uses `1e-3`.
- Infinite, zero and `None` bounds are asserted structurally.

### D7. Fallback provenance instead of a silent fallback

`RiskRatioResult` and `OddsRatioResult` gain `ci_method: str` (`"koopman"`, `"katz"`, `"baptista-pike"`, `"baptista-pike-midp"`, `"cornfield"`, `"haldane-anscombe"`). The `score-exact` path keeps the automatic fallback as a guard against numerical failure, but stamps the method that actually produced the bounds. `BinaryHypothesisResult` carries `rr_ci_method` / `or_ci_method` into `run.json` (`contribution.csv` holds only feature attributions and is unchanged). `to_markdown()` adds a marker and footnote to fallback rows. A unit test sweeps the 0–7 grid and asserts that no fallback fires for any of the three OR intervals or for Koopman.

### D8. Point estimates computed once, outside the CI branch

`evaluate_binary_hypothesis` takes the RR and OR point estimates from the raw table under every method choice. The zero-OR → Haldane–Anscombe reporting convention applies identically everywhere.

### D9. Where the baselines live

The baselines move to `tests/reference/` in this repository:

- `effect_size_cases.csv`
- `generate_effect_size_baselines.R`, runnable from the repository root, with paths from `commandArgs()`
- `hp_exact_or.py` plus `generate_effect_size_baselines.py`, which merges the R output with the high-precision values and cross-checks
- `effect_size_baselines.json`
- `README.md`, which also records the `contingencytables` 3.1.0 mid-p bug so nobody uses it as an exact-interval authority later

The comparison test goes under `tests/accuracy/` and is collected by the default `pytest` run. The superproject copies and their failing test are removed in a separate, user-approved superproject commit.

### D10. Exact 95% normal quantile as the default z

Every CI routine defaults to `z = 1.96`, while R, SciPy and the high-precision reference use `qnorm(0.975) = 1.959964…`. The difference is about 2e-5 relative on a bound. That is too large for the D6 tolerances, and it can flip a rounded manuscript value (`24.245…` sits on a two-decimal rounding edge). All routines will default to one module constant, `Z_95 = NormalDist().inv_cdf(0.975)`. Callers passing `z` explicitly are unaffected.

## Risks / Trade-offs

- **The hull hides gaps.** The BP confidence set can be non-convex. → Reporting the hull is the convention of `exact2x2`, and it errs wide. The docstring states it.
- **Breakpoint and grid search could miss a crossing inside a segment.** → A dense log grid per segment, plus a test against the independent mpmath reference over the whole case set and a randomized small-table sweep cross-checked against `exact2x2` minlike within its precision.
- **The high-precision reference shares a definition with the kit.** A shared misunderstanding would pass. → Its cross-checks against two unrelated implementations (`exact2x2` minlike for exact, `contingencytables` for mid-p) are recorded and asserted.
- **Manuscript numbers change** (Array v3 under review, geom-v0, MethodsX). → No prose changes. Exact replacement values are listed in the proposal for separate superproject commits. All conclusions stand.
- **`run.json` gains fields.** → Additive only. Golden fixtures that hold CI values are regenerated (none do today).
- **BP exact is slower than Cornfield** (a breakpoint scan instead of two monotone roots). → Support size is at most min(n1, m1). It is fine for the report sizes in use, and the test suite stays under its current runtime budget.

## Migration Plan

1. Land the code, tests, baselines and regenerated examples in this repository, bump the minor version, then push.
2. Bump the superproject gitlink as its own commit (`openspec/GIT_WORKFLOW.md`).
3. With the user's approval, make separate superproject commits: remove the obsolete effect-size baselines and test, then update the interval values in `paper/array-v3` §3, `paper/geom-v0` §3.2 with its `table_sources.md`, and `paper/methodsx` Table 1.

Rollback: revert the commit in this repository and the gitlink bump. No data migration is involved.

## Open Questions

- Should fallback provenance also appear as a Markdown column, or only as a marker and footnote? The default here is marker and footnote.
- Should the `contingencytables` mid-p collision be reported upstream? This is the user's call.
