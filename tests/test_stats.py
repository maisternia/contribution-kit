"""Tests for v0.2.0 binary effect-size utilities."""

from __future__ import annotations

import math

from contribution import baptista_pike_odds_ratio, haldane_anscombe_odds_ratio, koopman_risk_ratio


def test_koopman_risk_ratio_known_values() -> None:
    result = koopman_risk_ratio(1, 13, 9, 1)
    assert math.isclose(result.value, 0.07936507936507936, rel_tol=0, abs_tol=1e-12)
    assert result.ci_low is not None
    assert result.ci_high is not None
    assert math.isclose(result.ci_low, 0.013997665406812243, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(result.ci_high, 0.4726277228393074, rel_tol=0, abs_tol=1e-12)


def test_koopman_risk_ratio_single_zero_cell() -> None:
    result = koopman_risk_ratio(10, 90, 0, 100)
    assert math.isinf(result.value)
    assert math.isclose(result.ci_low, 0.8296124798021083, rel_tol=0, abs_tol=1e-12)
    assert math.isinf(result.ci_high)


def test_koopman_risk_ratio_boundary_case() -> None:
    result = koopman_risk_ratio(0, 100, 10, 90)
    assert result.value == 0.0
    assert result.ci_low == 0.0
    assert math.isinf(result.ci_high)


def test_baptista_pike_odds_ratio_known_values() -> None:
    result = baptista_pike_odds_ratio(1, 13, 9, 1)
    assert math.isclose(result.value, 0.008547008547008548, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(result.ci_low, 0.00018216187828897024, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(result.ci_high, 0.20517173620402557, rel_tol=0, abs_tol=1e-12)


def test_baptista_pike_odds_ratio_sparse_cells() -> None:
    result = baptista_pike_odds_ratio(10, 90, 0, 100)
    assert math.isinf(result.value)
    assert result.ci_low > 0
    assert math.isinf(result.ci_high)


def test_baptista_pike_odds_ratio_monotone_bounds() -> None:
    balanced = baptista_pike_odds_ratio(1, 1, 1, 1)
    sparse = baptista_pike_odds_ratio(10, 90, 0, 100)
    assert balanced.ci_low < balanced.value < balanced.ci_high
    assert sparse.ci_low > balanced.ci_low


def test_haldane_anscombe_odds_ratio_with_sparse_cells() -> None:
    result = haldane_anscombe_odds_ratio(10, 90, 0, 100)
    assert result.value > 1.0
    assert result.ci_low > 0
    assert result.ci_high > result.ci_low