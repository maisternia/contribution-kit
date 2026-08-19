# Design: Grouped Prediction Features

## Context

`Estimator.assess` builds one `_Feature` per `prediction_features` entry and
hands the feature names straight to the Shapley computation as the player set:

```python
features = self._formula_features()
feature_names = [feature.name for feature in features]
...
score = self._row_scorer(row, features)
row_result = self._assess_row(score, feature_names, ...)
```

Coalitions are subsets of `feature_names`, so every feature toggles
independently. That is the right model when features are separate knobs. It is
the wrong model when several features are one decision.

In the continuous-LoRa formula
`class_sf + round(2 * log2(measured_bw / class_bw))`, the detector emits a
single nominal `(BW, SF)` class from the scale-augmented lattice. `class_sf`
and `class_bw` are not two knobs; they are one choice reported in two columns.

### The two failures this causes

**Unrealizable coalitions.** `{class_sf}` sets the class SF to what the detector
produced while the class BW sits at ground truth — a class that is not on the
lattice. These are not edge cases: on the bundled dataset, split-class states
carry non-zero error on 270 rows (`class_sf` actual, `class_bw` baseline) and
318 rows (`class_bw` actual, `class_sf` baseline). Roughly half the lattice is
fiction, and it is fiction that moves the numbers.

**Unactionable attributions.** The kit's stated purpose is ranking what to fix.
`class_bw`'s −19.76% is a genuine interaction effect — the coherent `(BW, SF)`
pairing partially cancels its own SF offset — but there is no intervention it
describes, because the bandwidth class cannot be changed independently of the
class it belongs to.

The archived `dependent-prediction-feature-baselines` change corrected the
*reference point* (a baseline may now condition on a sibling) and explicitly
logged off-manifold coalitions as an accepted risk. That risk is what this
change closes.

### What grouping produces

Making the class decision one player gives a game where every coalition is a
state the detector can actually be in:

```
   PLAYERS: {class}  {measured_bw}                v(S)     non-zero rows
   ------------------------------------------------------------------------
   {}                                             0        0
   {class}          detector picked this class    -        95
   {measured_bw}    bandwidth mis-measured        -        217
   {class, measured_bw}                           observed 313
```

| Player set | class_sf | class_bw | class (joint) | measured_bw |
|---|---:|---:|---:|---:|
| current, three players | 44.11% | −19.76% | — | 75.65% |
| grouped, two players | — | — | 26.44% | 73.56% |

The 95 rows are exactly the rows where the joint class decision is unworkable,
matching the 24 + 71 from the archived change's confusion analysis. Note
26.44% ≠ 44.11 − 19.76 = 24.35%: merging players changes the game rather than
summing it, which is the point rather than a discrepancy to reconcile.

## Goals / Non-Goals

**Goals:**

- Let an author declare that a set of features is one decision, and score it as
  one player.
- Keep every existing invariant: `v(empty) = 0`, `sum(phi) = observed error`,
  and no effect on `target`, the mismatch predicate, regimes, factorials, or the
  burden ranking.
- Leave ungrouped specs bit-identical.

**Non-Goals:**

- No per-member split within a group (see D2).
- No change to the factorial axes or burden ranking, even though
  `class_ok`/`upscale`/`downscale` are declared over `Class BW` alone and carry
  the same actionability problem. Deferred deliberately to keep this change
  reviewable.
- No inference of groups from `prediction_expr` structure or column names.
- No new expression syntax. Members keep their own `actual` and `baseline`.

## Decisions

### D1: A group is one atomic player; members flip together

Coalitions become subsets of the **player** set: every group name plus every
ungrouped feature name. Resolution follows membership:

```
group in coalition      -> every member takes its `actual` value
group not in coalition  -> every member resolves its `baseline`
                           (in dependency order, exactly as today)
```

Members keep their individual `actual`/`baseline` expressions, so nothing about
the expression language changes. Only which coalition bit governs a feature
changes: its group's, rather than its own.

For the continuous-LoRa spec this makes the class group's baseline
`(GT SF, GT BW)` — the detector emitted the ground-truth class — and its actual
`(Class SF, Class BW)`. Both are real lattice entries.

### D2: No internal split — this is not the Owen value

The obvious reach is the Owen value \[Owen 1977\], which assigns per-member
values inside a union via a two-level Shapley. Rejected, because Owen's inner
step scores coalitions in which only *some* union members are actual — precisely
the 270 and 318 rows of impossible split-class states this change exists to
remove. An internal split would reintroduce the defect at a lower level and
report it as a finding.

So a group is atomic: one contribution, no decomposition. If an author wants
per-member numbers they should not declare a group, and should read the caveats
about off-manifold coalitions instead.

This also means the implementation is simpler than the literature suggests:
with atomic groups the game is plain Shapley over a coarser player set, not a
coalition-structure value.

### D3: Declare groups top-level, not inline on each feature

```json
"feature_groups": {
  "class": {
    "label": "Nominal class decision (BW and SF together)",
    "members": ["class_sf", "class_bw"]
  }
}
```

The alternative was an inline `"group": "class"` key on each member, which
matches the kit's inline-factorial-axes precedent and sits naturally beside the
existing `independent` flag. Rejected for two reasons: a group needs a label,
and repeating it on every member invites inconsistency; and group membership is
a property of the *set*, so a reader must otherwise scan every feature to learn
the player set — the one thing they most need to know to read the report.

Group `label` is optional and defaults to the group name.

### D4: Results report one entry per player

`assess` currently emits one `analysis="feature"` assessment per
`prediction_features` entry. It will emit one per player instead: grouped
members collapse into a single entry named for the group, carrying the group's
label and a new `members` tuple on `FeatureAttribution` naming the constituent
features. An ungrouped feature keeps its current shape with an empty `members`.

Ordering: groups take the declaration position of their first member, so a
report's player order still follows `prediction_features` order.

This is a visible change to the feature table for grouped specs only. Ungrouped
specs keep byte-identical output, including the absent `members` field in
serialized payloads when empty.

### D5: `max_exact_features` counts players

The exact path is `O(p * 2^p)` in players, so the cap must compare against the
player count. Grouping strictly reduces it, meaning a spec that previously fell
back to permutation sampling may now qualify for exact Shapley. The parameter
name is kept for compatibility; its docstring is corrected to say "players".

### D6: The absorption diagnostic is expressed over players

The archived formula-absorption check warns when `v(N \ {f}) = 0` on every row
for a feature `f` with a dependent baseline. With groups, `N` is the player set
and the excluded unit is a player. A group is flagged when the coalition of all
*other* players is null on every row, and the message names the group.

The scoping rule from the archived change carries over unchanged: only players
whose baselines reference siblings are checked, since a plain column baseline
has no formula to absorb and can score zero on small inputs by coincidence.

### D7: Validation

All fail fast at assessment time, naming the offending group:

- A member that is not a declared prediction feature.
- A feature listed in more than one group.
- An empty `members` list.
- A group name colliding with a prediction feature name or a regime name.

A single-member group is accepted; it is mathematically identical to leaving the
feature ungrouped, and rejecting it would punish an author who groups
defensively while a spec is in flux.

Intra-group baseline references stay legal. When the group is out of the
coalition every member resolves its baseline, so a reference from one member to
another is well defined; the existing acyclicity check still applies.

## Risks / Trade-offs

- **[The published split changes again]** `class_sf` 44.11% / `class_bw` −19.76%
  becomes a single `class` 26.44%. Anyone reading the archived change's numbers
  gets a different answer. → Accepted and intended; the archived change stays in
  history with its reasoning. Worth a README note that the two are answers to
  different questions, not a correction of an error.
- **[Grouping hides real internal structure]** If two features genuinely are
  separable and an author groups them anyway, per-feature signal is lost with no
  diagnostic. → Accepted: the tool cannot know which features are jointly
  determined; that is exactly why grouping is author-declared. Documented as the
  mirror of the over-referencing trap.
- **[Two mechanisms now address one problem]** Dependent baselines and grouping
  both respond to jointly-determined features, and for the continuous-LoRa case
  grouping alone would have sufficed — the grouped class baseline is
  `(GT SF, GT BW)`, plain columns, no sibling reference. → Accepted. They answer
  different questions: a dependent baseline asks "how wrong was this feature,
  given what its dependencies did", grouping asks "how wrong was this decision".
  The README must say when to reach for which, or authors will cargo-cult both.
- **[Player-vs-feature confusion in the code]** Two similar name lists now exist.
  → Mitigation: name them `player_names` and `feature_names` explicitly and never
  pass one where the other is meant; the Shapley helpers take players only.

## Migration Plan

1. Add `FeatureGroup` and `AttributionSpec.feature_groups` plus validation; no
   behavioural change while no spec declares groups.
2. Introduce the player layer in the estimator: build players from groups plus
   ungrouped features, and switch coalition membership and resolution onto it.
   With no groups, the player set equals the feature set and results are
   unchanged.
3. Move the `max_exact_features` comparison and the absorption diagnostic onto
   players.
4. Add `members` to `FeatureAttribution` and emit one assessment per player.
5. Parse `feature_groups` in the CLI loader.
6. Migrate the example and README; regenerate numbers.

Rollback: revert the kit commits. A config carrying `feature_groups` fails
loudly on the older kit as an unknown key rather than silently ungrouping.

## Open Questions

- Should the report state the player set explicitly (for example
  "2 players: class (class_sf, class_bw), measured_bw") above the contribution
  table? Leaning yes — with grouping, the table alone no longer reveals what was
  toggled — but it changes report output for every spec, so it is proposed
  separately rather than folded in here.
