# Effect-size reference baselines

Independent reference values for the kit's risk-ratio and odds-ratio intervals,
checked by `tests/accuracy/test_effect_size_baselines.py`. Running the tests
needs only the committed JSON; regenerating it needs R and a few Python
libraries.

| File | What it is |
|---|---|
| `effect_size_cases.csv` | The 2×2 tables `(a, b, c, d)` = (group A mismatches, group A matches, group B mismatches, group B matches), grouped as `legacy`, `realistic` (tables reported from the bundled example and the manuscripts), `edge`, and a seeded `sweep` of small tables. |
| `generate_effect_size_baselines.R` | R reference values: Koopman, Katz, Haldane–Anscombe, plus the `exact2x2` and `contingencytables` cross-checks. Writes `r_effect_size_values.json`. |
| `hp_exact_or.py` | Independent 60-digit (`mpmath`) implementation of the Baptista–Pike exact, Baptista–Pike mid-p and Cornfield exact odds-ratio intervals. It imports nothing from the kit, and finds interval ends by brute force rather than by the kit's breakpoint walk. |
| `generate_effect_size_baselines.py` | Merges both sources and records each cross-check's agreement. Writes `effect_size_baselines.json`, and exits non-zero if a cross-check is outside its tolerance. |
| `effect_size_baselines.json` | The committed baselines, with a `provenance` block (tool versions, the exact call per method, timestamp) and an `authority` for every value. |

## Regenerating

From the repository root:

```bash
Rscript tests/reference/generate_effect_size_baselines.R
python tests/reference/generate_effect_size_baselines.py
```

R packages: `PropCIs`, `exact2x2`, `epitools`, `DescTools`, `contingencytables`, `jsonlite`.
Python: `mpmath`, `numpy`, `scipy`.

## Authorities

| Kit function | Authority | Cross-check |
|---|---|---|
| `koopman_risk_ratio` | R `PropCIs::riskscoreci` | — |
| `katz_risk_ratio` | R `epitools::riskratio.wald` | — |
| `haldane_anscombe_odds_ratio` | R `DescTools::OddsRatio(tab + 0.5, method = "wald")` | — |
| `baptista_pike_odds_ratio` | `hp_exact_or.py` | R `exact2x2(tsmethod = "minlike")` |
| `baptista_pike_odds_ratio(mid_p=True)` | `hp_exact_or.py` | R `contingencytables::BaptistaPike_midP_CI_2x2` |
| `cornfield_exact_odds_ratio` | `hp_exact_or.py` | SciPy `odds_ratio(kind = "conditional")` |

The exact odds-ratio intervals use a high-precision reference rather than R
because no R implementation is accurate enough on these tables.
`exact2x2(tsmethod = "central")` stops `uniroot` early (6% off on small tables)
and reports 2⁵² as the upper bound of `22,1,291,12963`. `exact2x2` minlike
reports about ten significant digits, which is good for a cross-check but not
for a 1e-8 tolerance.

The Haldane–Anscombe interval adds 0.5 to every cell, as the kit and the
manuscripts define it. `DescTools::OddsRatio(correction = TRUE)` adds it only
when a cell is zero, so it is not used.

## Rules

- **Never fill a baseline from kit output.** The superproject's earlier
  `effect_size_baselines.json` was the kit's own output with an R generator that
  could not run. It hid a wrong Koopman statistic and a mislabelled odds-ratio
  interval for months. Every value here must come from R or `hp_exact_or.py`,
  and the accuracy test refuses a file without provenance.
- Interval conventions: 95% intervals use the exact normal quantile
  (`qnorm(0.975)`). Exact intervals are reported as the hull of the
  confidence set; `set_has_gaps` marks the sets that are not intervals (only
  mid-p sets on these tables).

## Known problems in other implementations

- **`contingencytables` 3.1.0** (the R package accompanying Fagerland, Lydersen
  & Laake 2017): `BaptistaPike_exact_conditional_CI_2x2` and
  `Cornfield_exact_conditional_CI_2x2` return the **mid-p** intervals, because
  the exact and mid-p source files each define an internal `calculate_limit`
  and the mid-p one wins. Only the mid-p function is used here. It also returns
  NA on large tables (`choose()` overflow; it searches θ ∈ [1e-5, 1e5] only), and
  on a mid-p set with gaps `uniroot` can return an inner end instead of the
  hull's. Those cross-checks are recorded as `skipped` with the reason.
- **`PropCIs::riskscoreci`** with integer counts overflows R's 32-bit integers
  on large tables and silently returns NA. The generator converts counts to
  doubles. When a group has every row mismatched, it uses an iterative branch
  with step 1.0001, which is accurate only to about 1e-4.
