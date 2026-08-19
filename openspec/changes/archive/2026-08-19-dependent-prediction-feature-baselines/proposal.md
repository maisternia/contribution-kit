# Dependent Prediction Feature Baselines

## Why

A prediction feature's `baseline` expression is evaluated once per row against
the raw CSV row only (`Estimator._feature_values` builds its context with
`build_row_context(row)` and no `extra`). A baseline therefore cannot depend on
what any other feature is set to in the coalition being scored. For formulas
whose features are *jointly* determined, this silently misattributes blame.

The bundled `examples/continuous_lora` case is the motivating instance. The
prediction formula is the paper's geometric-regression equation,
`class_sf + round(2 * log2(measured_bw / class_bw))`, where `class_sf` and
`class_bw` are two halves of a single detector decision: the detector emits one
nominal `(BW, SF)` class off a scale-augmented lattice. When the detector picks
a *scaled* class, the correct `class_sf` is deliberately **not** `GT SF` — the
formula is designed to correct it back. The ideal `class_sf` given the class
bandwidth in play is `GT SF - round(2 * log2(GT BW / class_bw))`.

The config can only express `baseline: "col('GT SF')"`, which asserts the
detector should have emitted `GT SF` regardless of which class it chose. The
paper's own worked example (Table 2.2, true signal `(812, 8)`) shows all three
of its rows scored backwards under that baseline:

| Nominal class | Formula output | Correct? | Current baseline verdict |
|---|---|---|---|
| `(1000, 8)` | 7 | no | "class_sf fine" — real error excused |
| `(1000, 9)` | 8 | yes | "class_sf wrong" — falsely blamed |
| `(500, 7)` | 8 | yes | "class_sf wrong" — falsely blamed |

Over the bundled 13,277-row dataset the current baseline flags 270 rows as
`class_sf` errors, of which **246 are false accusations and 24 are real**, while
**71 genuine errors are excused**.

Writing the dependent formula with a literal `col('Class BW')` does not fix it:
that pins to the observed value in every coalition, including coalitions where
`class_bw` is supposed to sit at its own baseline. The empty coalition then stops
reproducing `target`, `v(empty) != 0`, and Shapley efficiency breaks — measured
net contribution shares sum to 15.97% instead of 100%. The baseline must
reference the **coalition-resolved** value of `class_bw`, which requires
resolving features in dependency order inside coalition scoring.

A standalone prototype of the coalition-resolved form confirms the fix is sound:
`v(empty) = 0` on all 13,277 rows, shares sum to 100%, mean observed error is
unchanged at 0.0288 (so `target`, the mismatch predicate, and the 313-mismatch
burden ranking are untouched), and `v({class_bw})` drops from 0.0242 to exactly
0.0000 — i.e. a misclassified BW class with a correct SF and a clean BW
measurement becomes measurably harmless, which is precisely what the
geometric-regression method claims.

## What Changes

- Allow a `prediction_features` entry's `baseline` expression to reference other
  declared feature names as free variables, bound to their **coalition-resolved**
  values (actual when the referenced feature is in the coalition, its own
  resolved baseline otherwise).
- Resolve feature values in dependency order per coalition rather than
  precomputing one `actual` map and one `baseline` map per row.
- Resolve each free variable of a feature expression feature-first, then input
  column, then error. Bare column identifiers such as `Height` are already legal
  in the DSL and remain so; only names matching a declared feature become
  dependency edges.
- Validate the reference graph: a free variable matching neither a declared
  feature nor an input column is rejected, and the dependency graph must be
  acyclic. Both violations fail fast with an error naming the offending
  feature(s).
- `actual` expressions may not reference other features, only input columns. An
  `actual` that depends on another feature would make the full coalition no
  longer reproduce the observed prediction.
- Preserve the existing invariant that the empty coalition reproduces `target`,
  and surface a diagnostic when a spec violates it, instead of silently emitting
  shares that do not sum to 100%.
- Detect an over-referenced baseline that has absorbed the prediction formula,
  by warning when the coalition of all other features scores zero on every row.
- Add an optional `independent: true` flag on a prediction feature, declaring
  that it participates in no dependency edge in either direction, so an author
  who knows the causal structure gets a fail-fast error rather than a post-hoc
  warning. Defaults to `false`; omitting it leaves a feature referenceable.
- Migrate `examples/continuous_lora/config.json` to the dependent baseline and
  refresh the README's reported feature-attribution numbers.

Non-breaking: a `baseline` with no feature references behaves exactly as today.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `estimator-hypothesis-attribution`: prediction-feature `baseline` expressions
  may reference other declared features and are resolved per coalition in
  dependency order; free variables resolve feature-first then column, preserving
  bare column identifiers; new acyclicity, reference, and `actual` row-only
  validation; an optional `independent` flag forbids dependency edges on a
  feature; empty-coalition/`target` agreement and formula absorption become
  checked diagnostics.

## Impact

- `src/contribution/estimator.py`: `_feature_values` gains dependency-ordered,
  coalition-aware resolution; `_coalition_score` resolves baselines inside the
  coalition loop instead of reusing precomputed maps; `_validate_spec` gains
  reference and cycle checks plus the empty-coalition diagnostic.
- `src/contribution/spec.py`: `PredictionFeature` gains
  `independent: bool = False`; docstring documents that `baseline` may
  reference sibling features and `actual` may not.
- `src/contribution/expr.py`: reuse `free_variables` for baseline reference
  extraction; no DSL grammar change.
- `src/contribution/cli.py`: accept the optional `independent` boolean in the
  object form of a feature entry (unknown keys stay rejected); the equality
  string shorthand keeps working, and its right-hand side may now carry feature
  references.
- `examples/continuous_lora/config.json`: `class_sf.baseline` becomes
  `col('GT SF') - round(2 * log2(col('GT BW') / class_bw))`.
- `README.md`: the "How it works" feature bullet, the Quick start snippet, and
  the reported attribution numbers.
- `tests/unit/test_estimator.py`, `tests/unit/test_spec.py`,
  `tests/unit/test_cli.py`: dependent-baseline resolution, cycle rejection,
  unknown-reference rejection, and the Table 2.2 three-row acceptance case.
- Performance: coalition count is unchanged, but baseline resolution moves
  inside the coalition loop. With the exact path capped at 12 features and the
  bundled example at 3, the cost is a small constant factor.
