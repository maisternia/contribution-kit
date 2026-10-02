"""Compare the kit's risk-ratio and odds-ratio intervals with independent baselines.

The baselines and their provenance live in tests/reference/ (see its README);
nothing here needs R or network access.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from contribution.hypothesis import (
    BinaryHypothesisTest,
    evaluate_binary_hypotheses,
    evaluate_binary_hypothesis,
)
from contribution.stats import (
    baptista_pike_odds_ratio,
    cornfield_exact_odds_ratio,
    haldane_anscombe_odds_ratio,
    katz_risk_ratio,
    koopman_risk_ratio,
)

BASELINES = json.loads((Path(__file__).parents[1] / "reference" / "effect_size_baselines.json").read_text())
CASES = BASELINES["cases"]
OR_KEYS = ("baptista_pike", "baptista_pike_midp", "cornfield")

# Tolerance rationale: point estimates are closed-form ratios, so only rounding differs.
VALUE_REL_TOL = 1e-12
# Tolerance rationale: Koopman bounds are roots of the same score equation that
# riskscoreci solves in closed form; 1e-7 allows for the kit's root-finding.
KOOPMAN_REL_TOL = 1e-7
# Tolerance rationale: when a group has every row mismatched, riskscoreci walks
# its iterative branch in steps of 1.0001, so R itself is only good to ~1e-4.
KOOPMAN_ITERATIVE_REL_TOL = 1e-3
# Tolerance rationale: Katz and Haldane-Anscombe are closed forms in both tools.
CLOSED_FORM_REL_TOL = 1e-10
# Tolerance rationale: the reference ends are exact to ~45 digits; 1e-8 is the
# kit's root-finding budget on log(theta).
EXACT_OR_REL_TOL = 1e-8


def _number(value):
    if value is None:
        return None
    if isinstance(value, str):
        return math.inf if value == "inf" else -math.inf
    return float(value)


def _case_id(case: dict) -> str:
    return f"{case['set']}-{case['a']},{case['b']},{case['c']},{case['d']}"


def _assert_value(actual: float, expected, rel_tol: float) -> None:
    expected = _number(expected)
    if expected is None:
        # Undefined estimate (0/0): only the structure is fixed.
        assert not math.isfinite(actual)
        return
    if math.isinf(expected) or expected == 0.0:
        assert actual == expected
        return
    assert math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=0.0), (actual, expected)


def _assert_bound(actual: float | None, expected, rel_tol: float) -> None:
    expected = _number(expected)
    if expected is None:
        assert actual is None
        return
    assert actual is not None
    if math.isinf(expected) or expected == 0.0:
        assert actual == expected
        return
    assert math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=0.0), (actual, expected)


def _riskscoreci_iterates(a: int, b: int, c: int, d: int) -> bool:
    # Mirrors the branch order of PropCIs::riskscoreci (x1 = a, x2 = c).
    n1, n2 = a + b, c + d
    if c == 0 and a != 0:
        return False
    if c != n2 and a == 0:
        return False
    if c == n2 and a == n1:
        return False
    return a == n1 or c == n2


def test_baselines_carry_provenance() -> None:
    provenance = BASELINES.get("provenance")
    assert provenance, "effect_size_baselines.json has no provenance block"
    for key in ("generators", "generated_at", "conf_level", "r", "python", "high_precision_or"):
        assert key in provenance, f"provenance is missing {key!r}"
    assert provenance["conf_level"] == 0.95
    assert provenance["r"]["versions"]
    for case in CASES:
        for method in ("koopman", "katz", "haldane_anscombe", *OR_KEYS):
            assert case[method].get("authority"), f"{_case_id(case)} {method} has no authority"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_koopman_matches_riskscoreci(case: dict) -> None:
    a, b, c, d = case["a"], case["b"], case["c"], case["d"]
    expected = case["koopman"]
    actual = koopman_risk_ratio(a, b, c, d)
    rel_tol = KOOPMAN_ITERATIVE_REL_TOL if _riskscoreci_iterates(a, b, c, d) else KOOPMAN_REL_TOL
    _assert_value(actual.value, expected["value"], VALUE_REL_TOL)
    _assert_bound(actual.ci_low, expected["ci_low"], rel_tol)
    _assert_bound(actual.ci_high, expected["ci_high"], rel_tol)
    assert actual.ci_method == "koopman"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_katz_matches_epitools(case: dict) -> None:
    expected = case["katz"]
    actual = katz_risk_ratio(case["a"], case["b"], case["c"], case["d"])
    _assert_value(actual.value, expected["value"], VALUE_REL_TOL)
    _assert_bound(actual.ci_low, expected["ci_low"], CLOSED_FORM_REL_TOL)
    _assert_bound(actual.ci_high, expected["ci_high"], CLOSED_FORM_REL_TOL)


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_haldane_anscombe_matches_desctools(case: dict) -> None:
    expected = case["haldane_anscombe"]
    actual = haldane_anscombe_odds_ratio(case["a"], case["b"], case["c"], case["d"])
    _assert_value(actual.value, expected["value"], VALUE_REL_TOL)
    _assert_bound(actual.ci_low, expected["ci_low"], CLOSED_FORM_REL_TOL)
    _assert_bound(actual.ci_high, expected["ci_high"], CLOSED_FORM_REL_TOL)


def _or_interval(key: str, a: int, b: int, c: int, d: int):
    if key == "baptista_pike":
        return baptista_pike_odds_ratio(a, b, c, d)
    if key == "baptista_pike_midp":
        return baptista_pike_odds_ratio(a, b, c, d, mid_p=True)
    return cornfield_exact_odds_ratio(a, b, c, d)


@pytest.mark.parametrize("key", OR_KEYS)
@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_exact_odds_ratio_matches_high_precision_reference(case: dict, key: str) -> None:
    expected = case[key]
    actual = _or_interval(key, case["a"], case["b"], case["c"], case["d"])
    _assert_value(actual.value, expected["value"], VALUE_REL_TOL)
    _assert_bound(actual.ci_low, expected["ci_low"], EXACT_OR_REL_TOL)
    _assert_bound(actual.ci_high, expected["ci_high"], EXACT_OR_REL_TOL)
    assert actual.ci_method == key.replace("_", "-")


@pytest.mark.parametrize("key", OR_KEYS)
@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_high_precision_reference_agrees_with_its_cross_check(case: dict, key: str) -> None:
    check = case[key]["cross_check"]
    if check is None:
        pytest.skip("no cross-check implementation returned a value for this case")
    if "skipped" in check:
        pytest.skip(check["skipped"])
    assert _number(check["max_rel_diff"]) <= check["tolerance"], check


SWEEP_CASES = [case for case in CASES if case["set"] == "sweep"]


@pytest.mark.parametrize("case", SWEEP_CASES, ids=_case_id)
def test_baptista_pike_matches_exact2x2_minlike_on_the_sweep(case: dict) -> None:
    # Direct check against an unrelated implementation, at exact2x2's ~10-digit
    # precision, independent of the high-precision reference.
    check = case["baptista_pike"]["cross_check"]
    actual = baptista_pike_odds_ratio(case["a"], case["b"], case["c"], case["d"])
    _assert_bound(actual.ci_low, check["ci_low"], 1e-3)
    _assert_bound(actual.ci_high, check["ci_high"], 1e-3)


def _evaluate_case(case: dict, **options):
    a, b, c, d = case["a"], case["b"], case["c"], case["d"]
    return evaluate_binary_hypothesis(
        scope="accuracy",
        test_name=_case_id(case),
        group_a_label="A",
        group_b_label="B",
        group_a_rows=[{"m": index < a} for index in range(a + b)],
        group_b_rows=[{"m": index < c} for index in range(c + d)],
        mismatch_fn=lambda row: row["m"],
        **options,
    )


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_score_exact_path_reports_the_koopman_and_baptista_pike_baselines(case: dict) -> None:
    a, b, c, d = case["a"], case["b"], case["c"], case["d"]
    result = _evaluate_case(case)
    if a == 0:
        # Legacy convention: no mismatches in group A blank the RR interval.
        assert (result.rr_ci_low, result.rr_ci_high, result.rr_ci_method) == (None, None, None)
    else:
        rel_tol = KOOPMAN_ITERATIVE_REL_TOL if _riskscoreci_iterates(a, b, c, d) else KOOPMAN_REL_TOL
        _assert_bound(result.rr_ci_low, case["koopman"]["ci_low"], rel_tol)
        _assert_bound(result.rr_ci_high, case["koopman"]["ci_high"], rel_tol)
        assert result.rr_ci_method == "koopman"
    _assert_bound(result.or_ci_low, case["baptista_pike"]["ci_low"], EXACT_OR_REL_TOL)
    _assert_bound(result.or_ci_high, case["baptista_pike"]["ci_high"], EXACT_OR_REL_TOL)
    assert result.or_ci_method == "baptista-pike"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_wald_path_reports_the_katz_and_haldane_anscombe_baselines(case: dict) -> None:
    result = _evaluate_case(case, ci_method="wald")
    if case["a"] == 0:
        assert (result.rr_ci_low, result.rr_ci_high, result.rr_ci_method) == (None, None, None)
    else:
        _assert_bound(result.rr_ci_low, case["katz"]["ci_low"], CLOSED_FORM_REL_TOL)
        _assert_bound(result.rr_ci_high, case["katz"]["ci_high"], CLOSED_FORM_REL_TOL)
        assert result.rr_ci_method == "katz"
    _assert_bound(result.or_ci_low, case["haldane_anscombe"]["ci_low"], CLOSED_FORM_REL_TOL)
    _assert_bound(result.or_ci_high, case["haldane_anscombe"]["ci_high"], CLOSED_FORM_REL_TOL)
    assert result.or_ci_method == "haldane-anscombe"


@pytest.mark.parametrize("ci_method", ["score-exact", "wald"])
def test_single_group_regime_has_no_mismatch_risk(ci_method: str) -> None:
    # Every row matches group A, so there is no "rest" to compare against and
    # the mismatch risk is undefined rather than reported.
    rows = [{"g": "A", "m": index < 3} for index in range(10)]
    tests = [
        BinaryHypothesisTest(
            name="only-a",
            group_a_label="A",
            group_b_label="B",
            group_a_predicate=lambda row: row["g"] == "A",
            group_b_predicate=lambda row: row["g"] == "B",
        )
    ]
    results = evaluate_binary_hypotheses(
        scope="accuracy", rows=rows, tests=tests, mismatch_fn=lambda row: row["m"], ci_method=ci_method
    )
    assert results == []
