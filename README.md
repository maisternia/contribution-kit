# contribution-kit

[![GitHub](https://img.shields.io/badge/GitHub-maisternia%2Fcontribution--kit-blue)](https://github.com/maisternia/contribution-kit)

Answers *"what should we fix first?"* for any prediction pipeline. You declare failure **regimes** as boolean conditions over CSV columns and mark one factorial cell as the healthy **baseline**; the kit ranks every other cell by *recoverable mismatches* — how many errors would disappear if that cell reverted to the baseline rate — together with the accuracy you would reach by eliminating each cause.

> Running example: throughout this README the modeled quantity is a prediction *error* (`|prediction - target|`) on the bundled continuous-LoRa dataset \[[Dudarek & Martyniuk 2026](#ref-dudarek26)\]. Swap the expressions and `score_mode` and the same math attributes any positive or negative contribution.

## The result

One command over a CSV and a declarative config:

```bash
contrib run --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001
```

writes `contribution.csv`, `run.json`, and `report.md`. The centerpiece of the report is the **attributable burden ranking** — real output on the bundled 13,277-row dataset:

**BW quality × scaling direction** — baseline cell: `class_ok & measured_ok`

| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | class_ok & measured_off | 170 | 97.06% | 0.20% | 164.66 | 52.61% | 0.969 (0.931 to 0.985) | 98.88% |
| 2 | upscale & measured_ok | 464 | 17.03% | 0.20% | 78.06 | 24.94% | 0.168 (0.137 to 0.205) | 99.47% |
| 3 | downscale & measured_off | 35 | 57.14% | 0.20% | 19.93 | 6.37% | 0.569 (0.407 to 0.718) | 99.62% |
| 4 | upscale & measured_off | 12 | 100.00% | 0.20% | 11.98 | 3.83% | 0.998 (0.755 to 0.999) | 99.71% |
| 5 | downscale & measured_ok | 274 | 4.38% | 0.20% | 11.44 | 3.66% | 0.042 (0.023 to 0.073) | 99.80% |

Observed accuracy: 97.64% | Ceiling accuracy after ranked eliminations: 99.80% | Total observed mismatches: 313

Read it top-down as an intervention plan: fixing the rank-1 cell recovers ≈165 of the 313 observed mismatches and lifts accuracy from 97.64% to 98.88%; the rank-2 cell adds ≈78 more. Recoverable counts assume rows in a fixed regime revert to the baseline mismatch rate. Risk differences carry Miettinen-Nurminen score CIs with an Agresti-Caffo guardrail fallback \[[Miettinen & Nurminen 1985](#ref-miettinen85), [Agresti & Caffo 2000](#ref-agresti00)\].

The same report also contains the supporting analyses that explain *why* each cell misbehaves (run the command above to see them all):

- **Exact Shapley feature attribution** — closed-form decomposition of the prediction formula for ≤12 features, deterministic sampling beyond \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\].
- **Regime contribution shares** — observed-contribution share of the rows matching each declared condition.
- **Mismatch risk** — condition-vs-rest risk ratios (Koopman, with Katz guardrail) and odds ratios (Baptista-Pike, with Haldane-Anscombe guardrail) for sparse 2×2 tables \[[Koopman 1984](#ref-koopman84), [Baptista & Pike 1977](#ref-baptista77), [Fagerland et al. 2015](#ref-fagerland15), [Fagerland et al. 2017](#ref-fagerland17)\]. Pass `ci_method="wald"` to `assess()` (or `--ci-method wald`) to force the legacy Katz / Haldane-Anscombe pair.
- **Factorial matrices, partition warnings, and within-stratum contrasts** — per-cell counts and rates for each declared crossing, plus sibling-level 2×2 contrasts.
- **Contributor ranking** — lift/share/score scoring for categorical contribution buckets.

## How it works

- `target`, `prediction`, and `score_mode` (`"absolute"` or `"signed"`) define the modeled quantity; `prediction_expr` defines the formula that Shapley decomposition explains.
- `prediction_features` is the only source of Shapley features: each entry pairs an explicit `actual` expression with a `baseline` expression.
- Every entry in `regimes` declares a regime: the rows matching its boolean `condition` form a subset whose observed-contribution share and mismatch risk (versus the rest, using `prediction != target`) are reported. Equality conditions are legal and analyzed only as regimes.
- `factorials` declares two-axis crossings; every `(row level, column level)` cell becomes a regime automatically. A crossing that also names a `baseline` cell gets the attributable burden ranking.
- All expressions use a safe DSL — `col('Column Name')`, arithmetic, comparisons, `and`/`or`/`not`, ternary `a if cond else b`, and the functions `abs`, `bool`, `ceil`, `floor`, `float`, `int`, `log2`, `max`, `min`, `round`, `str` — with no arbitrary code execution.

A condition only selects rows; severity is not weighted implicitly. To encode "how far off", declare separate bands (for example 10-20%, 20-40%, >40%).

Validation rules:

- Every free variable in `prediction_expr` must have a matching `prediction_features` entry, and every declared feature must be used by `prediction_expr`.
- Prediction feature names must not collide with regime names.
- The `actual == baseline` string shorthand is accepted only inside `prediction_features` (config files only); labeled features should use the explicit object form.

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
from contribution import AttributionSpec, Estimator, FactorialCrossing, Regime, PredictionFeature

spec = AttributionSpec(
    target="col('GT SF')",
    prediction="col('Measured SF')",
    score_mode="absolute",  # interpret contributions as absolute amounts ("signed" keeps direction)
    prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",  # formula decomposed into Shapley contributions
    prediction_features={
        "class_sf": PredictionFeature(actual="col('Class SF')", baseline="col('GT SF')"),
        "class_bw": PredictionFeature(actual="col('Class BW')", baseline="col('GT BW')"),
        "measured_bw": PredictionFeature(actual="col('Measured BW')", baseline="col('GT BW')"),
    },
    regimes=[  # at least one regime is required; add any ad-hoc conditions you want reported
        Regime(name="class_sf_match", condition="col('Class SF') == col('GT SF')"),
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
        )
    ],
)

result = Estimator.from_csv("examples/continuous_lora/measurements.csv", spec=spec).assess()
result.save("outputs/run_001")  # writes contribution.csv, run.json, report.md
```

Ad-hoc regimes are declared through `regimes` (at least one is required). `assess()` accepts `exact=True`, `max_exact_features=12`, `n_samples=512`, and `seed=0` to control the Shapley computation. `AssessmentResult` exposes `feature_attributions`, `regime_summaries`, `binary_results`, `factorial_matrices`, `contrast_results`, and `burden_rankings`, plus `to_csv`, `to_markdown`, `to_json`, and `save`.

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

Config files are JSON or YAML with `target`, `prediction`, `prediction_expr`, required `prediction_features` (when `prediction_expr` uses variables), optional `scope` and `score_mode`, and a `regimes` mapping. Mapping keys are regime names and values are either a condition string shorthand or an object with `condition` and optional `label`.

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
- Feature objects must include `actual` and `baseline`; a string entry must parse to exactly one top-level `actual == baseline` equality (no label, no other operators). Unknown keys are rejected.
- The old list form of `regimes` is not accepted.

Optional factorial regime declarations:

- `factorials`: list of 2-axis crossings with inline level maps:
    - Each crossing is an object with `rows` (level map), `columns` (level map), optional `label`, and optional `baseline`:
    - `"factorials": [{"rows": {"level_a": "<bool expr>", "level_b": "<bool expr>"}, "columns": {"level_c": "<bool expr>", ...}, "label": "My Factorial"}]`
    - Baseline form: `"baseline": {"rows": "<row_level>", "columns": "<column_level>"}`
    - If `label` is omitted, a fallback label "Factorial <n>" is generated based on crossing position.

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
  continuous_lora/      — config.json + measurements.csv (13,277-row real sample used in The result)
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
