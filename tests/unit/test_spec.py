from contribution.spec import AttributionSpec, CategoricalHypothesis, ContinuousHypothesis, Factor, FactorialCrossing, Hypothesis


def test_hypothesis_defaults() -> None:
    hypothesis = Hypothesis(name="h", condition="x == y")
    assert hypothesis.label is None


def test_attribution_spec_defaults() -> None:
    spec = AttributionSpec(target="1", prediction="2", prediction_expr="3")
    assert spec.hypotheses == []
    assert spec.factors == {}
    assert spec.factorials == []
    assert spec.scope == "global"
    assert spec.score_mode == "absolute"


def test_factor_and_factorial_types() -> None:
    factor = Factor(name="axis", levels={"low": "x < 0", "high": "x >= 0"})
    crossing = FactorialCrossing(rows="axis", columns="axis")
    assert factor.levels["low"] == "x < 0"
    assert crossing.rows == "axis"


def test_backcompat_hypothesis_aliases() -> None:
    categorical = CategoricalHypothesis(name="cat", condition="x == y")
    continuous = ContinuousHypothesis(name="cont", condition="x < y")
    assert isinstance(categorical, Hypothesis)
    assert isinstance(continuous, Hypothesis)
