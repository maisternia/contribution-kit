"""Tests for the Estimator and Shapley attribution math."""

from __future__ import annotations

from pathlib import Path

from contribution import AttributionSpec, Estimator, Hypothesis

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


def _binary_risk_spec() -> AttributionSpec:
    return AttributionSpec(
        target_expr="0",
        prediction_expr="0",
        mismatch_expr="mismatch",
        hypotheses=[
            Hypothesis(
                name="group_a",
                label="Group A",
                condition="group != 'B'",
            ),
        ],
    )


def test_n_rows_and_features() -> None:
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", _ungated_sf_spec()).assess()
    assert result.n_rows == 4
    assert len(result.feature_attributions) == 3


def test_additivity_invariant() -> None:
    """Sum of per-feature net_contribution_share_pct must equal 100.0 (within float tolerance)."""
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", _ungated_sf_spec()).assess()
    total_share = sum(row.net_contribution_share_pct for row in result.feature_attributions)
    assert abs(total_share - 100.0) < 1e-6, f"shares do not sum to 100: {total_share}"


def test_dominated_by_class_sf() -> None:
    """In the synthetic fixture only row 3 has an error and it is purely from class_sf.
    class_sf must therefore hold all of the net error share."""
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", _ungated_sf_spec()).assess()
    by_name = {row.name: row for row in result.feature_attributions}
    assert abs(by_name["class_sf"].net_contribution_share_pct - 100.0) < 1e-6, (
        f"class_sf should own 100% of error, got {by_name['class_sf'].net_contribution_share_pct}"
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
        assert abs(a.net_contribution_share_pct - b.net_contribution_share_pct) < 1e-9


def test_assess_uses_default_score_exact_and_legacy_wald() -> None:
    rows = []
    rows.extend({"group": "A", "mismatch": i == 0} for i in range(14))
    rows.extend({"group": "B", "mismatch": i < 9} for i in range(10))

    estimator = Estimator.from_dataframe(list(rows), _binary_risk_spec())
    score_exact = estimator.assess()
    wald = estimator.assess(ci_method="wald")

    assert score_exact.metadata["ci_method"] == "score-exact"
    assert wald.metadata["ci_method"] == "wald"
    assert score_exact.binary_results[0].risk_ratio == wald.binary_results[0].risk_ratio
    assert score_exact.binary_results[0].odds_ratio == wald.binary_results[0].odds_ratio
    assert score_exact.binary_results[0].rr_ci_low != wald.binary_results[0].rr_ci_low


def test_markdown_uses_koopman_and_baptista_references() -> None:
    rows = []
    rows.extend({"group": "A", "mismatch": i == 0} for i in range(14))
    rows.extend({"group": "B", "mismatch": i < 9} for i in range(10))

    result = Estimator.from_dataframe(list(rows), _binary_risk_spec()).assess()
    markdown = result.to_markdown()

    assert "Koopman (1984)" in markdown
    assert "Baptista & Pike (1977)" in markdown
    assert "Fagerland, Lydersen & Laake" in markdown
    assert "Katz et al. (1978)" not in markdown
    assert "Haldane" not in markdown


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
