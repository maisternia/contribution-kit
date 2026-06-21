"""Binary mismatch hypothesis testing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from .stats import haldane_anscombe_odds_ratio, katz_risk_ratio


@dataclass(slots=True)
class BinaryHypothesisTest:
    name: str
    group_a_label: str
    group_b_label: str
    group_a_predicate: Callable[[dict[str, Any]], bool]
    group_b_predicate: Callable[[dict[str, Any]], bool]


@dataclass(slots=True)
class BinaryHypothesisResult:
    scope: str
    test_name: str
    group_a: str
    group_b: str
    mismatch_rate_a_pct: float
    mismatch_rate_b_pct: float
    mismatch_count_a: int
    total_count_a: int
    mismatch_count_b: int
    total_count_b: int
    risk_ratio: float
    rr_ci_low: float | None
    rr_ci_high: float | None
    odds_ratio: float
    or_ci_low: float
    or_ci_high: float


def evaluate_binary_hypothesis(
    *,
    scope: str,
    test_name: str,
    group_a_label: str,
    group_b_label: str,
    group_a_rows: Sequence[dict[str, Any]],
    group_b_rows: Sequence[dict[str, Any]],
    mismatch_fn: Callable[[dict[str, Any]], bool],
) -> BinaryHypothesisResult:
    a = sum(1 for row in group_a_rows if mismatch_fn(row))
    b = len(group_a_rows) - a
    c = sum(1 for row in group_b_rows if mismatch_fn(row))
    d = len(group_b_rows) - c

    rr = katz_risk_ratio(a, b, c, d)
    odds = haldane_anscombe_odds_ratio(a, b, c, d)

    rate_a = (a / len(group_a_rows) * 100.0) if group_a_rows else 0.0
    rate_b = (c / len(group_b_rows) * 100.0) if group_b_rows else 0.0

    return BinaryHypothesisResult(
        scope=scope,
        test_name=test_name,
        group_a=group_a_label,
        group_b=group_b_label,
        mismatch_rate_a_pct=rate_a,
        mismatch_rate_b_pct=rate_b,
        mismatch_count_a=a,
        total_count_a=len(group_a_rows),
        mismatch_count_b=c,
        total_count_b=len(group_b_rows),
        risk_ratio=rr.value,
        rr_ci_low=rr.ci_low,
        rr_ci_high=rr.ci_high,
        odds_ratio=odds.value,
        or_ci_low=odds.ci_low,
        or_ci_high=odds.ci_high,
    )


def evaluate_binary_hypotheses(
    *,
    scope: str,
    rows: Sequence[dict[str, Any]],
    tests: Iterable[BinaryHypothesisTest],
    mismatch_fn: Callable[[dict[str, Any]], bool],
) -> list[BinaryHypothesisResult]:
    results: list[BinaryHypothesisResult] = []
    for test in tests:
        group_a_rows = [row for row in rows if test.group_a_predicate(row)]
        group_b_rows = [row for row in rows if test.group_b_predicate(row)]
        if not group_a_rows or not group_b_rows:
            continue
        results.append(
            evaluate_binary_hypothesis(
                scope=scope,
                test_name=test.name,
                group_a_label=test.group_a_label,
                group_b_label=test.group_b_label,
                group_a_rows=group_a_rows,
                group_b_rows=group_b_rows,
                mismatch_fn=mismatch_fn,
            )
        )
    return results