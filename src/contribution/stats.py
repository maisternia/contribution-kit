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


def _canonical_z(z: float) -> float:
    if math.isclose(z, 1.96, rel_tol=0.0, abs_tol=1e-12):
        return 1.959963984540054
    return z


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


def _real_cuberoot(value: float) -> float:
    if value == 0.0:
        return 0.0
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def _rr_point_estimate(a: int, b: int, c: int, d: int) -> float:
    risk_a = a / (a + b)
    risk_b = c / (c + d)
    if risk_b == 0:
        return float("inf")
    return risk_a / risk_b


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


def _koopman_confidence_limits(x1: int, n1: int, x2: int, n2: int, z: float) -> tuple[float, float]:
    if x2 == 0 and x1 == 0:
        return 0.0, float("inf")

    z2 = z * z
    a1 = n2 * (n2 * (n2 + n1) * x1 + n1 * (n2 + x1) * z2)
    a2 = -n2 * (n2 * n1 * (x2 + x1) + 2.0 * (n2 + n1) * x2 * x1 + n1 * (n2 + x2 + 2.0 * x1) * z2)
    a3 = 2.0 * n2 * n1 * x2 * (x2 + x1) + (n2 + n1) * (x2 * x2) * x1 + n2 * n1 * (x2 + x1) * z2
    a4 = -n1 * (x2 * x2) * (x2 + x1)
    b1 = a2 / a1
    b2 = a3 / a1
    b3 = a4 / a1
    c1 = b2 - (b1 * b1) / 3.0
    c2 = b3 - b1 * b2 / 3.0 + 2.0 * (b1 * b1 * b1) / 27.0

    roots: list[float]
    if abs(c1) <= 1e-15:
        roots = [_real_cuberoot(-c2) - b1 / 3.0] * 3
    else:
        acos_arg = math.sqrt(27.0) * c2 / (2.0 * c1 * math.sqrt(-c1))
        acos_arg = min(1.0, max(-1.0, acos_arg))
        ceta = math.acos(acos_arg)
        scale = 2.0 * math.sqrt(-c1 / 3.0)
        t1 = -scale * math.cos(math.pi / 3.0 - ceta / 3.0)
        t2 = -scale * math.cos(math.pi / 3.0 + ceta / 3.0)
        t3 = scale * math.cos(ceta / 3.0)
        roots = [t1 - b1 / 3.0, t2 - b1 / 3.0, t3 - b1 / 3.0]

    p0up = min(roots)
    p0low = sum(roots) - p0up - max(roots)

    def limit_from_p0(p0: float) -> float:
        numerator = 1.0 - (n1 - x1) * (1.0 - p0) / (x2 + n1 - (n2 + n1) * p0)
        return numerator / p0

    if x2 == 0 and x1 != 0:
        return limit_from_p0(p0low), float("inf")

    if x2 != n2 and x1 == 0:
        return 0.0, limit_from_p0(p0up)

    if x2 == n2 and x1 == n1:
        return n1 / (n1 + z2), (n2 + z2) / n2

    def chi_stat(phi: float, i: int, j: int, ni: int, nj: int) -> float:
        a = (ni + nj) * phi
        b = -((i + nj) * phi + j + ni)
        c = i + j
        disc = max(b * b - 4.0 * a * c, 0.0)
        p1hat = (-b - math.sqrt(disc)) / (2.0 * a)
        p2hat = p1hat * phi
        q2hat = 1.0 - p2hat
        variance = (ni * nj * p2hat) / (nj * (phi - p2hat) + ni * q2hat)
        return ((j - nj * p2hat) / q2hat) / math.sqrt(variance)

    if x1 == n1 or x2 == n2:
        lower = 0.0
        if x2 == n2 and x1 != 0:
            phat1 = x2 / n2
            phat2 = x1 / n1
            phil = 0.95 * (phat2 / phat1)
            chi2 = 0.0
            while chi2 <= z:
                chi2 = chi_stat(phil, x2, x1, n2, n1)
                lower = phil
                phil = lower / 1.0001

        i = x2
        j = x1
        ni = n2
        nj = n1
        if x1 == n1:
            i = x1
            j = x2
            ni = n1
            nj = n2

        phat1 = i / ni
        phat2 = j / nj
        phiu = 1.1 * (phat2 / phat1)
        if x2 == n2 and x1 == 0:
            phiu = 0.01 if n2 < 100 else 0.001

        chi1 = 0.0
        phiu1 = phiu
        while chi1 >= -z:
            chi1 = chi_stat(phiu, i, j, ni, nj)
            phiu1 = phiu
            phiu = 1.0001 * phiu1

        if x1 == n1:
            return 1.0 / phiu1, limit_from_p0(p0up)
        return lower, phiu1

    return limit_from_p0(p0low), limit_from_p0(p0up)


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


def _exact_or_support(a: int, b: int, c: int, d: int) -> tuple[int, int, int, int, list[int], list[float]]:
    m = a + b
    n = c + d
    k = a + c
    lo = max(0, k - n)
    hi = min(m, k)
    support = list(range(lo, hi + 1))
    logf0 = [_log_comb(m, x) + _log_comb(n, k - x) - _log_comb(m + n, k) for x in support]
    return m, n, k, lo, support, logf0


def _noncentral_hypergeom_probs(support: list[int], logf0: list[float], theta: float) -> list[float]:
    ns = len(support)
    if theta == 0.0:
        return [1.0] + [0.0] * (ns - 1)
    if math.isinf(theta):
        return [0.0] * (ns - 1) + [1.0]

    log_theta = math.log(theta)
    log_weights = [base + log_theta * support_value for base, support_value in zip(logf0, support)]
    max_log = max(log_weights)
    weights = [math.exp(value - max_log) for value in log_weights]
    total = sum(weights)
    return [weight / total for weight in weights]


def _central_tail_probability(support: list[int], probs: list[float], observed: int, *, lower_tail: bool) -> float:
    if lower_tail:
        return sum(prob for support_value, prob in zip(support, probs) if support_value <= observed)
    return sum(prob for support_value, prob in zip(support, probs) if support_value >= observed)


def _baptista_pike_confidence_limits(a: int, b: int, c: int, d: int, *, conf_level: float = 0.95, tol: float = 1e-5) -> tuple[float, float]:
    alpha = 1.0 - conf_level
    or_range = (1e-10, 1e10)
    _m, _n, _k, lo, support, logf0 = _exact_or_support(a, b, c, d)
    hi = support[-1]
    observed = a

    root_tol = 1e-12

    def pnhyper(x: int, theta: float, *, lower_tail: bool) -> float:
        probs = _noncentral_hypergeom_probs(support, logf0, theta)
        return _central_tail_probability(support, probs, x, lower_tail=lower_tail)

    def intercept(xlo: int, xhi: int) -> float:
        idx_lo = support.index(xlo)
        idx_hi = support.index(xhi)
        return math.exp((logf0[idx_lo] - logf0[idx_hi]) / (xhi - xlo))

    def bnds(xlo: int, xhi: int, theta_range: tuple[float, float], ndiv: int = 1) -> dict[str, list[float]]:
        theta_lo, theta_hi = theta_range
        step = (theta_hi - theta_lo) / ndiv
        theta_values = [theta_lo + step * index for index in range(ndiv + 1)]
        lower_vals = [pnhyper(xlo, theta, lower_tail=True) for theta in theta_values]
        upper_vals = [pnhyper(xhi, theta, lower_tail=False) for theta in theta_values]
        bndlo = [lower_vals[index + 1] + upper_vals[index] for index in range(ndiv)]
        bndhi = [lower_vals[index] + upper_vals[index + 1] for index in range(ndiv)]
        return {"or": theta_values, "bndlo": bndlo, "bndhi": bndhi}

    def get_cl_bnds(bounds: dict[str, list[float]], *, limit: str) -> tuple[tuple[float, float] | None, bool]:
        hi_bound = max(bounds["bndhi"])
        lo_bound = min(bounds["bndlo"])
        if hi_bound <= alpha:
            return None, True
        if lo_bound > alpha:
            edge = max(bounds["or"]) if limit == "upper" else min(bounds["or"])
            return (edge - tol / 2.0, edge + tol / 2.0), False

        if limit == "upper":
            if any(value > alpha for value in bounds["bndlo"]):
                lo_value = max(bounds["or"][index + 1] for index, value in enumerate(bounds["bndlo"]) if value > alpha)
            else:
                lo_value = min(bounds["or"])
            hi_value = max(bounds["or"][index + 1] for index, value in enumerate(bounds["bndhi"]) if value > alpha)
            return (lo_value, hi_value), True

        if any(value > alpha for value in bounds["bndlo"]):
            hi_value = min(bounds["or"][index] for index, value in enumerate(bounds["bndlo"]) if value > alpha)
        else:
            hi_value = max(bounds["or"])
        lo_value = min(bounds["or"][index] for index, value in enumerate(bounds["bndhi"]) if value > alpha)
        return (lo_value, hi_value), True

    def refine(xlo: int, xhi: int, theta_range: tuple[float, float], *, limit: str, ndiv: int = 100, max_iter: int = 50) -> tuple[float, float] | None:
        bounds = bnds(xlo, xhi, theta_range, ndiv=1)
        cl_bounds, should_continue = get_cl_bnds(bounds, limit=limit)
        if cl_bounds is None or not should_continue:
            return cl_bounds

        current_range = cl_bounds
        for _ in range(max_iter):
            bounds = bnds(xlo, xhi, current_range, ndiv=ndiv)
            cl_bounds, should_continue = get_cl_bnds(bounds, limit=limit)
            if cl_bounds is None or not should_continue:
                return cl_bounds
            current_range = cl_bounds
            if current_range[1] - current_range[0] <= tol:
                return current_range
            ndiv *= 2
        return current_range

    lower = 0.0 if observed == lo else float("nan")
    upper = float("inf") if observed == hi else float("nan")

    if math.isnan(upper):
        xgreater_values = list(range(hi, observed, -1))
        upper_intercepts: list[float] = []
        for index, xgreater in enumerate(xgreater_values):
            theta_intercept = intercept(observed, xgreater)
            upper_intercepts.append(theta_intercept)
            lower_tail_prob = pnhyper(observed, theta_intercept, lower_tail=True)
            if index == 0:
                if lower_tail_prob > alpha:
                    if alpha - pnhyper(observed, or_range[1], lower_tail=True) < 0:
                        raise ValueError("very large odds ratio, modify search range")
                    upper = _bisect_root(
                        lambda theta: alpha - pnhyper(observed, theta, lower_tail=True),
                        theta_intercept,
                        or_range[1],
                        tol=root_tol,
                    )
                    break
                if lower_tail_prob == alpha:
                    upper = theta_intercept
                    break
            else:
                refined = refine(
                    observed,
                    xgreater_values[index - 1],
                    (upper_intercepts[index], upper_intercepts[index - 1]),
                    limit="upper",
                )
                if refined is not None:
                    upper = refined[1]
                    break
                if index == len(xgreater_values) - 1:
                    upper = theta_intercept

    if math.isnan(lower):
        xless_values = list(range(lo, observed))
        lower_intercepts: list[float] = []
        for index, xless in enumerate(xless_values):
            theta_intercept = intercept(xless, observed)
            lower_intercepts.append(theta_intercept)
            upper_tail_prob = pnhyper(observed, theta_intercept, lower_tail=False)
            if index == 0:
                if upper_tail_prob > alpha:
                    if alpha - pnhyper(observed, or_range[0], lower_tail=False) < 0:
                        raise ValueError("very small odds ratio, modify search range")
                    lower = _bisect_root(
                        lambda theta: alpha - pnhyper(observed, theta, lower_tail=False),
                        or_range[0],
                        theta_intercept,
                        tol=root_tol,
                    )
                    break
                if upper_tail_prob == alpha:
                    lower = theta_intercept
                    break
            else:
                refined = refine(
                    xless_values[index - 1],
                    observed,
                    (lower_intercepts[index - 1], lower_intercepts[index]),
                    limit="lower",
                )
                if refined is not None:
                    lower = refined[0]
                    break
                if index == len(xless_values) - 1:
                    lower = theta_intercept

    decimals = max(0, int(math.floor(-math.log10(tol)) - 1))
    return round(lower, decimals), round(upper, decimals)


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
    z = _canonical_z(z)

    point_estimate = _rr_point_estimate(a, b, c, d)
    lower, upper = _koopman_confidence_limits(a, a + b, c, c + d, z)
    return RiskRatioResult(value=point_estimate, ci_low=lower, ci_high=upper)


def baptista_pike_odds_ratio(a: int, b: int, c: int, d: int, z: float = 1.96) -> OddsRatioResult:
    """Compute the odds ratio and Baptista-Pike exact confidence interval."""

    _validate_2x2_counts(a, b, c, d)
    z = _canonical_z(z)

    point_estimate = _odds_ratio_value(a, b, c, d)
    m = a + b
    n = c + d
    k = a + c
    lower_support = max(0, k - n)
    upper_support = min(m, k)
    if lower_support == upper_support:
        return OddsRatioResult(value=point_estimate, ci_low=0.0, ci_high=float("inf"))

    lower, upper = _baptista_pike_confidence_limits(a, b, c, d, conf_level=1.0 - math.erfc(z / math.sqrt(2.0)))
    return OddsRatioResult(value=point_estimate, ci_low=lower, ci_high=upper)