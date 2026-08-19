## Context

The estimator already builds, for every row, a memoized coalition scorer (`_row_scorer`) that answers `v(S)`: resolve every feature to its actual value if its player is in `S` and to its dependency-ordered baseline otherwise, evaluate `prediction_expr`, and score against `target` under `score_mode`. The Shapley pass consumes the whole lattice of these; nothing else can see any of them.

Conditions — regime conditions and factorial axis levels — are compiled by the same `expr.py` DSL but evaluated against a context built only from the raw CSV row (`build_row_context(row)`). So an author asking "did the class decision actually cost me anything?" has to restate the prediction formula's arithmetic in column terms and pick a threshold by hand. In the continuous-LoRa example that produced an axis whose 10% tolerance disagrees with the formula's real 41% flip point, and whose three levels scatter the 95 genuinely-unrecoverable rows 23/42/30 without isolating any of them.

Two facts about the existing code shape this design. First, factorial cells are not a separate evaluation path: `_expand_factorials` compiles each axis level, evaluates it per row for partition checking, and emits generated `Regime` objects whose condition is the string `"(row) and (col)"`, which then flow through `_regime_summary` and `_regime_risk` exactly like declared regimes. Second, `assess()` currently calls `_expand_factorials()` *before* `_formula_features()` and `_build_players()`, so at factorial-expansion time no player set exists yet.

## Goals / Non-Goals

**Goals:**
- Let a condition ask the question the game already answers, without restating `prediction_expr` in column terms or inventing a threshold.
- Fail at configuration time, not per row, on a misspelled or non-addressable player.
- Keep the cost bounded by the number of *referenced* coalitions, not by `2^p`.
- Leave every existing condition, result field, report table, and config key byte-identical.

**Non-Goals:**
- Exposing the Shapley value `φ_i` to conditions. `φ` is an average over the whole lattice and is defined per row only as a decomposition of the observed error; conditioning on it would make regime membership depend on the attribution it is supposed to explain.
- Addressing individual members of a feature group. `v` is defined on player coalitions; resolving `class_sf` without `class_bw` names a state the detector cannot produce.
- Coalition scores inside `mismatch_expr`, `target`, `prediction`, `prediction_expr`, or any `prediction_features` expression. Those define the game.
- Any new report section, JSON field, or CSV column.

## Decisions

### A function taking string literals, not a bare identifier

`coalition_score('class')` rather than a `class` binding in scope.

Player names are author-chosen and grouped-player names especially tend to read like keywords — the example's group is literally named `class`, and `ast.parse("class > 0")` is a `SyntaxError` before any of our validation runs. A quoted argument sidesteps Python's grammar entirely. It also makes the coalition explicit and multi-player coalitions expressible (`coalition_score('class', 'measured_bw')`) with no operator invented for set union.

Arguments SHALL be string literals, not arbitrary expressions. That is what makes static validation possible: every referenced coalition is known before the first row is read, so a typo names the valid players once instead of raising 13,277 times, and the score table below can be sized in advance. Dynamic player selection has no use case here.

*Alternative considered:* binding each player name as a variable in condition scope. Rejected on the reserved-word collision, and because it would silently shadow an input column of the same name — the precedence rule already documented for `prediction_features` expressions is subtle enough in one place.

### The argument namespace is players, not features

Ungrouped features are addressable by their own name; grouped features are addressable only by their group name. `coalition_score('class_sf')` SHALL fail, naming the owning group. This is the grouped-features decision carried into conditions: a coalition containing `class_sf` but not `class_bw` is off-manifold, and offering it in the DSL would re-open exactly the split-class states the atomic-group design exists to prevent.

### Static collection, then one precomputed score table

Rather than binding a live scorer into every condition context, the estimator SHALL:

1. build features and players,
2. walk every regime and factorial-axis condition's AST, collecting the distinct argument tuples,
3. validate each against the player set,
4. evaluate each distinct coalition once per row into a table,
5. bind `coalition_score` in condition contexts to a lookup into that table.

Cost is `|distinct referenced coalitions| × n_rows` — two coalitions and 13,277 rows in the example — and is independent of `p`. The obvious alternative, caching a full `_row_scorer` per row for reuse by conditions, retains up to `2^p` floats per row (54M floats at the `max_exact_features` ceiling of 12) and grows for reasons unrelated to what the conditions asked. Rebuilding a scorer per condition per row, the other alternative, costs `|regimes| × n_rows` dependency-ordered resolutions and rises with every generated factorial cell.

### Reorder `assess()`: players before factorial expansion

`_formula_features()` and `_build_players()` SHALL move above `_expand_factorials()`. Neither reads factorial state — `_build_players` validates group-name collisions against `self.spec.regimes`, the declared regimes only, never the generated ones — so the move is safe. It is also required: `_expand_factorials` evaluates axis conditions per row for partition checking, which is condition evaluation and must see the table.

### Both regimes and factorial axes, because they are one path

Supporting only factorial axes would require an explicit prohibition in regime conditions while the *generated* regimes produced from those same axes use the function freely. Uniform availability is both the smaller implementation and the smaller rule.

### Scope enforcement lives in the estimator, not the DSL

`expr.py` is shared with the ad-hoc `contrib contributor` / hypothesis CLI subcommands, which have no spec and no players. It SHALL therefore stay scope-agnostic: it learns the grammar (accept the call, require literal arguments, exclude the name from `free_variables`), exposes a helper returning each call's argument tuple, and raises an explanatory `ValueError` — not a bare `KeyError` — when the function is used where no coalition table is bound. The estimator applies the actual scope rules, since only it knows which expression is a feature baseline and which is a regime condition.

### `coalition_score()` with no arguments stays legal

It is the empty coalition, which the estimator already checks must score zero on every row. Leaving it expressible gives an author a direct way to see the invariant that the `baseline_target_mismatch` warning reports.

## Risks / Trade-offs

- **A reader conflates `v(S)` with `φ_i`** → The README section states the distinction explicitly and the report gains no column suggesting equivalence. A cell's mismatch rate and a player's contribution share remain separately labelled quantities computed by separate machinery.
- **Coalition-scored axes are only as meaningful as the baselines** → If `baseline_target_mismatch` fires, `v(∅) ≠ 0` and every coalition score is measured from a shifted origin, so the axis silently mislabels rows. The existing warning already fires in that case; no new diagnostic is added, but the README ties the two together.
- **`score_mode` changes what a level means** → Under `absolute`, `coalition_score('x') != 0` reads "this player caused error". Under `signed`, `> 0` and `< 0` become directional and recover an over/under-estimate axis in the units the formula actually uses. This is desirable but must be documented, or an author porting a config between modes will silently change their partition.
- **Static validation rejects configs that used to compile** → Only if they already contained a `coalition_score` call, which no existing config can. New syntax cannot break old specs.
- **Reordering `assess()` disturbs warning emission order** → `_expand_factorials` emits partition `warnings.warn` calls; moving player construction earlier means feature-validation `ValueError`s now surface before partition warnings. A spec with both a bad feature graph and a non-partition axis reports the feature error first. Acceptable, and arguably better ordering; pinned by the backward-compatibility fixtures either way.

## Migration Plan

Additive. No config key is added, renamed, or removed; no result field changes; no author action is required. The continuous-LoRa example gains a crossing and a regime and keeps its existing ones, so its direction analysis stays available and its existing report sections are unchanged.

## Open Questions

None blocking. One deferred: whether a coalition-scored axis should suppress the partition warning check entirely, since `== 0` / `!= 0` over one coalition is a tautological partition. Left in place — the check is cheap, and an author writing three levels over two coalitions can still build a non-partition.
