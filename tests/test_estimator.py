"""Tests for the Estimator and Shapley attribution math."""

from __future__ import annotations

from pathlib import Path

import pytest

from error_attribution import AttributionSpec, Estimator, Hypothesis

FIXTURES = Path(__file__).parent / "fixtures"


def _ungated_sf_spec() -> AttributionSpec:
    return AttributionSpec(
        target_expr="col('GT SF')",
        prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",
        hypotheses=[
            Hypothesis(
                name="class_sf",
                label="Nominal class SF",
                condition="col('Detected SF') == col('GT SF')",
            ),
            Hypothesis(
                name="class_bw",
                label="Nominal class BW",
                condition="col('Detected BW (Hz)') == col('GT BW (Hz)')",
            ),
            Hypothesis(
                name="measured_bw",
                label="Measured BW",
                condition="col('Measured BW (Hz)') == col('GT BW (Hz)')",
            ),
        ],
    )


def test_n_rows_and_features() -> None:
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", _ungated_sf_spec()).assess()
    assert result.n_rows == 4
    assert len(result.feature_attributions) == 3


def test_additivity_invariant() -> None:
    """Sum of per-feature net_error_share_pct must equal 100.0 (within float tolerance)."""
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", _ungated_sf_spec()).assess()
    total_share = sum(row.net_error_share_pct for row in result.feature_attributions)
    assert abs(total_share - 100.0) < 1e-6, f"shares do not sum to 100: {total_share}"


def test_dominated_by_class_sf() -> None:
    """In the synthetic fixture only row 3 has an error and it is purely from class_sf.
    class_sf must therefore hold all of the net error share."""
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", _ungated_sf_spec()).assess()
    by_name = {row.name: row for row in result.feature_attributions}
    assert abs(by_name["class_sf"].net_error_share_pct - 100.0) < 1e-6, (
        f"class_sf should own 100% of error, got {by_name['class_sf'].net_error_share_pct}"
    )


def test_save_outputs_all_expected_files(tmp_path: Path) -> None:
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", _ungated_sf_spec()).assess()
    result.save(tmp_path)
    assert (tmp_path / "contribution.csv").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "run.json").exists()


def test_from_dataframe_equivalent() -> None:
    """Estimator.from_dataframe should produce identical results to from_csv."""
    spec = _ungated_sf_spec()
    result_csv = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec).assess()
    rows = []
    import csv as csv_module
    with (FIXTURES / "synthetic_measurements.csv").open("r") as handle:
        reader = csv_module.DictReader(handle)
        for row in reader:
            rows.append({k: _try_numeric(v) for k, v in row.items()})
    result_df = Estimator.from_dataframe(rows, spec).assess()
    assert result_csv.n_rows == result_df.n_rows
    for a, b in zip(result_csv.feature_attributions, result_df.feature_attributions):
        assert a.name == b.name
        assert abs(a.net_error_share_pct - b.net_error_share_pct) < 1e-9


def _try_numeric(value: str) -> int | float | str:
    text = value.strip()
    try:
        if "." not in text:
            return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text
