# Implementation notes

## Agreement with R on the handoff tables (task 7.2)

`Rscript build/handoff/compare_ci_with_r.R` against the kit after this change
(95% intervals, 4 significant digits):

| Table | Kit Koopman | R `riskscoreci` | Kit Baptista–Pike | R `exact2x2` minlike |
|---|---|---|---|---|
| 279,100,218,8081 | 24.25–32.35 | 24.25–32.35 | 78.7–135 | 78.7–135 |
| 15,14,482,8167 | 6.128–12.52 | 6.128–12.52 | 8.691–38.44 | 8.691–38.44 |
| 236,737,196,1333 | 1.594–2.246 | 1.594–2.246 | 1.764–2.697 | 1.764–2.696 ¹ |
| 248,746,0,6002 | 390.1–∞ | 390.1–∞ | 519.1–∞ | 519.1–∞ |
| 214,1348,0,6002 | 214.2–∞ | 214.2–∞ | 248–∞ | 248–∞ |
| 9,0,0,6002 | 1563–∞ | 1563–∞ | 8098–∞ | 8098–∞ |
| 26,85,0,6002 | 366.2–∞ | 366.2–∞ | 457–∞ | 457–∞ |
| 22,1,291,12963 | 35.32–49.49 | 35.32–49.49 | 162.5–19,952 | 162.5–19,952 |

¹ The handoff script runs `exact2x2` at its default `tol = 1e-5`; at
`tol = 1e-10` R gives 2.696528, which the kit matches (2.696527…).

The Cornfield option differs from R `exact2x2(tsmethod = "central")` exactly
where that R call is inaccurate (for example 6,519 vs R's 4,201 on `9,0,0,6002`,
and 40,447 vs 4.5e15 on `22,1,291,12963`); it matches SciPy and the 60-digit
reference. See `tests/reference/README.md`.

## Effect on the bundled runs (task 6.2)

Point estimates, Shapley shares and burden rankings are unchanged; only interval
bounds moved. No interval in either run used a fallback. Out of 71 intervals per
run, two change whether they exclude 1, both now agreeing with R:

- `runs/c18x2`, within-stratum contrast *Class decision × BW measurement,
  columns=bw_shifts, class_workable vs class_unworkable*: RR 2.06, CI 0.96–4.41
  → 1.09–4.65.
- `runs/c9x1`, regime `class_sf_match`: RR CI 0.75–1.07 → 0.81–0.94.

Neither appears in the manuscript paragraphs checked (Array v3 §3, geom-v0
§3.2, MethodsX Table 1).

## Decisions taken during implementation

- **Default z** (design D10, task 2.5): every interval now uses
  `NormalDist().inv_cdf(0.975)` instead of 1.96, so the kit reproduces R to the
  last digit. Risk-difference intervals move only in the fourth decimal; the
  README burden table (three decimals) is unchanged.
- **Haldane–Anscombe authority**: `DescTools::OddsRatio(correction = TRUE)` adds
  0.5 only when a cell is zero, so the baseline uses `OddsRatio(tab + 0.5)`, which
  matches the kit's and the manuscripts' definition (0.5 added to every cell).
- **Baptista–Pike search**: the p-value is bounded by (support + 1) × either
  one-sided tail, which gives a window that provably contains the confidence
  set; the scan walks inward from each window edge and stops at the first
  accepted point, so only the neighbourhood of each bound is evaluated.
- **`--or-interval`** is offered on `contrib run` as well as `contrib hypothesis`,
  so a full report can use the mid-p or Cornfield interval.
- The report footnote now names the methods actually used, including the Katz /
  Haldane–Anscombe citations under `ci_method="wald"` (previously it always
  cited Koopman and Baptista–Pike).

## Superproject follow-ups (not done here; each its own user-approved commit)

1. Remove `ResearchData/tests/reference/effect_size_{cases.csv,baselines.json}`,
   `generate_effect_size_baselines.R`, and the effect-size test in
   `tests/integration/test_contribution_baseline_accuracy.py` (failing since
   2026-07-08). Keep the Shapley baselines.
2. Regenerate the preserved grouped runs under
   `data/models/paper_runs/infer/contribution/grouped/` (they were byte-identical
   to `examples/continuous_lora/runs/` before this change).
3. `paper/array-v3` §3: 24.3–32.4 → 24.2–32.3; 6.1–12.9 → 6.1–12.5;
   1.36–3.86 → 1.59–2.25 (author notes: `array_review_details.txt:64`).
4. `paper/geom-v0` §3.2: 24.26–32.37 → 24.25–32.35; 6.05–12.91 → 6.13–12.52;
   1.36–3.86 → 1.59–2.25 (author notes: `array_review_details.txt:87`).
5. `paper/methodsx` Table 1: RR ≥ 18.0 / 11.5 / 351.4 / 64.7 → 390.1 / 214.2 /
   1,563 / 366.2; OR ≥ 535 / 256 / 6,519 / 449 → 519 / 248 / 8,098 / 457.
6. Bump the superproject gitlink after this repository is pushed.
