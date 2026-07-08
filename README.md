# contribution-kit

[![GitHub](https://img.shields.io/badge/GitHub-maisternia%2Fcontribution--kit-blue)](https://github.com/maisternia/contribution-kit)

Reusable Python toolkit for attributing a modeled quantity to user-defined hypotheses. The quantity is whatever you define through `target_expr`, `prediction_expr`, and `score_mode` — it can be a prediction *error*, but equally a reward, yield, deviation, or any signed contribution; the framing is entirely yours through the hypothesis conditions and how you name-interpret the results. You declare each hypothesis as a single boolean `condition` over CSV columns. The primary use case is directional or conditional **regimes** (e.g. "detected Height falls below GT Height"), whose observed-contribution share and condition-vs-rest mismatch risk are reported; top-level equality conditions are also supported as an extra **Shapley feature** of the prediction formula.

> Running example: throughout this README the modeled quantity is a prediction *error* (`|prediction - target|`), because that is the bundled dataset's use case. Swap the expressions and `score_mode` and the same math attributes any positive or negative contribution. See Dudarek & Martyniuk (2026) preprint for more information about the experiment used as the main example here \[[Dudarek & Martyniuk 2026](#ref-dudarek26)\].

## How it works

You declare every hypothesis with the single `Hypothesis` type — a `name` plus one boolean `condition` written in the safe DSL. The condition is used only to select rows (inside regime vs outside regime). After that selection, the estimator computes observed-contribution statistics on the selected rows and, if `mismatch_expr` is provided, compares mismatch rates between selected rows and the rest.

At a glance, the reported analyses are:

- **Shapley feature attribution** (feature-level decomposition of formula contribution)
- **Koopman risk-ratio intervals** (regime mismatch risk vs rest)
- **Baptista-Pike odds-ratio intervals** (sparse-table robust mismatch odds)


**Classification rule:** a hypothesis whose `condition` is a top-level equality (`==`) and whose `name` appears in `prediction_expr` becomes a Shapley feature; every other hypothesis is a regime. You never pick a type or set a flag — routing is derived entirely from the condition.

The two hypothesis-routing outputs are:

- **Regime (share + risk) — primary.** Any non-equality boolean condition declares a regime. The rows where it holds form a subset. For that subset, the toolkit reports observed-contribution share (`mean_contribution`, `total_contribution`, `contribution_share_pct`) and, when `mismatch_expr` is set, mismatch risk versus the remaining rows. Directional and conditional regimes are the main thing you declare.
- **Formula feature (Shapley) — extra.** A top-level equality `actual == baseline` declares a feature. The left operand is the model-produced value, the right operand is the ground-truth baseline, and the feature joins the exact Shapley attribution of the prediction-formula contribution. The feature `name` must appear in `prediction_expr`.

Callers never construct regimes or binary tests directly — they only declare conditions, and the relevant sub-results are populated automatically.

Mini-example (one regime):

- Condition: `col('Detected BW (Hz)') < col('GT BW (Hz)') * (1 - 0.10)`
- This condition only selects rows into group A (true) and group B (false/rest).
- Regime metrics (`mean_contribution`, `total_contribution`, `contribution_share_pct`) are computed from prediction-vs-target observed contribution over group A.
- Mismatch-risk metrics are computed from `mismatch_expr` rates in group A versus group B (for example, `col('Measured SF (ungated)') != col('GT SF')`).
- Therefore, "how far below" GT BW is not a direct weight by itself unless you encode severity explicitly (for example, separate bands such as 10-20%, 20-40%, >40%).

## Features

- **Safe expression DSL** — define hypotheses and formulas over CSV columns without executing arbitrary code. Supports `col('Column Name')`, arithmetic, comparisons, `and`/`or`/`not`, ternary `a if cond else b`, and the functions `abs`, `bool`, `ceil`, `floor`, `float`, `int`, `log2`, `max`, `min`, `round`, `str`.
- **Unified hypothesis model** — one flat list of `condition` strings drives regime shares, binary mismatch risk, and (for equality conditions) feature Shapley attribution.
- **Exact Shapley** — closed-form decomposition for ≤12 features; deterministic sampling fallback for larger sets \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\].
- **Binary effect sizes** — Koopman asymptotic-score risk-ratio CIs \[[Koopman 1984](#ref-koopman84), [Fagerland et al. 2015](#ref-fagerland15), [Fagerland et al. 2017](#ref-fagerland17)\] and Baptista-Pike exact odds-ratio CIs \[[Baptista & Pike 1977](#ref-baptista77), [Fagerland et al. 2017](#ref-fagerland17)\] for sparse 2×2 mismatch tables. If you need the legacy Katz / Haldane-Anscombe pair, pass `ci_method="wald"` to `assess()` or `--ci-method wald` to `contrib hypothesis`.
- **Contributor ranking** — reusable lift/share/score scoring for categorical contribution buckets.
- **CLI + Python API** — use from scripts, notebooks, or shell pipelines.

## Quick start

```python
from contribution import (
    AttributionSpec,
    Estimator,
    Hypothesis,
)

spec = AttributionSpec(
    target_expr="col('GT SF')",
    prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))", # is the formula you want to decompose — it defines what gets attributed to each Shapley feature.
    mismatch_expr="col('Measured SF (ungated)') != col('GT SF')", # may align with prediction-vs-target disagreement in some setups, but can also be independent (for example, tolerance exceedance or directional error event). 
    scope="sobel", # optional metadata for organizational purposes
    score_mode="absolute",  # or "signed", it just tells the attribution engine whether to interpret the resulting values as absolute amounts or as signed (directional) amounts when computing Shapley features and regime shares.
    hypotheses=[
        # Directional / conditional error regimes for risks and odds ratios (Koopman, Baptista-Pike)
        Hypothesis(
            name="class_bw < gt_bw (beyond tol)",
            condition="col('Detected BW (Hz)') < col('GT BW (Hz)') * (1 - 0.10)",
        ),
        Hypothesis(
            name="class_bw > gt_bw (beyond tol)",
            condition="col('Detected BW (Hz)') > col('GT BW (Hz)') * (1 + 0.10)",
        ),
        Hypothesis(
            name="class_bw within tol & sf wrong",
            condition=(
                "abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 "
                "and col('Detected SF') != col('GT SF')"
            ),
        ),
        Hypothesis(
            name="class_bw & sf ok, measured_bw off",
            condition=(
                "abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 "
                "and col('Detected SF') == col('GT SF') "
                "and abs(col('Measured BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') > 0.10"
            ),
        ),
        Hypothesis(
            name="class_bw & sf ok & measured ok (baseline)",
            condition=(
                "abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 "
                "and col('Detected SF') == col('GT SF') "
                "and abs(col('Measured BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10"
            ),
        ),
        # Top-level equalities whose name is in prediction_expr become Shapley features. No special type is required.
        Hypothesis(
            name="class_sf",
            condition="col('Detected SF') == col('GT SF')",
        ),
        Hypothesis(
            name="class_bw",
            condition="col('Detected BW (Hz)') == col('GT BW (Hz)')",
        ),
        Hypothesis(
            name="measured_bw",
            condition="col('Measured BW (Hz)') == col('GT BW (Hz)')",
        ),
    ],
)

result = Estimator.from_csv("examples/continuous_lora/measurements.csv", spec=spec).assess()
result.save("outputs/run_001")  # writes contribution.csv, run.json, report.md
```

`assess()` accepts `exact=True`, `max_exact_features=12`, `n_samples=512`, and `seed=0` to control the Shapley computation. `AssessmentResult` exposes `feature_attributions`, `regime_summaries`, and `binary_results`, plus `to_csv`, `to_markdown`, `to_json`, and `save`.

## Results

`save()` writes three files: `contribution.csv` (the feature-attribution table), `run.json` (the full machine-readable result), and `report.md`. The tables below are the real output of the Quick start spec on the bundled [examples/continuous_lora](examples/continuous_lora) dataset (13,277 rows of continuous-LoRa Sobel measurements). The prediction formula corresponds to formula (2.7), and the experimental data are referenced from \[[Dudarek & Martyniuk 2026](#ref-dudarek26)\].

**Feature attributions** — Shapley decomposition of the prediction-formula contribution \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\], one row per equality hypothesis, ranked by net contribution share:

| name | label | mean_abs_shapley | mean_signed_shapley | total_signed_shapley | net_contribution_share_pct |
|---|---:|---:|---:|---:|---:|
| measured_bw | Measured BW (box estimate vs GT BW) | 0.021215 | 0.019909 | 264.333333 | 69.20 |
| class_bw | Nominal class BW (detected vs GT BW) | 0.006804 | 0.004544 | 60.333333 | 15.79 |
| class_sf | Nominal class SF (detected vs GT SF) | 0.004620 | 0.004318 | 57.333333 | 15.01 |

**Regimes** — observed-contribution share of the rows matching each non-equality condition. These values come from prediction-vs-target observed contribution, not directly from `mismatch_expr`:

| regime | count | mean_contribution | total_contribution | contribution_share_pct |
|---|---:|---:|---:|---:|
| class_bw < gt_bw (beyond tol) | 476 | 0.1996 | 95.00 | 24.87 |
| class_bw > gt_bw (beyond tol) | 309 | 0.1165 | 36.00 | 9.42 |
| class_bw within tol & sf wrong | 23 | 1.2174 | 28.00 | 7.33 |
| class_bw & sf ok, measured_bw off | 497 | 0.4487 | 223.00 | 58.38 |
| class_bw & sf ok & measured ok (baseline) | 11972 | 0.0000 | 0.00 | 0.00% |

**Mismatch risk** — each regime's matching rows (group A) versus the rest (group B), using `mismatch_expr` as the mismatch indicator (for example, `col('Measured SF (ungated)') != col('GT SF')`), with Koopman risk ratios \[[Koopman 1984](#ref-koopman84), [Fagerland et al. 2015](#ref-fagerland15), [Fagerland et al. 2017](#ref-fagerland17)\] and Baptista-Pike odds ratios \[[Baptista & Pike 1977](#ref-baptista77), [Fagerland et al. 2017](#ref-fagerland17)\]:

| hypothesis | match mismatch rate | rest mismatch rate | risk ratio (95% CI) | odds ratio (95% CI) |
|---|---:|---:|---:|---:|
| class_bw < gt_bw (beyond tol) | 19.12% (91/476) | 1.73% (222/12801) | 11.02 (8.79 to 13.82) | 13.42 (10.31 to 17.47) |
| class_bw > gt_bw (beyond tol) | 10.36% (32/309) | 2.17% (281/12968) | 4.78 (3.38 to 6.77) | 5.28 (3.60 to 7.73) |
| class_bw within tol & sf wrong | 95.65% (22/23) | 2.20% (291/13254) | 43.57 (37.75 to 50.27) | 667.08 (127.23 to 3497.46) |
| class_bw & sf ok, measured_bw off | 33.80% (168/497) | 1.13% (145/12780) | 29.79 (24.31 to 36.51) | 44.41 (34.68 to 56.87) |

```
Rows: 13277
Mean observed contribution: 0.028772
```

If a regime has no matching rows (or no contrasting rest), it still appears in the contribution-share table but is omitted from the mismatch-risk table.

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

- `starter-config` writes a starter config file.
- `contributor` runs contributor-bucket ranking directly from input rows.
- `hypothesis` runs one explicit binary hypothesis test (group A vs group B).
- `help` prints a short workflow guide with the minimal and recommended command paths.

```bash
contrib help
contrib starter-config --out config.json
contrib validate  --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv
contrib run       --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001
contrib contributor --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF (ungated)') != col('GT SF')" --feature "detected_sf:col('Detected SF')" --out outputs/contributors.json
contrib hypothesis --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF (ungated)') != col('GT SF')" --name "Detected BW Underestimation" --group-a "col('Detected BW (Hz)') < col('GT BW (Hz)')" --group-b "col('Detected BW (Hz)') >= col('GT BW (Hz)')" --group-a-label "detected_bw < gt_bw" --group-b-label "detected_bw >= gt_bw" --out outputs/hypothesis.json
```

Config files are JSON or YAML with `target_expr`, `prediction_expr`, an optional `mismatch_expr`, optional `scope` and `score_mode`, and a `hypotheses` list. Each hypothesis entry is `{ "name", "condition", "label"? }`. Classification is derived only from the `condition`. See [examples/continuous_lora/config.json](examples/continuous_lora/config.json) and its [measurements.csv](examples/continuous_lora/measurements.csv).

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
    spec.py               — AttributionSpec, Hypothesis
  estimator.py          — Estimator (from_csv, from_dataframe, assess); private feature/regime routing
  expr.py               — safe AST expression evaluator and equality splitting
    stats.py              — Koopman risk ratio and Baptista-Pike odds ratio
  contributor.py        — contributor lift/share/score ranking
  hypothesis.py         — binary mismatch hypothesis test helpers
  results.py            — AssessmentResult (feature/regime/risk) → contribution.csv + report.md + run.json
    cli.py                — contrib CLI (starter-config, help, validate, run, report, contributor, hypothesis)
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

<a id="ref-shapley53"></a>
[Shapley 1953] Shapley, L. S. (1953). A value for n-person games. In *Contributions to the Theory of Games II* (pp. 307–317). Princeton University Press.

<a id="ref-lundberg17"></a>
[Lundberg & Lee 2017] Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems (NeurIPS)*, 30, 4765–4774.

<a id="ref-dudarek26"></a>
[Dudarek & Martyniuk 2026] Dudarek, G., & Martyniuk, A. (2026). From Discrete to Continuous LoRa Parameter Estimation Using Vision-Based Deep Learning. *Preprint*. SSRN. http://ssrn.com/abstract=6891362

## License

MIT
