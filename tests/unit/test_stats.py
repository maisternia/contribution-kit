from __future__ import annotations

import itertools
import math

import pytest

from contribution import stats
from contribution.stats import (
    Z_95,
    agresti_caffo_risk_difference,
    baptista_pike_odds_ratio,
    cornfield_exact_odds_ratio,
    haldane_anscombe_odds_ratio,
    katz_risk_ratio,
    koopman_risk_ratio,
    miettinen_nurminen_risk_difference,
    risk_difference_with_guardrail,
)


def test_validate_2x2_count_guards() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        stats._validate_2x2_counts(-1, 0, 1, 1)
    with pytest.raises(ValueError, match="Exposed group cannot be empty"):
        stats._validate_2x2_counts(0, 0, 1, 1)
    with pytest.raises(ValueError, match="Baseline group cannot be empty"):
        stats._validate_2x2_counts(1, 1, 0, 0)


def test_default_z_is_the_exact_95_percent_quantile() -> None:
    assert math.isclose(Z_95, 1.959963984540054, rel_tol=1e-15)
    assert koopman_risk_ratio(20, 80, 10, 90) == koopman_risk_ratio(20, 80, 10, 90, z=Z_95)
    assert katz_risk_ratio(20, 80, 10, 90) != katz_risk_ratio(20, 80, 10, 90, z=1.96)


def test_katz_risk_ratio_paths() -> None:
    finite = katz_risk_ratio(20, 80, 10, 90)
    assert finite.ci_low is not None and finite.ci_high is not None
    assert finite.ci_method == "katz"

    inf_case = katz_risk_ratio(10, 90, 0, 100)
    assert math.isinf(inf_case.value)
    assert inf_case.ci_low is None and inf_case.ci_high is None
    assert inf_case.ci_method == "katz"

    zero_cell = katz_risk_ratio(0, 100, 10, 90)
    assert zero_cell.ci_low is None and zero_cell.ci_high is None
    assert zero_cell.ci_method == "katz"


def test_haldane_anscombe_odds_ratio_sparse() -> None:
    result = haldane_anscombe_odds_ratio(10, 90, 0, 100)
    assert result.value > 1.0
    assert result.ci_low > 0.0
    assert result.ci_high > result.ci_low
    assert result.ci_method == "haldane-anscombe"


def test_koopman_risk_ratio_value_classes() -> None:
    finite = koopman_risk_ratio(1, 13, 9, 1)
    assert math.isclose(finite.value, 0.07936507936507936, rel_tol=0, abs_tol=1e-12)
    # PropCIs::riskscoreci(1, 14, 9, 10, 0.95)
    assert math.isclose(finite.ci_low, 0.014034259570284, rel_tol=1e-7)
    assert math.isclose(finite.ci_high, 0.361965891057327, rel_tol=1e-7)
    assert finite.ci_method == "koopman"

    zero_point = koopman_risk_ratio(0, 100, 10, 90)
    assert zero_point.value == 0.0
    assert zero_point.ci_low == 0.0
    assert math.isclose(zero_point.ci_high, 0.37356166327359, rel_tol=1e-7)

    inf_point = koopman_risk_ratio(10, 90, 0, 100)
    assert math.isinf(inf_point.value)
    assert math.isclose(inf_point.ci_low, 2.67693422081022, rel_tol=1e-7)
    assert math.isinf(inf_point.ci_high)

    no_events = koopman_risk_ratio(0, 5, 0, 5)
    assert no_events.ci_low == 0.0 and math.isinf(no_events.ci_high)
    assert no_events.ci_method == "koopman"


def test_koopman_zero_event_reference_has_correct_lower_bound() -> None:
    # The old score statistic put this at 18.0; riskscoreci gives 390.07.
    result = koopman_risk_ratio(248, 746, 0, 6002)
    assert math.isinf(result.value) and math.isinf(result.ci_high)
    assert math.isclose(result.ci_low, 390.067506133976, rel_tol=1e-7)


def test_koopman_sparse_tables_use_the_primary_method() -> None:
    # These rows used to need the Katz fallback; the corrected score needs none.
    for a, b, c, d in [(22, 1, 291, 12963), (168, 329, 145, 12635), (1, 1, 1, 1)]:
        rr = koopman_risk_ratio(a, b, c, d)
        assert rr.ci_method == "koopman"
        assert rr.ci_low is not None and rr.ci_high is not None
        assert math.isfinite(rr.ci_low) and math.isfinite(rr.ci_high)
        assert rr.ci_low <= rr.value <= rr.ci_high


def test_point_estimates_are_raw_ratios() -> None:
    for a, b, c, d in [(22, 1, 291, 13254), (168, 329, 145, 12780)]:
        expected_rr = a / (a + b) / (c / (c + d))
        assert math.isclose(koopman_risk_ratio(a, b, c, d).value, expected_rr, rel_tol=0.0, abs_tol=1e-12)
        expected_or = (a * d) / (b * c)
        for result in (
            baptista_pike_odds_ratio(a, b, c, d),
            baptista_pike_odds_ratio(a, b, c, d, mid_p=True),
            cornfield_exact_odds_ratio(a, b, c, d),
        ):
            assert math.isclose(result.value, expected_or, rel_tol=0.0, abs_tol=1e-12)


def test_koopman_fallback_is_labelled(monkeypatch) -> None:
    monkeypatch.setattr(stats, "_solve_log_root", lambda *args, **kwargs: math.inf)
    fallback = koopman_risk_ratio(20, 80, 10, 90)
    assert fallback.ci_method == "katz"
    assert (fallback.ci_low, fallback.ci_high) == (
        katz_risk_ratio(20, 80, 10, 90).ci_low,
        katz_risk_ratio(20, 80, 10, 90).ci_high,
    )


def test_koopman_keeps_its_own_bounds_when_katz_has_none(monkeypatch) -> None:
    # A zero cell leaves Katz without an interval, so the failed inversion stands.
    monkeypatch.setattr(stats, "_solve_log_root", lambda *args, **kwargs: math.inf)
    result = koopman_risk_ratio(0, 10, 5, 5)
    assert result.ci_method == "koopman"
    assert result.ci_low == 0.0 and math.isinf(result.ci_high)


@pytest.mark.parametrize(
    ("func", "kwargs", "label"),
    [
        (baptista_pike_odds_ratio, {}, "baptista-pike"),
        (baptista_pike_odds_ratio, {"mid_p": True}, "baptista-pike-midp"),
        (cornfield_exact_odds_ratio, {}, "cornfield"),
    ],
)
def test_odds_ratio_interval_paths(func, kwargs, label) -> None:
    finite = func(1, 13, 9, 1, **kwargs)
    assert finite.ci_low < finite.value < finite.ci_high
    assert finite.ci_method == label

    zero_point = func(0, 100, 10, 90, **kwargs)
    assert zero_point.value == 0.0
    assert zero_point.ci_low == 0.0 and math.isfinite(zero_point.ci_high)

    inf_point = func(10, 90, 0, 100, **kwargs)
    assert math.isinf(inf_point.value)
    assert math.isfinite(inf_point.ci_low) and math.isinf(inf_point.ci_high)

    collapsed = func(0, 1, 0, 1, **kwargs)
    assert collapsed.ci_low == 0.0 and math.isinf(collapsed.ci_high)
    assert collapsed.ci_method == label


def test_baptista_pike_lower_bound_sits_on_a_breakpoint() -> None:
    # The p-value jumps across alpha at theta ~ 162.5 (exact2x2 minlike: 162.505555).
    result = baptista_pike_odds_ratio(22, 1, 291, 12963)
    assert math.isclose(result.ci_low, 162.505553, rel_tol=1e-6)
    assert math.isclose(result.ci_high, 19952.23983, rel_tol=1e-6)
    midp = baptista_pike_odds_ratio(22, 1, 291, 12963, mid_p=True)
    assert math.isclose(midp.ci_low, 162.505553, rel_tol=1e-6)
    assert math.isclose(midp.ci_high, 10184.3, rel_tol=1e-5)


def test_baptista_pike_midp_reports_the_hull_of_a_set_with_gaps() -> None:
    # The mid-p set is (.., 0.1311] and [0.18, 0.1859]: the hull ends at 0.1859,
    # not at the first crossing that a root search from the estimate would find.
    result = baptista_pike_odds_ratio(1, 13, 9, 1, mid_p=True)
    assert math.isclose(result.ci_high, 0.1858962763, rel_tol=1e-6)


def test_cornfield_matches_the_central_exact_interval() -> None:
    # scipy.stats.contingency.odds_ratio(kind="conditional"), 50-digit verified.
    result = cornfield_exact_odds_ratio(1, 13, 9, 1)
    assert math.isclose(result.ci_low, 0.00018217752702010258, rel_tol=1e-8)
    assert math.isclose(result.ci_high, 0.2051650955120704, rel_tol=1e-8)


@pytest.mark.parametrize(
    ("func", "solver"),
    [
        (cornfield_exact_odds_ratio, "_solve_log_root"),
        (baptista_pike_odds_ratio, "_bp_end"),
    ],
)
def test_odds_ratio_fallback_is_labelled(monkeypatch, func, solver) -> None:
    monkeypatch.setattr(stats, solver, lambda *args, **kwargs: math.inf)
    result = func(20, 80, 10, 90)
    fallback = haldane_anscombe_odds_ratio(20, 80, 10, 90)
    assert result.ci_method == "haldane-anscombe"
    assert (result.ci_low, result.ci_high) == (fallback.ci_low, fallback.ci_high)
    assert result.value == pytest.approx(20 * 90 / (80 * 10))


def test_primary_methods_never_fall_back_on_small_tables() -> None:
    fallbacks = []
    for a, b, c, d in itertools.product(range(8), repeat=4):
        if a == 0 or c == 0:
            continue
        labels = (
            koopman_risk_ratio(a, b, c, d).ci_method,
            baptista_pike_odds_ratio(a, b, c, d).ci_method,
            baptista_pike_odds_ratio(a, b, c, d, mid_p=True).ci_method,
            cornfield_exact_odds_ratio(a, b, c, d).ci_method,
        )
        if labels != ("koopman", "baptista-pike", "baptista-pike-midp", "cornfield"):
            fallbacks.append(((a, b, c, d), labels))
    assert fallbacks == []


def test_solve_log_root_branches() -> None:
    assert stats._solve_log_root(lambda u: u, 2.0, 0.0, increasing=True) == pytest.approx(2.0, abs=1e-12)
    assert stats._solve_log_root(lambda u: u, -3.0, 0.0, increasing=True) == pytest.approx(-3.0, abs=1e-12)
    assert stats._solve_log_root(lambda u: -u, 3.0, 0.0, increasing=False) == pytest.approx(-3.0, abs=1e-12)
    assert stats._solve_log_root(lambda u: u, 500.0, 0.0, increasing=True) == math.inf
    assert stats._solve_log_root(lambda u: u, -500.0, 0.0, increasing=True) == -math.inf
    # A start beyond the search bound is clamped to it.
    assert stats._solve_log_root(lambda u: u, 1.0, 1e6, increasing=True) == pytest.approx(1.0, abs=1e-12)


def test_internal_helpers_and_branches() -> None:
    root = stats._bisect_root(lambda x: x - 2.0, 0.0, 4.0)
    assert abs(root - 2.0) < 1e-10
    with pytest.raises(ValueError, match="root is not bracketed"):
        stats._bisect_root(lambda x: x + 2.0, 0.0, 4.0)

    assert stats._rr_point_estimate(10, 90, 0, 100) == float("inf")
    assert stats._odds_ratio_value(0, 1, 1, 0) == 0.0
    assert math.isinf(stats._odds_ratio_value(1, 0, 0, 1))
    assert stats._two_sided_alpha(Z_95) == pytest.approx(0.05, abs=1e-15)

    lo, hi, log_weights = stats._conditional_log_weights(2, 3, 4, 5)
    assert (lo, hi, len(log_weights)) == (0, 5, 6)
    probs = stats._conditional_probabilities(log_weights, 0.0)
    assert math.fsum(probs) == pytest.approx(1.0, abs=1e-15)


def test_bisect_root_endpoint_and_max_iter_paths() -> None:
    assert stats._bisect_root(lambda x: x, 0.0, 2.0) == 0.0
    assert stats._bisect_root(lambda x: x - 2.0, 0.0, 2.0) == 2.0
    approx = stats._bisect_root(lambda x: x - 1.0, 0.0, 2.0, max_iter=0)
    assert 0.9 <= approx <= 1.1


def test_private_odds_ratio_zero_numerator_zero_denominator() -> None:
    assert math.isinf(stats._odds_ratio_value(0, 0, 1, 1))


def test_miettinen_nurminen_risk_difference_reference_window() -> None:
    # Published worked examples report this table as a small positive RD;
    # we assert expected sign and stable CI ordering in a narrow range.
    result = miettinen_nurminen_risk_difference(7, 43, 1, 49)
    assert 0.09 <= result.value <= 0.15
    assert result.ci_low is not None and result.ci_high is not None
    assert result.ci_low < result.value < result.ci_high
    assert -0.05 <= result.ci_low <= 0.05
    assert 0.20 <= result.ci_high <= 0.35


def test_agresti_caffo_risk_difference_matches_closed_form() -> None:
    result = agresti_caffo_risk_difference(7, 43, 1, 49, z=1.96)
    assert math.isclose(result.value, 0.12, rel_tol=0.0, abs_tol=1e-12)
    assert result.ci_low is not None and result.ci_high is not None
    assert math.isclose(result.ci_low, 0.008872825214188973, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.ci_high, 0.23112717478581105, rel_tol=0.0, abs_tol=1e-12)


def test_risk_difference_guardrail_falls_back_on_degenerate_primary(monkeypatch) -> None:
    monkeypatch.setattr(
        stats,
        "miettinen_nurminen_risk_difference",
        lambda *_args, **_kwargs: stats.RiskDifferenceResult(value=0.1, ci_low=None, ci_high=None),
    )
    result = risk_difference_with_guardrail(10, 90, 1, 99)
    assert result.ci_low is not None and result.ci_high is not None


@pytest.mark.parametrize("bad_z", [0.0, -1.0, float("inf"), float("nan")])
def test_ci_methods_reject_non_positive_or_non_finite_z(bad_z: float) -> None:
    with pytest.raises(ValueError, match="finite positive"):
        katz_risk_ratio(20, 80, 10, 90, z=bad_z)
    with pytest.raises(ValueError, match="finite positive"):
        haldane_anscombe_odds_ratio(20, 80, 10, 90, z=bad_z)
    with pytest.raises(ValueError, match="finite positive"):
        koopman_risk_ratio(20, 80, 10, 90, z=bad_z)
    with pytest.raises(ValueError, match="finite positive"):
        baptista_pike_odds_ratio(20, 80, 10, 90, z=bad_z)
    with pytest.raises(ValueError, match="finite positive"):
        baptista_pike_odds_ratio(20, 80, 10, 90, z=bad_z, mid_p=True)
    with pytest.raises(ValueError, match="finite positive"):
        cornfield_exact_odds_ratio(20, 80, 10, 90, z=bad_z)
