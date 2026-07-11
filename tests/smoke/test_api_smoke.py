from pathlib import Path

from contribution import (
    AttributionSpec,
    Estimator,
    Hypothesis,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _spec(
    hypotheses: list,
    *,
    prediction_expr: str = "class_sf + round(2 * log2(measured_bw / class_bw))",
) -> AttributionSpec:
    return AttributionSpec(
        target="col('GT SF')",
        prediction="col('Detected SF')",
        prediction_expr=prediction_expr,
        hypotheses=hypotheses,
    )


def test_estimator_construction() -> None:
    spec = _spec(
        [
            Hypothesis(name="class_bw", condition="col('Detected BW (Hz)') == col('GT BW (Hz)')"),
            Hypothesis(name="measured_bw", condition="col('Measured BW (Hz)') == col('GT BW (Hz)')"),
            Hypothesis(name="class_sf", condition="col('Detected SF') == col('GT SF')"),
        ]
    )
    est = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec=spec)
    assert est.spec == spec


def test_equality_hypothesis_routes_to_feature() -> None:
    spec = _spec(
        [Hypothesis(name="class_sf", condition="col('Detected SF') == col('GT SF')")],
        prediction_expr="class_sf",
    )
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec=spec).assess()
    assert [a.name for a in result.feature_attributions] == ["class_sf"]
    assert result.regime_summaries == []
    assert result.hypotheses[0].analysis == "feature"


def test_nonequality_hypothesis_routes_to_regime() -> None:
    spec = _spec(
        [Hypothesis(name="bw_under", condition="col('Detected BW (Hz)') < col('GT BW (Hz)')")],
        prediction_expr="col('Detected SF')",
    )
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec=spec).assess()
    assert result.feature_attributions == []
    assert [r.name for r in result.regime_summaries] == ["bw_under"]
    assert result.hypotheses[0].analysis == "regime"
