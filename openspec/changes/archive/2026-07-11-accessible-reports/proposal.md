## Why

The contribution-kit markdown report is a bare stack of tables with machine-style
column names (`mean_abs_shapley`, `net_contribution_share_pct`) and no statement
of what each analysis does or which inputs produced it. Readers who are not
comfortable with statistics cannot tell a Shapley table from a regime table, what
formula generated the numbers, or what the result means. The report needs a
self-explanatory, human-readable presentation layer.

## What Changes

- Give every analysis section in the markdown report a titled heading naming the
  analysis (e.g. "Shapley Value Contributions", "Error Regimes", "Mismatch Risk").
- Add a one-line plain-language description under each section title stating what
  the analysis does and referencing the inputs it used.
- Echo the analysis inputs in the report: the prediction/target formula for the
  Shapley attribution, plus `target_expr`, `prediction_expr`, and `mismatch_expr`,
  so the report is reproducible on its own.
- Rename report table columns to concise, widely-used human-readable terms
  (e.g. `mean_abs_shapley` → "Mean absolute", `total_signed_shapley` → "Total
  signed", `net_contribution_share_pct` → "Net share (%)").
- Add a brief plain-language conclusion sentence under each table summarising the
  headline takeaway (e.g. which feature or regime dominates).
- Carry the spec inputs (`target_expr`, `prediction_expr`, `mismatch_expr`,
  `score_mode`) into `AssessmentResult.metadata` so the report can render them, and
  keep the `contrib report` CLI regeneration path consistent with the new layout.

## Framework Update

- Replace the previous config contract with a non-backward-compatible split:
  `target`, `prediction`, and `prediction_expr`.
- Define regime contribution and mismatch risk from observed values only:
  outcome is computed from `prediction` vs `target` under `score_mode`, and mismatch
  is derived as `prediction != target`.
- Reserve `prediction_expr` exclusively for Shapley decomposition so explanatory
  feature attribution remains formula-driven while regimes/risk stay tied to the
  precomputed observed prediction column.
- Update report wording/inputs to reflect the split and remove dependence on
  `mismatch_expr`.

## Capabilities

### New Capabilities
- `accessible-reports`: Human-readable presentation of contribution-kit markdown
  reports — section titles, plain-language descriptions, echoed analysis inputs,
  renamed columns, and per-table conclusions.

### Modified Capabilities
<!-- No existing requirement changes: the confidence-interval column labels and
     reference footnotes defined by estimator-hypothesis-attribution are preserved. -->

## Impact

- `external/contribution-kit/src/contribution/results.py`: `AssessmentResult.to_markdown()`
  rewritten to emit titles, descriptions, input echoes, renamed columns, and
  conclusions.
- `external/contribution-kit/src/contribution/estimator.py`: `assess()` populates
  `AssessmentResult.metadata` with the spec inputs used to render the report.
- `external/contribution-kit/src/contribution/cli.py`: the `report` command
  regenerates the same accessible layout from `run.json`.
- `external/contribution-kit/src/contribution/spec.py`: schema now requires
  `target`, `prediction`, `prediction_expr` and removes `mismatch_expr`.
- `external/contribution-kit/build/run/report.md` and other generated reports gain
  the new presentation; `contribution.csv` and `run.json` machine schemas are
  unchanged.
