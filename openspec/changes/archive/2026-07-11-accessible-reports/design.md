## Context

The contribution-kit renders its markdown report entirely in
`AssessmentResult.to_markdown()` in
[results.py](../../../external/contribution-kit/src/contribution/results.py). The
current output is three untitled tables (Shapley feature attribution, error
regimes, mismatch risk) followed by two summary lines and a references footer.
Column headers are the raw dataclass field names (`mean_abs_shapley`,
`total_signed_shapley`, `net_contribution_share_pct`, `contribution_share_pct`).

The spec inputs that generated the numbers now need to be split by purpose:
`target` and `prediction` for observed outcomes, plus `prediction_expr` for
Shapley-only decomposition and `score_mode` for outcome semantics. These values
must be carried into `AssessmentResult.metadata` so reports can render the exact
analysis contract. Today `metadata` only holds `{"exact", "n_samples", "seed",
"ci_method"}`. The `contrib report` CLI command
regenerates a (currently thinner) report from `run.json` independently.

An existing capability, `estimator-hypothesis-attribution`, already pins two
report facts: the mismatch table effect-size columns are labelled
`risk ratio (95% CI)` / `odds ratio (95% CI)`, and the footer cites Koopman /
Baptista-Pike / Fagerland. Those must be preserved.

## Goals / Non-Goals

**Goals:**
- Make the markdown report self-explanatory for a non-statistician: each analysis
  is titled, described in one plain sentence, and shows the inputs that produced it.
- Rename table columns to concise, widely-used human-readable terms.
- Add a one-line takeaway conclusion under each table.
- Keep the `contrib report` regeneration path visually consistent with `save`.

**Non-Goals:**
- No change to `contribution.csv` or `run.json` machine schemas (column keys,
  field names, ordering stay as-is for downstream consumers).
- No change to the numbers, the statistical methods, or the CI-column labels and
  reference footnotes owned by `estimator-hypothesis-attribution`.
- No new output formats (HTML, PDF) — markdown only.

## Decisions

**1. Carry spec inputs through `metadata`, not a new field.**
`assess()` will add `target`, `prediction`, `prediction_expr`, and
`score_mode` to the existing `metadata` dict. Rationale: `metadata` already flows
into `run.json` and is the natural home for run provenance, so both `to_markdown()`
(via `save`) and the `contrib report` regeneration path read the inputs from one
place. Alternative considered: adding typed fields to `AssessmentResult` — rejected
as a larger schema change for data that is descriptive provenance.

**1a. Remove `mismatch_expr` from the core attribution contract.**
Mismatch risk is derived as `prediction != target`, and regime outcome is always
computed from `prediction` vs `target` under `score_mode`. Rationale: this makes
regime/risk behavior explicit and aligned with precomputed observed predictions,
while leaving `prediction_expr` solely for explanatory Shapley decomposition.

**2. Presentation-only changes live in `to_markdown()`.**
All titles, descriptions, column renames, and conclusions are produced in
`to_markdown()`. The CSV/JSON exporters keep raw field names. Rationale: separates
the human-facing layer from machine schemas; downstream parsers of `run.json` are
unaffected.

**3. Column display names map raw field → human label at render time.**
A small local mapping (e.g. `mean_abs_shapley` → "Mean absolute",
`mean_signed_shapley` → "Mean signed", `total_signed_shapley` → "Total signed",
`net_contribution_share_pct` → "Net share (%)"; regime `mean_contribution` → "Mean
contribution", `total_contribution` → "Total contribution",
`contribution_share_pct` → "Share (%)"). Rationale: keeps naming centralised and
easy to review; no dataclass renames required.

**4. Conclusions are computed from already-available result data.**
Each table's takeaway is derived from the rows the method already holds (e.g. the
top-ranked feature by net share, the highest-share regime, the highest-risk-ratio
hypothesis). Rationale: no extra computation passes; deterministic and testable.

**5. `contrib report` reuses the same rendering.**
The CLI `report` command will reconstruct an `AssessmentResult` (or call shared
rendering helpers) from `run.json` so it emits the identical accessible layout
rather than its own reduced table. Rationale: one source of truth for the report
format.

## Risks / Trade-offs

- [Existing tests assert raw column headers or exact report text] → Update the
  affected assertions in the same change; renames are localized to `to_markdown()`.
- [A caller expects custom mismatch semantics (for example threshold exceedance)]
  → Out of scope for this framework revision; mismatch is intentionally fixed to
  `prediction != target`.
- [Over-wordy report hurts experts skimming for numbers] → Keep descriptions to a
  single line and conclusions to one sentence; tables and numbers stay primary.
- [Conclusion wording could imply causation from a correlational regime] → Phrase
  conclusions as descriptive ("largest share", "highest mismatch risk"), not causal.
