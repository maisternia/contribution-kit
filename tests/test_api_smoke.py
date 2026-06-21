from pathlib import Path

from error_attribution import AttributionSpec, CategoricalHypothesis, ContinuousHypothesis, Estimator

FIXTURES = Path(__file__).parent / "fixtures"


def test_estimator_construction() -> None:
    spec = AttributionSpec(
        target_expr="col('GT SF')",
        prediction_expr="class_sf + round(2 * log2(measured_bw / class_bw))",
        hypotheses=[
            ContinuousHypothesis(name="class_bw", actual_expr="col('Detected BW (Hz)')", baseline_expr="col('GT BW (Hz)')"),
            ContinuousHypothesis(name="measured_bw", actual_expr="col('Measured BW (Hz)')", baseline_expr="col('GT BW (Hz)')"),
            CategoricalHypothesis(name="class_sf", actual_expr="col('Detected SF')", baseline_expr="col('GT SF')"),
        ],
    )
    est = Estimator.from_csv(FIXTURES / "synthetic_measurements.csv", spec=spec)
    assert est.spec == spec
