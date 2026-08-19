# Delta: estimator-hypothesis-attribution — grouped prediction features

## ADDED Requirements

### Requirement: Prediction Features MAY Be Grouped Into Atomic Shapley Players
The system SHALL accept a `feature_groups` declaration on `AttributionSpec` and in the JSON/YAML config: a mapping from group name to an entry with a required `members` list of declared prediction feature names and an optional `label` defaulting to the group name. Each declared group SHALL act as one atomic Shapley player. When a group is a member of the coalition being scored, every one of its member features SHALL take its `actual` value; when the group is not a member, every one of its member features SHALL resolve its `baseline`, in dependency order, exactly as an ungrouped feature does. Features not listed in any group SHALL remain players in their own right. Member features SHALL keep their own `actual` and `baseline` expressions; grouping SHALL NOT introduce new expression syntax.

#### Scenario: Group members enter a coalition together
- **WHEN** a group `class` declares members `class_sf` and `class_bw`, and the coalition contains `class`
- **THEN** both `class_sf` and `class_bw` resolve to their `actual` values for that row

#### Scenario: Group members leave a coalition together
- **WHEN** the same coalition does not contain `class`
- **THEN** both `class_sf` and `class_bw` resolve to their `baseline` values, and no coalition exists in which one is actual while the other is at baseline

#### Scenario: Ungrouped features remain independent players
- **WHEN** a spec groups `class_sf` and `class_bw` but leaves `measured_bw` ungrouped
- **THEN** the player set is `class` and `measured_bw`, and `measured_bw` toggles independently of the group

#### Scenario: The empty coalition still reproduces the target
- **WHEN** a grouped spec is assessed and every baseline is ground-truth-derived
- **THEN** the empty-coalition prediction equals `target` on every row, the empty-coalition score is `0`, and the per-player net contribution shares sum to 100%

#### Scenario: A single-member group is accepted
- **WHEN** a group declares exactly one member
- **THEN** the spec is valid and the resulting attribution equals what that feature would receive ungrouped

### Requirement: A Group SHALL Be Reported As One Contribution Without Internal Split
The system SHALL report exactly one `analysis="feature"` assessment per player. A group's assessment SHALL carry the group name, the group label, and the names of its member features, and SHALL NOT report any per-member decomposition of the group's contribution. The system SHALL NOT compute a coalition-structure value that scores coalitions in which only some members of a group are at their actual values, because such coalitions are the unrealizable states grouping exists to remove. Player ordering SHALL follow the declaration position of a group's first member, so report order continues to track `prediction_features` order.

#### Scenario: A grouped spec reports one entry for the group
- **WHEN** a spec groups `class_sf` and `class_bw` into `class`
- **THEN** the assessment list contains one feature entry named `class` listing both member names, and no separate entries for `class_sf` or `class_bw`

#### Scenario: An ungrouped feature reports no members
- **WHEN** a feature belongs to no group
- **THEN** its assessment carries an empty member list and is otherwise shaped exactly as before this change

#### Scenario: Player order follows first-member declaration order
- **WHEN** `prediction_features` declares `class_sf`, `class_bw`, `measured_bw` in that order and `class` groups the first two
- **THEN** the reported player order is `class`, then `measured_bw`

### Requirement: Feature Groups SHALL Be Validated Against The Declared Features
The system SHALL fail fast at assessment time, naming the offending group, when a group lists a member that is not a declared prediction feature, when a feature is listed in more than one group, when a group's `members` list is empty, or when a group name collides with a prediction feature name or a regime name.

#### Scenario: Unknown member is an error
- **WHEN** a group lists a member that is not a declared prediction feature
- **THEN** `assess` fails with a validation error naming the group and the unknown member

#### Scenario: A feature in two groups is an error
- **WHEN** the same prediction feature is listed in two different groups
- **THEN** `assess` fails with a validation error naming the feature and both groups

#### Scenario: An empty group is an error
- **WHEN** a group declares an empty `members` list
- **THEN** `assess` fails with a validation error naming the group

#### Scenario: A group name colliding with a feature or regime is an error
- **WHEN** a group name equals a declared prediction feature name or a declared regime name
- **THEN** `assess` fails with a validation error reporting the duplicate name

#### Scenario: Intra-group baseline references stay legal
- **WHEN** one member of a group has a `baseline` referencing another member of the same group, and the reference graph is acyclic
- **THEN** the spec is valid, and when the group is out of the coalition the referenced member's resolved baseline is used

### Requirement: Specs Without Feature Groups SHALL Produce Unchanged Results
The system SHALL produce, for any spec declaring no `feature_groups`, a player set equal to its feature set and assessment output identical to that produced before grouping was supported. The new validations SHALL NOT reject any previously valid spec.

#### Scenario: An ungrouped config is unaffected
- **WHEN** a config that declares no `feature_groups` is assessed
- **THEN** every per-feature attribution value, every regime summary, every factorial result, and the burden ranking equal those produced before this change

### Requirement: Exact Shapley Computation SHALL Be Bounded By The Player Count
The system SHALL compare `max_exact_features` against the number of Shapley **players** — declared groups plus ungrouped features — rather than the number of declared prediction features, because the exact path's cost is exponential in players. Grouping SHALL therefore be able to bring a spec that previously fell back to permutation sampling back within the exact path. The parameter name SHALL be retained for compatibility and its documentation SHALL state that it counts players.

#### Scenario: Grouping brings a spec back to the exact path
- **WHEN** a spec declares more features than `max_exact_features` but groups enough of them that the player count falls at or below the cap
- **THEN** the estimator uses the exact closed-form Shapley computation rather than permutation sampling

#### Scenario: Ungrouped specs compare unchanged
- **WHEN** a spec declares no groups
- **THEN** the player count equals the feature count and the exact-versus-sampling decision is unchanged

## MODIFIED Requirements

### Requirement: The Estimator SHALL Report When A Baseline Absorbs The Prediction Formula
The system SHALL detect, for each **player** whose member baselines reference at least one feature outside that player, whether the coalition of all other players scores zero on every row. When it does, that player's baselines have absorbed the prediction formula: every feature referenced from outside becomes attributable only in interaction with that player, and the reported attribution is degenerate. The system SHALL emit a diagnostic naming the player and the features whose contributions are affected. A player whose baselines reference no feature outside itself SHALL NOT be checked: it has no formula to absorb, and on small inputs its all-but-one coalition can score zero by coincidence. A zero-scoring coalition smaller than the all-but-one-player coalition SHALL NOT trigger the diagnostic, because a fully compensated player is a legitimate and intended finding. The diagnostic SHALL be a warning rather than a hard error.

#### Scenario: Over-referenced baseline is detected
- **WHEN** `class_sf.baseline` references both `class_bw` and `measured_bw` such that it inverts `prediction_expr`, and the coalition of all other players scores zero on every row
- **THEN** `assess` emits a diagnostic naming the affected player and identifying the degenerately attributed features

#### Scenario: A sibling-free spec is never flagged
- **WHEN** a spec declares only baselines that reference input columns, and some all-but-one-player coalition happens to score zero on every row of a small input
- **THEN** `assess` emits no absorption diagnostic

#### Scenario: A single fully compensated player is not flagged
- **WHEN** a coalition smaller than the all-but-one-player coalition scores zero on every row
- **THEN** `assess` emits no absorption diagnostic

#### Scenario: References inside a group do not trigger the check
- **WHEN** a group's member baseline references another member of the same group, and no member baseline references a feature outside the group
- **THEN** that player is not checked for absorption, because the reference never crosses a player boundary

#### Scenario: Detection covers the sampling path
- **WHEN** a spec declares more players than `max_exact_features`, so Shapley values are estimated by permutation sampling rather than exhaustive coalition evaluation
- **THEN** the estimator still evaluates each all-but-one-player coalition explicitly and applies the same absorption detection
