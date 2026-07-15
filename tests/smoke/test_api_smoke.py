from pathlib import Path

from contribution import (
    AttributionSpec,
    Estimator,
    Hypothesis,
    PredictionFeature,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _spec(
    regimes: list,
    *,
    prediction_expr: str = "class_sf + round(2 * log2(measured_bw / class_bw))",
    prediction_features: dict[str, PredictionFeature] | None = None,
) -> AttributionSpec:
    if prediction_features is None:
        prediction_features = {
            "class_sf": PredictionFeature(actual="col('Detected SF')", baseline="col('GT SF')"),
            "class_bw": PredictionFeature(actual="col('Detected BW (Hz)')", baseline="col('GT BW (Hz)')"),
            "measured_bw": PredictionFeature(actual="col('Measured BW (Hz)')", baseline="col('GT BW (Hz)')"),
        }
    return AttributionSpec(
        target="col('GT SF')",
        prediction="col('Detected SF')",
        prediction_expr=prediction_expr,
        prediction_features=prediction_features,
        regimes=regimes,
    )


def test_estimator_construction() -> None:
    spec = _spec(
        [
            Hypothesis(name="bw_under", condition="col('Detected BW (Hz)') < col('GT BW (Hz)')"),
        ]
    )
    est = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec=spec)
    assert est.spec == spec


def test_prediction_feature_routes_to_feature() -> None:
    spec = _spec(
        [Hypothesis(name="sf_regime", condition="col('Detected SF') == col('GT SF')")],
        prediction_expr="class_sf",
        prediction_features={
            "class_sf": PredictionFeature(actual="col('Detected SF')", baseline="col('GT SF')")
        },
    )
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec=spec).assess()
    assert [a.name for a in result.feature_attributions] == ["class_sf"]
    assert [summary.name for summary in result.regime_summaries] == ["sf_regime"]
    assert result.regimes[0].analysis == "feature"


def test_nonequality_hypothesis_routes_to_regime() -> None:
    spec = _spec(
        [Hypothesis(name="bw_under", condition="col('Detected BW (Hz)') < col('GT BW (Hz)')")],
        prediction_expr="1",
        prediction_features={},
    )
    result = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec=spec).assess()
    assert result.feature_attributions == []
    assert [r.name for r in result.regime_summaries] == ["bw_under"]
    assert result.regimes[0].analysis == "regime"
