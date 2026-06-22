"""Statistical utilities for binary 2x2 table effect sizes."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class RiskRatioResult:
    value: float
    ci_low: float | None
    ci_high: float | None


@dataclass(slots=True)
class OddsRatioResult:
    value: float
    ci_low: float
    ci_high: float


def _validate_2x2_counts(a: int, b: int, c: int, d: int) -> None:
    if min(a, b, c, d) < 0:
        raise ValueError("2x2 table counts must be non-negative")
    if a + b == 0:
        raise ValueError("Exposed group cannot be empty")
    if c + d == 0:
        raise ValueError("Baseline group cannot be empty")


def katz_risk_ratio(a: int, b: int, c: int, d: int, z: float = 1.96) -> RiskRatioResult:
    """Compute risk ratio and Katz log-transform confidence interval.

    The CI is returned as None/None when any cell is zero.

    Reference:
        Katz, D., Baptista, J., Azen, S. P., & Pike, M. C. (1978). Obtaining
        confidence intervals for the risk ratio in cohort studies.
        Biometrics, 34(3), 469-474.
    """

    _validate_2x2_counts(a, b, c, d)

    p_exposed = a / (a + b)
    p_baseline = c / (c + d)

    if p_baseline == 0:
        return RiskRatioResult(value=float("inf"), ci_low=None, ci_high=None)

    rr = p_exposed / p_baseline  # @cite: Katz et al., 1978

    if min(a, b, c, d) == 0:
        return RiskRatioResult(value=rr, ci_low=None, ci_high=None)

    # Log-transform SE and CI @cite: Katz et al., 1978
    se = math.sqrt((1 / a) - (1 / (a + b)) + (1 / c) - (1 / (c + d)))
    ci_low = math.exp(math.log(rr) - z * se)
    ci_high = math.exp(math.log(rr) + z * se)
    return RiskRatioResult(value=rr, ci_low=ci_low, ci_high=ci_high)


def haldane_anscombe_odds_ratio(a: int, b: int, c: int, d: int, z: float = 1.96) -> OddsRatioResult:
    """Compute odds ratio with Haldane-Anscombe continuity correction.

    References:
        Haldane, J. B. S. (1956). The estimation and significance of the
        logarithm of a ratio of frequencies. Annals of Human Genetics,
        20(4), 309-311.
        Anscombe, F. J. (1956). On estimating binomial response relations.
        Biometrika, 43(3-4), 461-464.
        Agresti, A. (2013). Categorical Data Analysis (3rd ed.). Wiley.
    """

    _validate_2x2_counts(a, b, c, d)

    # Add 0.5 to each cell — Haldane-Anscombe continuity correction
    # @cite: Haldane, 1956; Anscombe, 1956; Agresti, 2013
    aa = a + 0.5
    bb = b + 0.5
    cc = c + 0.5
    dd = d + 0.5

    odds_ratio = (aa * dd) / (bb * cc)  # @cite: Agresti, 2013
    se = math.sqrt((1 / aa) + (1 / bb) + (1 / cc) + (1 / dd))
    ci_low = math.exp(math.log(odds_ratio) - z * se)
    ci_high = math.exp(math.log(odds_ratio) + z * se)
    return OddsRatioResult(value=odds_ratio, ci_low=ci_low, ci_high=ci_high)