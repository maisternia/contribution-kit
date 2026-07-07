"""Tests for contributor ranking helpers."""

from __future__ import annotations

from contribution import combine_contributors, rank_contributors


def test_rank_contributors_orders_by_score() -> None:
    rows = [
        {"bucket": "A", "mismatch": True},
        {"bucket": "A", "mismatch": True},
        {"bucket": "A", "mismatch": False},
        {"bucket": "B", "mismatch": True},
        {"bucket": "B", "mismatch": False},
        {"bucket": "B", "mismatch": False},
    ]
    ranked = rank_contributors(
        rows,
        feature="bucket",
        value_fn=lambda row: row["bucket"],
        mismatch_fn=lambda row: bool(row["mismatch"]),
        min_count=1,
    )
    assert [row.value for row in ranked] == ["A", "B"]
    assert ranked[0].score > ranked[1].score


def test_combine_contributors_merges_and_sorts() -> None:
    rows = [{"bucket": "A", "mismatch": True}, {"bucket": "A", "mismatch": False}]
    group_1 = rank_contributors(
        rows,
        feature="f1",
        value_fn=lambda row: row["bucket"],
        mismatch_fn=lambda row: bool(row["mismatch"]),
        min_count=1,
    )
    group_2 = rank_contributors(
        rows,
        feature="f2",
        value_fn=lambda row: row["bucket"],
        mismatch_fn=lambda row: bool(row["mismatch"]),
        min_count=1,
    )
    merged = combine_contributors([group_1, group_2])
    assert len(merged) == 2
    assert merged[0].score >= merged[1].score