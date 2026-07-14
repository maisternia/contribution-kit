from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from contribution.estimator import _parse_scalar, _score
from contribution.spec import AttributionSpec, Factor, FactorialCrossing, Hypothesis
from contribution import Estimator


def _write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "rows.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _spec() -> AttributionSpec:
    return AttributionSpec(
        target="col('GT SF')",
        prediction="col('Measured SF (ungated)')",
        prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",
        scope="sobel",
        hypotheses=[
            Hypothesis(name="class_sf", condition="col('Detected SF') == col('GT SF')"),
            Hypothesis(name="class_bw", condition="col('Detected BW (Hz)') == col('GT BW (Hz)')"),
            Hypothesis(name="measured_bw", condition="col('Measured BW (Hz)') == col('GT BW (Hz)')"),
            Hypothesis(name="under", condition="col('Detected BW (Hz)') < col('GT BW (Hz)')"),
        ],
    )


def _rows() -> list[dict[str, str]]:
    return [
        {
            "GT SF": "9",
            "Detected SF": "9",
            "Measured SF (ungated)": "9",
            "GT BW (Hz)": "125000",
            "Detected BW (Hz)": "125000",
            "Measured BW (Hz)": "125000",
        },
        {
            "GT SF": "9",
            "Detected SF": "10",
            "Measured SF (ungated)": "10",
            "GT BW (Hz)": "125000",
            "Detected BW (Hz)": "100000",
            "Measured BW (Hz)": "110000",
        },
    ]


def test_parse_scalar() -> None:
    assert _parse_scalar("") is None
    assert _parse_scalar(" true ") is True
    assert _parse_scalar("10") == 10
    assert _parse_scalar("10.5") == 10.5
    assert _parse_scalar("hello") == "hello"


def test_score_modes() -> None:
    assert _score(4.0, 1.0, "signed") == 3.0
    assert _score(1.0, 4.0, "absolute") == 3.0


def test_from_dataframe_variants_and_errors() -> None:
    spec = _spec()
    rows = [{"x": 1}]
    assert Estimator.from_dataframe(rows, spec=spec).rows == rows

    class FauxDF:
        def to_dict(self, orient: str):
            assert orient == "records"
            return [{"x": 1}]

    assert Estimator.from_dataframe(FauxDF(), spec=spec).rows == [{"x": 1}]

    with pytest.raises(TypeError, match="Unsupported dataframe-like object"):
        Estimator.from_dataframe(123, spec=spec)


def test_validate_spec_errors() -> None:
    est = Estimator(rows=[])
    with pytest.raises(ValueError, match="Attribution spec is required"):
        est.assess()

    est.spec = AttributionSpec(target="1", prediction="1", prediction_expr="1", hypotheses=[])
    with pytest.raises(ValueError, match="At least one hypothesis"):
        est.assess()

    est.spec = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="1",
        hypotheses=[Hypothesis(name="dup", condition="1==1"), Hypothesis(name="dup", condition="1==1")],
    )
    with pytest.raises(ValueError, match="unique"):
        est.assess()


def test_assess_exact_and_sampled_and_regime_none_paths(tmp_path: Path) -> None:
    spec = _spec()
    csv_path = _write_csv(tmp_path, _rows())
    est = Estimator.from_csv(csv_path, spec=spec)

    exact = est.assess(exact=True, max_exact_features=12)
    sampled = est.assess(exact=True, max_exact_features=1, n_samples=8, seed=7)

    assert exact.n_rows == 2
    assert sampled.n_rows == 2
    assert any(item.analysis == "feature" for item in exact.hypotheses)
    assert any(item.analysis == "regime" for item in exact.hypotheses)

    # single-group path => risk is None
    single_group = AttributionSpec(
        target="0",
        prediction="0",
        prediction_expr="0",
        hypotheses=[Hypothesis(name="all", condition="1 == 1")],
    )
    est3 = Estimator(rows=[{}], spec=single_group)
    assessed_single = est3.assess()
    assert assessed_single.hypotheses[0].risk is None


def test_assess_allows_spec_override() -> None:
    rows = [{"y": 1, "x": 1}]
    base = AttributionSpec(target="y", prediction="x", prediction_expr="x", hypotheses=[Hypothesis(name="h", condition="x == y")])
    replacement = AttributionSpec(target="y", prediction="x", prediction_expr="x", hypotheses=[Hypothesis(name="h2", condition="x == y")])
    estimator = Estimator.from_dataframe(rows, base)
    result = estimator.assess(spec=replacement)
    assert result.hypotheses[0].name == "h2"


def test_regime_risk_none_when_group_b_missing() -> None:
    rows = [{"g": "A", "mismatch": False}, {"g": "A", "mismatch": True}]
    spec = AttributionSpec(
        target="0",
        prediction="mismatch",
        prediction_expr="0",
        hypotheses=[Hypothesis(name="all_a", condition="g != 'B'")],
    )
    result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    assert result.binary_results == []


def test_assess_spec_override_on_empty_rows() -> None:
    replacement = AttributionSpec(target="0", prediction="0", prediction_expr="0", hypotheses=[Hypothesis(name="h", condition="1 == 1")])
    estimator = Estimator(rows=[], spec=None)
    result = estimator.assess(spec=replacement)
    assert result.n_rows == 0


def _factorial_rows() -> list[dict[str, object]]:
    return [
        {"target": 0, "prediction": 0, "row": "up", "quality": "ok", "f": 1},
        {"target": 0, "prediction": 1, "row": "up", "quality": "off", "f": 1},
        {"target": 0, "prediction": 1, "row": "down", "quality": "ok", "f": 1},
        {"target": 0, "prediction": 1, "row": "down", "quality": "off", "f": 1},
    ]


def _factorial_spec() -> AttributionSpec:
    return AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="f",
        hypotheses=[Hypothesis(name="f", condition="f == f")],
        factors={
            "row_axis": Factor(name="row_axis", levels={"up": "row == 'up'", "down": "row == 'down'"}),
            "col_axis": Factor(name="col_axis", levels={"ok": "quality == 'ok'", "off": "quality == 'off'"}),
        },
        factorials=[FactorialCrossing(rows="row_axis", columns="col_axis")],
    )


def test_factorial_expansion_matrix_and_contrasts() -> None:
    result = Estimator.from_dataframe(_factorial_rows(), _factorial_spec()).assess(exact=True)

    names = [item.name for item in result.hypotheses]
    assert "up & ok" in names
    assert "down & off" in names
    assert len(result.factorial_matrices) == 1
    matrix = result.factorial_matrices[0]
    assert matrix.rows_axis == "row_axis"
    assert matrix.columns_axis == "col_axis"
    assert len(matrix.cells) == 4
    assert len(result.contrast_results) == 4


def test_factorial_generated_name_collision_error() -> None:
    spec = _factorial_spec()
    spec.hypotheses.append(Hypothesis(name="up & ok", condition="row == 'up' and col == 'ok'"))
    with pytest.raises(ValueError, match="name collision"):
        Estimator.from_dataframe(_factorial_rows(), spec).assess(exact=True)


def test_factorial_partition_warning_and_unused_axis_warning() -> None:
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="f",
        hypotheses=[Hypothesis(name="f", condition="f == f")],
        factors={
            "row_axis": Factor(name="row_axis", levels={"up": "row == 'up'", "also_up": "row == 'up'"}),
            "col_axis": Factor(name="col_axis", levels={"ok": "quality == 'ok'", "off": "quality == 'off'"}),
            "unused_axis": Factor(name="unused_axis", levels={"x": "1 == 1"}),
        },
        factorials=[FactorialCrossing(rows="row_axis", columns="col_axis")],
    )
    with pytest.warns(UserWarning, match="unused"):
        with pytest.warns(UserWarning, match="not a strict partition"):
            result = Estimator.from_dataframe(_factorial_rows(), spec).assess(exact=True)
    assert result.partition_warnings
    assert result.partition_warnings[0].axis == "row_axis"
    assert result.partition_warnings[0].overlap_count == 2
    assert result.partition_warnings[0].gap_count == 2


def test_contrast_sparse_case_keeps_positive_odds_ratio() -> None:
    rows = [
        {"target": 0, "prediction": 0, "row": "up", "quality": "ok", "f": 1},
        {"target": 0, "prediction": 0, "row": "up", "quality": "ok", "f": 1},
        {"target": 0, "prediction": 1, "row": "up", "quality": "off", "f": 1},
        {"target": 0, "prediction": 1, "row": "up", "quality": "off", "f": 1},
        {"target": 0, "prediction": 0, "row": "down", "quality": "ok", "f": 1},
        {"target": 0, "prediction": 1, "row": "down", "quality": "off", "f": 1},
    ]
    result = Estimator.from_dataframe(rows, _factorial_spec()).assess(exact=True)
    up_stratum = [item for item in result.contrast_results if item.stratum.endswith("row_axis=up")]
    assert up_stratum
    contrast = up_stratum[0]
    assert contrast.mismatch_count_a == 0
    assert contrast.odds_ratio > 0.0


def test_factor_free_run_json_keeps_legacy_top_level_keys(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path, _rows())
    result = Estimator.from_csv(csv_path, _spec()).assess(exact=True)
    out = tmp_path / "run.json"
    result.to_json(out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert sorted(payload.keys()) == [
        "binary_results",
        "feature_attributions",
        "hypotheses",
        "mean_observed_contribution",
        "metadata",
        "n_rows",
        "regime_summaries",
    ]
