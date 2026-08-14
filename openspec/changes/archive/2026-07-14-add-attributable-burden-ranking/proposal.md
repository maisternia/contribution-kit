# Proposal: add-attributable-burden-ranking

## Why

The factorial matrix, contrasts, and Shapley attribution each answer part of "what drives mismatches", but the actionable question — *what to fix first to improve prediction-vs-target matching* — currently requires manual arithmetic over the report. All required quantities are already computed except a designated reference cell; a ranked attributable-burden table (excess mismatches per cell over a baseline rate, with expected accuracy if eliminated) closes the analysis loop automatically.

## What Changes

- Each factorial crossing accepts an optional `baseline` key naming one cell (`{rows: <level>, columns: <level>}`) as the reference for burden computation.
- When a crossing declares a `baseline`, the system computes per non-baseline cell the excess (recoverable) mismatches `n_cell × (p_cell − p_baseline)`, its share of all observed mismatches, and a cumulative "accuracy if eliminated" trajectory over the ranking (each fixed cell's rows reassigned the baseline rate).
- Each burden row carries a risk-difference confidence interval (`p_cell − p_baseline`) using the Miettinen–Nurminen asymptotic score interval, with an Agresti–Caffo guardrail fallback when the primary interval is non-finite or unordered for a finite point estimate — consistent with the kit's existing small-sample CI policy.
- The report renders a ranked "Attributable burden" table per baselined crossing, and `run.json` carries the corresponding entries.
- Semantic guards:
  - the ranking is rendered only when the crossing's axes passed partition validation with no overlap warnings (gaps in coverage are tolerated but reported alongside);
  - a warning is emitted when the declared baseline cell does not have the lowest mismatch rate in the crossing;
  - the report prints the counterfactual assumption ("recoverable" assumes rows in a fixed regime revert to the baseline rate).
- Crossings without a `baseline` key behave exactly as today; the feature is opt-in and factorial-only (ad-hoc regimes are not ranked — they lack partition guarantees).
- Discoverability: when a run contains a factorial crossing without a `baseline`, the CLI prints a one-line hint to stderr suggesting the key; `report.md` and `run.json` stay byte-identical for baseline-free runs.

Out of scope:

- Automatic baseline selection (lowest-rate cell) — an interpretive choice the caller must make.
- Burden ranking over ad-hoc (non-factorial) hypotheses.
- Cost/effort weighting of interventions; the ranking is by recoverable mismatches only.

## Capabilities

### New Capabilities

- `attributable-burden-ranking`: baseline cell declaration, excess-mismatch computation with risk-difference CIs, ranked report table with cumulative accuracy trajectory, JSON output, and the partition/baseline/counterfactual guards.

### Modified Capabilities

- `factorial-regime-declaration`: the crossing object schema gains the optional `baseline` key (the current requirement rejects unknown keys, so the allowed-key set changes).

## Impact

- `external/contribution-kit/src/contribution/spec.py`: crossing schema (`baseline` field) and validation.
- `external/contribution-kit/src/contribution/cli.py`: config parsing of the `baseline` key.
- `external/contribution-kit/src/contribution/stats.py`: Miettinen–Nurminen risk-difference interval with Agresti–Caffo fallback.
- `external/contribution-kit/src/contribution/estimator.py`: burden computation and guards.
- `external/contribution-kit/src/contribution/results.py`: burden result type, report table, JSON serialization, report reference footnote entries for the new CI methods.
- `external/contribution-kit/README.md`: burden table documentation and new `## References` entries (Miettinen & Nurminen 1985; Agresti & Caffo 2000).
- `external/contribution-kit/examples/continuous_lora/config.json`: declare `baseline` on the existing crossing.
- Backward compatible: baseline-free crossings and factor-free configs produce unchanged output.
