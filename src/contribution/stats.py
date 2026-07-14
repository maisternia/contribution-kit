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


@dataclass(slots=True)
class RiskDifferenceResult:
    value: float
    ci_low: float | None
    ci_high: float | None


def _validate_2x2_counts(a: int, b: int, c: int, d: int) -> None:
    if min(a, b, c, d) < 0:
        raise ValueError("2x2 table counts must be non-negative")
    if a + b == 0:
        raise ValueError("Exposed group cannot be empty")
    if c + d == 0:
        raise ValueError("Baseline group cannot be empty")


def _validate_z_score(z: float) -> None:
    if not math.isfinite(z) or z <= 0.0:
        raise ValueError("z must be a finite positive value")


def _finite_ordered_interval(ci_low: float | None, ci_high: float | None) -> bool:
    if ci_low is None or ci_high is None:
        return False
    if not math.isfinite(ci_low) or not math.isfinite(ci_high):
        return False
    return ci_low <= ci_high


def katz_risk_ratio(a: int, b: int, c: int, d: int, z: float = 1.96) -> RiskRatioResult:
    """Compute risk ratio and Katz log-transform confidence interval.

    The CI is returned as None/None when any cell is zero.

    Reference:
        Katz, D., Baptista, J., Azen, S. P., & Pike, M. C. (1978). Obtaining
        confidence intervals for the risk ratio in cohort studies.
        Biometrics, 34(3), 469-474.
    """

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

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
    _validate_z_score(z)

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


def _normal_two_sided_pvalue(zscore: float) -> float:
    return math.erfc(abs(zscore) / math.sqrt(2.0))


def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.log(math.comb(n, k))


def _bisect_root(
    func,
    lower: float,
    upper: float,
    *,
    tol: float = 1e-12,
    max_iter: int = 256,
) -> float:
    low_value = func(lower)
    high_value = func(upper)
    if abs(low_value) <= tol:
        return lower
    if abs(high_value) <= tol:
        return upper
    if low_value * high_value > 0:
        raise ValueError("root is not bracketed")
    lo = lower
    hi = upper
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        mid_value = func(mid)
        if abs(mid_value) <= tol or (hi - lo) <= tol * max(1.0, abs(mid)):
            return mid
        if low_value * mid_value <= 0:
            hi = mid
            high_value = mid_value
        else:
            lo = mid
            low_value = mid_value
    return (lo + hi) / 2.0


def _adjusted_risk_ratio(a: int, b: int, c: int, d: int) -> float:
    n1 = a + b
    n0 = c + d
    return ((a + 0.5) / (n1 + 1.0)) / ((c + 0.5) / (n0 + 1.0))


def _adjusted_odds_ratio(a: int, b: int, c: int, d: int) -> float:
    aa = a + 0.5
    bb = b + 0.5
    cc = c + 0.5
    dd = d + 0.5
    return (aa * dd) / (bb * cc)


def _rr_point_estimate(a: int, b: int, c: int, d: int) -> float:
    risk_a = a / (a + b)
    risk_b = c / (c + d)
    if risk_b == 0:
        return float("inf")
    return risk_a / risk_b


def _risk_difference_value(a: int, b: int, c: int, d: int) -> float:
    return (a / (a + b)) - (c / (c + d))


def _mn_constrained_p0(a: int, b: int, c: int, d: int, risk_difference: float) -> float:
    eps = 1e-12
    lower = max(0.0, -risk_difference) + eps
    upper = min(1.0, 1.0 - risk_difference) - eps
    if lower >= upper:
        return max(min((lower + upper) / 2.0, 1.0), 0.0)

    def derivative(p0: float) -> float:
        p1 = p0 + risk_difference
        return (
            (a / p1)
            - (b / (1.0 - p1))
            + (c / p0)
            - (d / (1.0 - p0))
        )

    low_value = derivative(lower)
    high_value = derivative(upper)
    if low_value <= 0.0:
        return lower
    if high_value >= 0.0:
        return upper
    return _bisect_root(derivative, lower, upper)


def _mn_score_z(a: int, b: int, c: int, d: int, risk_difference: float) -> float:
    n1 = a + b
    n0 = c + d
    n_total = n1 + n0
    observed_difference = _risk_difference_value(a, b, c, d)

    p0 = _mn_constrained_p0(a, b, c, d, risk_difference)
    p1 = p0 + risk_difference
    p0 = min(max(p0, 0.0), 1.0)
    p1 = min(max(p1, 0.0), 1.0)
    variance = (p1 * (1.0 - p1) / n1) + (p0 * (1.0 - p0) / n0)
    if n_total > 1:
        variance *= n_total / (n_total - 1.0)
    if variance <= 0.0:
        if observed_difference > risk_difference:
            return float("inf")
        if observed_difference < risk_difference:
            return float("-inf")
        return 0.0
    return (observed_difference - risk_difference) / math.sqrt(variance)


def _solve_mn_bound(a: int, b: int, c: int, d: int, z: float, *, lower: bool) -> float:
    target = z if lower else -z

    def objective(risk_difference: float) -> float:
        return _mn_score_z(a, b, c, d, risk_difference) - target

    grid = 1024
    domain_low = -1.0
    domain_high = 1.0
    step = (domain_high - domain_low) / grid
    previous_x = domain_low
    previous_value = objective(previous_x)

    for index in range(1, grid + 1):
        current_x = domain_low + index * step
        current_value = objective(current_x)
        if math.isnan(previous_value) or math.isnan(current_value):
            previous_x = current_x
            previous_value = current_value
            continue
        if previous_value == 0.0:
            return previous_x
        if current_value == 0.0:
            return current_x
        if previous_value * current_value < 0.0:
            return _bisect_root(objective, previous_x, current_x)
        previous_x = current_x
        previous_value = current_value

    if lower:
        return domain_low
    return domain_high


def miettinen_nurminen_risk_difference(a: int, b: int, c: int, d: int, z: float = 1.96) -> RiskDifferenceResult:
    """Compute risk difference and Miettinen-Nurminen score confidence interval.

    Reference:
        Miettinen, O., & Nurminen, M. (1985). Comparative analysis of two rates.
        Statistics in Medicine, 4(2), 213-226.
    """

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

    value = _risk_difference_value(a, b, c, d)
    lower = _solve_mn_bound(a, b, c, d, z, lower=True)
    upper = _solve_mn_bound(a, b, c, d, z, lower=False)
    lower = max(min(lower, 1.0), -1.0)
    upper = max(min(upper, 1.0), -1.0)
    if upper < lower:
        return RiskDifferenceResult(value=value, ci_low=None, ci_high=None)
    return RiskDifferenceResult(value=value, ci_low=lower, ci_high=upper)


def agresti_caffo_risk_difference(a: int, b: int, c: int, d: int, z: float = 1.96) -> RiskDifferenceResult:
    """Compute risk difference with Agresti-Caffo add-two confidence interval.

    Reference:
        Agresti, A., & Caffo, B. (2000). Simple and effective confidence
        intervals for proportions and differences of proportions result from
        adding two successes and two failures. The American Statistician,
        54(4), 280-288.
    """

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

    n1 = a + b
    n0 = c + d
    value = _risk_difference_value(a, b, c, d)
    p1_tilde = (a + 1.0) / (n1 + 2.0)  # @cite: Agresti & Caffo, 2000
    p0_tilde = (c + 1.0) / (n0 + 2.0)  # @cite: Agresti & Caffo, 2000
    se = math.sqrt((p1_tilde * (1.0 - p1_tilde) / (n1 + 2.0)) + (p0_tilde * (1.0 - p0_tilde) / (n0 + 2.0)))
    ci_low = value - z * se
    ci_high = value + z * se
    ci_low = max(ci_low, -1.0)
    ci_high = min(ci_high, 1.0)
    return RiskDifferenceResult(value=value, ci_low=ci_low, ci_high=ci_high)


def risk_difference_with_guardrail(a: int, b: int, c: int, d: int, z: float = 1.96) -> RiskDifferenceResult:
    primary = miettinen_nurminen_risk_difference(a, b, c, d, z=z)
    if math.isfinite(primary.value) and _finite_ordered_interval(primary.ci_low, primary.ci_high):
        return primary
    fallback = agresti_caffo_risk_difference(a, b, c, d, z=z)
    if _finite_ordered_interval(fallback.ci_low, fallback.ci_high):
        return fallback
    return primary


def _odds_ratio_value(a: int, b: int, c: int, d: int) -> float:
    numerator = a * d
    denominator = b * c
    if denominator == 0:
        if numerator == 0:
            return float("inf")
        return float("inf") if numerator > 0 else 0.0
    return numerator / denominator


def _rr_score_statistic(a: int, b: int, c: int, d: int, ratio: float) -> float:
    n1 = a + b
    n0 = c + d
    nobs = n1 + n0
    count = a + c
    p1 = a / n1

    if ratio <= 0:
        raise ValueError("risk ratio must be positive")

    if ratio == 1:
        prop0 = count / nobs
    else:
        qa = nobs * ratio
        qb = -(n1 * ratio + a + n0 + c * ratio)
        qc = count
        disc = max(qb * qb - 4.0 * qa * qc, 0.0)
        prop0 = (-qb - math.sqrt(disc)) / (2.0 * qa)

    prop1 = prop0 * ratio
    eps = 1e-12
    prop0 = min(max(prop0, eps), 1.0 - eps)
    prop1 = min(max(prop1, eps), 1.0 - eps)
    variance = prop1 * (1.0 - prop1) / n1 + ratio * ratio * prop0 * (1.0 - prop0) / n0
    return (p1 - prop1) / math.sqrt(variance)


def _rr_pvalue(a: int, b: int, c: int, d: int, ratio: float) -> float:
    return _normal_two_sided_pvalue(_rr_score_statistic(a, b, c, d, ratio))


def _tail_probability(
    observed: int,
    n1: int,
    n0: int,
    m1: int,
    theta: float,
    *,
    tail: str,
) -> float:
    lower = max(0, m1 - n0)
    upper = min(n1, m1)
    if lower == upper:
        return 1.0
    if theta <= 0:
        if tail == "lower":
            return 1.0 if observed <= lower else 0.0
        if tail == "upper":
            return 1.0 if observed >= upper else 0.0
        raise ValueError("tail must be 'lower' or 'upper'")
    if math.isinf(theta):
        if tail == "lower":
            return 1.0 if observed >= upper else 0.0
        if tail == "upper":
            return 1.0 if observed <= lower else 0.0
        raise ValueError("tail must be 'lower' or 'upper'")

    log_theta = math.log(theta)
    log_weights = [
        _log_comb(n1, x) + _log_comb(n0, m1 - x) + x * log_theta
        for x in range(lower, upper + 1)
    ]
    max_log = max(log_weights)
    weights = [math.exp(value - max_log) for value in log_weights]
    total = sum(weights)
    if total == 0:
        return 0.0
    probs = [weight / total for weight in weights]
    observed_index = observed - lower
    if tail == "lower":
        return sum(probs[: observed_index + 1])
    if tail == "upper":
        return sum(probs[observed_index:])
    raise ValueError("tail must be 'lower' or 'upper'")


def _invert_monotone_tail(
    func,
    target: float,
    *,
    start: float,
    increasing: bool,
    lower_limit: float = 0.0,
    upper_limit: float = float("inf"),
) -> float:
    if start <= 0 or not math.isfinite(start):
        start = 1e-12
    start_value = func(start)
    if math.isclose(start_value, target, rel_tol=0.0, abs_tol=1e-12):
        return start

    if increasing:
        if start_value < target:
            lo = start
            hi = start
            for _ in range(128):
                hi *= 2.0
                if hi >= upper_limit:
                    return upper_limit
                hi_value = func(hi)
                if hi_value >= target:
                    return _bisect_root(lambda value: func(value) - target, lo, hi)
                lo = hi
            return upper_limit
        hi = start
        lo = start
        for _ in range(128):
            lo /= 2.0
            if lo <= lower_limit:
                return lower_limit
            lo_value = func(lo)
            if lo_value <= target:
                return _bisect_root(lambda value: func(value) - target, lo, hi)
            hi = lo
        return lower_limit

    if start_value > target:
        lo = start
        hi = start
        for _ in range(128):
            hi *= 2.0
            if hi >= upper_limit:
                return upper_limit
            hi_value = func(hi)
            if hi_value <= target:
                return _bisect_root(lambda value: func(value) - target, lo, hi)
            lo = hi
        return upper_limit
    hi = start
    lo = start
    for _ in range(128):
        lo /= 2.0
        if lo <= lower_limit:
            return lower_limit
        lo_value = func(lo)
        if lo_value >= target:
            return _bisect_root(lambda value: func(value) - target, lo, hi)
        hi = lo
    return lower_limit


def koopman_risk_ratio(a: int, b: int, c: int, d: int, z: float = 1.96) -> RiskRatioResult:
    """Compute the risk ratio and Koopman asymptotic-score confidence interval."""

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

    point_estimate = _rr_point_estimate(a, b, c, d)
    alpha = math.erfc(z / math.sqrt(2.0))
    target = alpha

    if point_estimate == 0:
        upper = _invert_monotone_tail(
            lambda ratio: _rr_pvalue(a, b, c, d, ratio),
            target,
            start=max(_adjusted_risk_ratio(a, b, c, d), 1e-12),
            increasing=False,
        )
        return RiskRatioResult(value=point_estimate, ci_low=0.0, ci_high=upper)

    if math.isinf(point_estimate):
        lower = _invert_monotone_tail(
            lambda ratio: _rr_pvalue(a, b, c, d, ratio),
            target,
            start=max(_adjusted_risk_ratio(a, b, c, d), 1.0),
            increasing=True,
        )
        return RiskRatioResult(value=point_estimate, ci_low=lower, ci_high=float("inf"))

    lower = _invert_monotone_tail(
        lambda ratio: _rr_pvalue(a, b, c, d, ratio),
        target,
        start=point_estimate,
        increasing=True,
    )
    upper = _invert_monotone_tail(
        lambda ratio: _rr_pvalue(a, b, c, d, ratio),
        target,
        start=point_estimate,
        increasing=False,
    )
    if not _finite_ordered_interval(lower, upper):
        # Paper-grounded guardrail: when score inversion is numerically unstable or
        # yields an open interval for a finite estimate, fall back to Katz CI.
        fallback = katz_risk_ratio(a, b, c, d, z=z)
        if _finite_ordered_interval(fallback.ci_low, fallback.ci_high):
            lower = fallback.ci_low
            upper = fallback.ci_high

    return RiskRatioResult(value=point_estimate, ci_low=lower, ci_high=upper)


def baptista_pike_odds_ratio(a: int, b: int, c: int, d: int, z: float = 1.96) -> OddsRatioResult:
    """Compute the odds ratio and Baptista-Pike exact confidence interval."""

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

    point_estimate = _odds_ratio_value(a, b, c, d)
    n1 = a + b
    n0 = c + d
    m1 = a + c
    lower_support = max(0, m1 - n0)
    upper_support = min(n1, m1)
    if lower_support == upper_support:
        return OddsRatioResult(value=point_estimate, ci_low=0.0, ci_high=float("inf"))

    alpha = math.erfc(z / math.sqrt(2.0))
    tail = alpha / 2.0

    if point_estimate == 0:
        upper = _invert_monotone_tail(
            lambda theta: _tail_probability(a, n1, n0, m1, theta, tail="lower"),
            tail,
            start=max(_adjusted_odds_ratio(a, b, c, d), 1e-12),
            increasing=False,
        )
        return OddsRatioResult(value=point_estimate, ci_low=0.0, ci_high=upper)

    if math.isinf(point_estimate):
        lower = _invert_monotone_tail(
            lambda theta: _tail_probability(a, n1, n0, m1, theta, tail="upper"),
            tail,
            start=max(_adjusted_odds_ratio(a, b, c, d), 1.0),
            increasing=True,
        )
        return OddsRatioResult(value=point_estimate, ci_low=lower, ci_high=float("inf"))

    lower = _invert_monotone_tail(
        lambda theta: _tail_probability(a, n1, n0, m1, theta, tail="upper"),
        tail,
        start=point_estimate,
        increasing=True,
    )
    upper = _invert_monotone_tail(
        lambda theta: _tail_probability(a, n1, n0, m1, theta, tail="lower"),
        tail,
        start=point_estimate,
        increasing=False,
    )
    if not _finite_ordered_interval(lower, upper):
        # Paper-grounded guardrail: continuity-corrected Wald CI is used only when
        # exact inversion cannot provide a finite ordered interval.
        fallback = haldane_anscombe_odds_ratio(a, b, c, d, z=z)
        if _finite_ordered_interval(fallback.ci_low, fallback.ci_high):
            lower = fallback.ci_low
            upper = fallback.ci_high

    return OddsRatioResult(value=point_estimate, ci_low=lower, ci_high=upper)