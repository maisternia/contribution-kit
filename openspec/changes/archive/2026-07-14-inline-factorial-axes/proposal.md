# Inline Factorial Axes

## Why

Declaring a factorial today requires two coupled blocks: named axes in
`factors` and name references in `factorials`. For the kit's actual usage —
one crossing per config, axes never reused — the indirection adds schema
weight, two error classes (unknown axis reference, unused factor warning),
and forces readers to jump between blocks to reconstruct a single matrix.
Axis names turn out to be header decoration only: every report table row,
generated cell hypothesis, and contrast is built purely from level names.

## What Changes

- **BREAKING**: Each `factorials` entry declares its axes inline —
  `rows` and `columns` become level-name → condition-string maps instead of
  string references to `factors` axes.
- **BREAKING**: Remove the top-level `factors` block from the JSON/YAML config
  and the `factors` field (and `Factor` reference semantics) from
  `AttributionSpec`. The unknown-axis error and unused-factor warning are
  removed with it.
- Add an optional `label` field to each factorial crossing — human display
  text used as the report matrix header, contrast-section prefix, and
  partition-warning identifier. Absent a label, a positional fallback
  (`Factorial <n>`) is used.
- `run.json` factorial payloads carry the crossing label (or fallback) instead
  of `rows_axis`/`columns_axis` names; `contrib report` regeneration follows.
- Partition validation, cell expansion, generated cell naming
  (`<row_level> & <column_level>`), marginals, and within-stratum contrasts
  are behaviorally unchanged — only how axes are declared and titled changes.
- Update README schema docs and `examples/continuous_lora` configs to the
  inline form.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `factorial-regime-declaration`: axes are declared inline per crossing rather
  than as named `factors` referenced by name; the unknown-axis-reference
  scenario is removed; crossings gain an optional `label` with a positional
  fallback that titles the matrix, contrast sections, and partition warnings.

## Impact

- `external/contribution-kit/src/contribution/spec.py`: `FactorialCrossing`
  gains inline level maps and optional `label`; `Factor` and
  `AttributionSpec.factors` are removed.
- `external/contribution-kit/src/contribution/cli.py`: `_load_spec` parses
  inline axes and `label`; drops `factors` parsing and axis-reference
  validation.
- `external/contribution-kit/src/contribution/estimator.py`: `_validate_spec`
  and `_expand_factorials` read levels from the crossing; partition warnings
  and `_FactorialPlan` identify axes via crossing label + rows/columns role.
- `external/contribution-kit/src/contribution/results.py`:
  `FactorialMatrixResult` keys on crossing label instead of
  `rows_axis`/`columns_axis`; markdown headers render the label.
- Tests: `tests/unit/test_spec.py`, `tests/unit/test_cli.py`,
  `tests/unit/test_estimator.py`, smoke tests, and the ResearchData
  integration tests that consume factorial run payloads.
- Docs/examples: `README.md`, `examples/continuous_lora/config_factorial.json`
  (and `idea.json` as the working draft of the new shape).
- Depends on the in-flight `explicit-prediction-features` change only at the
  level of shared example configs; the schema changes are orthogonal.
