"""High-precision reference for the exact conditional odds-ratio intervals.

Independent of the kit: this module imports nothing from ``contribution`` and
locates interval ends by brute force (a dense float scan of log(theta), then
60-digit bisection), whereas the kit walks the closed-form breakpoints of the
p-value. Every interval is the hull of a confidence set ``{theta : accept(theta)}``:

- ``baptista-pike``: accept when the minimum-likelihood p-value, the summed
  conditional probability of every table no more probable than the observed one
  (relative tie tolerance 1e-7, as in ``exact2x2``), exceeds alpha
  (Baptista & Pike 1977; Fagerland, Lydersen & Laake 2017).
- ``baptista-pike-midp``: the same p-value minus half the observed table's
  probability (Lancaster 1961).
- ``cornfield``: accept when both one-sided tails exceed alpha / 2
  (Cornfield 1956).

Tables are (a, b, c, d) = (group A events, group A non-events, group B events,
group B non-events); theta is the odds ratio of A versus B.
"""

from __future__ import annotations

import math

import mpmath as mp
import numpy as np

METHODS = ("baptista-pike", "baptista-pike-midp", "cornfield")
TIE_TOLERANCE = 1e-7
SCAN_HALF_WIDTH = 40.0  # log(theta) units either side of the start point
SCAN_STEP = 0.004
REFINE_POINTS = 64
mp.mp.dps = 60


def _support(a: int, b: int, c: int, d: int) -> tuple[int, int, int, int, int]:
    n1, n0, m1 = a + b, c + d, a + c
    return n1, n0, m1, max(0, m1 - n0), min(n1, m1)


def _accept_float(method: str, observed: int, xs: np.ndarray, log_comb: np.ndarray, log_theta: np.ndarray, alpha: float) -> np.ndarray:
    log_w = log_comb[None, :] + xs[None, :] * log_theta[:, None]
    log_w -= log_w.max(axis=1, keepdims=True)
    probs = np.exp(log_w)
    probs /= probs.sum(axis=1, keepdims=True)
    index = observed - int(xs[0])
    p_obs = probs[:, index]
    if method == "cornfield":
        upper_tail = probs[:, index:].sum(axis=1)
        lower_tail = probs[:, : index + 1].sum(axis=1)
        return (upper_tail > alpha / 2) & (lower_tail > alpha / 2)
    pvalue = np.where(probs <= p_obs[:, None] * (1 + TIE_TOLERANCE), probs, 0.0).sum(axis=1)
    if method == "baptista-pike-midp":
        pvalue = pvalue - p_obs / 2
    return pvalue > alpha


def _accept_mp(method: str, observed: int, lo: int, comb: list, log_theta, alpha) -> bool:
    theta = mp.exp(log_theta)
    weights = [w * theta ** (lo + i) for i, w in enumerate(comb)]
    total = mp.fsum(weights)
    probs = [w / total for w in weights]
    index = observed - lo
    p_obs = probs[index]
    if method == "cornfield":
        return mp.fsum(probs[index:]) > alpha / 2 and mp.fsum(probs[: index + 1]) > alpha / 2
    pvalue = mp.fsum(p for p in probs if p <= p_obs * (1 + mp.mpf(TIE_TOLERANCE)))
    if method == "baptista-pike-midp":
        pvalue -= p_obs / 2
    return pvalue > alpha


def _refine(accept, outside, inside):
    """Boundary of the accepted set between an outside and an inside log(theta)."""

    # Sub-scan first so that the bisection starts next to the outermost switch.
    grid = [outside + (inside - outside) * k / REFINE_POINTS for k in range(REFINE_POINTS + 1)]
    for left, right in zip(grid, grid[1:]):
        if accept(right):
            outside, inside = left, right
            break
    while abs(inside - outside) > mp.mpf(10) ** -45:
        mid = (outside + inside) / 2
        if accept(mid):
            inside = mid
        else:
            outside = mid
    return mp.exp((outside + inside) / 2)


def exact_or_interval(a: int, b: int, c: int, d: int, method: str, alpha: float = 0.05) -> tuple[float, float, bool]:
    """Return the (low, high) hull of the method's confidence set as floats, and
    whether the set itself has gaps (so the hull is wider than any one piece)."""

    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}")
    n1, n0, m1, lo, hi = _support(a, b, c, d)
    if lo == hi:
        return 0.0, math.inf, False
    xs = np.arange(lo, hi + 1, dtype=float)
    log_comb = np.array([math.lgamma(n1 + 1) - math.lgamma(x + 1) - math.lgamma(n1 - x + 1) + math.lgamma(n0 + 1) - math.lgamma(m1 - x + 1) - math.lgamma(n0 - m1 + x + 1) for x in range(lo, hi + 1)])
    comb = [mp.binomial(n1, x) * mp.binomial(n0, m1 - x) for x in range(lo, hi + 1)]
    mp_alpha = mp.mpf(alpha)

    def accept(log_theta) -> bool:
        return _accept_mp(method, a, lo, comb, mp.mpf(log_theta), mp_alpha)

    centre = math.log((a + 0.5) * (d + 0.5) / ((b + 0.5) * (c + 0.5)))
    grid = np.arange(centre - SCAN_HALF_WIDTH, centre + SCAN_HALF_WIDTH + SCAN_STEP, SCAN_STEP)
    inside = np.flatnonzero(_accept_float(method, a, xs, log_comb, grid, alpha))
    if inside.size == 0:
        raise RuntimeError(f"empty confidence set for {(a, b, c, d)} / {method}")
    first, last = int(inside[0]), int(inside[-1])
    has_gaps = bool(inside.size != last - first + 1)

    if a == lo:
        low = 0.0
    elif first == 0:
        raise RuntimeError(f"lower end below the scan range for {(a, b, c, d)} / {method}")
    else:
        low = float(_refine(accept, mp.mpf(grid[first - 1]), mp.mpf(grid[first])))

    if a == hi:
        high = math.inf
    elif last == grid.size - 1:
        raise RuntimeError(f"upper end above the scan range for {(a, b, c, d)} / {method}")
    else:
        high = float(_refine(accept, mp.mpf(grid[last + 1]), mp.mpf(grid[last])))
    return low, high, has_gaps
