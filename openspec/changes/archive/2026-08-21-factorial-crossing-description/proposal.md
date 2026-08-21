## Why

A factorial crossing's axis levels are terse by design — `bw_neutral`,
`bw_shifts`, `class_workable`, `class_unworkable` — and that compactness is
worth keeping: the axis maps read as a grid, and the level name is the identity
that composes cell names, points `baseline`, and keys every marginal, contrast,
and burden-ranking record.

What is missing is anywhere to say what those names mean. A crossing can carry a
`label`, but a label is a title, not an explanation. In the shipped example the
second crossing's four levels are all defined by `coalition_score(...)`
comparisons whose meaning is not recoverable from the name, and there is no
field in which to record it. The sibling regime `class_unworkable` is readable
only because a regime may carry a `label` long enough to explain itself.

## What Changes

- A factorial crossing accepts an optional `description` string: prose that
  explains the crossing's levels, written once per crossing rather than once per
  level, so the axis maps stay compact.
- The description is rendered with the crossing's matrix in the markdown report
  and carried in the JSON output.
- `FactorialCrossing` gains the field, so Python callers can declare it too.
- `examples/continuous_lora/config.json` gains a description on both crossings,
  recording what each level of each axis means. Its `class_sf_match` regime also
  moves from the bare-string form to the labelled object form, matching its two
  siblings.
- The governing spec's stale "Unknown crossing key is rejected" scenario is
  corrected: it still names only `rows`, `columns`, and `label` as allowed
  crossing keys, but `baseline` has been allowed since the burden-ranking work,
  and `description` is added here.

Not breaking. `description` is optional, axis declarations are untouched, and a
crossing that declares no description produces byte-identical output.

## Capabilities

### New Capabilities

None. This adds an optional field to an existing declaration surface.

### Modified Capabilities

- `factorial-regime-declaration`: a new requirement governs the optional
  per-crossing `description` and where it is rendered; the inline-axis
  requirement's unknown-crossing-key scenario is corrected to include
  `baseline` and `description`.

## Impact

- `src/contribution/spec.py` — `FactorialCrossing` gains `description`.
- `src/contribution/cli.py` — crossing parsing accepts and validates the key.
- `src/contribution/estimator.py` — the description is carried onto the
  crossing's matrix result.
- `src/contribution/results.py` — the matrix section renders it; the JSON
  payload carries it.
- `examples/continuous_lora/config.json` — descriptions added; its generated
  report gains two prose lines.
- Golden fixtures covering description-free specs must remain byte-identical.
