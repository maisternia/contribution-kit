# error-attribution-kit

[![GitHub](https://img.shields.io/badge/GitHub-maisternia%2Ferror--attribution--kit-blue)](https://github.com/maisternia/error-attribution-kit)

Reusable Python toolkit for attributing ML prediction error to user-defined hypotheses. You declare each hypothesis as a single boolean `condition` over CSV columns. The primary use case is directional or conditional **error regimes** (e.g. "detected BW falls below GT BW"), whose observed-error share and condition-vs-rest mismatch risk are reported; top-level equality conditions are also supported as an extra **Shapley feature** of the prediction formula.

## How it works

Every hypothesis is one boolean `condition` written in the safe DSL. The estimator inspects the shape of each condition and routes it to one of two analyses:

- **Error regime (share + risk) — primary.** Any non-equality boolean condition declares a regime. The rows where it holds form a subset whose observed-error share and mismatch risk (versus the remaining rows) are reported. Directional and conditional regimes are the main thing you declare.
- **Formula feature (Shapley) — extra.** A top-level equality `actual == baseline` declares a feature. The left operand is the model-produced value, the right operand is the ground-truth baseline, and the feature joins the exact Shapley attribution of the prediction-formula error. The feature `name` must appear in `prediction_expr`.

Callers never construct regimes or binary tests directly — they only declare conditions, and the relevant sub-results are populated automatically.

## Features

- **Safe expression DSL** — define hypotheses and formulas over CSV columns without executing arbitrary code. Supports `col('Column Name')`, arithmetic, comparisons, `and`/`or`/`not`, ternary `a if cond else b`, and the functions `abs`, `bool`, `ceil`, `floor`, `float`, `int`, `log2`, `max`, `min`, `round`, `str`.
- **Unified hypothesis model** — one flat list of `condition` strings drives error-regime shares, binary mismatch risk, and (for equality conditions) feature Shapley attribution.
- **Exact Shapley** — closed-form decomposition for ≤12 features; deterministic sampling fallback for larger sets \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\].
- **Binary effect sizes** — Katz log-transform risk-ratio CIs \[[Katz et al. 1978](#ref-katz78)\] and Haldane-Anscombe continuity-corrected odds-ratio CIs \[[Haldane 1956](#ref-haldane56), [Anscombe 1956](#ref-anscombe56), [Agresti 2013](#ref-agresti13)\] for sparse 2×2 mismatch tables.
- **Contributor ranking** — reusable lift/share/score scoring for categorical error buckets.
- **CLI + Python API** — use from scripts, notebooks, or shell pipelines.

## Quick start

```python
from error_attribution import (
    AttributionSpec,
    CategoricalHypothesis,
    ContinuousHypothesis,
    Estimator,
)

spec = AttributionSpec(
    target_expr="col('GT SF')",
    prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",
    mismatch_expr="col('Measured SF (ungated)') != col('GT SF')",
    scope="sobel",
    score_mode="absolute_error",  # or "signed_error"
    hypotheses=[
        # Primary use case: directional / conditional error regimes.
        ContinuousHypothesis(
            name="class_bw < gt_bw (beyond tol)",
            condition="col('Detected BW (Hz)') < col('GT BW (Hz)') * (1 - 0.10)",
        ),
        ContinuousHypothesis(
            name="class_bw > gt_bw (beyond tol)",
            condition="col('Detected BW (Hz)') > col('GT BW (Hz)') * (1 + 0.10)",
        ),
        ContinuousHypothesis(
            name="class_bw within tol & sf wrong",
            condition=(
                "abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 "
                "and col('Detected SF') != col('GT SF')"
            ),
        ),
        ContinuousHypothesis(
            name="class_bw & sf ok, measured_bw off",
            condition=(
                "abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 "
                "and col('Detected SF') == col('GT SF') "
                "and abs(col('Measured BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') > 0.10"
            ),
        ),
        # Extra capability: top-level equalities become Shapley features.
        # Each feature name must appear in prediction_expr.
        CategoricalHypothesis(
            name="class_sf",
            condition="col('Detected SF') == col('GT SF')",
        ),
        ContinuousHypothesis(
            name="class_bw",
            condition="col('Detected BW (Hz)') == col('GT BW (Hz)')",
        ),
        ContinuousHypothesis(
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

`save()` writes three files: `contribution.csv` (the feature-attribution table), `run.json` (the full machine-readable result), and `report.md`. The tables below are the real output of the Quick start spec on the bundled [examples/continuous_lora](examples/continuous_lora) dataset (13,277 rows of continuous-LoRa Sobel measurements).

**Feature attributions** — Shapley decomposition of the prediction-formula error \[[Shapley 1953](#ref-shapley53), [Lundberg & Lee 2017](#ref-lundberg17)\], one row per equality hypothesis, ranked by net error share:

| name | label | mean_abs_shapley | mean_signed_shapley | total_signed_shapley | net_error_share_pct |
|---|---:|---:|---:|---:|---:|
| measured_bw | Measured BW (box estimate vs GT BW) | 0.021215 | 0.019909 | 264.333333 | 69.20 |
| class_bw | Nominal class BW (detected vs GT BW) | 0.006804 | 0.004544 | 60.333333 | 15.79 |
| class_sf | Nominal class SF (detected vs GT SF) | 0.004620 | 0.004318 | 57.333333 | 15.01 |

**Error regimes** — observed-error share of the rows matching each non-equality condition:

| regime | count | mean_error | total_error | error_share_pct |
|---|---:|---:|---:|---:|
| class_bw < gt_bw (beyond tol) | 476 | 0.1996 | 95.00 | 24.87 |
| class_bw > gt_bw (beyond tol) | 309 | 0.1165 | 36.00 | 9.42 |
| class_bw within tol & sf wrong | 23 | 1.2174 | 28.00 | 7.33 |
| class_bw & sf ok, measured_bw off | 497 | 0.4487 | 223.00 | 58.38 |

**Mismatch risk** — each regime's matching rows (group A) versus the rest (group B), using `mismatch_expr`, with Katz risk ratios \[[Katz et al. 1978](#ref-katz78)\] and Haldane-Anscombe odds ratios \[[Haldane 1956](#ref-haldane56), [Anscombe 1956](#ref-anscombe56)\]:

| hypothesis | match mismatch rate | rest mismatch rate | risk ratio | odds ratio |
|---|---:|---:|---:|---:|
| class_bw < gt_bw (beyond tol) | 19.12% (91/476) | 1.73% (222/12801) | 11.02 | 13.42 |
| class_bw > gt_bw (beyond tol) | 10.36% (32/309) | 2.17% (281/12968) | 4.78 | 5.28 |
| class_bw within tol & sf wrong | 95.65% (22/23) | 2.20% (291/13254) | 43.57 | 667.08 |
| class_bw & sf ok, measured_bw off | 33.80% (168/497) | 1.13% (145/12780) | 29.79 | 44.41 |

```
Rows: 13277
Mean observed error: 0.028772
```

If a regime has no matching rows (or no contrasting rest), it still appears in the error-share table but is omitted from the mismatch-risk table.

## CLI

```bash
error-attrib init-config --out config.json --template ungated_sf
error-attrib validate  --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv
error-attrib run       --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001
error-attrib report    --run outputs/run_001/run.json --out outputs/run_001/report.md
error-attrib contributor --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF (ungated)') != col('GT SF')" --feature "detected_sf:col('Detected SF')" --out outputs/contributors.json
error-attrib hypothesis --input examples/continuous_lora/measurements.csv --mismatch-expr "col('Measured SF (ungated)') != col('GT SF')" --name "Detected BW Underestimation" --group-a "col('Detected BW (Hz)') < col('GT BW (Hz)')" --group-b "col('Detected BW (Hz)') >= col('GT BW (Hz)')" --group-a-label "detected_bw < gt_bw" --group-b-label "detected_bw >= gt_bw" --out outputs/hypothesis.json
```

Config files are JSON or YAML with `target_expr`, `prediction_expr`, an optional `mismatch_expr`, optional `scope` and `score_mode`, and a `hypotheses` list. Each hypothesis entry is `{ "name", "condition", "label"?, "kind"? }` where `kind` is `"continuous"` (default) or `"categorical"`. See [examples/continuous_lora/config.json](examples/continuous_lora/config.json) and its [measurements.csv](examples/continuous_lora/measurements.csv).

## Install

```bash
pip install -e .
```

## Using as a submodule

This repository is mounted as a git submodule in the [Unchirp](https://github.com/maisternia/Unchirp) workspace at `ultralytics-lora/ResearchData/external/error-attribution-kit`.

```bash
git submodule update --init ultralytics-lora/ResearchData/external/error-attribution-kit
```

## Layout

```
src/error_attribution/  — reusable library
  spec.py               — AttributionSpec, Hypothesis, ContinuousHypothesis, CategoricalHypothesis
  estimator.py          — Estimator (from_csv, from_dataframe, assess); private feature/regime routing
  expr.py               — safe AST expression evaluator and equality splitting
  stats.py              — Katz risk ratio and Haldane-Anscombe odds ratio
  contributor.py        — contributor lift/share/score ranking
  hypothesis.py         — binary mismatch hypothesis test helpers
  results.py            — AssessmentResult (feature/regime/risk) → contribution.csv + report.md + run.json
  cli.py                — error-attrib CLI (init-config, validate, run, report, contributor, hypothesis)
tests/                  — pytest suite (Shapley invariants, DSL, estimator, contributor, hypothesis, stats)
examples/               — example configs and data
  continuous_lora/      — config.json + measurements.csv (13,277-row real sample used in Results)
```

## References

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

## License

MIT
