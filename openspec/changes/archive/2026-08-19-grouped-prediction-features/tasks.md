# Tasks: Grouped Prediction Features

## 1. Backward-Compatibility Pin

- [x] 1.1 Before any estimator change, capture the current `assess()` output for `tests/fixtures/continuous_lora_sibling_free_config.json` **and** the migrated `examples/continuous_lora/config.json` as golden fixtures, so both the ungrouped-and-sibling-free and ungrouped-with-dependent-baseline paths are pinned
- [x] 1.2 Extend `tests/unit/test_backward_compatibility.py` to assert byte-equality against the second fixture; run only this file

## 2. Spec Types And Validation

- [x] 2.1 Add a `FeatureGroup` dataclass (`members: tuple[str, ...]`, `label: str | None = None`) and `AttributionSpec.feature_groups: dict[str, FeatureGroup]` in `src/contribution/spec.py`, documenting that a group is one atomic player with no internal split
- [x] 2.2 Validate groups in `Estimator._validate_spec`: unknown member, feature in two groups, empty `members`, and group-name collision with a feature or regime name; each error names the offending group
- [x] 2.3 Add unit tests for all four validation failures; run only these selected tests

## 3. Player Layer

- [x] 3.1 Build the player set in the estimator: one player per declared group plus one per ungrouped feature, ordered by the declaration position of a group's first member
- [x] 3.2 Add a player→member-features mapping and use it in `_resolve_coalition_values` so membership of a player, not of a feature, decides actual-versus-baseline
- [x] 3.3 Switch `_row_scorer`, `_assess_row`, `_exact_shapley`, and `_sample_shapley` to take player names; keep `feature_names` and `player_names` as distinct, explicitly named locals
- [x] 3.4 Compare `max_exact_features` against the player count and update its docstring to say "players"
- [x] 3.5 Add unit tests: members flip together in both directions, no split-member coalition is ever scored, an ungrouped spec has a player set equal to its feature set; run only these selected tests

## 4. Results And Reporting

- [x] 4.1 Add `members: tuple[str, ...] = ()` to `FeatureAttribution` in `src/contribution/results.py`, omitted from serialized payloads when empty
- [x] 4.2 Emit one `analysis="feature"` assessment per player, carrying the group name, label, and member names for grouped players
- [x] 4.3 Render the member list in the report's contribution table for grouped players only
- [x] 4.4 Add unit tests for the grouped and ungrouped result shapes, including that an ungrouped spec's serialized payload is unchanged; run only these selected tests

## 5. Absorption Diagnostic Over Players

- [x] 5.1 Scope the absorption check to players whose member baselines reference a feature outside that player, and evaluate all-but-one-*player* coalitions
- [x] 5.2 Name the player rather than the feature in the diagnostic message
- [x] 5.3 Add unit tests: an intra-group reference does not trigger the check; a cross-player over-reference still does; run only these selected tests

## 6. CLI Config

- [x] 6.1 Parse `feature_groups` in `src/contribution/cli.py` (object with required `members` list and optional `label`), rejecting unknown keys and non-list members
- [x] 6.2 Add unit tests for loading, for the malformed-entry errors, and confirming `feature_groups` is absent-by-default; run only these selected tests

## 7. Example And Documentation Migration

- [x] 7.1 Group `class_sf` and `class_bw` as `class` in `examples/continuous_lora/config.json` and simplify `class_sf`'s baseline back to `col('GT SF')`, since the grouped baseline is the ground-truth class and needs no sibling reference
- [x] 7.2 Run `contrib run` against the migrated config; confirm the class player reports ≈26.44%, `measured_bw` ≈73.56%, shares sum to 100%, and the burden ranking, mismatch total, and observed accuracy are unchanged
- [x] 7.3 Document `feature_groups` in the README: what a group is, that it is atomic, and the validation rules
- [x] 7.4 Add a README section on **when to group versus when to use a dependent baseline** — grouping asks "how wrong was this decision", a dependent baseline asks "how wrong was this feature given what its dependencies did" — so the two mechanisms are not cargo-culted together
- [x] 7.5 Note in the README that the grouped and ungrouped splits answer different questions rather than one correcting the other
- [x] 7.6 Document the mirror-image trap: grouping features that are genuinely separable silently destroys per-feature signal, and the kit cannot detect it

## 8. Verification

- [x] 8.1 Run the full `pytest` suite and confirm no regressions
- [x] 8.2 Confirm invariance by assessing the example spec grouped and ungrouped, diffing everything except the feature attributions
- [x] 8.3 Confirm the 95-row correspondence: the class player carries non-zero coalition error on exactly the rows where the joint class decision is unworkable
