## ADDED Requirements

### Requirement: The Condition DSL SHALL Expose Coalition Scores Through coalition_score

The expression DSL SHALL provide a function `coalition_score(...)` that returns, for the row being evaluated, the Shapley game's characteristic function `v(S)` over the coalition `S` named by its arguments. The system SHALL compute it by resolving every prediction feature whose player is in `S` to its `actual` value and every other feature to its dependency-ordered `baseline`, evaluating `prediction_expr` against those values, and scoring the result against `target`. The returned value SHALL be the same number the Shapley pass consumes for that row and coalition, so a condition and the reported attribution never disagree about what a coalition costs.

#### Scenario: Single-player coalition isolates one decision
- **WHEN** a regime condition is `coalition_score('class') != 0` on a row where the class decision alone shifts the prediction away from `target`
- **THEN** the row matches the regime, and the value the condition observed equals the value the estimator's own coalition scorer returns for `{class}` on that row

#### Scenario: Multi-player coalition names a joint state
- **WHEN** a condition is `coalition_score('class', 'measured_bw') == 0` on a row where each player alone scores non-zero but the two together reproduce `target`
- **THEN** the row matches, reflecting that the two errors cancel rather than that neither occurred

#### Scenario: Full coalition reproduces the observed error
- **WHEN** a condition names every declared player
- **THEN** the returned value equals the row's observed error, the same quantity the per-row contributions sum to

### Requirement: coalition_score Arguments SHALL Be String Literals Naming Declared Players

Every argument to `coalition_score` SHALL be a string literal. The system SHALL reject a non-literal argument with a configuration error rather than evaluating it. Each argument SHALL name a declared Shapley player — an ungrouped prediction feature by its own name, or a feature group by its group name. The system SHALL validate every argument of every condition against the player set before reading any row, and SHALL reject an unknown name with an error identifying the offending condition, the offending argument, and the list of valid player names. The system SHALL reject a call that repeats the same player name.

#### Scenario: Misspelled player fails before evaluation
- **WHEN** a factorial axis level is `coalition_score('clas') == 0` and the declared players are `class` and `measured_bw`
- **THEN** validation fails with an error naming the axis level, the argument `clas`, and the valid players `class`, `measured_bw`, and no row is evaluated

#### Scenario: Non-literal argument is rejected
- **WHEN** a condition is `coalition_score(col('Player Name')) != 0`
- **THEN** validation fails, stating that arguments must be string literals

#### Scenario: Repeated player is rejected
- **WHEN** a condition is `coalition_score('class', 'class') != 0`
- **THEN** validation fails, naming the duplicated argument

### Requirement: Grouped Features SHALL Be Addressable Only By Their Group Name

When a prediction feature belongs to a declared feature group, the system SHALL reject `coalition_score` arguments naming that member, and the error SHALL name the group that owns it. A coalition holding one member of a group at its actual value while its siblings sit at baseline is a state the modelled system cannot produce, and the DSL SHALL NOT offer a way to score one.

#### Scenario: Group member is rejected in favour of the group
- **WHEN** `class_sf` and `class_bw` are grouped as `class` and a condition is `coalition_score('class_sf') != 0`
- **THEN** validation fails with an error stating that `class_sf` is a member of group `class` and that the group SHALL be named instead

#### Scenario: Ungrouped feature is addressable by its own name
- **WHEN** `measured_bw` is declared with no group and a condition is `coalition_score('measured_bw') != 0`
- **THEN** validation succeeds and the coalition `{measured_bw}` is scored

### Requirement: coalition_score SHALL Be Rejected In Expressions That Define The Game

The system SHALL reject `coalition_score` in any expression whose evaluation the coalition score itself depends on: a `prediction_features` entry's `actual` or `baseline`, `prediction_expr`, `target`, and `prediction`. Because the spec-level mismatch predicate is derived as `prediction != target` rather than declared separately, guarding those two SHALL also guard it. The rejection SHALL be a configuration error naming the offending expression and stating where the function is available. Where no coalition table is bound at all — such as the ad-hoc CLI subcommands that accept expressions without an attribution spec — the system SHALL raise an explanatory error rather than an unhandled lookup failure.

#### Scenario: Coalition score inside a feature baseline is rejected
- **WHEN** a prediction feature declares `"baseline": "col('GT SF') - coalition_score('measured_bw')"`
- **THEN** validation fails, naming the feature and its baseline expression, and stating that `coalition_score` is available only in regime conditions and factorial axis levels

#### Scenario: Coalition score in an observed expression is rejected
- **WHEN** a spec declares `target` or `prediction` using `coalition_score('class')`
- **THEN** validation fails with the same explanatory error, which also closes the mismatch predicate, since that predicate compares exactly those two expressions

#### Scenario: Ad-hoc CLI expression reports the missing context
- **WHEN** `contrib contributor --mismatch-expr "coalition_score('class') != 0"` is run, where no attribution spec and no players exist
- **THEN** the command fails with an error stating that `coalition_score` requires a spec declaring `prediction_features`, rather than a raw key or name error

### Requirement: Coalition Scores SHALL Be Available To Every Condition Evaluation

The system SHALL construct prediction features and Shapley players before it expands factorial crossings, so that a coalition score is available at every point a condition is evaluated. This SHALL include the per-row evaluation of factorial axis levels performed for partition validation, the generated cell conditions produced by crossing expansion, and the evaluation of declared regime conditions for both contribution summary and mismatch risk. A condition SHALL observe the same coalition score at every one of these sites.

#### Scenario: Factorial axis level uses a coalition score
- **WHEN** a crossing declares its rows axis as `class_workable: "coalition_score('class') == 0"` and `class_unworkable: "coalition_score('class') != 0"`
- **THEN** the axis is evaluated over all rows, partition validation reports neither overlap nor gap, and each generated cell is analysed by the regime machinery with no separate evaluation path

#### Scenario: Generated cell condition combines two coalition-scored axes
- **WHEN** both axes of a crossing use `coalition_score`
- **THEN** each generated cell's row count equals the number of rows satisfying both level conditions, and its mismatch risk is computed against the rest as for any other regime

#### Scenario: A declared regime and a factorial level agree
- **WHEN** a declared regime and a factorial axis level carry the identical `coalition_score` condition text
- **THEN** both select exactly the same rows

### Requirement: Each Referenced Coalition SHALL Be Evaluated Once Per Row

The system SHALL collect the distinct coalitions referenced across all regime and factorial-axis conditions before reading rows, and SHALL evaluate each referenced coalition at most once per row regardless of how many conditions reference it or how many generated cells repeat it. Work SHALL be bounded by the number of distinct referenced coalitions and SHALL NOT grow with the size of the coalition lattice.

#### Scenario: Repeated references do not repeat work
- **WHEN** `coalition_score('class')` appears in a declared regime, in a factorial rows level, and in each generated cell condition derived from that level
- **THEN** the coalition `{class}` is resolved and scored once per row

#### Scenario: Unreferenced coalitions are never scored for conditions
- **WHEN** a spec declares three players and its conditions reference only two single-player coalitions
- **THEN** condition evaluation scores exactly those two coalitions per row, not the full lattice

### Requirement: The Empty Coalition SHALL Be Expressible

The system SHALL accept `coalition_score()` with no arguments as the empty coalition, evaluating every feature at its baseline. This value SHALL be zero on every row of a well-formed spec, and is the quantity the existing baseline-versus-target diagnostic reports on.

#### Scenario: Empty coalition scores zero on a well-formed spec
- **WHEN** a condition is `coalition_score() != 0` and every baseline reproduces `target`
- **THEN** the condition matches no rows

#### Scenario: Empty coalition exposes a broken baseline
- **WHEN** baselines do not reproduce `target` on some rows
- **THEN** `coalition_score() != 0` selects exactly the rows counted by the `baseline_target_mismatch` warning

### Requirement: Coalition Scores SHALL Follow The Spec's Score Mode

The system SHALL score coalitions under the spec's declared `score_mode`, the same mode the Shapley attribution uses. Under an absolute mode a coalition score SHALL be non-negative, so `!= 0` distinguishes only whether a coalition caused error; under a signed mode the sign SHALL be retained, so comparisons against zero SHALL distinguish the direction of the induced error.

#### Scenario: Signed mode yields a directional axis
- **WHEN** `score_mode` is signed and an axis declares `over: "coalition_score('class') > 0"` and `under: "coalition_score('class') < 0"`
- **THEN** the two levels separate rows by the direction in which the class decision moves the prediction

#### Scenario: Absolute mode yields a magnitude axis
- **WHEN** `score_mode` is absolute
- **THEN** no coalition score is negative and a `< 0` level matches no rows

### Requirement: Specs That Do Not Use coalition_score SHALL Produce Unchanged Results

A spec whose conditions contain no `coalition_score` call SHALL produce output identical to the behaviour before this capability, across feature attributions, regime summaries, mismatch risks, factorial matrices, contrasts, burden rankings, partition warnings, and attribution warnings. No config key SHALL be added, renamed, or removed, and no result, JSON, CSV, or markdown field SHALL change shape.

#### Scenario: Existing example config is unaffected
- **WHEN** a config declaring only column-predicate conditions is assessed
- **THEN** every reported value matches the pinned pre-change fixture

#### Scenario: Column predicates keep their meaning alongside coalition scores
- **WHEN** one crossing uses column predicates and another in the same spec uses coalition scores
- **THEN** the column-predicate crossing's matrix, contrasts, and burden ranking are identical to those it produces when declared alone

### Requirement: The Shipped Example SHALL Carry Both A Direction And A Decision Crossing

The continuous-LoRa example SHALL retain its existing direction crossing and its existing declared regimes unchanged, and SHALL additionally declare a coalition-scored crossing over the class decision and the bandwidth measurement, plus at least one coalition-scored regime. The example SHALL therefore demonstrate that a column-predicate crossing and a coalition-scored crossing coexist in one `factorials` list and are reported side by side.

#### Scenario: Both crossings are reported
- **WHEN** the shipped example config is assessed
- **THEN** the report contains a matrix, contrast set, and burden ranking for the direction crossing and for the decision crossing, and the direction crossing's values are unchanged from before this capability

#### Scenario: The decision crossing partitions cleanly
- **WHEN** the decision crossing's axes are declared as `== 0` / `!= 0` over one coalition each
- **THEN** neither axis emits a partition warning

### Requirement: Public Documentation SHALL Distinguish Coalition Scores From Shapley Values

`README.md` SHALL document `coalition_score` in the expression reference, SHALL state where it is and is not available, and SHALL explain that it returns the characteristic function `v(S)` — one evaluation of the prediction formula under a held state — and not a Shapley value, which is an average of differences of `v` across the whole coalition lattice. The documentation SHALL note that coalition scores are measured from the baseline origin, so they are only interpretable when the empty coalition scores zero.

#### Scenario: Reference documents scope and semantics
- **WHEN** a reader consults the expression reference
- **THEN** it lists `coalition_score` alongside `col`, names the surfaces where it is available, and states the `v(S)` versus Shapley-value distinction and the baseline-origin caveat
