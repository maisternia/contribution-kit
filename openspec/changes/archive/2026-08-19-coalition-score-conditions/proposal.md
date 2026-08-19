## Why

The Shapley game already computes, per row, exactly how much error each player causes in isolation — the characteristic function `v(S)`. Callers writing regime conditions and factorial axis levels cannot see it, so they re-derive it by hand from raw columns, and they usually get a different question than the one they meant to ask.

The continuous-LoRa example shows the cost. Its factorial rows axis splits on `Class BW` alone (`class_ok` / `upscale` / `downscale`), but `class_bw` is not independently actionable: the detector picks BW and SF as one lattice entry, and the geometric regression rescues most BW errors. The 95 rows whose class decision is genuinely unrecoverable scatter 23/42/30 across those three levels, so no level names the defect and no cell ranks a fix. A tolerance chosen by eye (10%) also silently disagrees with the formula's real threshold (`round(2·log2(·))` flips at a 41% ratio), so the axis mislabels rows the model handles correctly. Both problems disappear when the axis asks the question the game already answers.

## What Changes

- Add `coalition_score('<player>', ...)` to the condition DSL. It evaluates `prediction_expr` with the named players held at their `actual` values and every other player at its `baseline`, scores the result against `target` under the spec's `score_mode`, and returns that number — the same `v(S)` the Shapley pass consumes.
- Make it available in **regime conditions** and **factorial axis level conditions**, which are one evaluation path: factorial cells already compile into generated regimes.
- Keep it out of `prediction_features` expressions, `prediction_expr`, `target`, `prediction`, and `mismatch_expr`, which define the game itself. Using it there SHALL fail with an explanatory error rather than a `KeyError`.
- Validate player names, argument literalness, and duplicate arguments at compile time, so a typo names the valid players instead of failing per row.
- Guarantee the players are resolved before any condition is evaluated, including the partition validation inside factorial expansion.
- Extend the continuous-LoRa example **additively**: keep the existing direction crossing, add a decision-based crossing and a coalition-scored regime alongside it. `factorials` is a list, so one report carries both.
- Document the function, its scope, and the `v(S)` vs. Shapley-value distinction in `README.md`.

Not breaking. Every existing condition is a column predicate and keeps its exact meaning; a spec that never writes `coalition_score` produces byte-identical output.

## Capabilities

### New Capabilities
- `coalition-scored-conditions`: exposing the Shapley characteristic function `v(S)` as a DSL function usable in regime and factorial-axis conditions, with its scope restrictions, validation rules, and evaluation-ordering guarantee.

### Modified Capabilities

None. No existing requirement constrains the DSL's function set, the ordering of player construction relative to factorial expansion, or the example's factorial axes; the direction crossing and both existing regimes are retained unchanged, so `factorial-regime-declaration` and `estimator-hypothesis-attribution` keep their current requirements intact.

## Impact

- `src/contribution/expr.py` — recognise `coalition_score` in `_validate_node`, `_eval_node`, and `free_variables`; resolve it from the row context like `col`.
- `src/contribution/estimator.py` — build features and players before `_expand_factorials()`; bind a memoized per-row coalition scorer into the contexts used by `_expand_factorials`, `_regime_summary`, and `_regime_risk`; validate player names in every condition up front.
- `examples/continuous_lora/config.json` — one added crossing, one added regime.
- `README.md` — DSL reference and a worked section.
- No config schema keys added, so `src/contribution/cli.py` parsing is unchanged.
- No result or report schema change; existing JSON/CSV/markdown fields are untouched.
