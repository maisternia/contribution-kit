from __future__ import annotations

import math

import pytest

from contribution.hypothesis import (
    OR_INTERVALS,
    BinaryHypothesisTest,
    _raw_odds_ratio,
    _raw_risk_ratio,
    evaluate_binary_hypotheses,
    evaluate_binary_hypothesis,
    validate_ci_options,
)


def test_raw_ratio_helpers() -> None:
    assert _raw_risk_ratio(10, 90, 5, 95) > 1.0
    assert math.isinf(_raw_risk_ratio(1, 9, 0, 10))
    assert _raw_odds_ratio(1, 0, 1, 0) == float("inf")
    assert _raw_odds_ratio(0, 1, 1, 0) == 0.0


def test_evaluate_binary_hypothesis_ci_methods_and_error() -> None:
    group_a_rows = [{"mismatch": i == 0} for i in range(14)]
    group_b_rows = [{"mismatch": i < 9} for i in range(10)]

    score_exact = evaluate_binary_hypothesis(
        scope="s",
        test_name="t",
        group_a_label="A",
        group_b_label="B",
        group_a_rows=group_a_rows,
        group_b_rows=group_b_rows,
        mismatch_fn=lambda row: bool(row["mismatch"]),
        ci_method="score-exact",
    )
    wald = evaluate_binary_hypothesis(
        scope="s",
        test_name="t",
        group_a_label="A",
        group_b_label="B",
        group_a_rows=group_a_rows,
        group_b_rows=group_b_rows,
        mismatch_fn=lambda row: bool(row["mismatch"]),
        ci_method="wald",
    )

    assert score_exact.scope == "s"
    assert score_exact.test_name == "t"
    assert score_exact.risk_ratio == wald.risk_ratio
    assert score_exact.odds_ratio > 0.0
    assert wald.odds_ratio > 0.0

    with pytest.raises(ValueError, match="ci_method"):
        evaluate_binary_hypothesis(
            scope="s",
            test_name="t",
            group_a_label="A",
            group_b_label="B",
            group_a_rows=group_a_rows,
            group_b_rows=group_b_rows,
            mismatch_fn=lambda row: bool(row["mismatch"]),
            ci_method="nope",
        )


def test_raw_odds_ratio_negative_numerator_path() -> None:
    # Private helper branch coverage: denominator == 0 and numerator < 0.
    assert _raw_odds_ratio(-1, 1, 0, 1) == 0.0


def test_evaluate_binary_hypotheses_skips_empty_group() -> None:
    rows = [{"group": "A", "mismatch": True}, {"group": "A", "mismatch": False}]
    tests = [
        BinaryHypothesisTest(
            name="empty",
            group_a_label="A",
            group_b_label="B",
            group_a_predicate=lambda row: row["group"] == "A",
            group_b_predicate=lambda row: row["group"] == "B",
        )
    ]
    assert evaluate_binary_hypotheses(
        scope="x",
        rows=rows,
        tests=tests,
        mismatch_fn=lambda row: bool(row["mismatch"]),
    ) == []


def test_evaluate_binary_hypotheses_appends_non_empty() -> None:
    rows = [{"g": "A", "m": True}, {"g": "B", "m": False}]
    tests = [
        BinaryHypothesisTest(
            name="non-empty",
            group_a_label="A",
            group_b_label="B",
            group_a_predicate=lambda row: row["g"] == "A",
            group_b_predicate=lambda row: row["g"] == "B",
        )
    ]
    out = evaluate_binary_hypotheses(
        scope="s",
        rows=rows,
        tests=tests,
        mismatch_fn=lambda row: bool(row["m"]),
    )
    assert len(out) == 1


def test_evaluate_binary_hypotheses_with_multiple_tests() -> None:
    rows = [{"g": "A", "m": True}, {"g": "B", "m": False}, {"g": "A", "m": False}]
    tests = [
        BinaryHypothesisTest(
            name="a-vs-b",
            group_a_label="A",
            group_b_label="B",
            group_a_predicate=lambda row: row["g"] == "A",
            group_b_predicate=lambda row: row["g"] == "B",
        )
    ]
    results = evaluate_binary_hypotheses(
        scope="global",
        rows=rows,
        tests=tests,
        mismatch_fn=lambda row: bool(row["m"]),
        ci_method="wald",
    )
    assert [item.test_name for item in results] == ["a-vs-b"]


def _evaluate_table(a: int, b: int, c: int, d: int, **options):
    group_a_rows = [{"mismatch": index < a} for index in range(a + b)]
    group_b_rows = [{"mismatch": index < c} for index in range(c + d)]
    return evaluate_binary_hypothesis(
        scope="s",
        test_name="t",
        group_a_label="A",
        group_b_label="B",
        group_a_rows=group_a_rows,
        group_b_rows=group_b_rows,
        mismatch_fn=lambda row: bool(row["mismatch"]),
        **options,
    )


@pytest.mark.parametrize("table", [(1, 13, 9, 1), (91, 385, 0, 11972), (0, 100, 10, 90)])
def test_point_estimates_do_not_depend_on_ci_choice(table) -> None:
    results = [_evaluate_table(*table, ci_method="score-exact", or_interval=name) for name in OR_INTERVALS]
    results.append(_evaluate_table(*table, ci_method="wald"))
    assert len({result.risk_ratio for result in results}) == 1
    assert len({result.odds_ratio for result in results}) == 1


def test_wald_reports_the_raw_odds_ratio_not_the_corrected_one() -> None:
    wald = _evaluate_table(91, 385, 0, 11972, ci_method="wald")
    assert math.isinf(wald.odds_ratio)
    assert wald.or_ci_method == "haldane-anscombe"
    assert math.isfinite(wald.or_ci_low) and math.isfinite(wald.or_ci_high)


@pytest.mark.parametrize(
    ("options", "rr_label", "or_label"),
    [
        ({}, "koopman", "baptista-pike"),
        ({"or_interval": "baptista-pike-midp"}, "koopman", "baptista-pike-midp"),
        ({"or_interval": "cornfield"}, "koopman", "cornfield"),
        ({"ci_method": "wald"}, "katz", "haldane-anscombe"),
    ],
)
def test_results_record_the_ci_methods(options, rr_label, or_label) -> None:
    result = _evaluate_table(12, 30, 4, 40, **options)
    assert result.rr_ci_method == rr_label
    assert result.or_ci_method == or_label


def test_blanked_risk_ratio_interval_has_no_method() -> None:
    result = _evaluate_table(0, 100, 10, 90)
    assert result.rr_ci_low is None and result.rr_ci_high is None
    assert result.rr_ci_method is None
    assert result.or_ci_method == "baptista-pike"


def test_validate_ci_options() -> None:
    validate_ci_options("score-exact", "cornfield")
    with pytest.raises(ValueError, match="ci_method"):
        validate_ci_options("nope", "baptista-pike")
    with pytest.raises(ValueError, match="or_interval must be one of"):
        validate_ci_options("score-exact", "nope")
    with pytest.raises(ValueError, match="or_interval='cornfield'.*ci_method='wald'"):
        validate_ci_options("wald", "cornfield")
    with pytest.raises(ValueError, match="ci_method='wald'"):
        _evaluate_table(1, 13, 9, 1, ci_method="wald", or_interval="baptista-pike-midp")


def test_evaluate_binary_hypotheses_passes_the_or_interval() -> None:
    rows = [{"g": "A", "m": index < 5} for index in range(12)] + [{"g": "B", "m": index < 2} for index in range(20)]
    tests = [
        BinaryHypothesisTest(
            name="a-vs-b",
            group_a_label="A",
            group_b_label="B",
            group_a_predicate=lambda row: row["g"] == "A",
            group_b_predicate=lambda row: row["g"] == "B",
        )
    ]
    results = evaluate_binary_hypotheses(
        scope="global",
        rows=rows,
        tests=tests,
        mismatch_fn=lambda row: bool(row["m"]),
        or_interval="cornfield",
    )
    assert results[0].or_ci_method == "cornfield"


def test_guardrail_fallback_applies_only_to_the_failed_interval(monkeypatch) -> None:
    # A broken Koopman statistic makes the score inversion fail for a finite
    # estimate; Katz stands in for that interval only, and the chosen
    # odds-ratio interval keeps its own label.
    import contribution.stats as stats

    monkeypatch.setattr(stats, "_koopman_score", lambda *args: 0.0)
    katz = stats.katz_risk_ratio(20, 80, 10, 90)
    for name in OR_INTERVALS:
        result = _evaluate_table(20, 80, 10, 90, or_interval=name)
        assert result.rr_ci_method == "katz"
        assert (result.rr_ci_low, result.rr_ci_high) == (katz.ci_low, katz.ci_high)
        assert result.or_ci_method == name
