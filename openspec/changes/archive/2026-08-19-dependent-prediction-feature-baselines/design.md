# Design: Dependent Prediction Feature Baselines

## Context

`Estimator` scores a Shapley coalition `S` by mixing per-feature values:

```python
def _coalition_score(self, row, features, subset):
    actual   = self._feature_values(row, features, actual=True)
    baseline = self._feature_values(row, features, actual=False)
    mixed    = {n: actual[n] if n in subset else baseline[n] for n in actual}
    prediction = self._evaluate_prediction_formula(row, mixed)
    return _score(prediction, float(self._evaluate_target(row)), self.spec.score_mode)
```

`_feature_values` evaluates each feature's expression against
`build_row_context(row)` with no `extra`, so features are resolved
independently and cannot see each other. Both maps are coalition-independent;
only the *selection* between them varies with `S`.

That is correct when features are independent knobs. It is wrong when two
features are two halves of one decision. In the continuous-LoRa formula
`class_sf + round(2 * log2(measured_bw / class_bw))`, the detector emits a
single nominal `(BW, SF)` class from a scale-augmented lattice, so `class_sf`
and `class_bw` are jointly determined. "Nothing went wrong with `class_sf`"
cannot be stated without reference to which `class_bw` is in play.

The invariant that makes the report's arithmetic work is that the empty
coalition reproduces `target`, giving `v(empty) = 0` and therefore
`sum(phi) = observed error`, which the report prints as net contribution shares
summing to 100%. Today that invariant holds by construction only because every
baseline happens to be a ground-truth column and the formula collapses to
`GT SF + round(2 * log2(GT BW / GT BW))`. It is never checked.

### The mis-scoring, concretely

For true signal `(812, 8)` (paper Table 2.2), the ideal `class_sf` given the
detector's chosen class bandwidth is
`GT SF - round(2 * log2(GT BW / class_bw))`:

| Nominal class | Formula output | Correct? | ideal `class_sf` | actual `class_sf` | Real verdict | Current baseline (`GT SF`) verdict |
|---|---|---|---|---|---|---|
| `(1000, 8)` | 7 | no | 9 | 8 | error | "fine" (8 == 8) |
| `(1000, 9)` | 8 | yes | 9 | 9 | fine | "error" (9 != 8) |
| `(500, 7)` | 8 | yes | 7 | 7 | fine | "error" (7 != 8) |

All three rows inverted. Dataset-wide: 246 false accusations, 71 excused
errors, 24 correct calls out of 270 flagged rows.

### Why the literal-column workaround fails

Writing `baseline: "col('GT SF') - round(2 * log2(col('GT BW') / col('Class BW')))"`
is legal in today's DSL but wrong. `col('Class BW')` reads the observed value
unconditionally, including in coalitions where `class_bw` sits at its own
baseline. Measured on the bundled dataset:

| | class_sf | class_bw | measured_bw | sum |
|---|---|---|---|---|
| current (`GT SF`) | 15.01% | 15.79% | 69.20% | 100.00% |
| literal `col('Class BW')` | 2.62% | −61.26% | 74.61% | **15.97%** |
| coalition-resolved (this change) | 44.11% | −19.76% | 75.65% | 100.00% |

The middle row is broken bookkeeping, not a finding: `v(empty) != 0`, so
`sum(phi) != observed error`.

## Goals / Non-Goals

**Goals:**

- Let a `baseline` expression reference sibling features, bound to their
  coalition-resolved values, so a baseline can state a conditional ideal.
- Keep `v(empty) = 0` and `sum(phi) = observed error` for every valid spec, and
  detect violations instead of emitting silently wrong shares.
- Leave `target`, the mismatch predicate, regimes, factorials, and the burden
  ranking bit-identical — this change only affects Shapley decomposition.
- Fail fast on unknown references and dependency cycles.

**Non-Goals:**

- No DSL grammar change. `free_variables` already extracts the reference set.
- No change to the Shapley math itself (`_exact_shapley`, `_sample_shapley`,
  weights, sampling) — only to how a coalition's feature values are produced.
- No support for feature references in `actual` expressions (see D4).
- No new config keys; the existing `{actual, baseline, label?}` object and the
  equality string shorthand both carry this unchanged.
- No automatic inference of dependencies from the formula's algebraic structure.
  Baselines stay author-declared.

## Decisions

### D1: A baseline reference binds to the sibling's coalition-resolved value

Given coalition `S`, feature `f` resolves to:

```
resolve(f, S) = f.actual  evaluated on the row                 if f in S
                f.baseline evaluated on the row + {g: resolve(g, S) for g in deps(f)}   otherwise
```

The alternatives were rejected:

- *Bind to the sibling's actual value* — this is the literal-`col()` behavior,
  which breaks `v(empty) = 0` (measured above, 15.97%).
- *Bind to the sibling's baseline value* — makes the reference constant across
  coalitions, so `v({class_bw})` would not return to zero and `class_bw`'s
  compensating effect stays invisible. It also cannot express "given what the
  detector actually chose."

Only the resolved binding satisfies both endpoints simultaneously:

```
   coalition            class_bw resolves to    class_sf baseline becomes        v(S)
   ----------------------------------------------------------------------------------
   {}                   GT BW                   GT SF - round(2*log2(GT/GT))=GT SF   0   <- invariant holds
   {class_bw}           Class BW                GT SF - round(2*log2(GT/Class))      0   <- compensation visible
```

`v({class_bw}) = 0` says: a misclassified BW class, with a correct SF and a
clean BW measurement, produces no error. That is the geometric-regression claim,
and it is what the current baseline charges 0.0242 for.

### D2: Resolution is per (row, coalition), memoized, in topological order

`deps(f)` = `free_variables(compile_expression(f.baseline))` intersected with
the declared feature names. Sort features topologically once at validation time
and store the order on the compiled feature list; resolution then walks that
order, accumulating an `extra` mapping that later features can read via
`build_row_context(row, extra)`.

`actual` values stay coalition-independent (D4), so they are computed once per
row and reused. Baseline values are computed once per `(row, S)` and memoized
for the duration of that coalition's scoring. Coalition count is unchanged;
`_exact_shapley` remains `O(n * 2^n)` scoring calls with the exact path capped
at `max_exact_features = 12`.

This also removes existing waste: `_coalition_score` currently rebuilds *both*
full value maps on every call, when `actual` need only be built once per row.

### D3: Free variables resolve feature-first, then column, then error

`build_row_context` seeds the context with `dict(row)`, so **a bare identifier
already resolves to an input column**: `Height * 2` evaluates today without
`col()`, and `free_variables` reports `Height`. A naive "any non-`col` free
variable is a sibling reference" rule would therefore misread bare column names
as feature references and reject currently-valid specs.

Resolution order is: **the owner's own name binds to a column when one exists**,
else declared feature, else input column, else unknown-name error. Only names in
the feature class become dependency edges. Feature-wins matches existing
precedence — `build_row_context(row, extra)` does `context.update(extra)`, so
`prediction_expr`'s feature bindings already override row values.

The owner-name carve-out is not a nicety. Naming a feature after the column it
reads is an established idiom in this codebase — the existing unit fixtures use
`PredictionFeature(actual="x", baseline="y")` for a feature named `x` over a
CSV with an `x` column. Without the carve-out, "feature always wins" turns every
such declaration into a self-reference error. A feature can never usefully
reference itself (it would be a cycle in a baseline and meaningless in an
actual), so binding the owner's own name to the column loses nothing.

The shadowing diagnostic is therefore scoped to the case where precedence
actually decides something: a name in some feature's `baseline_deps` that is
*also* a column. Warning on the common idiom would be noise.

Validation needs the input columns, which the estimator already holds in
`self.rows` by the time `assess` runs.

### D4: `actual` expressions stay row-only

If `actual` could reference siblings, the full coalition would no longer
evaluate to the observed prediction, so `v(full)` would stop equalling the
observed error and efficiency would break at the opposite endpoint from D1.
Validation rejects any free variable in an `actual` expression that resolves to
a declared feature under D3, naming the feature and the offending variable.
Column references, bare or via `col(...)`, stay permitted.

### D5: Cycles are rejected at validation time

`class_sf -> class_bw` is a DAG. A mutual reference (`a.baseline` reads `b`,
`b.baseline` reads `a`) has no fixed point and must fail fast rather than
recurse. `_validate_spec` builds the reference graph, rejects any edge to an
undeclared name, and rejects any cycle, reporting the participating feature
names in declaration order.

### D6: The empty-coalition invariant becomes a checked diagnostic

After validation, evaluate `v(empty)` on every row. If it is non-zero anywhere,
the spec's baselines do not jointly reproduce `target` and every reported share
is unsound. Emit a diagnostic naming the count of violating rows and one
example row index.

Warning rather than hard error, because `score_mode="signed"` and
deliberately-partial baselines are legitimate exploratory setups, and because a
hard error would break any existing spec whose baselines do not collapse to
`target`. The report surfaces it so a broken 15.97% total can never again pass
as a finding. Whether this should escalate to an error is left as an open
question.

### D7: Null sub-lattice detection catches over-referenced baselines

A dependent baseline can reference *too many* siblings and silently absorb the
whole formula. If `class_sf.baseline` used `measured_bw` in place of
`col('GT BW')`, the baseline becomes the algebraic inverse of `prediction_expr`,
and every coalition leaving `class_sf` at baseline collapses to `target`.
Measured on the bundled dataset (rows with non-zero score, out of 13,277):

| Coalition | current | dependent (correct) | over-referenced |
|---|---|---|---|
| `{}` | 0 | 0 | 0 |
| `{class_bw}` | 318 | **0** | **0** |
| `{measured_bw}` | 217 | 217 | **0** |
| `{class_bw, measured_bw}` | 450 | 280 | **0** |

The D6 empty-coalition check does not fire — `v(empty)` is 0 in all three
columns. The distinguishing signature is that the entire sub-lattice on
`N \ {class_sf}` is null: the referenced features cannot produce error at all
unless `class_sf` is already at actual.

So: warn when `v(N \ {f}) = 0` on every row, for any feature `f` **whose
baseline references at least one sibling**. It means `f`'s baseline has absorbed
the prediction formula and every feature it references is attributable only in
interaction with `f`. A single null coalition is *not* a problem —
`v({class_bw}) = 0` is the intended finding of this change; only the
`n-1`-sized null coalition is.

Restricting to dependent baselines is load-bearing, not an optimization. A
sibling-free baseline has no formula to absorb, and on small inputs its
all-but-one coalition can score zero by coincidence: the kit's own 2-row unit
fixture — all baselines plain ground-truth columns — has
`v({class_bw, measured_bw}) = 0` on both rows purely through rounding, and an
unrestricted check fires a false positive on it.

No syntactic rule is possible here. The estimator cannot distinguish `class_bw`
from `measured_bw`: both are variables of `prediction_expr`. The distinction is
causal and domain-specific — the detector emits `(BW, SF)` jointly, so
conditioning `class_sf` on `class_bw` is sound, while `measured_bw` is derived
independently from box geometry and `class_sf` cannot depend on it. Encoding
that would require an author-declared causal ordering, which is rejected as
heavier than the numeric check and no more reliable. Detection, not prohibition:
it catches the consequence however the author arrived at it, and does not block
legitimate uses that a structural ban would.

Cost is zero on the exact path, which already evaluates every coalition; the
sampling path (`n > max_exact_features`) evaluates the `n` coalitions
`N \ {f}` explicitly, one extra pass per row.

Warning rather than hard error, for the same reason as D6: a genuinely dominant
feature could produce this pattern legitimately, and the author is better placed
to judge. An author who knows the causal structure in advance can escalate to a
hard error by declaring the protected feature `independent` (D9).

### D8: Migrate the bundled example and README numbers in this change

`examples/continuous_lora/config.json` is the README's headline evidence.
Leaving it on the inverted baseline while shipping the fix would keep the
documented attribution numbers wrong. The example's `class_sf.baseline` becomes
`col('GT SF') - round(2 * log2(col('GT BW') / class_bw))` and the README's
feature-attribution figures are regenerated.

The burden-ranking table in the README is unaffected — it derives from `target`
and the mismatch predicate, neither of which moves.

## Risks / Trade-offs

- **[Negative contribution shares become normal]** `class_bw` lands at −19.76%.
  This is real: from the `{class_sf}` coalition, `v` drops 0.0211 → 0.0076 when
  `class_bw` goes actual, because the detector's coherent `(BW, SF)` pairing
  partially cancels its own SF offset. Under this framing `class_bw` is a net
  *corrector*. → Mitigation: README and report caption explain that a negative
  share means the feature compensates for others rather than contributing error.

- **[Authoring trap: over-referencing collapses attribution]** A baseline should
  reference only the features whose state it conditions on, and use ground-truth
  columns for the rest; referencing more absorbs the formula. → Mitigation: the
  D7 null-sub-lattice diagnostic detects it numerically, the D9 `independent`
  flag turns it into a fail-fast error when the author knows the causal
  structure, plus the README worked counter-example. Residual risk: D7 is a
  warning, so an author who neither flags nor heeds it still publishes collapsed
  attributions.

- **[Off-manifold coalitions remain]** Mixed coalitions such as
  `{class_sf}` (actual SF, baseline BW class) still describe detector states
  that cannot occur, since the lattice emits pairs. This change makes the
  *baseline* coherent but does not restrict the coalition lattice. → Accepted:
  it is inherent to Shapley over jointly-determined features, and constraining
  the lattice is a much larger change.

- **[Interpretation shift in published numbers]** `class_sf` moves 15.01% →
  44.11%. Anyone citing the old split gets a different answer. → Accepted and
  intended: the old split was computed against a baseline that inverted the
  paper's own worked example. The archived change stays in history.

- **[Resolution cost inside the coalition loop]** Baseline evaluation moves from
  once-per-row to once-per-(row, coalition). → Bounded by memoization and the
  12-feature exact cap; the bundled example has 3 features.

## Migration Plan

1. Add reference extraction, cycle detection, and `actual` row-only validation
   to `_validate_spec`; no behavior change yet since no baseline references
   siblings.
2. Rewrite feature resolution to be dependency-ordered and coalition-aware,
   hoisting `actual` to once-per-row. Existing specs are unaffected: with an
   empty reference graph, resolution reduces to today's behavior.
3. Add the D5 empty-coalition diagnostic.
4. Add the D7 null-sub-lattice diagnostic.
5. Migrate `examples/continuous_lora/config.json`, regenerate README numbers.
6. Add tests, including the Table 2.2 three-row acceptance case.

Rollback: revert the kit commits. Configs are forward-compatible in the sense
that a reverted kit reads a dependent baseline as an unknown-variable error
rather than silently mis-scoring.

## Open Questions

- Should the D5 empty-coalition violation escalate from warning to hard error
  once the bundled example and tests are migrated? Leaning yes for
  `score_mode="absolute"`, but it needs a survey of whether any legitimate spec
  wants a non-zero baseline score.
- Should the report print `v(empty)` and `sum(phi)` alongside the shares as a
  standing self-check, rather than only warning on violation?

### D9: An optional `independent` flag turns the trap into a validation error

D7 detects an over-referenced baseline only *after* scoring, from the shape of
the results. Authors who know the causal structure up front should be able to
state it and get a hard error instead. `independent: true` on a feature declares
that it participates in no dependency edge.

```json
"measured_bw": {
  "label": "Measured BW (box estimate vs GT BW)",
  "actual": "col('Measured BW')",
  "baseline": "col('GT BW')",
  "independent": true
}
```

In the continuous-LoRa spec this encodes exactly the domain fact that motivated
D7: `measured_bw` is derived from bounding-box geometry independently of the
detector's class decision, so no feature's ideal may be conditioned on it.
Marking it turns the trap from a post-hoc warning into a fail-fast error naming
both features.

**Naming.** Chosen over `referenceable: false`, `no_dependents: true`, and
`exclude_from_baselines: true`. The rejected `dependency_disabled` form was
directionally ambiguous — it reads equally as "may not have dependencies" and
"may not be a dependency". `independent` is the shortest term that matches the
domain rationale, at the cost of not carrying direction in the name itself; the
spec compensates by mandating that the validation error state the direction and
name both features.

**Symmetric by design.** An independent feature is *isolated* in the dependency
graph: nothing may reference it, and its own baseline may not reference others.
The one-way reading (only "nothing may reference it") was rejected because the
word does not support it and because the asymmetric failure mode is the silent
one. An author who genuinely wants a non-referenceable feature that itself has a
dependent baseline simply omits the flag and relies on D7.

**Default is permissive.** Omitting the key leaves a feature referenceable.
Opt-in referenceability was considered — it would make the trap unreachable by
omission rather than merely detectable — but it doubles the declaration burden
for the common case, requiring a flag on both the depending and depended-upon
feature for every dependent baseline. D7 remains the backstop for unflagged
specs.

The flag is available only in the explicit object form. The equality string
shorthand cannot express it, matching how `label` already behaves.
