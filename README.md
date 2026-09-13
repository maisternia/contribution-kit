# contribution-kit

[![GitHub](https://img.shields.io/badge/GitHub-maisternia%2Fcontribution--kit-blue)](https://github.com/maisternia/contribution-kit)

Answers *"what should we fix first?"* for any prediction pipeline. You declare failure **regimes** as boolean conditions over CSV columns and mark one factorial cell as the healthy **baseline**; the kit ranks every other cell by *recoverable mismatches* — how many errors would disappear if that cell reverted to the baseline rate — together with the accuracy you would reach by eliminating each cause.

> Running example: throughout this README the modeled quantity is a prediction *error* (`|prediction - target|`) on the bundled continuous-LoRa dataset — the 8,678 matched detections of the C18x2 model on the continuous-bandwidth evaluation set \[[Dudarek & Martyniuk 2026](#ref-dudarek26)\]. Swap the expressions and `score_mode` and the same math attributes any positive or negative contribution.

## The result

One command over a CSV and a declarative config:

```bash
contrib run --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001
```

writes `contribution.csv`, `run.json`, and `report.md`. The centerpiece of the report is the **attributable burden ranking** — real output on the bundled 8,678-row dataset:

**BW quality × scaling direction** — baseline cell: `class_ok & measured_ok`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated (accumulating) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | upscale & measured_ok | 973 | 24.25% | 0.33% | 232.81 | 46.84% | 0.239 (0.213 to 0.267) | 96.96% |
| 2 | downscale & measured_ok | 1529 | 12.82% | 0.33% | 190.98 | 38.43% | 0.125 (0.109 to 0.143) | 99.16% |
| 3 | downscale & measured_off | 33 | 54.55% | 0.33% | 17.89 | 3.60% | 0.542 (0.377 to 0.698) | 99.36% |
| 4 | class_ok & measured_off | 29 | 51.72% | 0.33% | 14.90 | 3.00% | 0.514 (0.341 to 0.683) | 99.53% |
| 5 | upscale & measured_off | 21 | 57.14% | 0.33% | 11.93 | 2.40% | 0.568 (0.362 to 0.752) | 99.67% |

Observed accuracy: 94.27% | Ceiling accuracy after ranked eliminations: 99.67% | Total observed mismatches: 497

Read it top-down as an intervention plan: fixing the rank-1 cell recovers ≈233 of the 497 observed mismatches and lifts accuracy from 94.27% to 96.96%; the rank-2 cell adds ≈191 more. Recoverable counts assume rows in a fixed regime revert to the baseline mismatch rate. Risk differences carry Miettinen-Nurminen score CIs with an Agresti-Caffo guardrail fallback \[[Miettinen & Nurminen 1985](#ref-miettinen85), [Agresti & Caffo 2000](#ref-agresti00)\].

The same report also contains the supporting analyses that explain *why* each cell misbehaves (run the command above to see them all):

- **Exact Shapley feature attribution** — closed-form decomposition of the prediction formula for ≤12 features, deterministic sampling beyond \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\].
- **Regime contribution shares** — observed-contribution share of the rows matching each declared condition.
- **Mismatch risk** — condition-vs-rest risk ratios (Koopman, with Katz guardrail) and odds ratios (Baptista-Pike, with Haldane-Anscombe guardrail) for sparse 2×2 tables \[[Koopman 1984](#ref-koopman84), [Baptista & Pike 1977](#ref-baptista77), [Fagerland et al. 2015](#ref-fagerland15), [Fagerland et al. 2017](#ref-fagerland17)\]. Pass `ci_method="wald"` to `assess()` (or `--ci-method wald`) to force the legacy Katz / Haldane-Anscombe pair.
- **Factorial matrices, partition warnings, and within-stratum contrasts** — per-cell counts and rates for each declared crossing, plus sibling-level 2×2 contrasts.
- **Contributor ranking** — lift/share/score scoring for categorical contribution buckets.

## How it works

- `target`, `prediction`, and `score_mode` (`"absolute"` or `"signed"`) define the modeled quantity; `prediction_expr` defines the formula that Shapley decomposition explains.
- `prediction_features` is the only source of Shapley features: each entry pairs an explicit `actual` expression with a `baseline` expression.
- A `baseline` may reference other declared features by name, to state a *conditional* ideal — "what this feature should have been, given what the features it depends on actually did". Each reference resolves to the referenced feature's **coalition-resolved** value: its `actual` when that feature is in the coalition being scored, its own baseline otherwise. `actual` expressions may reference only input columns. See [Dependent baselines](#dependent-baselines).
- Every entry in `regimes` declares a regime: the rows matching its boolean `condition` form a subset whose observed-contribution share and mismatch risk (versus the rest, using `prediction != target`) are reported. Equality conditions are legal and analyzed only as regimes.
- `factorials` declares two-axis crossings; every `(row level, column level)` cell becomes a regime automatically. A crossing that also names a `baseline` cell gets the attributable burden ranking, and an optional `description` records what its levels mean.
- All expressions use a safe DSL — `col('Column Name')`, arithmetic, comparisons, `and`/`or`/`not`, ternary `a if cond else b`, and the functions `abs`, `bool`, `ceil`, `floor`, `float`, `int`, `log2`, `max`, `min`, `round`, `str` — with no arbitrary code execution.
- Conditions may additionally call `coalition_score('<player>', ...)`, which returns the error a row would still carry if only the named players were as observed and everything else were ideal. It is available **only** in `regimes` conditions and `factorials` axis level conditions; it is rejected in `target`, `prediction`, `prediction_expr`, and any `prediction_features` expression, because those define the quantity it measures. See [Conditioning on coalition scores](#conditioning-on-coalition-scores).

A condition only selects rows; severity is not weighted implicitly. To encode "how far off", declare separate bands (for example 10-20%, 20-40%, >40%).

Validation rules:

- Every free variable in `prediction_expr` must have a matching `prediction_features` entry, and every declared feature must be used by `prediction_expr`.
- Prediction feature names must not collide with regime names.
- The `actual == baseline` string shorthand is accepted only inside `prediction_features` (config files only); labeled features should use the explicit object form.
- Inside a feature's expressions, its own name binds to an input column when one exists, so naming a feature after the column it reads (`"x": {"actual": "x", ...}`) stays valid. Other names bind to a declared feature first, then an input column, then fail as unknown.
- Baseline references must form an acyclic graph, and an `actual` expression may not reference another feature.

### Dependent baselines

A plain `baseline` asserts what a feature should have been in isolation. When two features are two halves of one decision, that is the wrong question. In the bundled continuous-LoRa example the detector emits a single nominal `(BW, SF)` class from a scale-augmented lattice, and the prediction formula deliberately corrects the class SF using the measured bandwidth — so when the detector picks a *scaled* class, the correct `class_sf` is **not** `GT SF`:

```json
"class_sf": {
  "actual": "col('Class SF')",
  "baseline": "col('GT SF') - round(2 * log2(col('GT BW') / class_bw))"
},
"measured_bw": {
  "actual": "col('Measured BW')",
  "baseline": "col('GT BW')",
  "independent": true
}
```

That snippet is the **ungrouped** form of the example, kept here to show the mechanism; the shipped config supersedes it by making the class decision one player, which makes the dependent baseline redundant — see [Grouping or a dependent baseline?](#grouping-or-a-dependent-baseline).

`class_bw` inside that baseline is the coalition-resolved sibling, not the raw observed column. Writing `col('Class BW')` there instead pins it to the observed value in every coalition, so the empty coalition stops reproducing `target` and the reported shares stop summing to 100%.

Two things to know when reading the output:

- **A negative share is meaningful.** It means the feature *compensates* for others rather than contributing error. No player is net-compensating on the bundled example, but the mechanism is visible in its `class_unworkable & bw_shifts` cell: a bad measurement rescues a bad class in 12 of those 17 rows (29.41% mismatch against 75.69% when the measurement is neutral) — the detector's coherent `(BW, SF)` pairing partially cancels its own SF offset, which is exactly what the geometric-regression correction is for.
- **Do not over-reference.** A baseline should reference only the features whose state it conditions on, and use ground-truth columns for the rest. Had `class_sf.baseline` used `measured_bw` in place of `col('GT BW')`, it would become the algebraic inverse of `prediction_expr`, and every coalition leaving `class_sf` at baseline would score zero — burying the bandwidth-measurement error inside the baseline. The kit warns when it detects this (`formula_absorption`).

`independent: true` turns that warning into a fail-fast error. It declares that a feature sits in no dependency edge in **either** direction: nothing may reference it, and its own baseline may not reference another feature. Use it for features determined independently of the rest — here, `measured_bw` comes from bounding-box geometry and cannot inform what the detector's class SF should have been. Omitting it leaves a feature referenceable.

### Feature groups

A dependent baseline fixes a feature's *reference point*. It does not change the
fact that each feature is a separately togglable Shapley player — and that is
wrong when several features are one decision. The LoRa detector emits a single
nominal `(BW, SF)` class off a lattice, so a coalition holding the detector's SF
alongside a ground-truth BW class describes a class that does not exist.

`feature_groups` makes a set of features one **atomic** player. Members enter
and leave every coalition together, so no such state is ever scored:

```json
"feature_groups": {
  "class": {
    "label": "Nominal class decision (BW and SF chosen together)",
    "members": ["class_sf", "class_bw"]
  }
}
```

Members keep their own `actual` and `baseline`. The group is reported as one
contribution, listing its members; there is deliberately **no per-member split**,
because splitting a group would have to score exactly the states grouping
removes. Features left out of every group stay players in their own right.

This is not a new value. Partitioning players into blocks that act as units is a
*coalition structure* / *a priori unions* game \[[Aumann & Drèze 1974](#ref-aumann74),
[Owen 1977](#ref-owen77)\], and what the kit computes is plain Shapley on the
**quotient game** — the game in which each block is a single player,
`v^P(Q) = v(union of the blocks in Q)`. In ML terms it is groupShapley
\[[Jullum et al. 2021](#ref-jullum21)\], here over an explicit
`prediction_expr` and author-declared baselines \[[Sundararajan & Najmi 2020](#ref-sundararajan20)\]
rather than a black-box model; see also \[[Xu et al. 2025](#ref-xu25)\] for
baseline Shapley over feature groups on tree models.

The per-member alternative is the **Owen value** \[[Owen 1977](#ref-owen77)\],
which the kit deliberately does not compute. Nothing is lost at the group level:
the Owen value satisfies the quotient game property, so members' Owen values sum
to exactly the group figure reported here — on the bundled example both the plain
and the dependent baseline give Owen values summing to the reported `class`
contribution, while disagreeing sharply on the split. Only the split is declined,
and only because it is defined by the unrealizable states grouping removes.

Group rules: members must be declared features, a feature may belong to at most
one group, `members` may not be empty, and a group name may not collide with a
feature or regime name. A single-member group is allowed and is equivalent to
leaving the feature ungrouped. `max_exact_features` counts *players*, so
grouping can bring a large spec back within the exact Shapley path.

### Grouping or a dependent baseline?

They answer different questions, and reaching for both out of habit will
mis-state your analysis:

| | Use a dependent baseline | Use a feature group |
|---|---|---|
| Question | "How wrong was this feature, given what its dependencies did?" | "How wrong was this decision?" |
| When | Features are separately controllable, but one's ideal depends on another's state | Features cannot be manipulated independently; they are one choice |
| Reports | One contribution per feature | One contribution for the whole group |

On the bundled example the two give different, individually correct answers:
ungrouped with a dependent baseline splits the class into `class_sf` 60.90% and
`class_bw` 11.90%; grouping reports the class decision as a single 79.78%.
Neither corrects the other. The shipped config groups, because "fix `class_bw`
alone" is not an available action — you cannot change the bandwidth class
without changing the class that was picked.

Grouping does not merely make the dependent baseline optional here — it makes it
provably redundant. `class_sf`'s baseline is only ever evaluated in coalitions
where the `class` player is *out*, and then every member of the group is at its
baseline, so `class_bw` is `GT BW` and the correction term vanishes identically
on every row:

```
GT SF - round(2 * log2(GT BW / GT BW))  =  GT SF - round(2 * log2(1))  =  GT SF
```

Running the grouped example with the dependent baseline restored reproduces the
shipped config's output exactly — `class` 79.78%, `measured_bw` 20.22%, equal to
full float precision. The dependent baseline only ever corrected the split
coalitions `{class_sf}` and `{class_bw}`, which are the states grouping removes.
So `class_sf` reverting to a plain `col('GT SF')` in the shipped config is not a
regression against the archived `dependent-prediction-feature-baselines` change:
it is the same game, written without a term that is zero everywhere.

The mirror of the over-referencing trap applies: grouping features that really
are separable silently destroys per-feature signal, and unlike over-referencing
there is **no** numeric signature for it. Only group what is genuinely one
decision.

### Conditioning on coalition scores

Grouping and dependent baselines both fix how *features* are scored. Conditions
have the same problem one level up: a condition written over raw columns asks
about a column, and a column is often not something you can act on.

`coalition_score('<player>', ...)` lets a condition ask the question the Shapley
game already answers. It sets the named players to their observed values, leaves
every other player at its baseline, evaluates `prediction_expr`, and scores the
result against `target`:

```json
"regimes": {
  "class_unworkable": {
    "label": "Class decision the geometric regression cannot rescue",
    "condition": "coalition_score('class') != 0"
  }
}
```

Arguments are string literals naming **players**, so a grouped feature is
reachable only through its group — `coalition_score('class_sf')` is an error
naming `class`, because a coalition holding one member of a group while its
siblings sit at baseline is not a state the detector can produce. Names are
checked before the first row is read, so a typo fails once with the valid
players listed rather than once per row. Quoting also sidesteps Python's
grammar: `class` is a reserved word, and a bare identifier could never carry it.

`coalition_score()` with no arguments is the empty coalition. It must be zero on
every row; if it is not, your baselines do not reproduce `target`, every other
coalition score is measured from a shifted origin, and the `baseline_target_mismatch`
warning is already telling you so.

Under `score_mode: "absolute"` a coalition score is never negative, so `!= 0`
asks only *whether* a player caused error. Under `"signed"` the sign is kept, so
`> 0` and `< 0` split rows by the direction the player moves the estimate.

**This is not a Shapley value.** `coalition_score(S)` is the characteristic
function `v(S)` — one evaluation of the formula under one held state. A Shapley
value is an average of *differences* of `v` across the whole coalition lattice,
and is defined per row only as a decomposition of the observed error. Conditions
read `v`; the attribution table reports `φ`. A cell's mismatch rate and a
player's contribution share are separate quantities.

#### Two crossings, two questions

The bundled example declares both, since `factorials` is a list:

```json
{
  "label": "BW quality × scaling direction",
  "rows": { "class_ok": "...", "upscale": "...", "downscale": "..." },
  "columns": { "measured_ok": "...", "measured_off": "..." }
},
{
  "label": "Class decision × BW measurement",
  "baseline": { "rows": "class_workable", "columns": "bw_neutral" },
  "rows": {
    "class_workable":   "coalition_score('class') == 0",
    "class_unworkable": "coalition_score('class') != 0"
  },
  "columns": {
    "bw_neutral": "coalition_score('measured_bw') == 0",
    "bw_shifts":  "coalition_score('measured_bw') != 0"
  }
}
```

The first asks *which way* the detector misses — a real diagnostic question. The
second asks *which decision to fix*, and only the second ranks actions. Its
axes also partition by construction, so they cannot raise a partition warning.

The difference shows up in the burden ranking. The direction axis scatters the
379 rows whose class is genuinely unrecoverable across all three of its levels
(9/171/199), so no level isolates them; its 10% tolerance is also a hand-picked
number that disagrees with the formula's real flip point, which sits at a 41%
bandwidth ratio. The decision crossing separates them: 362 rows at 75.69%
mismatch where only the class is at fault (266.2 recoverable), 66 rows at
60.61% where only the measurement is (38.6 recoverable), and 17 rows at just 29.41%
where both are — because a bad measurement often *rescues* a bad class.

#### Describing a crossing

Level names are the crossing's identity — they compose cell names, resolve
`baseline`, and key every marginal, contrast, and burden record — so they stay
short, and the axis maps stay one line per level. That leaves nowhere to say
what `bw_neutral` means. An optional `description` on the crossing is that
place:

```json
{
  "label": "Class decision × BW measurement",
  "description": "Each axis holds one Shapley player at its observed value and every other player at its declared baseline — for measured_bw that baseline is col('GT BW'), i.e. an exact bandwidth measurement. Rows: class_workable means the observed class decision reaches GT SF once the bandwidth is measured exactly, so measuring better rescues it; class_unworkable means it misses GT SF even with an exact measurement ...",
  "rows": { "class_workable": "...", "class_unworkable": "..." },
  "columns": { "bw_neutral": "...", "bw_shifts": "..." }
}
```

One paragraph per crossing, not one label per level: it can say what both axes
are and what separates their levels in one place, and the grid above stays
readable. It renders under the crossing's matrix heading — where every level
name of the crossing appears together — and is carried on the matrix record in
`run.json`. Nothing validates that it still matches the axes, so it sits
directly above the levels it describes.

## Install

```bash
pip install -e .
```

Runtime dependency: `pyyaml>=6.0` (used by `contrib` for YAML config files; JSON configs work as well).

To use inside another project, add it as a git submodule:

```bash
git submodule add https://github.com/maisternia/contribution-kit.git path/to/contribution-kit
git submodule update --init path/to/contribution-kit
```

## Quick start (Python)

```python
from contribution import AttributionSpec, Estimator, FactorialCrossing, FeatureGroup, Regime, PredictionFeature

spec = AttributionSpec(
    target="col('GT SF')",
    prediction="col('Measured SF')",
    score_mode="absolute",  # interpret contributions as absolute amounts ("signed" keeps direction)
    prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",  # formula decomposed into Shapley contributions
    prediction_features={
        "class_sf": PredictionFeature(actual="col('Class SF')", baseline="col('GT SF')"),
        "class_bw": PredictionFeature(actual="col('Class BW')", baseline="col('GT BW')"),
        # Derived from box geometry, so nothing may condition its ideal on it.
        "measured_bw": PredictionFeature(
            actual="col('Measured BW')", baseline="col('GT BW')", independent=True
        ),
    },
    # The detector emits one (BW, SF) class, so the two are one Shapley player.
    feature_groups={
        "class": FeatureGroup(members=("class_sf", "class_bw"), label="Nominal class decision"),
    },
    regimes=[  # at least one regime is required; add any ad-hoc conditions you want reported
        Regime(name="class_sf_match", condition="col('Class SF') == col('GT SF')"),
        # Rows the geometric regression cannot rescue, asked of the game itself.
        Regime(name="class_unworkable", condition="coalition_score('class') != 0"),
    ],
    factorials=[
        FactorialCrossing(
            label="BW quality × scaling direction",
            rows={
                "class_ok": "abs(col('Class BW') - col('GT BW')) / col('GT BW') <= 0.10",
                "upscale": "col('Class BW') < col('GT BW') * (1 - 0.10)",
                "downscale": "col('Class BW') > col('GT BW') * (1 + 0.10)",
            },
            columns={
                "measured_ok": "abs(2 * log2(col('Measured BW') / col('GT BW'))) < 0.5",
                "measured_off": "abs(2 * log2(col('Measured BW') / col('GT BW'))) >= 0.5",
            },
            baseline={"rows": "class_ok", "columns": "measured_ok"},
        ),
        # Which way the detector misses (above) versus which decision to fix (below).
        FactorialCrossing(
            label="Class decision × BW measurement",
            rows={
                "class_workable": "coalition_score('class') == 0",
                "class_unworkable": "coalition_score('class') != 0",
            },
            columns={
                "bw_neutral": "coalition_score('measured_bw') == 0",
                "bw_shifts": "coalition_score('measured_bw') != 0",
            },
            baseline={"rows": "class_workable", "columns": "bw_neutral"},
        ),
    ],
)

result = Estimator.from_csv("examples/continuous_lora/measurements.csv", spec=spec).assess()
result.save("outputs/run_001")  # writes contribution.csv, run.json, report.md
```

Ad-hoc regimes are declared through `regimes` (at least one is required). `assess()` accepts `exact=True`, `max_exact_features=12`, `n_samples=512`, and `seed=0` to control the Shapley computation. `AssessmentResult` exposes `feature_attributions`, `regime_summaries`, `binary_results`, `factorial_matrices`, `contrast_results`, `burden_rankings`, and `attribution_warnings`, plus `to_csv`, `to_markdown`, `to_json`, and `save`.

## CLI

Commands are subcommands of `contrib` and can be run independently. For the main attribution output, you do not need to run everything.

**Minimal path (get results in one command):**

```bash
contrib run --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001
```

**Recommended path (safer):**

```bash
contrib validate --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv
contrib run      --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001
```

**Other commands (optional / independent):**

- `contributor` runs contributor-bucket ranking directly from input rows.
- `hypothesis` runs one explicit binary hypothesis test (group A vs group B).
- `help` prints a short workflow guide.

```bash
contrib contributor --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF') != col('GT SF')" --feature "class_sf:col('Class SF')" --out outputs/contributors.json
contrib hypothesis --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF') != col('GT SF')" --name "Class BW Underestimation" --group-a "col('Class BW') < col('GT BW')" --group-b "col('Class BW') >= col('GT BW')" --group-a-label "class_bw < gt_bw" --group-b-label "class_bw >= gt_bw" --out outputs/hypothesis.json
```

Config files are JSON or YAML with `target`, `prediction`, `prediction_expr`, required `prediction_features` (when `prediction_expr` uses variables), optional `feature_groups`, optional `scope` and `score_mode`, and a `regimes` mapping. Mapping keys are regime names and values are either a condition string shorthand or an object with `condition` and optional `label`.

```json
{
    "prediction_features": {
        "class_sf_match": "col('Class SF') == col('GT SF')",
        "class_bw": {
            "actual": "col('Class BW')",
            "baseline": "col('GT BW')",
            "label": "Nominal class BW"
        }
    },
    "regimes": {
        "class_bw_under": "col('Class BW') < col('GT BW') * (1 - 0.10)",
        "class_sf_correct": {
            "condition": "col('Class SF') == col('GT SF')",
            "label": "Class SF matches GT SF (regime)"
        }
    }
}
```

Config validation:

- Object-valued regimes must include `condition` and must not include `name` (the mapping key provides it).
- Feature objects must include `actual` and `baseline`, and may carry `label` and `independent`; a string entry must parse to exactly one top-level `actual == baseline` equality (no label, no other operators, though its right-hand side may reference sibling features). Unknown keys are rejected, so `independent` needs the object form.
- The old list form of `regimes` is not accepted.
- `feature_groups` entries must include a `members` list of declared feature names and may include a `label`. Unknown keys are rejected.

Optional factorial regime declarations:

- `factorials`: list of 2-axis crossings with inline level maps:
    - Each crossing is an object with `rows` (level map), `columns` (level map), optional `label`, optional `description`, and optional `baseline`:
    - `"factorials": [{"rows": {"level_a": "<bool expr>", "level_b": "<bool expr>"}, "columns": {"level_c": "<bool expr>", ...}, "label": "My Factorial"}]`
    - Baseline form: `"baseline": {"rows": "<row_level>", "columns": "<column_level>"}`
    - If `label` is omitted, a fallback label "Factorial <n>" is generated based on crossing position.
    - `description` is prose explaining what the crossing's levels mean. It renders under the crossing's matrix heading and is carried in the JSON matrix record. See [Describing a crossing](#describing-a-crossing).

Each crossing generates one regime cell per `(row_level, column_level)` with condition `(<row_cond>) and (<col_cond>)` and name `"<label>: rows=<row_level>, columns=<column_level>"`. Generated cells are appended to the same regime/risk pipeline used by declared non-equality regimes.

If factorials are present, reports add:

- `## Partition Warnings` when a factorial axis has overlaps or gaps over loaded rows
- `## Factorial Matrices` with per-cell count, mismatch rate, risk ratio vs rest, and union-based row/column marginals
- `## Within-stratum contrasts` with sibling-level pairwise contrasts inside each stratum using Koopman/Baptista-Pike intervals
- `## Attributable burden` per baselined crossing: rank, cell size, mismatch rate, recoverable mismatches, share of all mismatches, risk difference CI, and cumulative accuracy-if-eliminated

Burden table semantics:

- Recoverable mismatches for a cell are `n_cell * (p_cell - p_baseline)`.
- Non-positive recoverable cells are listed last and shown as not recoverable.
- Accuracy-if-eliminated is cumulative and always uses all dataset rows as denominator.
- Counterfactual caveat: recoverable counts assume rows in a fixed regime revert to the baseline mismatch rate.

The bundled [examples/continuous_lora/config.json](examples/continuous_lora/config.json) declares the baselined crossing that produces the burden ranking shown in [The result](#the-result).

## Testing

Install test dependencies and run the unit-coverage gate:

```bash
pip install -e '.[test]'
pytest tests/unit --cov=contribution --cov-branch --cov-fail-under=100
```

Test layout:

- `tests/unit/` contains exhaustive unit tests and is the required coverage gate.
- `tests/smoke/` contains lightweight API smoke checks (fast integration-style sanity tests).

Optional smoke run:

```bash
pytest tests/smoke
```

## Layout

```
src/contribution/  — reusable library
    spec.py               — AttributionSpec, Regime, PredictionFeature, FactorialCrossing
  estimator.py          — Estimator (from_csv, from_dataframe, assess); feature, regime, and burden analyses
  expr.py               — safe AST expression evaluator and free-variable discovery
  stats.py              — Koopman/Katz risk ratio, Baptista-Pike/Haldane-Anscombe odds ratio, Miettinen-Nurminen/Agresti-Caffo risk difference
  contributor.py        — contributor lift/share/score ranking
  hypothesis.py         — binary mismatch hypothesis test helpers
  results.py            — AssessmentResult → contribution.csv + report.md + run.json
  cli.py                — contrib CLI (help, validate, run, report, contributor, hypothesis)
tests/                  — pytest suite
  unit/                 — exhaustive unit tests and coverage gate
  smoke/                — lightweight API smoke checks
examples/               — example configs and data
  continuous_lora/      — config.json + measurements.csv (8,678-row real sample used in The result)
openspec/               — spec-driven development artifacts (see Generative AI usage notice)
  specs/                — current capability specifications
  changes/archive/      — every applied change: proposal.md, design.md, tasks.md, spec deltas
```

### Additional example datasets

The repository also includes a few smaller, more familiar life-domain examples under [examples/](examples):

- [household_temperature](examples/household_temperature)
- [rainy_walkway](examples/rainy_walkway)
- [grocery_shelf_count](examples/grocery_shelf_count)

Each folder ships a `config.json` and a matching `measurements.csv` that can be used directly with `contrib validate` and `contrib run`.

## References

<a id="ref-koopman84"></a>
[Koopman 1984] Koopman, P. A. R. (1984). Confidence intervals for the ratio of two binomial proportions. *Biometrics*, 40(2), 513–517.

<a id="ref-baptista77"></a>
[Baptista & Pike 1977] Baptista, J., & Pike, M. C. (1977). Algorithm AS 64: Exact two-sided confidence limits for the odds ratio in a 2×2 table. *Journal of the Royal Statistical Society, Series C (Applied Statistics)*, 26(2), 214–220.

<a id="ref-fagerland15"></a>
[Fagerland et al. 2015] Fagerland, M. W., Lydersen, S., & Laake, P. (2015). Recommended confidence intervals for two independent binomial proportions. *Statistical Methods in Medical Research*, 24(2), 224–254.

<a id="ref-fagerland17"></a>
[Fagerland et al. 2017] Fagerland, M. W., Lydersen, S., & Laake, P. (2017). *Statistical Analysis of Contingency Tables*. CRC Press.

<a id="ref-katz78"></a>
[Katz 1978] Katz, D., Baptista, J., Azen, S. P., & Pike, M. C. (1978). Obtaining confidence intervals for the risk ratio in cohort studies. *Biometrics*, 34(3), 469–474.

<a id="ref-haldane56"></a>
[Haldane 1956] Haldane, J. B. S. (1956). The estimation and significance of the logarithm of a ratio of frequencies. *Annals of Human Genetics*, 20(4), 309–311.

<a id="ref-anscombe56"></a>
[Anscombe 1956] Anscombe, F. J. (1956). On estimating binomial response relations. *Biometrika*, 43(3–4), 461–464.

<a id="ref-agresti13"></a>
[Agresti 2013] Agresti, A. (2013). *Categorical Data Analysis* (3rd ed.). Wiley.

<a id="ref-miettinen85"></a>
[Miettinen & Nurminen 1985] Miettinen, O., & Nurminen, M. (1985). Comparative analysis of two rates. *Statistics in Medicine*, 4(2), 213-226.

<a id="ref-agresti00"></a>
[Agresti & Caffo 2000] Agresti, A., & Caffo, B. (2000). Simple and effective confidence intervals for proportions and differences of proportions result from adding two successes and two failures. *The American Statistician*, 54(4), 280-288.

<a id="ref-shapley53"></a>
[Shapley 1953] Shapley, L. S. (1953). A value for n-person games. In *Contributions to the Theory of Games II* (pp. 307–317). Princeton University Press.

<a id="ref-lundberg17"></a>
[Lundberg & Lee 2017] Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems (NeurIPS)*, 30, 4765–4774.

<a id="ref-aumann74"></a>
[Aumann & Drèze 1974] Aumann, R. J., & Drèze, J. H. (1974). Cooperative games with coalition structures. *International Journal of Game Theory*, 3(4), 217–237.

<a id="ref-owen77"></a>
[Owen 1977] Owen, G. (1977). Values of games with a priori unions. In R. Henn & O. Moeschlin (Eds.), *Mathematical Economics and Game Theory: Essays in Honor of Oskar Morgenstern* (pp. 76–88). Springer.

<a id="ref-sundararajan20"></a>
[Sundararajan & Najmi 2020] Sundararajan, M., & Najmi, A. (2020). The many Shapley values for model explanation. *Proceedings of the 37th International Conference on Machine Learning (ICML)*, PMLR 119, 9269–9278.

<a id="ref-jullum21"></a>
[Jullum et al. 2021] Jullum, M., Redelmeier, A., & Aas, K. (2021). groupShapley: Efficient prediction explanation with Shapley values for feature groups. arXiv:2106.12228.

<a id="ref-xu25"></a>
[Xu et al. 2025] Xu, F., Zhou, Z.-J., Ni, J., & Gao, W. (2025). Interpretation with baseline Shapley value for feature groups on tree models. *Frontiers of Computer Science*, 19(5), 195316.

<a id="ref-dudarek26"></a>
[Dudarek & Martyniuk 2026] Dudarek, G., & Martyniuk, A. (2026). From Discrete to Continuous LoRa Parameter Estimation Using Vision-Based Deep Learning. *Preprint*. SSRN. http://ssrn.com/abstract=6891362

## Generative AI usage notice

In the spirit of the [Elsevier generative AI policy for authors](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals), the authors declare the following.

Everything in this repository — the source code, tests, CLI, example configurations, documentation, the OpenSpec proposals, designs, task lists, and specifications, this README, and this notice itself — was generated with GitHub Copilot, driven by several underlying models including Anthropic's Claude Fable 5, under the close control of the authors. The only exception is the measurement data bundled under [examples/continuous_lora/](examples/continuous_lora), which was produced by the experimental pipeline of \[[Dudarek & Martyniuk 2026](#ref-dudarek26)\] rather than by an AI tool.

Development followed spec-driven development (SDD) with [OpenSpec](https://github.com/Fission-AI/OpenSpec). Every capability was first captured as a proposal, a design, a task list, and a specification delta that the authors reviewed and approved before any code was applied. All SDD artifacts are retained in [openspec/](openspec): the current specifications live under `openspec/specs/`, and the complete change history, including the artifacts of every archived change, lives under `openspec/changes/archive/`, so each capability can be traced from its proposal to the code that implements it.

While the AI contribution is significant, the ideas, the decisions on methods, the CLI and configuration design, and the fine-tuning remain solely the credit and responsibility of the authors. The authors reviewed and edited all generated content as needed and take full responsibility for the content of this repository.

## License

MIT
