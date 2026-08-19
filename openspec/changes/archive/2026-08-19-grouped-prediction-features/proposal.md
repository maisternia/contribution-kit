# Grouped Prediction Features

## Why

Every declared prediction feature is an independently togglable Shapley player.
That is wrong whenever two features are two halves of a single decision, because
the coalition lattice then contains states the system cannot produce, and the
resulting per-feature attributions name interventions that are not available.

The bundled continuous-LoRa case is the motivating instance. The detector emits
**one** nominal `(BW, SF)` class from the scale-augmented lattice, so `class_sf`
and `class_bw` are one choice, not two. Scoring them as separate players means:

- Coalitions such as `{class_sf}` — actual class SF alongside a ground-truth
  class BW — describe a detector that emitted an SF from one lattice entry and a
  BW from another. No such class exists. On the bundled dataset those split
  states carry non-zero error on 270 and 318 rows respectively, so they are not
  a rounding artifact; they materially drive the reported split.
- The reported contributions are not actionable. This kit answers "what should
  we fix first?", and "fix `class_bw` alone" is not an available action: the
  bandwidth class cannot be changed without changing the class that was picked,
  SF included. `class_bw`'s current −19.76% share is a real interaction effect
  but names no intervention.

The archived `dependent-prediction-feature-baselines` change fixed the
*reference point* for `class_sf` (its baseline now conditions on the chosen
class BW) but deliberately left the *lattice* alone, logging off-manifold
coalitions as an accepted risk. This change addresses that risk.

Treating the class decision as one player yields a game in which every coalition
is physically realizable:

| Player set | class_sf | class_bw | class (joint) | measured_bw |
|---|---:|---:|---:|---:|
| current, three players | 44.11% | −19.76% | — | 75.65% |
| **grouped, two players** | — | — | **26.44%** | **73.56%** |

The grouped game also reads correctly against the data: the class player carries
non-zero error on exactly the 95 rows where the joint class decision is
unworkable, and `measured_bw` on the 217 rows where the bandwidth measurement
alone is off.

## What Changes

- Add a `feature_groups` declaration to `AttributionSpec` and the config: a
  mapping from group name to an optional `label` and a required `members` list
  of declared prediction feature names.
- Treat each group as **one atomic Shapley player**. Its members enter and leave
  every coalition together: all members take their `actual` values when the
  group is in the coalition, and all resolve to their `baseline` values when it
  is not. Ungrouped features remain players in their own right.
- Report one contribution per player. A group's assessment carries the group
  name, its label, and the member feature names. No per-member split inside a
  group is computed or reported.
- Count *players*, not raw features, against `max_exact_features`, so grouping
  can bring a spec back within reach of the exact path.
- Scope the archived formula-absorption diagnostic to all-but-one-*player*
  coalitions rather than all-but-one-feature.
- Validate groups: members must be declared features, a feature may belong to at
  most one group, a group must be non-empty, and group names must not collide
  with feature or regime names.
- Migrate `examples/continuous_lora/config.json` to group `class_sf` and
  `class_bw`, and refresh the README.

Non-breaking: a spec that declares no `feature_groups` has one player per
feature and produces identical results.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `estimator-hypothesis-attribution`: prediction features may be partitioned
  into named groups that act as single atomic Shapley players; results report
  one contribution per player rather than per feature; the exact-path feature
  cap and the formula-absorption diagnostic are expressed over players.

## Impact

- `src/contribution/spec.py`: new `FeatureGroup` dataclass and
  `AttributionSpec.feature_groups`.
- `src/contribution/estimator.py`: a player layer between features and the
  Shapley computation — coalition membership, resolution, `_row_scorer`,
  `_exact_shapley`/`_sample_shapley`, the absorption check, and the
  `max_exact_features` comparison all move from feature names to player names.
- `src/contribution/results.py`: `FeatureAttribution` gains an optional
  `members` field naming the grouped features (empty for a lone feature).
- `src/contribution/cli.py`: parse and validate `feature_groups`.
- `examples/continuous_lora/config.json`, `README.md`: grouped class decision,
  regenerated attribution numbers, and an explanation of when to group.
- `tests/unit/test_estimator.py`, `tests/unit/test_cli.py`,
  `tests/unit/test_backward_compatibility.py`: grouping behaviour, validation,
  and an ungrouped-spec equivalence pin.
- Performance: strictly favourable. Grouping shrinks the player count, and the
  exact Shapley path is `O(p * 2^p)` in players.

## Non-Goals

- No per-member split inside a group (no Owen value) — see `design.md`.
- No change to the factorial axes or the attributable burden ranking, whose
  levels are also declared over `Class BW` alone. That question is deferred to a
  separate change.
- No automatic inference of which features should be grouped.
