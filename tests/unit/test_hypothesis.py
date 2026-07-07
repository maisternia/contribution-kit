from __future__ import annotations

import math

import pytest

from contribution.hypothesis import (
    BinaryHypothesisTest,
    _raw_odds_ratio,
    _raw_risk_ratio,
    evaluate_binary_hypotheses,
    evaluate_binary_hypothesis,
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
