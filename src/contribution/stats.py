"""Statistical utilities for binary 2x2 table effect sizes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

Z_95 = NormalDist().inv_cdf(0.975)
"""Two-sided 95% normal quantile (1.959964...), the default ``z`` of every interval."""


@dataclass(slots=True)
class RiskRatioResult:
    value: float
    ci_low: float | None
    ci_high: float | None
    ci_method: str
    """Method that produced the bounds: ``"koopman"`` or ``"katz"``."""


@dataclass(slots=True)
class OddsRatioResult:
    value: float
    ci_low: float
    ci_high: float
    ci_method: str
    """Method that produced the bounds: ``"baptista-pike"``, ``"baptista-pike-midp"``,
    ``"cornfield"`` or ``"haldane-anscombe"``."""


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


def katz_risk_ratio(a: int, b: int, c: int, d: int, z: float = Z_95) -> RiskRatioResult:
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
        return RiskRatioResult(value=float("inf"), ci_low=None, ci_high=None, ci_method="katz")

    rr = p_exposed / p_baseline  # @cite: Katz et al., 1978

    if min(a, b, c, d) == 0:
        return RiskRatioResult(value=rr, ci_low=None, ci_high=None, ci_method="katz")

    # Log-transform SE and CI @cite: Katz et al., 1978
    se = math.sqrt((1 / a) - (1 / (a + b)) + (1 / c) - (1 / (c + d)))
    ci_low = math.exp(math.log(rr) - z * se)
    ci_high = math.exp(math.log(rr) + z * se)
    return RiskRatioResult(value=rr, ci_low=ci_low, ci_high=ci_high, ci_method="katz")


def haldane_anscombe_odds_ratio(a: int, b: int, c: int, d: int, z: float = Z_95) -> OddsRatioResult:
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
    return OddsRatioResult(value=odds_ratio, ci_low=ci_low, ci_high=ci_high, ci_method="haldane-anscombe")


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
    if n_total > 1:  # pragma: no branch
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


def miettinen_nurminen_risk_difference(a: int, b: int, c: int, d: int, z: float = Z_95) -> RiskDifferenceResult:
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


def agresti_caffo_risk_difference(a: int, b: int, c: int, d: int, z: float = Z_95) -> RiskDifferenceResult:
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


def risk_difference_with_guardrail(a: int, b: int, c: int, d: int, z: float = Z_95) -> RiskDifferenceResult:
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


def _rr_point_estimate(a: int, b: int, c: int, d: int) -> float:
    risk_a = a / (a + b)
    risk_b = c / (c + d)
    if risk_b == 0:
        return float("inf")
    return risk_a / risk_b


def _two_sided_alpha(z: float) -> float:
    return math.erfc(z / math.sqrt(2.0))


_LOG_RATIO_LIMIT = 300.0
"""Search bound on log(ratio); a bound beyond e**300 is reported as 0 or infinity."""


def _solve_log_root(func, target: float, start: float, *, increasing: bool) -> float:
    """Return the ``u = log(ratio)`` where the monotone ``func(u)`` crosses ``target``.

    The crossing is bracketed by doubling steps away from ``start`` and refined by
    bisection to 1e-13 in ``u``, a relative 1e-13 on the ratio. A crossing beyond
    +/- ``_LOG_RATIO_LIMIT`` is returned as +/- infinity.
    """

    def excess(u: float) -> float:
        value = func(u) - target
        return value if increasing else -value

    start = min(max(start, -_LOG_RATIO_LIMIT), _LOG_RATIO_LIMIT)
    step = 1.0
    if excess(start) < 0.0:
        lo = start
        hi = start + step
        while excess(hi) < 0.0:
            if hi >= _LOG_RATIO_LIMIT:
                return math.inf
            lo = hi
            step *= 2.0
            hi = min(start + step, _LOG_RATIO_LIMIT)
    else:
        hi = start
        lo = start - step
        while excess(lo) >= 0.0:
            if lo <= -_LOG_RATIO_LIMIT:
                return -math.inf
            hi = lo
            step *= 2.0
            lo = max(start - step, -_LOG_RATIO_LIMIT)
    while hi - lo > 1e-13:
        mid = (lo + hi) / 2.0
        if excess(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _koopman_score(a: int, b: int, c: int, d: int, ratio: float) -> float:
    """Koopman's score statistic for the null hypothesis ``p1 = ratio * p0``.

    ``(p1_hat - ratio * p0_hat) / sqrt(p1(1 - p1)/n1 + ratio**2 * p0(1 - p0)/n0)``
    at the restricted maximum-likelihood estimates ``p1 = ratio * p0`` (Koopman
    1984; the Miettinen-Nurminen score without its N/(N - 1) factor). It decreases
    as ``ratio`` grows.
    """

    n1 = a + b
    n0 = c + d
    events = a + c
    # p0 is the smaller root of N*ratio*p0**2 - B*p0 + (a + c) = 0, written as
    # 2C / (B + sqrt(B**2 - 4AC)) so that it does not cancel for large ratios.
    qa = (n1 + n0) * ratio
    qb = n1 * ratio + a + n0 + c * ratio
    disc = max(qb * qb - 4.0 * qa * events, 0.0)
    p0 = 2.0 * events / (qb + math.sqrt(disc))
    p1 = p0 * ratio
    eps = 1e-12
    p0 = min(max(p0, eps), 1.0 - eps)
    p1 = min(max(p1, eps), 1.0 - eps)
    variance = p1 * (1.0 - p1) / n1 + ratio * ratio * p0 * (1.0 - p0) / n0
    return (a / n1 - ratio * c / n0) / math.sqrt(variance)


def koopman_risk_ratio(a: int, b: int, c: int, d: int, z: float = Z_95) -> RiskRatioResult:
    """Compute the risk ratio and the Koopman asymptotic-score confidence interval.

    The bounds are the ratios at which the score statistic equals ``z`` and
    ``-z``. No mismatches in group A give ``[0, upper]``; none in group B give
    ``[lower, inf)``; none in either give ``[0, inf)``. If the inversion fails
    numerically for a finite estimate, the Katz interval is returned instead and
    the result's ``ci_method`` says so.

    Reference:
        Koopman, P. A. R. (1984). Confidence intervals for the ratio of two
        binomial proportions. Biometrics, 40(2), 513-517.
    """

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

    point_estimate = _rr_point_estimate(a, b, c, d)
    if a == 0 and c == 0:
        return RiskRatioResult(value=point_estimate, ci_low=0.0, ci_high=math.inf, ci_method="koopman")

    def score(log_ratio: float) -> float:
        return _koopman_score(a, b, c, d, math.exp(log_ratio))

    # The continuity-adjusted ratio is finite and positive for every table.
    start = math.log(((a + 0.5) / (a + b + 1.0)) / ((c + 0.5) / (c + d + 1.0)))
    lower = 0.0 if a == 0 else math.exp(_solve_log_root(score, z, start, increasing=False))
    upper = math.inf if c == 0 else math.exp(_solve_log_root(score, -z, start, increasing=False))
    if math.isfinite(point_estimate) and not _finite_ordered_interval(lower, upper):
        fallback = katz_risk_ratio(a, b, c, d, z=z)
        if _finite_ordered_interval(fallback.ci_low, fallback.ci_high):
            return fallback
    return RiskRatioResult(value=point_estimate, ci_low=lower, ci_high=upper, ci_method="koopman")


def _conditional_log_weights(a: int, b: int, c: int, d: int) -> tuple[int, int, list[float]]:
    """Support ``[lo, hi]`` of the conditional distribution of ``a`` given the
    margins, and ``log(C(n1, x) * C(n0, m1 - x))`` for each support point."""

    n1 = a + b
    n0 = c + d
    m1 = a + c
    lo = max(0, m1 - n0)
    hi = min(n1, m1)
    log_weights = [
        math.lgamma(n1 + 1) - math.lgamma(x + 1) - math.lgamma(n1 - x + 1)
        + math.lgamma(n0 + 1) - math.lgamma(m1 - x + 1) - math.lgamma(n0 - m1 + x + 1)
        for x in range(lo, hi + 1)
    ]
    return lo, hi, log_weights


def _conditional_probabilities(log_weights: list[float], log_theta: float) -> list[float]:
    """Noncentral hypergeometric probabilities of the support points, lowest first."""

    terms = [weight + index * log_theta for index, weight in enumerate(log_weights)]
    peak = max(terms)
    exps = [math.exp(term - peak) for term in terms]
    total = math.fsum(exps)
    return [value / total for value in exps]


def _adjusted_log_odds_ratio(a: int, b: int, c: int, d: int) -> float:
    return math.log((a + 0.5) * (d + 0.5) / ((b + 0.5) * (c + 0.5)))


def _odds_ratio_result(
    a: int, b: int, c: int, d: int, z: float, point_estimate: float, lower: float, upper: float, method: str
) -> OddsRatioResult:
    if math.isfinite(point_estimate) and not _finite_ordered_interval(lower, upper):
        # Guard against a numerical failure of the exact inversion; the
        # Haldane-Anscombe interval is always finite and the label records it.
        fallback = haldane_anscombe_odds_ratio(a, b, c, d, z=z)
        return OddsRatioResult(
            value=point_estimate, ci_low=fallback.ci_low, ci_high=fallback.ci_high, ci_method=fallback.ci_method
        )
    return OddsRatioResult(value=point_estimate, ci_low=lower, ci_high=upper, ci_method=method)


def cornfield_exact_odds_ratio(a: int, b: int, c: int, d: int, z: float = Z_95) -> OddsRatioResult:
    """Compute the odds ratio and the Cornfield exact conditional confidence interval.

    Each bound inverts one tail of the conditional (noncentral hypergeometric)
    distribution of ``a`` given the table margins at alpha / 2: ``P(X >= a)`` for
    the lower and ``P(X <= a)`` for the upper bound. This is the central exact
    interval that ``fisher.test`` reports.

    Reference:
        Cornfield, J. (1956). A statistical problem arising from retrospective
        studies. Proceedings of the Third Berkeley Symposium on Mathematical
        Statistics and Probability, 4, 135-148.
    """

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

    point_estimate = _odds_ratio_value(a, b, c, d)
    lo, hi, log_weights = _conditional_log_weights(a, b, c, d)
    if lo == hi:
        return OddsRatioResult(value=point_estimate, ci_low=0.0, ci_high=math.inf, ci_method="cornfield")

    tail = _two_sided_alpha(z) / 2.0
    index = a - lo
    start = _adjusted_log_odds_ratio(a, b, c, d)

    def upper_tail(log_theta: float) -> float:
        return math.fsum(_conditional_probabilities(log_weights, log_theta)[index:])

    def lower_tail(log_theta: float) -> float:
        return math.fsum(_conditional_probabilities(log_weights, log_theta)[: index + 1])

    lower = 0.0 if a == lo else math.exp(_solve_log_root(upper_tail, tail, start, increasing=True))
    upper = math.inf if a == hi else math.exp(_solve_log_root(lower_tail, tail, start, increasing=False))
    return _odds_ratio_result(a, b, c, d, z, point_estimate, lower, upper, "cornfield")


_BP_TIE_TOLERANCE = 1e-7
"""Relative tolerance for "no more probable than the observed table" (as in exact2x2)."""
_BP_SAMPLE_STEP = 0.02
"""Largest spacing, in log(theta), between p-value evaluations within a segment."""
_BP_MIN_SAMPLES = 8


def _bp_pvalue(log_weights: list[float], index: int, log_theta: float, mid_p: bool) -> float:
    probs = _conditional_probabilities(log_weights, log_theta)
    observed = probs[index]
    limit = observed * (1.0 + _BP_TIE_TOLERANCE)
    pvalue = math.fsum(prob for prob in probs if prob <= limit)
    return pvalue - observed / 2.0 if mid_p else pvalue


def _bp_boundary(accept, outside: float, inside: float) -> float:
    """Bisect between a rejected and an accepted log(theta) to 1e-13."""

    while abs(inside - outside) > 1e-13:
        mid = (outside + inside) / 2.0
        if accept(mid):
            inside = mid
        else:
            outside = mid
    return math.exp((outside + inside) / 2.0)


def _bp_end(accept, edges: list[float], *, inward: int) -> float:
    """Outermost end of the accepted set, scanning inward from one window edge
    (``inward`` 1: from the low edge, -1: from the high edge).

    The p-value is evaluated segment by segment between breakpoints, at least
    ``_BP_MIN_SAMPLES`` times per segment and no further apart than
    ``_BP_SAMPLE_STEP``. The window edge itself is outside the set, so the first
    accepted point and the point before it bracket the end."""

    segments = list(zip(edges, edges[1:]))[::inward]
    outside = edges[0] if inward == 1 else edges[-1]
    for left, right in segments:  # pragma: no branch - the set is never empty
        count = max(_BP_MIN_SAMPLES, math.ceil((right - left) / _BP_SAMPLE_STEP))
        nudge = 1e-12 * max(1.0, abs(left), abs(right))
        points = [left + nudge + (right - left - 2 * nudge) * k / (count - 1) for k in range(count)]
        for inside in points[::inward]:
            if accept(inside):
                return _bp_boundary(accept, outside, inside)
            outside = inside


def baptista_pike_odds_ratio(
    a: int, b: int, c: int, d: int, z: float = Z_95, *, mid_p: bool = False
) -> OddsRatioResult:
    """Compute the odds ratio and the Baptista-Pike exact conditional confidence interval.

    The p-value of an odds ratio theta is the summed conditional (noncentral
    hypergeometric) probability of every table, with the observed margins, that
    is no more probable than the observed one (relative tie tolerance 1e-7). The
    confidence set is every theta whose p-value exceeds alpha. That p-value is
    neither continuous nor monotone in theta, so the set can have gaps; the
    interval returned is its hull, as in ``exact2x2(tsmethod = "minlike")``.
    With ``mid_p=True`` half the observed table's probability is subtracted from
    the p-value (the mid-p interval).

    The set is searched within a window that provably contains it: the p-value
    never exceeds (support size + 1) times either one-sided tail. Inside the
    window the p-value is evaluated at every closed-form breakpoint (where a
    table becomes as probable as the observed one) and densely between them,
    and each end is refined by bisection.

    References:
        Baptista, J., & Pike, M. C. (1977). Algorithm AS 115: Exact two-sided
        confidence limits for the odds ratio in a 2x2 table. Journal of the
        Royal Statistical Society, Series C, 26(2), 214-220.
        Fagerland, M. W., Lydersen, S., & Laake, P. (2017). Statistical
        Analysis of Contingency Tables. CRC Press.
        Lancaster, H. O. (1961). Significance tests in discrete distributions.
        Journal of the American Statistical Association, 56(294), 223-234.
    """

    _validate_2x2_counts(a, b, c, d)
    _validate_z_score(z)

    method = "baptista-pike-midp" if mid_p else "baptista-pike"
    point_estimate = _odds_ratio_value(a, b, c, d)
    lo, hi, log_weights = _conditional_log_weights(a, b, c, d)
    if lo == hi:
        return OddsRatioResult(value=point_estimate, ci_low=0.0, ci_high=math.inf, ci_method=method)

    alpha = _two_sided_alpha(z)
    index = a - lo
    start = _adjusted_log_odds_ratio(a, b, c, d)

    def accept(log_theta: float) -> bool:
        return _bp_pvalue(log_weights, index, log_theta, mid_p) > alpha

    # Window: outside it one tail is below alpha / (K + 1), so the p-value is at
    # most alpha there.
    window_tail = alpha / (len(log_weights) + 1)
    window_low = -_LOG_RATIO_LIMIT
    window_high = _LOG_RATIO_LIMIT
    if a != lo:
        window_low = max(window_low, _solve_log_root(
            lambda u: math.fsum(_conditional_probabilities(log_weights, u)[index:]),
            window_tail, start, increasing=True,
        ))
    if a != hi:
        window_high = min(window_high, _solve_log_root(
            lambda u: math.fsum(_conditional_probabilities(log_weights, u)[: index + 1]),
            window_tail, start, increasing=False,
        ))

    # Breakpoints: support point i is in the summed set for u <= t_i (i > index)
    # or u >= t_i (i < index), where t_i solves log f(i) = log f(index) + tol.
    tolerance = math.log1p(_BP_TIE_TOLERANCE)
    edges = [window_low, window_high]
    for i, weight in enumerate(log_weights):
        if i != index:
            t = (tolerance - (weight - log_weights[index])) / (i - index)
            if window_low < t < window_high:
                edges.append(t)
    edges.sort()
    lower = 0.0 if a == lo else _bp_end(accept, edges, inward=1)
    upper = math.inf if a == hi else _bp_end(accept, edges, inward=-1)
    return _odds_ratio_result(a, b, c, d, z, point_estimate, lower, upper, method)
