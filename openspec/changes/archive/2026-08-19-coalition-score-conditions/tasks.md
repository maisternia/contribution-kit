## 1. DSL grammar

- [x] 1.1 Accept `coalition_score` calls in `expr.py::_validate_node`, requiring every argument to be a string-literal `ast.Constant` and rejecting non-literals with a message stating that arguments must be string literals
- [x] 1.2 Exclude `coalition_score` from `expr.py::free_variables` so it is never mistaken for a column reference
- [x] 1.3 Add `expr.py::coalition_score_arguments(expression) -> list[tuple[str, ...]]` returning each call's argument tuple in source order, for static collection and scope checks
- [x] 1.4 Resolve `coalition_score` from the row context in `expr.py::_eval_node`; when it is absent, raise a `ValueError` naming the surfaces where it is available rather than a `KeyError`

## 2. Player construction ordering

- [x] 2.1 Move `_formula_features()` and `_build_players()` above `_expand_factorials()` in `Estimator.assess()`, leaving the feature/player/`feature_player` values used by the existing Shapley pass unchanged
- [x] 2.2 Confirm `_build_players` still validates group-name collisions against declared regimes only, so the move introduces no dependency on generated cell names

## 3. Static validation

- [x] 3.1 Collect the distinct coalitions referenced across all declared regime conditions and all factorial axis level conditions, before any row is read
- [x] 3.2 Reject an argument that names no declared player, with an error naming the condition, the argument, and the valid player names
- [x] 3.3 Reject an argument naming a feature that belongs to a group, with an error naming the owning group and directing the author to use it
- [x] 3.4 Reject a call that repeats a player name, naming the duplicate
- [x] 3.5 Reject `coalition_score` in `prediction_features` `actual` and `baseline` expressions, and in `prediction_expr`, `target`, and `prediction`, naming the offending expression and stating where the function is available (the spec-level mismatch predicate is derived as `prediction != target`, so it needs no separate guard)

## 4. Coalition score table

- [x] 4.1 Evaluate each distinct referenced coalition once per row into a table keyed by coalition and row index, reusing `_resolve_coalition_values` and the existing scoring path so table values match the Shapley pass exactly
- [x] 4.2 Bind `coalition_score` as a table lookup in the row contexts built by `_expand_factorials`, `_regime_summary`, and `_regime_risk`
- [x] 4.3 Verify no other `build_row_context` call site gains the binding, so the game-defining expressions stay structurally unable to see it

## 5. CLI surface

- [x] 5.1 Confirm the ad-hoc `contributor` and hypothesis subcommands, which build contexts without a spec, surface the explanatory error from 1.4 for `--mismatch-expr`, `--group-a`, `--group-b`, and `--feature`
- [x] 5.2 Confirm no config parsing change is needed in `cli.py`, since no new config key is introduced

## 6. Example migration

- [x] 6.1 Add a coalition-scored crossing to `examples/continuous_lora/config.json` over the class decision and the bandwidth measurement, with level names distinct from the existing crossing's, leaving the direction crossing and both declared regimes untouched
- [x] 6.2 Add one coalition-scored regime to the same config
- [x] 6.3 Run the example end to end and record the decision crossing's cell counts, mismatch rates, and burden ranking; confirm neither new axis emits a partition warning

## 7. Tests

- [x] 7.1 Unit-test the DSL grammar: literal-argument acceptance, non-literal rejection, `free_variables` exclusion, `coalition_score_arguments` extraction, and the explanatory error when unbound
- [x] 7.2 Unit-test static validation: unknown player, group member, duplicate argument, and each forbidden expression site, asserting the error text names the condition and the valid players
- [x] 7.3 Unit-test semantics on a small fixture: single-player, multi-player, full-coalition equals observed error, and empty-coalition equals zero
- [x] 7.4 Unit-test that a coalition score observed by a condition equals the estimator's own coalition scorer for the same row and coalition
- [x] 7.5 Unit-test the cost bound: a spec with three players and two referenced single-player coalitions resolves exactly those two per row
- [x] 7.6 Unit-test signed versus absolute `score_mode` behaviour at the `> 0` / `< 0` / `!= 0` boundaries
- [x] 7.7 Extend `tests/unit/test_backward_compatibility.py` to pin that the existing fixtures and the direction crossing produce unchanged output with the new crossing present in the same spec
- [x] 7.8 Add a fixture pinning the shipped example's decision-crossing output so the new numbers are regression-protected alongside the existing goldens

## 8. Documentation

- [x] 8.1 Add `coalition_score` to the `README.md` expression reference, listing where it is and is not available
- [x] 8.2 Add a README section explaining `v(S)` versus the Shapley value, the baseline-origin caveat and its link to the `baseline_target_mismatch` warning, and the `score_mode` sign behaviour
- [x] 8.3 Show the example's decision crossing in the README beside the direction crossing, stating that the two answer different questions

## 9. Verification

- [x] 9.1 Run the full `pytest` suite and confirm no pre-existing test changes behaviour
- [x] 9.2 Run `openspec validate --strict coalition-score-conditions`
