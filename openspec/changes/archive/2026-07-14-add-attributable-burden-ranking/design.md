# Design: add-attributable-burden-ranking

## Context

The factorial machinery (inline `rows`/`columns` axes, generated cell regimes, partition validation, matrix rendering, within-stratum contrasts) landed via the 2026-07-13/14 changes. Reports now show per-cell counts, mismatch rates, and RR/OR effect sizes, but no synthesis that ranks causes by how many mismatches fixing them would recover. The prioritization arithmetic was validated manually on the `continuous_lora` example (meas_log run: 313 mismatches; `class_ok & measured_off` recoverable ≈ 165, `upscale & measured_ok` ≈ 78).

Relevant internals:

- `spec.py`: `FactorialCrossing` (label, rows, columns mappings).
- `estimator.py`: cell expansion, partition validation, `_regime_risk` generalized for explicit group-B masks (contrasts).
- `stats.py`: Koopman/Baptista-Pike primaries with Katz/Haldane-Anscombe guardrails.
- `results.py`: matrix + contrast rendering, `run.json` serialization.

## Goals / Non-Goals

**Goals:**

- Opt-in per-crossing `baseline` cell; ranked attributable-burden table computed from existing per-cell counts.
- Risk-difference CIs consistent with the kit's small-sample method policy.
- Guards that make the table statistically honest (partition gate, baseline sanity, counterfactual caveat).
- No behavior change without `baseline`.

**Non-Goals:**

- Auto-selecting the baseline; ranking ad-hoc regimes; multi-crossing combined rankings; intervention cost modeling.

## Decisions

### D1: Baseline is declared per crossing as a cell reference

`"baseline": {"rows": "<row_level>", "columns": "<col_level>"}` on the crossing object. Both levels must exist on their axes; otherwise a configuration error names the missing level. If the baseline cell matches zero rows at assessment time, the run fails with an error naming the crossing (an undefined `p0` makes every burden number meaningless); a small-but-nonempty baseline is allowed — its uncertainty is conveyed by the risk-difference CIs, with no minimum-n threshold. A cell (not a whole row/column stratum) is the reference because the burden question is "versus fully-healthy operation", which is a single cell in a well-designed crossing.

*Alternative considered*: baseline as a hypothesis name string (`"class_ok & measured_ok"`) — rejected: couples config text to the generated-name convention; the structured form survives level renames mechanically.

### D2: Burden math

For baseline rate `p0 = m0/n0` and cell `(n_i, m_i, p_i)`, excess mismatches `e_i = n_i * (p_i - p0)` (may be negative; such cells rank last and render with a dash in the recoverable column). Share = `e_i / M` where `M` = total observed mismatches over all rows. Ties in `e_i` break by declaration order (rows axis first, then columns axis), keeping the ranking deterministic and reproducible from the config. Cumulative accuracy trajectory: starting from observed accuracy, after "fixing" each ranked cell replace its mismatches with `n_i * p0` and recompute; report per row. The trajectory denominator is **all dataset rows** — coverage-gap rows keep their observed outcomes — so the figures stay comparable to the headline observed accuracy. Total-row context (`M`, observed accuracy, ceiling accuracy when all non-baseline cells are fixed) is included under the table.

### D3: Risk-difference CI methods

Primary: Miettinen–Nurminen asymptotic score interval for `p_i - p0` (the Fagerland, Lydersen & Laake 2015 recommendation for the difference of two independent proportions, matching the kit's citation policy). Guardrail: Agresti–Caffo add-2 Wald interval, applied per result only when the primary is non-finite/unordered for a finite point estimate — mirroring the existing Koopman→Katz / Baptista-Pike→Haldane-Anscombe pattern. The `--ci-method wald` opt-in stays scoped to RR/OR as documented; the risk-difference method is always Miettinen–Nurminen with the Agresti–Caffo guardrail and is not switched by the flag.

The two new references join every citation surface the kit maintains:

- `stats.py` docstring `Reference:` blocks and inline `@cite:` comments (same style as `katz_risk_ratio` / `haldane_anscombe_odds_ratio`);
- the `report.md` footnote block in `results.py` (rendered only when a burden table is present);
- the README `## References` section (new anchors `ref-miettinen85`, `ref-agresti00`) with bracketed inline citations where the burden table is documented.

Full citations:

- Miettinen, O., & Nurminen, M. (1985). Comparative analysis of two rates. *Statistics in Medicine*, 4(2), 213–226.
- Agresti, A., & Caffo, B. (2000). Simple and effective confidence intervals for proportions and differences of proportions result from adding two successes and two failures. *The American Statistician*, 54(4), 280–288.
- Fagerland, M. W., Lydersen, S., & Laake, P. (2015). Recommended confidence intervals for two independent binomial proportions. *Statistical Methods in Medical Research*, 24(2), 224–254. (already cited by the kit; extends to the risk-difference recommendation)

### D4: Guards

1. **Partition gate**: the ranking renders only if the crossing produced no *overlap* partition warnings (overlap double-counts excess). Coverage *gaps* do not block the table but are noted next to it ("N rows outside all cells excluded from ranking"). Rationale: overlap corrupts the arithmetic; gaps merely shrink its domain.
2. **Baseline sanity**: if any cell has a mismatch rate strictly below the baseline's, emit a warning (report note + `run.json` entry). Not an error — a caller may deliberately baseline the *intended* healthy cell.
3. **Counterfactual caveat**: a fixed sentence rendered under every burden table stating the revert-to-baseline assumption.

### D5: Rendering and serialization

New report section "Attributable burden" per baselined crossing, titled by the crossing label, columns: rank, cell, n, mismatch rate, baseline rate, recoverable mismatches, share of all mismatches (%), risk difference (95% CI), accuracy if eliminated (cumulative). The table follows the accessible-reports conventions: plain-language column labels, CI cells formatted as `value (low to high)`, and the footnote style of the existing effect-size tables. `run.json` gains `burden_rankings` (crossing label, baseline cell, per-cell entries, guards' outcomes). Baseline-free crossings serialize nothing new.

### D6: Placement in the pipeline

Burden computation runs after cell regime summaries and partition validation inside `assess()`, reusing cell membership masks already evaluated for the matrix — no extra data passes.

### D7: Discoverability hint is CLI-only

When a run contains at least one factorial crossing without a `baseline`, the CLI prints one line to stderr (e.g. `hint: crossing "<label>" has no baseline — declare one to get an attributable-burden ranking`). The hint never enters `report.md` or `run.json`, preserving the byte-identical guarantee for baseline-free outputs while making the feature self-documenting at the point of use.

*Alternative considered*: a note under the matrix in `report.md` — rejected: breaks the byte-identical regression guarantee and perturbs existing report snapshots for a purely advisory message.

## Risks / Trade-offs

- [Negative excess for cells better than baseline] → rendered as non-recoverable (dash), ranked last, documented; avoids implying a fix could *create* mismatches.
- [Caller baselines a mid-rate cell, inflating every excess] → D4 baseline-sanity warning.
- [Cumulative accuracy implies independence of fixes] → cells are disjoint under the partition gate, so reassignment is additive by construction; the caveat sentence covers the causal (not statistical) assumption.
- [New CI method grows stats.py surface] → MN and AC are small closed-form/score computations with the same structure as existing methods; reuse the guardrail dispatch pattern.

## Open Questions

- None blocking.
