from contribution.spec import AttributionSpec, CategoricalHypothesis, ContinuousHypothesis, Hypothesis


def test_hypothesis_defaults() -> None:
    hypothesis = Hypothesis(name="h", condition="x == y")
    assert hypothesis.label is None


def test_attribution_spec_defaults() -> None:
    spec = AttributionSpec(target="1", prediction="2", prediction_expr="3")
    assert spec.hypotheses == []
    assert spec.scope == "global"
    assert spec.score_mode == "absolute"


def test_backcompat_hypothesis_aliases() -> None:
    categorical = CategoricalHypothesis(name="cat", condition="x == y")
    continuous = ContinuousHypothesis(name="cont", condition="x < y")
    assert isinstance(categorical, Hypothesis)
    assert isinstance(continuous, Hypothesis)
