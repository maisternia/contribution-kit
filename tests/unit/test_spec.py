import pytest

from contribution import Estimator
from contribution.spec import AttributionSpec, CategoricalHypothesis, ContinuousHypothesis, FactorialCrossing, Hypothesis, PredictionFeature, Regime


def test_regime_defaults() -> None:
    regime = Regime(name="h", condition="x == y")
    assert regime.label is None


def test_attribution_spec_defaults() -> None:
    spec = AttributionSpec(target="1", prediction="2", prediction_expr="3")
    assert spec.prediction_features == {}
    assert spec.regimes == []
    assert spec.factorials == []
    assert spec.scope == "global"
    assert spec.score_mode == "absolute"


def test_prediction_feature_defaults() -> None:
    feature = PredictionFeature(actual="a", baseline="b")
    assert feature.label is None


def test_factorial_crossing_inline_axes() -> None:
    crossing = FactorialCrossing(rows={"low": "x < 0", "high": "x >= 0"}, columns={"a": "y == 1", "b": "y == 2"})
    assert crossing.rows["low"] == "x < 0"
    assert crossing.columns["a"] == "y == 1"
    assert crossing.label is None
    assert crossing.baseline is None


def test_factorial_crossing_with_label() -> None:
    crossing = FactorialCrossing(
        rows={"low": "x < 0", "high": "x >= 0"},
        columns={"a": "y == 1", "b": "y == 2"},
        label="Test Crossing"
    )
    assert crossing.label == "Test Crossing"


def test_factorial_crossing_with_baseline() -> None:
    crossing = FactorialCrossing(
        rows={"low": "x < 0", "high": "x >= 0"},
        columns={"a": "y == 1", "b": "y == 2"},
        baseline={"rows": "low", "columns": "a"},
    )
    assert crossing.baseline == {"rows": "low", "columns": "a"}


def test_backcompat_hypothesis_aliases() -> None:
    categorical = CategoricalHypothesis(name="cat", condition="x == y")
    continuous = ContinuousHypothesis(name="cont", condition="x < y")
    assert isinstance(categorical, Regime)
    assert isinstance(continuous, Regime)


def test_prediction_expr_variable_requires_prediction_feature() -> None:
    spec = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="missing",
        regimes=[Hypothesis(name="h", condition="1 == 1")],
    )
    with pytest.raises(ValueError, match=r"undeclared prediction feature\(s\): missing"):
        Estimator.from_dataframe([{}], spec).assess(exact=True)
