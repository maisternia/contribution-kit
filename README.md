# contribution-kit

[![GitHub](https://img.shields.io/badge/GitHub-maisternia%2Fcontribution--kit-blue)](https://github.com/maisternia/contribution-kit)

Reusable Python toolkit for attributing a modeled quantity to user-defined hypotheses. The quantity is whatever you define through `target`, `prediction`, and `score_mode` for observed outcomes, plus `prediction_expr` for Shapley decomposition. It can be a prediction *error*, but equally a reward, yield, deviation, or any signed contribution; the framing is entirely yours through explicit prediction-feature declarations and regime conditions. You declare regimes as boolean `condition` expressions over CSV columns. The primary use case is directional or conditional **regimes** (e.g. "detected Height falls below GT Height"), whose observed-contribution share and condition-vs-rest mismatch risk are reported.

> Running example: throughout this README the modeled quantity is a prediction *error* (`|prediction - target|`), because that is the bundled dataset's use case. Swap the expressions and `score_mode` and the same math attributes any positive or negative contribution. See Dudarek & Martyniuk (2026) preprint for more information about the experiment used as the main example here \[[Dudarek & Martyniuk 2026](#ref-dudarek26)\].

## How it works

You declare every regime with the single `Hypothesis` type — a `name` plus one boolean `condition` written in the safe DSL. The condition is used only to select rows (inside regime vs outside regime). After that selection, the estimator computes observed-contribution statistics on the selected rows and compares mismatch rates between selected rows and the rest using `prediction != target`.

At a glance, the reported analyses are:

- **Shapley feature attribution** (feature-level decomposition of formula contribution)
- **Koopman risk-ratio intervals** (regime mismatch risk vs rest; with automatic Katz guardrail fallback only when Koopman inversion is non-finite/unordered for a finite point estimate)
- **Baptista-Pike odds-ratio intervals** (sparse-table robust mismatch odds; with automatic Haldane-Anscombe guardrail fallback only when exact inversion is non-finite/unordered for a finite point estimate)


**Classification rule:** `prediction_features` is the only source of Shapley features. Every entry in `hypotheses` is analyzed as a regime, including equality conditions.

The two output classes are:

- **Regime (share + risk) — primary.** Any boolean condition in `hypotheses` declares a regime. The rows where it holds form a subset. For that subset, the toolkit reports observed-contribution share (`mean_contribution`, `total_contribution`, `contribution_share_pct`) and mismatch risk versus the remaining rows.
- **Formula feature (Shapley) — explicit.** Each entry in `prediction_features` declares one feature with explicit `actual` and `baseline` expressions. Config files may also use a convenience shorthand string whose top-level expression is exactly `actual == baseline`; the loader normalizes it to the same internal feature shape, and labeled features should still use the explicit object form.

Validation and routing semantics:

- Every free variable in `prediction_expr` must have a matching `prediction_features` entry.
- Every declared prediction feature must be used by `prediction_expr`.
- Prediction feature names must not collide with hypothesis names.
- Equality conditions in `hypotheses` are still legal, but they are analyzed only as regimes.

Callers never construct regimes or binary tests directly — they only declare conditions, and the relevant sub-results are populated automatically.

Mini-example (one regime):

- Condition: `col('Class BW') < col('GT BW') * (1 - 0.10)`
- This condition only selects rows into group A (true) and group B (false/rest).
- Regime metrics (`mean_contribution`, `total_contribution`, `contribution_share_pct`) are computed from prediction-vs-target observed contribution over group A.
- Mismatch-risk metrics are computed from `prediction != target` rates in group A versus group B.
- Therefore, "how far below" GT BW is not a direct weight by itself unless you encode severity explicitly (for example, separate bands such as 10-20%, 20-40%, >40%).

## Features

- **Safe expression DSL** — define hypotheses and formulas over CSV columns without executing arbitrary code. Supports `col('Column Name')`, arithmetic, comparisons, `and`/`or`/`not`, ternary `a if cond else b`, and the functions `abs`, `bool`, `ceil`, `floor`, `float`, `int`, `log2`, `max`, `min`, `round`, `str`.
- **Explicit feature + regime model** — `prediction_features` declares Shapley features; `hypotheses` declares regimes; config files may use `lhs == rhs` shorthand only inside `prediction_features`.
- **Exact Shapley** — closed-form decomposition for ≤12 features; deterministic sampling fallback for larger sets \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\].
- **Binary effect sizes** — Koopman asymptotic-score risk-ratio CIs \[[Koopman 1984](#ref-koopman84), [Fagerland et al. 2015](#ref-fagerland15), [Fagerland et al. 2017](#ref-fagerland17)\] and Baptista-Pike exact odds-ratio CIs \[[Baptista & Pike 1977](#ref-baptista77), [Fagerland et al. 2017](#ref-fagerland17)\] for sparse 2×2 mismatch tables. For finite point estimates, if default interval inversion is non-finite or unordered, the toolkit applies an automatic guardrail fallback (Katz for risk ratio, Haldane-Anscombe for odds ratio) for that result only. If you need to force the legacy Katz / Haldane-Anscombe pair, pass `ci_method="wald"` to `assess()` or `--ci-method wald` to `contrib hypothesis`.
- **Attributable burden ranking** — for factorial crossings that declare a baseline cell, reports rank non-baseline cells by recoverable mismatches and cumulative accuracy-if-eliminated. Risk differences use Miettinen-Nurminen score CIs with Agresti-Caffo guardrail fallback \[[Miettinen & Nurminen 1985](#ref-miettinen85), [Agresti & Caffo 2000](#ref-agresti00)\].
- **Contributor ranking** — reusable lift/share/score scoring for categorical contribution buckets.
- **CLI + Python API** — use from scripts, notebooks, or shell pipelines.

## Quick start

```python
from contribution import (
    AttributionSpec,
    Estimator,
    Hypothesis,
    PredictionFeature,
)

spec = AttributionSpec(
    target="col('GT SF')",
    prediction="col('Measured SF')",
    prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))", # formula to decompose into Shapley contributions.
    prediction_features={
        "class_sf": PredictionFeature(
            actual="col('Class SF')",
            baseline="col('GT SF')",
            label="Nominal class SF (detected vs GT SF)",
        ),
        "class_bw": PredictionFeature(
            actual="col('Class BW')",
            baseline="col('GT BW')",
            label="Nominal class BW (detected vs GT BW)",
        ),
        "measured_bw": PredictionFeature(
            actual="col('Measured BW')",
            baseline="col('GT BW')",
            label="Measured BW (box estimate vs GT BW)",
        ),
    },
    scope="sobel", # optional metadata for organizational purposes
    score_mode="absolute",  # or "signed", it just tells the attribution engine whether to interpret the resulting values as absolute amounts or as signed (directional) amounts when computing Shapley features and regime shares.
    hypotheses=[
        # Directional / conditional error regimes for risks and odds ratios (Koopman, Baptista-Pike)
        Hypothesis(
            name="class_bw < gt_bw (upscale)",
            condition="col('Class BW') < col('GT BW') * (1 - 0.10)",
        ),
        Hypothesis(
            name="class_bw > gt_bw (downscale)",
            condition="col('Class BW') > col('GT BW') * (1 + 0.10)",
        ),
        Hypothesis(
            name="class_bw within tol & sf wrong",
            condition=(
                "abs(col('Class BW') - col('GT BW')) / col('GT BW') <= 0.10 "
                "and col('Class SF') != col('GT SF')"
            ),
        ),
        Hypothesis(
            name="class_bw & sf ok, measured_bw off",
            condition=(
                "abs(col('Class BW') - col('GT BW')) / col('GT BW') <= 0.10 "
                "and col('Class SF') == col('GT SF') "
                "and abs(col('Measured BW') - col('GT BW')) / col('GT BW') > 0.10"
            ),
        ),
        Hypothesis(
            name="class_bw & sf ok & measured ok (baseline)",
            condition=(
                "abs(col('Class BW') - col('GT BW')) / col('GT BW') <= 0.10 "
                "and col('Class SF') == col('GT SF') "
                "and abs(col('Measured BW') - col('GT BW')) / col('GT BW') <= 0.10"
            ),
        ),
        # Equality conditions are legal regimes when declared in hypotheses.
        Hypothesis(
            name="class_sf correct regime",
            condition="col('Class SF') == col('GT SF')",
        ),
    ],
)

result = Estimator.from_csv("examples/continuous_lora/measurements.csv", spec=spec).assess()
result.save("outputs/run_001")  # writes contribution.csv, run.json, report.md
```

`assess()` accepts `exact=True`, `max_exact_features=12`, `n_samples=512`, and `seed=0` to control the Shapley computation. `AssessmentResult` exposes `feature_attributions`, `regime_summaries`, and `binary_results`, plus `to_csv`, `to_markdown`, `to_json`, and `save`.

## Results

`save()` writes three files: `contribution.csv` (the feature-attribution table), `run.json` (the full machine-readable result), and `report.md`. The tables below are the real output of the Quick start spec on the bundled [examples/continuous_lora](examples/continuous_lora) dataset (13,277 rows of continuous-LoRa Sobel measurements). The prediction formula corresponds to formula (2.7), and the experimental data are referenced from \[[Dudarek & Martyniuk 2026](#ref-dudarek26)\].

**Feature attributions** — Shapley decomposition of the prediction-formula contribution \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\], one row per declared prediction feature, ranked by net contribution share:

| name | label | mean_abs_shapley | mean_signed_shapley | total_signed_shapley | net_contribution_share_pct |
|---|---:|---:|---:|---:|---:|
| measured_bw | Measured BW (box estimate vs GT BW) | 0.021215 | 0.019909 | 264.333333 | 69.20 |
| class_bw | Nominal class BW (detected vs GT BW) | 0.006804 | 0.004544 | 60.333333 | 15.79 |
| class_sf | Nominal class SF (detected vs GT SF) | 0.004620 | 0.004318 | 57.333333 | 15.01 |

**Regimes** — observed-contribution share of the rows matching each non-equality condition. These values come from prediction-vs-target observed contribution.

| regime | count | mean_contribution | total_contribution | contribution_share_pct |
|---|---:|---:|---:|---:|
| class_bw < gt_bw (upscale) | 476 | 0.1996 | 95.00 | 24.87 |
| class_bw > gt_bw (downscale) | 309 | 0.1165 | 36.00 | 9.42 |
| class_bw within tol & sf wrong | 23 | 1.2174 | 28.00 | 7.33 |
| class_bw & sf ok, measured_bw off | 497 | 0.4487 | 223.00 | 58.38 |
| class_bw & sf ok & measured ok (baseline) | 11972 | 0.0000 | 0.00 | 0.00% |

**Mismatch risk** — each regime's matching rows (group A) versus the rest (group B), using `prediction != target` as the mismatch indicator, with Koopman risk ratios \[[Koopman 1984](#ref-koopman84), [Fagerland et al. 2015](#ref-fagerland15), [Fagerland et al. 2017](#ref-fagerland17)\] and Baptista-Pike odds ratios \[[Baptista & Pike 1977](#ref-baptista77), [Fagerland et al. 2017](#ref-fagerland17)\]:

| hypothesis | Regime mismatch rate | Rest mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_bw < gt_bw (upscale) | 19.12% (91:385) | 1.73% (222:12579) | 11.02 (8.10 to 16.35) | 13.39 (10.16 to 17.54) |
| class_bw > gt_bw (downscale) | 10.36% (32:277) | 2.17% (281:12687) | 4.78 (3.27 to 7.16) | 5.22 (3.43 to 7.70) |
| class_bw within tol & sf wrong | 95.65% (22:1) | 2.20% (291:12963) | 43.57 (37.75 to 50.27) | 980.02 (156.82 to 40450.82) |
| class_bw & sf ok, measured_bw off | 33.80% (168:329) | 1.13% (145:12635) | 29.79 (24.31 to 36.51) | 44.50 (34.44 to 57.42) |

```
Rows: 13277
Mean observed contribution: 0.028772
```

If a regime has no matching rows, no contrasting rest, or zero mismatches in its matching rows, it still appears in the contribution-share table but is omitted from the mismatch-risk table.

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
- `help` prints a short workflow guide with the minimal and recommended command paths.

```bash
contrib help
contrib validate  --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv
contrib run       --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001
contrib contributor --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF') != col('GT SF')" --feature "class_sf:col('Class SF')" --out outputs/contributors.json
contrib hypothesis --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF') != col('GT SF')" --name "Class BW Underestimation" --group-a "col('Class BW') < col('GT BW')" --group-b "col('Class BW') >= col('GT BW')" --group-a-label "class_bw < gt_bw" --group-b-label "class_bw >= gt_bw" --out outputs/hypothesis.json
```

Config files are JSON or YAML with `target`, `prediction`, `prediction_expr`, required `prediction_features` (when `prediction_expr` uses variables), optional `scope` and `score_mode`, and a `hypotheses` mapping. Mapping keys are hypothesis names and values are either a condition string shorthand or an object with `condition` and optional `label`.

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
    "hypotheses": {
        "class_bw_under": "col('Class BW') < col('GT BW') * (1 - 0.10)",
        "class_sf_correct": {
            "condition": "col('Class SF') == col('GT SF')",
            "label": "Class SF matches GT SF (regime)"
        }
    }
}
```

Validation rules for object-valued hypotheses:

- The object must include `condition`.
- The object must not include `name` (the mapping key already provides it).

Validation rules for `prediction_features` entries:

- Each feature object must include `actual` and `baseline` string expressions.
- As a config-only convenience, a feature may instead be a string whose parsed top-level expression is exactly one `actual == baseline` equality.
- String shorthand does not carry a `label`; use the explicit object form whenever you need a custom label.
- Non-equality string forms such as `!=`, `<`, chained comparisons, or compound boolean expressions are rejected.
- Unknown keys are rejected.
- Every free variable in `prediction_expr` must be declared in `prediction_features`.
- Every declared feature must appear in `prediction_expr`.

Before/after migration example for old equality feature-hypotheses:

```json
{
    "prediction_expr": "class_sf + class_bw",
    "hypotheses": {
        "class_sf": "col('Class SF') == col('GT SF')",
        "class_bw": "col('Class BW') == col('GT BW')"
    }
}
```

```json
{
    "prediction_expr": "class_sf + class_bw",
    "prediction_features": {
        "class_sf": {"actual": "col('Class SF')", "baseline": "col('GT SF')"},
        "class_bw": {"actual": "col('Class BW')", "baseline": "col('GT BW')"}
    },
    "hypotheses": {
        "class_sf_correct": "col('Class SF') == col('GT SF')"
    }
}
```

Breaking change: the old list form of `hypotheses` is no longer accepted.

Optional factorial regime declarations:

- `factorials`: list of 2-axis crossings with inline level maps:
    - Each crossing is an object with `rows` (level map), `columns` (level map), optional `label`, and optional `baseline`:
    - `"factorials": [{"rows": {"level_a": "<bool expr>", "level_b": "<bool expr>"}, "columns": {"level_c": "<bool expr>", ...}, "label": "My Factorial"}]`
    - Baseline form: `"baseline": {"rows": "<row_level>", "columns": "<column_level>"}`
    - If `label` is omitted, a fallback label "Factorial <n>" is generated based on crossing position.

Each crossing generates one regime cell per `(row_level, column_level)` with condition `(<row_cond>) and (<col_cond>)` and name `"<label>: rows=<row_level>, columns=<column_level>"`. Generated cells are appended to the same regime/risk pipeline used by declared non-equality hypotheses.

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

See [examples/continuous_lora/config_factorial.json](examples/continuous_lora/config_factorial.json) and [examples/continuous_lora/measurements.csv](examples/continuous_lora/measurements.csv) for the factorial example inputs, and [build/bw_matrix_factorial/report.md](build/bw_matrix_factorial/report.md) plus [build/bw_matrix_factorial/run.json](build/bw_matrix_factorial/run.json) for the resulting report and structured results.

## Install

```bash
pip install -e .
```

Runtime dependency:

- `pyyaml>=6.0` (used by `contrib` for YAML config files; JSON configs work as well).

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

## Using as a submodule

You can add this repository as a git submodule in your own project:

```bash
git submodule add https://github.com/maisternia/contribution-kit.git path/to/contribution-kit
git submodule update --init path/to/contribution-kit
```

## Layout

```
src/contribution/  — reusable library
    spec.py               — AttributionSpec, Hypothesis, PredictionFeature
    estimator.py          — Estimator (from_csv, from_dataframe, assess); explicit feature + regime analyses
    expr.py               — safe AST expression evaluator and free-variable discovery
  stats.py              — Koopman risk ratio and Baptista-Pike odds ratio
  contributor.py        — contributor lift/share/score ranking
  hypothesis.py         — binary mismatch hypothesis test helpers
  results.py            — AssessmentResult (feature/regime/risk) → contribution.csv + report.md + run.json
  cli.py                — contrib CLI (help, validate, run, report, contributor, hypothesis)
tests/                  — pytest suite
  unit/                 — exhaustive unit tests and coverage gate
  smoke/                — lightweight API smoke checks
examples/               — example configs and data
  continuous_lora/      — config.json + measurements.csv (13,277-row real sample used in Results)
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

<a id="ref-dudarek26"></a>
[Dudarek & Martyniuk 2026] Dudarek, G., & Martyniuk, A. (2026). From Discrete to Continuous LoRa Parameter Estimation Using Vision-Based Deep Learning. *Preprint*. SSRN. http://ssrn.com/abstract=6891362

## License

MIT
