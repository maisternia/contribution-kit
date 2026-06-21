# error-attribution-kit

[![GitHub](https://img.shields.io/badge/GitHub-maisternia%2Ferror--attribution--kit-blue)](https://github.com/maisternia/error-attribution-kit)

Reusable Python toolkit for attributing ML prediction error to user-defined categorical and continuous hypothesis sources using exact Shapley value decomposition.

## Features

- **Safe expression DSL** — define hypothesis formulas over CSV columns without executing arbitrary code.
- **Mixed source types** — combine categorical predicates (e.g. `(col('Detected BW (Hz)') * 1.10) < col('GT BW (Hz)')`) and continuous error measures in the same run.
- **Exact Shapley** — closed-form decomposition for ≤12 features; sampling fallback for larger sets.
- **Binary effect sizes** — Katz risk-ratio CIs and Haldane-Anscombe odds-ratio CIs for sparse 2x2 tables.
- **Contributor ranking** — reusable lift/share scoring for categorical error buckets.
- **CLI + Python API** — use from scripts, notebooks, or shell pipelines.

## Quick start

```python
from error_attribution import AttributionSpec, CategoricalHypothesis, ContinuousHypothesis, Estimator

spec = AttributionSpec(
    target_expr="col('GT SF')",
    prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",
    hypotheses=[
        CategoricalHypothesis(
            name="class_sf",
            actual_expr="col('Detected SF')",
            baseline_expr="col('GT SF')",
        ),
        ContinuousHypothesis(
            name="measured_bw",
            actual_expr="col('Measured BW (Hz)')",
            baseline_expr="col('GT BW (Hz)')",
        ),
    ],
)
result = Estimator.from_csv("measurements.csv", spec=spec).assess()
result.save("outputs/run_001")
```

## CLI

```bash
error-attrib init-config --out config.json --template ungated_sf
error-attrib validate  --config config.json --input measurements.csv
error-attrib run       --config config.json --input measurements.csv --out outputs/run_001
error-attrib report    --run outputs/run_001/run.json --out outputs/run_001/report.md
error-attrib contributor --input measurements.csv --mismatch-expr "col('Measured SF (ungated)') != col('GT SF')" --feature "detected_sf:col('Detected SF')" --out outputs/contributors.json
error-attrib hypothesis --input measurements.csv --mismatch-expr "col('Measured SF (ungated)') != col('GT SF')" --name "Detected BW Underestimation" --group-a "col('Detected BW (Hz)') < col('GT BW (Hz)')" --group-b "col('Detected BW (Hz)') >= col('GT BW (Hz)')" --group-a-label "detected_bw < gt_bw" --group-b-label "detected_bw >= gt_bw" --out outputs/hypothesis.json
```

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
  spec.py               — AttributionSpec, ContinuousHypothesis, CategoricalHypothesis
  estimator.py          — Estimator (from_csv, from_dataframe, assess)
  expr.py               — safe AST expression evaluator
    stats.py              — Katz risk ratio and Haldane-Anscombe odds ratio
    contributor.py        — contributor lift/share/score ranking
    hypothesis.py         — binary hypothesis test helpers
  results.py            — AssessmentResult.save() → CSV + Markdown + JSON
    cli.py                — error-attrib CLI (init-config, validate, run, report, contributor, hypothesis)
tests/                  — pytest suite with Shapley invariant checks
examples/               — example JSON config files
```

## License

MIT
