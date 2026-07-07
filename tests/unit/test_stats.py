from __future__ import annotations

import math

import pytest

from contribution import stats
from contribution.stats import (
    baptista_pike_odds_ratio,
    haldane_anscombe_odds_ratio,
    katz_risk_ratio,
    koopman_risk_ratio,
)


def test_validate_2x2_count_guards() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        stats._validate_2x2_counts(-1, 0, 1, 1)
    with pytest.raises(ValueError, match="Exposed group cannot be empty"):
        stats._validate_2x2_counts(0, 0, 1, 1)
    with pytest.raises(ValueError, match="Baseline group cannot be empty"):
        stats._validate_2x2_counts(1, 1, 0, 0)


def test_katz_risk_ratio_paths() -> None:
    finite = katz_risk_ratio(20, 80, 10, 90)
    assert finite.ci_low is not None and finite.ci_high is not None

    inf_case = katz_risk_ratio(10, 90, 0, 100)
    assert math.isinf(inf_case.value)
    assert inf_case.ci_low is None and inf_case.ci_high is None

    zero_cell = katz_risk_ratio(0, 100, 10, 90)
    assert zero_cell.ci_low is None and zero_cell.ci_high is None


def test_haldane_anscombe_odds_ratio_sparse() -> None:
    result = haldane_anscombe_odds_ratio(10, 90, 0, 100)
    assert result.value > 1.0
    assert result.ci_low > 0.0
    assert result.ci_high > result.ci_low


def test_koopman_risk_ratio_value_classes() -> None:
    finite = koopman_risk_ratio(1, 13, 9, 1)
    assert math.isclose(finite.value, 0.07936507936507936, rel_tol=0, abs_tol=1e-12)

    zero_point = koopman_risk_ratio(0, 100, 10, 90)
    assert zero_point.value == 0.0
    assert zero_point.ci_low == 0.0
    assert math.isinf(zero_point.ci_high)

    inf_point = koopman_risk_ratio(10, 90, 0, 100)
    assert math.isinf(inf_point.value)
    assert inf_point.ci_low is not None
    assert math.isinf(inf_point.ci_high)


def test_baptista_pike_paths() -> None:
    finite = baptista_pike_odds_ratio(1, 13, 9, 1)
    assert finite.ci_low < finite.value < finite.ci_high

    zero_point = baptista_pike_odds_ratio(0, 100, 10, 90)
    assert zero_point.value == 0.0
    assert zero_point.ci_low == 0.0

    inf_point = baptista_pike_odds_ratio(10, 90, 0, 100)
    assert math.isinf(inf_point.value)
    assert math.isinf(inf_point.ci_high)


def test_internal_helpers_and_branches() -> None:
    assert stats._normal_two_sided_pvalue(0.0) == 1.0
    assert stats._log_comb(5, 2) > 0
    assert stats._log_comb(2, 5) == float("-inf")

    root = stats._bisect_root(lambda x: x - 2.0, 0.0, 4.0)
    assert abs(root - 2.0) < 1e-10
    with pytest.raises(ValueError, match="root is not bracketed"):
        stats._bisect_root(lambda x: x + 2.0, 0.0, 4.0)

    assert stats._adjusted_risk_ratio(1, 13, 9, 1) > 0
    assert stats._adjusted_odds_ratio(1, 13, 9, 1) > 0

    assert stats._rr_point_estimate(10, 90, 0, 100) == float("inf")
    assert stats._odds_ratio_value(0, 1, 1, 0) == 0.0
    assert math.isinf(stats._odds_ratio_value(1, 0, 0, 1))

    assert stats._rr_score_statistic(1, 13, 9, 1, 1.0) != 0
    with pytest.raises(ValueError, match="must be positive"):
        stats._rr_score_statistic(1, 13, 9, 1, 0.0)

    assert 0.0 <= stats._rr_pvalue(1, 13, 9, 1, 1.0) <= 1.0

    assert stats._tail_probability(1, 1, 1, 1, 1.0, tail="lower") >= 0.0
    assert stats._tail_probability(1, 1, 1, 1, float("inf"), tail="upper") == 0.0
    assert stats._tail_probability(0, 1, 1, 0, 0.0, tail="lower") == 1.0
    with pytest.raises(ValueError, match="tail"):
        stats._tail_probability(1, 1, 1, 1, 1.0, tail="middle")

    inc = stats._invert_monotone_tail(lambda x: x, 0.5, start=0.1, increasing=True, upper_limit=1.0)
    assert 0.49 <= inc <= 0.51
    dec = stats._invert_monotone_tail(
        lambda x: 1.0 / (1.0 + x),
        0.5,
        start=0.2,
        increasing=False,
        upper_limit=1000.0,
    )
    assert 0.9 <= dec <= 1.1
