## Why

A baselined crossing with an empty non-baseline cell crashes the run. `_build_burden_rankings` computes the Miettinen–Nurminen risk difference for every non-baseline cell, and `miettinen_nurminen_risk_difference` rejects a zero-row exposed group with `ValueError: Exposed group cannot be empty`. The shipped continuous-LoRa config hits this on the standard evaluation set, where the coalition crossing's `class_unworkable & bw_shifts` cell matches no rows. Empty cells are normal in sparse crossings, and the factorial matrix and contrasts already handle them.

The same loop also scores an empty cell's mismatch rate as 0%, so any baseline with at least one mismatch triggers the baseline-sanity warning, even when every non-empty cell fails more often than the baseline.

## What Changes

- An empty non-baseline cell is left out of the burden ranking. It has no rows to recover and no defined mismatch rate or risk difference.
- Each burden ranking records the names of its empty cells (`empty_cells`, in declaration order). The report lists them in a note under the burden table.
- The baseline-sanity check considers non-empty cells only.
- The empty-baseline error is unchanged.
- **Output schema (additive)**: `burden_rankings[].empty_cells` in `run.json`, defaulting to an empty list when loading older payloads.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `attributable-burden-ranking`: burden is computed per non-empty non-baseline cell, empty cells are recorded and reported, and the baseline-sanity guard ignores empty cells.

## Impact

- **Code**: `src/contribution/estimator.py` (`_build_burden_rankings`), `src/contribution/results.py` (`BurdenRankingResult.empty_cells`, report note), `src/contribution/cli.py` (payload round trip).
- **Tests**: `tests/unit/test_estimator.py` gains empty-cell cases; `tests/unit/test_results.py` covers the note.
- **Bundled example**: adds `examples/continuous_lora/measurements_standard.csv` (the standard evaluation set of the same C18x2 detector) and its run under `runs/standard/`, which needs this fix to complete with the shipped config. The existing `runs/c18x2` and `runs/c9x1` have no empty cells; they are regenerated only to carry the new empty `empty_cells` field.
