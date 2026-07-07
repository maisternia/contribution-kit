from __future__ import annotations

import csv
from pathlib import Path

import pytest

from contribution.estimator import _parse_scalar, _score
from contribution.spec import AttributionSpec, Hypothesis
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
        target_expr="col('GT SF')",
        prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",
        mismatch_expr="col('Measured SF (ungated)') != col('GT SF')",
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

    est.spec = AttributionSpec(target_expr="1", prediction_expr="1", hypotheses=[])
    with pytest.raises(ValueError, match="At least one hypothesis"):
        est.assess()

    est.spec = AttributionSpec(
        target_expr="1",
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

    # no mismatch expression path => risk is None for regime assessments
    no_mismatch = AttributionSpec(
        target_expr="1",
        prediction_expr="1",
        hypotheses=[Hypothesis(name="reg", condition="col('v') > 0")],
    )
    est2 = Estimator(rows=[{"v": 1}, {"v": 0}], spec=no_mismatch)
    assessed = est2.assess()
    assert assessed.hypotheses[0].risk is None

    # single-group path => risk is None
    single_group = AttributionSpec(
        target_expr="0",
        prediction_expr="0",
        mismatch_expr="mismatch",
        hypotheses=[Hypothesis(name="all", condition="1 == 1")],
    )
    est3 = Estimator(rows=[{"mismatch": True}], spec=single_group)
    assessed_single = est3.assess()
    assert assessed_single.hypotheses[0].risk is None
