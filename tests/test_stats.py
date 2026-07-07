"""Tests for v0.2.0 binary effect-size utilities."""

from __future__ import annotations

import math

from contribution import haldane_anscombe_odds_ratio, katz_risk_ratio


def test_katz_risk_ratio_known_values() -> None:
    result = katz_risk_ratio(30, 70, 15, 85)
    assert result.value == 2.0
    assert result.ci_low is not None
    assert result.ci_high is not None
    assert math.isclose(result.ci_low, 1.1488661093658992, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(result.ci_high, 3.481693791287607, rel_tol=0, abs_tol=1e-12)


def test_katz_ci_absent_when_sparse() -> None:
    result = katz_risk_ratio(10, 90, 0, 100)
    assert math.isinf(result.value)
    assert result.ci_low is None
    assert result.ci_high is None


def test_haldane_anscombe_odds_ratio_with_sparse_cells() -> None:
    result = haldane_anscombe_odds_ratio(10, 90, 0, 100)
    assert result.value > 1.0
    assert result.ci_low > 0
    assert result.ci_high > result.ci_low