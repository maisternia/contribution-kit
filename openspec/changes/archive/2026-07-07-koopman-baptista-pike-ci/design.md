## Context

The contribution-kit computes condition-vs-rest mismatch risk for each error
regime and reports a relative risk (risk ratio) and odds ratio, each with a 95%
confidence interval, in the markdown mismatch-risk table. Today those intervals
come from:

- `katz_risk_ratio` in [external/contribution-kit/src/contribution/stats.py](external/contribution-kit/src/contribution/stats.py) — a log-transform (delta-method) risk-ratio CI that returns `None`/`None` whenever any cell is zero.
- `haldane_anscombe_odds_ratio` in the same file — a `+0.5`-per-cell continuity-corrected Wald odds-ratio CI.

Both are asymptotic Wald-type intervals. On the small, frequently sparse 2×2
tables produced here (single-digit mismatch counts, occasional zero cells) they
under-cover and, for the risk ratio, collapse to `n/a` on any zero cell.

The methodological evidence for switching comes from a peer-reviewed coverage
study: Fagerland, Lydersen & Laake (2015) evaluate interval methods for two
independent binomial proportions and recommend the asymptotic-score (Koopman)
interval for the ratio of proportions over Wald/Katz intervals, and their 2017
contingency-tables text recommends the Baptista-Pike interval for the odds ratio
among exact methods. Both keep closer to nominal coverage on small and sparse
tables. This change makes Koopman and Baptista-Pike the methods the kit uses.
The previous two intervals are retained in the code only as opt-in fallbacks and
are not part of the default output. (The chosen pair also matches GraphPad
Prism's defaults.)

## Goals / Non-Goals

**Goals:**
- Add a Koopman asymptotic-score risk-ratio CI and use it as the risk-ratio CI.
- Add a Baptista-Pike exact odds-ratio CI and use it as the odds-ratio CI.
- Retain Katz and Haldane-Anscombe in the code as opt-in fallbacks, reachable
  through a single option and documented once in the README.
- Keep the point estimates (risk ratio, odds ratio values) unchanged; only the
  interval methods change.
- Update reference footnotes and README to cite the Koopman and Baptista-Pike
  methods.

**Non-Goals:**
- No change to how mismatch counts, rates, or point estimates are derived.
- No new external runtime dependencies. Neither method is available ready-made in
  SciPy/statsmodels (only in R packages such as `ratesci`/`exact2x2`), so SciPy
  would only replace root-finding and the noncentral-hypergeometric pmf (~30–50
  lines) while still requiring the score statistic and interval inversion by hand;
  the kit stays pure Python + stdlib `math` to preserve its zero-dependency
  footprint (tables are tiny, so hand-rolled `math.comb` sums are fast and exact).
- No change to the confidence level: both methods keep the existing 95% default
  (`z = 1.96`).
- No change to legacy `scripts/` analyses.
- No change to dataset or model artifacts, and no regeneration of committed report
  fixtures/tables in this change (they can be refreshed separately).

## Decisions

### Decision: Koopman and Baptista-Pike are the methods; fallbacks are opt-in
The binary-hypothesis evaluation uses Koopman (risk ratio) and Baptista-Pike
(odds ratio) for all reporting output. A single `ci_method` string selector,
default `"score-exact"` (Koopman + Baptista-Pike) with a `"wald"` opt-in that
selects Katz + Haldane-Anscombe, exposes the previous methods for callers who
need to reproduce prior tables. The fallback is surfaced once in the README and
is otherwise not advertised in the default output.

- Alternative considered: removing the previous methods entirely. Rejected so
  prior published tables can still be reproduced on demand, but they are kept out
  of the default surface to avoid presenting them as co-equal choices.
- Alternative considered: separate independent RR-method and OR-method arguments.
  Rejected because it multiplies the option space; the single paired `ci_method`
  flag keeps the common case one flag, while the underlying stats functions remain
  independently callable for advanced use.

### Decision: Koopman relative-risk CI via score-based root finding
Koopman's interval inverts the asymptotic score test for the risk ratio: the
confidence limits are the values of the ratio $\phi$ for which the score
statistic equals the critical value $z^2$. There is no closed form, so the limits
are found by a numeric root-find (bisection) over $\phi$ on each side of the point
estimate, using the standard restricted-MLE expression for the score statistic of
a 2×2 table. This is the "asymptotic score" interval recommended by Fagerland et
al. (2015) and implemented as Prism's "Koopman asymptotic score" default.

- Alternative considered: Miettinen-Nurminen score interval. It is closely
  related and also recommended by Fagerland et al.; we implement Koopman (1984)
  to match the cited primary reference and the common default output.
- Zero-cell handling: unlike Katz, the score interval remains defined for many
  sparse tables, so the RR CI no longer collapses to `n/a` on a single zero cell.

### Decision: Baptista-Pike exact odds-ratio CI
Baptista-Pike (1977, AS 64) gives exact two-sided limits for the odds ratio of a
2×2 table by inverting the conditional (non-central hypergeometric) test: each
limit is the odds-ratio value at which the sum of hypergeometric probabilities of
tables "as or more extreme" equals $\alpha/2$, using the Baptista-Pike ordering.
Implemented with the noncentral hypergeometric distribution evaluated over the
support of `a` given fixed margins, and a numeric root-find for each limit.

- Alternative considered: Fisher (Cornfield) exact interval. Fagerland, Lydersen
  & Laake (2017) recommend Baptista-Pike over Cornfield as typically less
  conservative while retaining exact-style guarantees; we implement Baptista-Pike
  to match that recommendation and the cited primary reference.

### Decision: Point estimates and result dataclasses stay stable
`RiskRatioResult` and `OddsRatioResult` keep their fields. Only which function
fills `ci_low`/`ci_high` changes with the selected method. `RiskRatioResult.ci_*`
stays `float | None` to preserve the sparse-table contract for the fallback Katz
path; the Koopman path fills real bounds wherever it is defined.

## Risks / Trade-offs

- [Numeric root-finding may fail to converge or hit degenerate margins (all-zero row/column, boundary tables)] → Bracket carefully around the point estimate, cap iterations, and fall back to defined boundary limits (0 or +∞) for degenerate tables; add tests for zero-cell and boundary cases.
- [Baptista-Pike exact computation is heavier than a Wald formula] → Tables here are tiny (small margins), so the hypergeometric sums are cheap; acceptable for report generation.
- [Results will differ numerically from previously published tables] → Expected and intended (more accurate small-sample intervals); the previous methods remain reachable as opt-in fallbacks for exact reproduction of prior outputs, and reference footnotes are updated to reflect the methods now used.
- [Implementing exact/score intervals correctly is subtle] → Validate against expected bounds precomputed from established R implementations (`ratesci` for Koopman, `exact2x2` for Baptista-Pike) hard-coded into unit tests for both methods.

## Migration Plan

1. Add the two new functions alongside the existing ones (no removals).
2. Make the binary-evaluation use the score/exact pair; expose the opt-in
   selector for the fallback methods.
3. Update references/README (single mention of the opt-in fallbacks).
4. Reproducing prior tables: pass the fallback selector to restore Katz +
   Haldane-Anscombe output. No rollback of data artifacts is required.

## References

- Koopman, P. A. R. (1984). Confidence intervals for the ratio of two binomial
  proportions. *Biometrics*, 40(2), 513–517.
- Baptista, J., & Pike, M. C. (1977). Algorithm AS 64: Exact two-sided confidence
  limits for the odds ratio in a 2×2 table. *Journal of the Royal Statistical
  Society, Series C (Applied Statistics)*, 26(2), 214–220.
- Fagerland, M. W., Lydersen, S., & Laake, P. (2015). Recommended confidence
  intervals for two independent binomial proportions. *Statistical Methods in
  Medical Research*, 24(2), 224–254.
- Fagerland, M. W., Lydersen, S., & Laake, P. (2017). *Statistical Analysis of
  Contingency Tables*. CRC Press.

## Open Questions

- None blocking. The selector's exact surface (paired string vs. dataclass) is
  finalized in tasks; both satisfy the spec requirement of "methods = Koopman +
  Baptista-Pike, previous methods = opt-in fallback documented once".
