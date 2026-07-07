"""Tests for binary hypothesis test helpers."""

from __future__ import annotations

import math

from contribution import BinaryHypothesisTest, evaluate_binary_hypotheses, evaluate_binary_hypothesis


def test_evaluate_binary_hypothesis_basic_rates() -> None:
    group_a_rows = [{"mismatch": i < 30} for i in range(100)]
    group_b_rows = [{"mismatch": i < 15} for i in range(100)]

    result = evaluate_binary_hypothesis(
        scope="global",
        test_name="test",
        group_a_label="A",
        group_b_label="B",
        group_a_rows=group_a_rows,
        group_b_rows=group_b_rows,
        mismatch_fn=lambda row: bool(row["mismatch"]),
    )

    assert math.isclose(result.mismatch_rate_a_pct, 30.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(result.mismatch_rate_b_pct, 15.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(result.risk_ratio, 2.0, rel_tol=0, abs_tol=1e-9)
    assert result.rr_ci_low is not None
    assert result.rr_ci_high is not None


def test_evaluate_binary_hypotheses_skips_empty_groups() -> None:
    rows = [{"mismatch": True, "group": "A"}, {"mismatch": False, "group": "A"}]
    tests = [
        BinaryHypothesisTest(
            name="empty_b",
            group_a_label="A",
            group_b_label="B",
            group_a_predicate=lambda row: row["group"] == "A",
            group_b_predicate=lambda row: row["group"] == "B",
        )
    ]
    results = evaluate_binary_hypotheses(
        scope="global",
        rows=rows,
        tests=tests,
        mismatch_fn=lambda row: bool(row["mismatch"]),
    )
    assert results == []