from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from contribution.estimator import _parse_scalar, _score
from contribution.spec import AttributionSpec, FactorialCrossing, Hypothesis, PredictionFeature
from contribution import Estimator


def _write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "rows.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            # Parse scalar values where possible
            parsed_row = {}
            for key, value in row.items():
                parsed_row[key] = _parse_scalar(value)
            rows.append(parsed_row)
    return rows


def _spec() -> AttributionSpec:
    return AttributionSpec(
        target="col('GT SF')",
        prediction="col('Measured SF (ungated)')",
        prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",
        prediction_features={
            "class_sf": PredictionFeature(actual="col('Detected SF')", baseline="col('GT SF')"),
            "class_bw": PredictionFeature(actual="col('Detected BW (Hz)')", baseline="col('GT BW (Hz)')"),
            "measured_bw": PredictionFeature(actual="col('Measured BW (Hz)')", baseline="col('GT BW (Hz)')"),
        },
        scope="sobel",
        regimes=[Hypothesis(name="under", condition="col('Detected BW (Hz)') < col('GT BW (Hz)')")],
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

    est.spec = AttributionSpec(target="1", prediction="1", prediction_expr="1", regimes=[])
    with pytest.raises(ValueError, match="At least one regime"):
        est.assess()

    est.spec = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="1",
        regimes=[Hypothesis(name="dup", condition="1==1"), Hypothesis(name="dup", condition="1==1")],
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
    assert any(item.analysis == "feature" for item in exact.regimes)
    assert any(item.analysis == "regime" for item in exact.regimes)

    # single-group path => risk is None
    single_group = AttributionSpec(
        target="0",
        prediction="0",
        prediction_expr="0",
        regimes=[Hypothesis(name="all", condition="1 == 1")],
    )
    est3 = Estimator(rows=[{}], spec=single_group)
    assessed_single = est3.assess()
    assert assessed_single.regimes[0].risk is None


def test_assess_allows_spec_override() -> None:
    rows = [{"y": 1, "x": 1}]
    base = AttributionSpec(
        target="y",
        prediction="x",
        prediction_expr="x",
        prediction_features={"x": PredictionFeature(actual="x", baseline="y")},
        regimes=[Hypothesis(name="h", condition="x == y")],
    )
    replacement = AttributionSpec(
        target="y",
        prediction="x",
        prediction_expr="x",
        prediction_features={"x": PredictionFeature(actual="x", baseline="y")},
        regimes=[Hypothesis(name="h2", condition="x == y")],
    )
    estimator = Estimator.from_dataframe(rows, base)
    result = estimator.assess(spec=replacement)
    assert result.regimes[1].name == "h2"


def test_regime_risk_none_when_group_b_missing() -> None:
    rows = [{"g": "A", "mismatch": False}, {"g": "A", "mismatch": True}]
    spec = AttributionSpec(
        target="0",
        prediction="mismatch",
        prediction_expr="0",
        regimes=[Hypothesis(name="all_a", condition="g != 'B'")],
    )
    result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    assert result.binary_results == []


def test_assess_spec_override_on_empty_rows() -> None:
    replacement = AttributionSpec(target="0", prediction="0", prediction_expr="0", regimes=[Hypothesis(name="h", condition="1 == 1")])
    estimator = Estimator(rows=[], spec=None)
    result = estimator.assess(spec=replacement)
    assert result.n_rows == 0


def test_factorial_expansion_matrix_and_contrasts() -> None:
    # Test using the new inline factorial crossing format
    rows = [
        {"target": 1, "prediction": 1, "row": "up", "quality": "ok", "f": 0},
        {"target": 1, "prediction": 1, "row": "up", "quality": "off", "f": 1},
        {"target": 1, "prediction": 0, "row": "down", "quality": "ok", "f": 1},
        {"target": 1, "prediction": 0, "row": "down", "quality": "off", "f": 1},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="f", baseline="0")},
        regimes=[Hypothesis(name="all_rows", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"up": "col('row') == 'up'", "down": "col('row') == 'down'"},
                columns={"ok": "col('quality') == 'ok'", "off": "col('quality') == 'off'"},
                label="Row × Quality"
            )
        ],
    )
    result = Estimator.from_dataframe(rows, spec).assess(exact=True)

    # Check factorial matrix was created with correct label
    assert len(result.factorial_matrices) == 1
    matrix = result.factorial_matrices[0]
    assert matrix.label == "Row × Quality"
    assert len(matrix.cells) == 4
    # Contrasts should be generated
    assert len(result.contrast_results) > 0
    for contrast in result.contrast_results:
        assert contrast.factorial == "Row × Quality"


def test_factorial_generated_name_collision_error() -> None:
    rows = [
        {"target": 1, "prediction": 1, "row": "up", "quality": "ok", "f": 0},
        {"target": 1, "prediction": 0, "row": "down", "quality": "off", "f": 1},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="f", baseline="0")},
        regimes=[Hypothesis(name="up & ok", condition="col('row') == 'up' and col('quality') == 'ok'")],
        factorials=[
            FactorialCrossing(
                rows={"up": "col('row') == 'up'", "down": "col('row') == 'down'"},
                columns={"ok": "col('quality') == 'ok'", "off": "col('quality') == 'off'"},
            )
        ],
    )
    # Cell names generated by factorials should not collide with regime names
    with pytest.raises(ValueError, match="name collision|already declared"):
        Estimator.from_dataframe(rows, spec).assess(exact=True)


def test_factorial_partition_warning() -> None:
    rows = [
        {"target": 1, "prediction": 1, "row": "up", "quality": "ok", "f": 0},
        {"target": 1, "prediction": 1, "row": "up", "quality": "off", "f": 1},
        {"target": 1, "prediction": 0, "row": "down", "quality": "ok", "f": 1},
        {"target": 1, "prediction": 0, "row": "down", "quality": "off", "f": 1},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="f", baseline="0")},
        regimes=[Hypothesis(name="all_rows", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"up": "col('row') == 'up'", "also_up": "col('row') == 'up'"},  # Overlap!
                columns={"ok": "col('quality') == 'ok'", "off": "col('quality') == 'off'"},
                label="Overlapped"
            )
        ],
    )
    with pytest.warns(UserWarning, match="not a strict partition"):
        result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    assert result.partition_warnings
    # Partition warning should identify the crossing by label and axis role
    assert any("Overlapped" in w.axis for w in result.partition_warnings)
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
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="f", baseline="0")},
        regimes=[Hypothesis(name="all_rows", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"up": "col('row') == 'up'", "down": "col('row') == 'down'"},
                columns={"ok": "col('quality') == 'ok'", "off": "col('quality') == 'off'"},
                label="Row × Quality"
            )
        ],
    )
    result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    # With new stratum format, look for contrasts in "rows=up" stratum
    up_stratum = [item for item in result.contrast_results if item.stratum == "rows=up"]
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
        "mean_observed_contribution",
        "metadata",
        "n_rows",
        "regime_summaries",
        "regimes",
    ]


def test_validate_spec_errors_for_undeclared_prediction_expr_variable() -> None:
    spec = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="missing_feature",
        regimes=[Hypothesis(name="h", condition="1 == 1")],
    )
    with pytest.raises(ValueError, match=r"undeclared prediction feature\(s\): missing_feature"):
        Estimator.from_dataframe([{}], spec).assess(exact=True)


def test_validate_spec_errors_for_unused_prediction_feature() -> None:
    spec = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="1",
        prediction_features={"unused": PredictionFeature(actual="1", baseline="0")},
        regimes=[Hypothesis(name="h", condition="1 == 1")],
    )
    with pytest.raises(ValueError, match="unused by prediction_expr: unused"):
        Estimator.from_dataframe([{}], spec).assess(exact=True)


def test_validate_spec_errors_for_prediction_feature_hypothesis_name_collision() -> None:
    spec = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="dup",
        prediction_features={"dup": PredictionFeature(actual="1", baseline="0")},
        regimes=[Hypothesis(name="dup", condition="1 == 1")],
    )
    with pytest.raises(ValueError, match="must not collide with regime names: dup"):
        Estimator.from_dataframe([{}], spec).assess(exact=True)


def test_factorial_expansion_with_inline_axes_and_explicit_label(tmp_path: Path) -> None:
    data_path = _write_csv(
        tmp_path,
        [
            {"gt": "1", "pred": "1", "row": "A", "col": "X"},
            {"gt": "1", "pred": "1", "row": "B", "col": "X"},
            {"gt": "1", "pred": "1", "row": "A", "col": "Y"},
            {"gt": "1", "pred": "1", "row": "B", "col": "Y"},
        ],
    )
    spec = AttributionSpec(
        target="col('gt')",
        prediction="col('pred')",
        prediction_expr="1",
        regimes=[Hypothesis(name="h", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"A": "col('row') == 'A'", "B": "col('row') == 'B'"},
                columns={"X": "col('col') == 'X'", "Y": "col('col') == 'Y'"},
                label="Test Crossing"
            )
        ],
    )
    result = Estimator.from_dataframe(
        _load_csv(data_path),
        spec,
    ).assess(exact=True)
    
    assert len(result.factorial_matrices) == 1
    matrix = result.factorial_matrices[0]
    assert matrix.label == "Test Crossing"
    assert len(matrix.cells) == 4  # A-X, A-Y, B-X, B-Y


def test_factorial_expansion_with_inline_axes_and_fallback_label(tmp_path: Path) -> None:
    data_path = _write_csv(
        tmp_path,
        [
            {"gt": "1", "pred": "1", "row": "A", "col": "X"},
            {"gt": "1", "pred": "1", "row": "B", "col": "X"},
        ],
    )
    spec = AttributionSpec(
        target="col('gt')",
        prediction="col('pred')",
        prediction_expr="1",
        regimes=[Hypothesis(name="h", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"A": "col('row') == 'A'", "B": "col('row') == 'B'"},
                columns={"X": "col('col') == 'X'", "Y": "col('col') == 'Y'"},
                # No explicit label; should use "Factorial 1" fallback
            )
        ],
    )
    result = Estimator.from_dataframe(
        _load_csv(data_path),
        spec,
    ).assess(exact=True)
    
    assert len(result.factorial_matrices) == 1
    matrix = result.factorial_matrices[0]
    assert matrix.label == "Factorial 1"  # Fallback for first crossing


def test_factorial_contrast_results_use_label_and_stratum_format() -> None:
    # Test that contrasts use label and stratum format by checking contrast result structure
    # Use simple numeric row indices for factorial partitioning
    data = [
        {"gt": 1, "pred": 0, "idx": 0},  # mismatch
        {"gt": 1, "pred": 1, "idx": 1},
        {"gt": 1, "pred": 1, "idx": 2},
        {"gt": 1, "pred": 1, "idx": 3},
        {"gt": 1, "pred": 1, "idx": 4},
        {"gt": 1, "pred": 1, "idx": 5},
    ]
    spec = AttributionSpec(
        target="col('gt')",
        prediction="col('pred')",
        prediction_expr="1",
        regimes=[Hypothesis(name="h", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"low": "col('idx') < 3", "high": "col('idx') >= 3"},
                columns={"a": "col('idx') == 0", "b": "col('idx') != 0"},
                label="My Factorial"
            )
        ],
    )
    result = Estimator.from_dataframe(
        data,
        spec,
    ).assess(exact=True)
    
    # Check that if contrasts are generated, they use the right format
    if result.contrast_results:
        for contrast in result.contrast_results:
            assert contrast.factorial == "My Factorial", f"Expected factorial='My Factorial', got '{contrast.factorial}'"
            # Stratum should be "rows=<level>" or "columns=<level>"
            assert contrast.stratum.startswith("rows=") or contrast.stratum.startswith("columns="), \
                f"Expected stratum to start with 'rows=' or 'columns=', got '{contrast.stratum}'"


def test_multiple_factorials_each_with_fallback_labels(tmp_path: Path) -> None:
    data_path = _write_csv(
        tmp_path,
        [
            {"gt": "1", "pred": "1", "x1": "A", "y1": "P", "x2": "M", "y2": "Q"},
            {"gt": "1", "pred": "1", "x1": "B", "y1": "P", "x2": "N", "y2": "Q"},
        ],
    )
    spec = AttributionSpec(
        target="col('gt')",
        prediction="col('pred')",
        prediction_expr="1",
        regimes=[Hypothesis(name="h", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"A": "col('x1') == 'A'", "B": "col('x1') == 'B'"},
                columns={"P": "col('y1') == 'P'"},
            ),
            FactorialCrossing(
                rows={"M": "col('x2') == 'M'", "N": "col('x2') == 'N'"},
                columns={"Q": "col('y2') == 'Q'"},
            ),
        ],
    )
    result = Estimator.from_dataframe(
        _load_csv(data_path),
        spec,
    ).assess(exact=True)
    
    assert len(result.factorial_matrices) == 2
    assert result.factorial_matrices[0].label == "Factorial 1"
    assert result.factorial_matrices[1].label == "Factorial 2"


def test_burden_ranking_excess_share_and_cumulative_ordering() -> None:
    rows = [
        {"target": 0, "prediction": 0, "row": "a", "axis_col": "x"},
        {"target": 0, "prediction": 0, "row": "a", "axis_col": "x"},
        {"target": 0, "prediction": 0, "row": "a", "axis_col": "x"},
        {"target": 0, "prediction": 1, "row": "a", "axis_col": "x"},
        {"target": 0, "prediction": 1, "row": "a", "axis_col": "y"},
        {"target": 0, "prediction": 1, "row": "a", "axis_col": "y"},
        {"target": 0, "prediction": 1, "row": "a", "axis_col": "y"},
        {"target": 0, "prediction": 0, "row": "a", "axis_col": "y"},
        {"target": 0, "prediction": 1, "row": "b", "axis_col": "x"},
        {"target": 0, "prediction": 1, "row": "b", "axis_col": "x"},
        {"target": 0, "prediction": 0, "row": "b", "axis_col": "x"},
        {"target": 0, "prediction": 0, "row": "b", "axis_col": "x"},
        {"target": 0, "prediction": 0, "row": "b", "axis_col": "y"},
        {"target": 0, "prediction": 0, "row": "b", "axis_col": "y"},
        {"target": 0, "prediction": 0, "row": "b", "axis_col": "y"},
        {"target": 0, "prediction": 0, "row": "b", "axis_col": "y"},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="1",
        regimes=[Hypothesis(name="all", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"a": "col('row') == 'a'", "b": "col('row') == 'b'"},
                columns={"x": "col('axis_col') == 'x'", "y": "col('axis_col') == 'y'"},
                baseline={"rows": "a", "columns": "x"},
                label="Burden",
            )
        ],
    )
    result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    assert len(result.burden_rankings) == 1
    ranking = result.burden_rankings[0]
    assert [entry.cell for entry in ranking.entries] == ["a & y", "b & x", "b & y"]
    assert ranking.entries[0].recoverable_mismatches is not None
    assert ranking.entries[1].recoverable_mismatches is not None
    assert ranking.entries[2].recoverable_mismatches is None
    assert ranking.entries[0].cumulative_accuracy_if_eliminated_pct >= ranking.observed_accuracy_pct
    assert ranking.entries[1].cumulative_accuracy_if_eliminated_pct >= ranking.entries[0].cumulative_accuracy_if_eliminated_pct


def test_burden_tie_breaks_by_declaration_order() -> None:
    rows = [
        {"target": 0, "prediction": 0, "row": "r1", "axis_col": "c1"},
        {"target": 0, "prediction": 0, "row": "r1", "axis_col": "c1"},
        {"target": 0, "prediction": 1, "row": "r1", "axis_col": "c2"},
        {"target": 0, "prediction": 1, "row": "r1", "axis_col": "c2"},
        {"target": 0, "prediction": 1, "row": "r2", "axis_col": "c1"},
        {"target": 0, "prediction": 1, "row": "r2", "axis_col": "c1"},
        {"target": 0, "prediction": 0, "row": "r2", "axis_col": "c2"},
        {"target": 0, "prediction": 0, "row": "r2", "axis_col": "c2"},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="1",
        regimes=[Hypothesis(name="all", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"r1": "col('row') == 'r1'", "r2": "col('row') == 'r2'"},
                columns={"c1": "col('axis_col') == 'c1'", "c2": "col('axis_col') == 'c2'"},
                baseline={"rows": "r1", "columns": "c1"},
            )
        ],
    )
    result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    cells = [entry.cell for entry in result.burden_rankings[0].entries]
    assert cells[0] == "r1 & c2"
    assert cells[1] == "r2 & c1"


def test_burden_guards_overlap_gap_and_baseline_sanity() -> None:
    rows = [
        {"target": 0, "prediction": 1, "row": "up", "quality": "ok"},
        {"target": 0, "prediction": 0, "row": "up", "quality": "off"},
        {"target": 0, "prediction": 0, "row": "down", "quality": "ok"},
        {"target": 0, "prediction": 0, "row": "down", "quality": "unknown"},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="1",
        regimes=[Hypothesis(name="all", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"up": "col('row') == 'up'", "also_up": "col('row') == 'up'"},
                columns={"ok": "col('quality') == 'ok'", "off": "col('quality') == 'off'"},
                baseline={"rows": "up", "columns": "ok"},
                label="Guarded",
            )
        ],
    )
    with pytest.warns(UserWarning):
        result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    ranking = result.burden_rankings[0]
    assert ranking.overlap_suppressed is True
    assert ranking.entries == []
    assert ranking.coverage_gap_excluded_rows > 0
    assert ranking.baseline_sanity_warning is not None


def test_burden_raises_on_empty_baseline_cell() -> None:
    rows = [
        {"target": 0, "prediction": 0, "row": "a", "axis_col": "x"},
        {"target": 0, "prediction": 1, "row": "a", "axis_col": "x"},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="1",
        regimes=[Hypothesis(name="all", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"a": "col('row') == 'a'", "b": "col('row') == 'b'"},
                columns={"x": "col('axis_col') == 'x'", "y": "col('axis_col') == 'y'"},
                baseline={"rows": "b", "columns": "y"},
                label="Empty Baseline",
            )
        ],
    )
    with pytest.raises(ValueError, match="matches zero rows"):
        Estimator.from_dataframe(rows, spec).assess(exact=True)


def test_baseline_free_outputs_do_not_add_burden_fields(tmp_path: Path) -> None:
    rows = [
        {"target": 0, "prediction": 0, "row": "a", "axis_col": "x"},
        {"target": 0, "prediction": 1, "row": "a", "axis_col": "y"},
    ]
    spec = AttributionSpec(
        target="target",
        prediction="prediction",
        prediction_expr="1",
        regimes=[Hypothesis(name="all", condition="1 == 1")],
        factorials=[
            FactorialCrossing(
                rows={"a": "col('row') == 'a'"},
                columns={"x": "col('axis_col') == 'x'", "y": "col('axis_col') == 'y'"},
                label="No Baseline",
            )
        ],
    )
    result = Estimator.from_dataframe(rows, spec).assess(exact=True)
    assert result.burden_rankings == []

    out = tmp_path / "run.json"
    result.to_json(out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "burden_rankings" not in payload
    assert "## Attributable burden" not in result.to_markdown()
