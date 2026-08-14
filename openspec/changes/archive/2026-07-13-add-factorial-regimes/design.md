# Design: add-factorial-regimes

## Context

contribution-kit accepts one flat `hypotheses` list. Each hypothesis carries a boolean `condition` DSL string; `assess()` privately routes top-level equalities to Shapley feature attribution and everything else to regime analysis (share vs total observed contribution + mismatch risk vs rest). Factorial designs — crossing a class-BW axis with a measured-BW axis, as in the `continuous_lora` BW-matrix example — currently require hand-writing every cell as a composite condition. This duplicates threshold expressions, gives no partition guarantee, renders as a flat regime list rather than a matrix, and cannot compare two cells against each other (group B is always "rest").

Key existing structures:

- `spec.py`: `Hypothesis` (name, label, condition), `AttributionSpec` (target, prediction, prediction_expr, hypotheses, score_mode, scope).
- `estimator.py`: `Estimator.assess()` routes hypotheses, computes `RegimeSummary` per regime and `BinaryHypothesisResult` (Koopman RR CI, Baptista-Pike OR CI, guardrail fallbacks) via `_regime_risk` with group B = complement.
- `results.py`: `AssessmentResult` with `regime_summaries`, `binary_results`, `to_markdown()`, `to_json()`, `save()`.
- `cli.py`: `_load_spec` parses the config JSON into `AttributionSpec`.

## Goals / Non-Goals

**Goals:**

- Declare each factor level condition exactly once; cells derived, never hand-written.
- Keep the flat `hypotheses` list and its automatic equality→Shapley routing untouched.
- Generated cells reuse the existing regime/risk machinery without modification.
- Detect and warn on non-partition axes (overlap / non-exhaustive) against the loaded data.
- Render factorial matrices with marginals in `report.md`; include cells and contrasts in `run.json`.
- Provide within-stratum sibling-cell contrasts with the existing Koopman/Baptista-Pike CI machinery.

**Non-Goals:**

- No `params`/constants block (deferred, independent).
- No renaming of `hypotheses`, no removal of the equality-routing rule.
- No 3+-axis crossings (two-axis `rows × columns` only, but multiple factorials per config).
- No interaction significance testing (ratio-of-RR homogeneity tests); contrasts only.
- No changes to Shapley computation.

## Decisions

### D1: Factors as named axes of named level conditions

`factors` is a mapping `axis_name -> {level_name -> condition}`. In Python, a new `Factor` dataclass (name, levels: ordered mapping) on `AttributionSpec.factors`; in JSON, a plain object preserving insertion order for row/column ordering.

*Alternative considered*: flat level list with an `axis` tag per hypothesis — rejected: keeps duplication pressure and makes axis ordering/rendering ambiguous.

### D2: Factorials reference axes by name; expansion generates regime hypotheses

`factorials` is a list of `{rows: axis_name, columns: axis_name}`. At `assess()` time (before routing), each crossing expands into one generated `Hypothesis` per cell with `condition = "(<row_cond>) and (<col_cond>)"` and `name = "<row_level> & <col_level>"`. Generated hypotheses are appended to the effective hypothesis list and flow through `_regime_summary` / `_regime_risk` unchanged. Cell conditions are conjunctions of non-equality conditions, so the routing rule classifies every generated cell as a regime — the equality→feature rule never sees a generated cell as a feature.

*Alternative considered*: a separate cell-evaluation path bypassing `Hypothesis` — rejected: duplicates regime machinery and breaks the "hypotheses are the only analysis unit" invariant.

### D3: Name collisions are errors

If a generated cell name collides with a declared hypothesis name (or another generated name), `assess()` raises a spec validation error. Silent override would make reports ambiguous.

### D4: Partition validation warns, does not fail

Per axis, evaluate all level conditions over the data rows once: if any row matches ≥2 levels (overlap) or 0 levels (gap), collect counts and emit a warning (Python `warnings.warn` + a `partition_warnings` entry in `run.json` metadata and a note in the report). Not an error: exploratory overlapping axes remain legitimate; only the matrix accounting interpretation degrades, and the warning states that.

*Alternative considered*: hard error — rejected: contradicts the kit's exploratory-first philosophy and would forbid intentionally overlapping axes.

### D5: Matrix rendering with marginals

`to_markdown()` gains a "Factorial Matrices" section: one table per factorial, rows = row-axis levels, columns = column-axis levels, each cell showing count, mismatch rate, and risk ratio vs rest (compact `rate% (n, RR x.x)` form); plus a row-marginal column and column-marginal row computed as unions of cells (union counts/mismatches evaluated directly, not summed, so overlap cannot double-count). Existing flat regime and risk tables continue to list generated cells so accessible-reports guarantees hold.

### D6: Within-stratum contrasts via generalized `_regime_risk`

`_regime_risk` (or a sibling helper) is generalized to accept an explicit group-B row mask instead of always using the complement. For each factorial, for each stratum (each row-axis level and each column-axis level), every ordered pair of sibling cells... reduced to: each pair of distinct levels of the crossed axis within that stratum produces one 2×2 contrast (group A = cell, group B = sibling cell) with the same Koopman/Baptista-Pike + guardrail logic. Results go to a new `contrast_results` list (`stratum`, `level_a`, `level_b`, counts, RR/OR + CIs) in `run.json` and a "Within-stratum contrasts" report table. For axes with >2 levels, all unordered level pairs are reported.

*Alternative considered*: only contrasts against a designated baseline level — rejected for now: requires new config vocabulary; all-pairs is small for realistic axis sizes (≤4 levels).

### D7: Config surface

`cli._load_spec` parses optional top-level `factors` and `factorials` keys. Unknown axis references, empty axes, and axes used in no factorial raise clear config errors (the last one a warning). Python API mirrors JSON: `AttributionSpec(factors=..., factorials=...)`.

### D8: Example migration

`examples/continuous_lora/config_bw_matrix.json` is rewritten with `factors` (class_axis: class_ok/upscale/downscale; measured_axis: measured_ok/measured_off) and one factorial, deleting the six hand-written cells; the three equality hypotheses stay in `hypotheses`. The stale hand-edited `"factorials"` sketch block currently in that file is replaced by the real schema. `config.json` and `config_factorial.json` remain untouched as flat-list examples/regression fixtures.

## Risks / Trade-offs

- [Generated names differ from prior hand-written cells (e.g. missing "(baseline)" suffix)] → labels: an optional per-level `label` is not introduced; cell labels are composed from level names only. Report wording stays neutral; domain labels live in the config description.
- [Partition validation cost on large CSVs] → level conditions are evaluated once per row per axis and reused for cell membership; no extra passes.
- [All-pairs contrasts can produce many rows for wide axes] → realistic axes are 2–4 levels; report groups contrasts by stratum; no cap implemented.
- [Backward-compat drift in outputs for factor-free configs] → factorial sections render only when factorials exist; add a regression check that a factor-free run's `report.md`/`run.json` are unchanged.
- [Sparse cells (e.g. n=37) give wide Baptista-Pike CIs] → existing guardrail fallbacks already handle degenerate tables; contrasts inherit them.

## Open Questions

- None blocking. `params` block and >2-axis crossings deliberately deferred.
