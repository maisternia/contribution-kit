from contribution.contributor import combine_contributors, rank_contributors


def test_rank_contributors_orders_and_filters() -> None:
    rows = [
        {"bucket": "A", "mismatch": True},
        {"bucket": "A", "mismatch": True},
        {"bucket": "A", "mismatch": False},
        {"bucket": "B", "mismatch": False},
        {"bucket": "B", "mismatch": False},
        {"bucket": "C", "mismatch": True},
    ]
    ranked = rank_contributors(
        rows,
        feature="bucket",
        value_fn=lambda row: row["bucket"],
        mismatch_fn=lambda row: bool(row["mismatch"]),
        min_count=2,
    )
    assert [item.value for item in ranked] == ["A", "B"]
    assert ranked[0].score >= ranked[1].score


def test_rank_contributors_zero_global_mismatch_rate_branch() -> None:
    rows = [{"bucket": "A", "mismatch": False}, {"bucket": "A", "mismatch": False}]
    ranked = rank_contributors(
        rows,
        feature="bucket",
        value_fn=lambda row: row["bucket"],
        mismatch_fn=lambda row: bool(row["mismatch"]),
        min_count=1,
    )
    assert ranked[0].lift == 0.0
    assert ranked[0].mismatch_share == 0.0


def test_combine_contributors_merges_and_sorts() -> None:
    rows = [{"bucket": "A", "mismatch": True}, {"bucket": "A", "mismatch": False}]
    group_a = rank_contributors(
        rows,
        feature="x",
        value_fn=lambda row: row["bucket"],
        mismatch_fn=lambda row: bool(row["mismatch"]),
        min_count=1,
    )
    group_b = rank_contributors(
        rows,
        feature="y",
        value_fn=lambda row: row["bucket"],
        mismatch_fn=lambda row: bool(row["mismatch"]),
        min_count=1,
    )
    merged = combine_contributors([group_b, group_a])
    assert len(merged) == 2
    assert merged[0].score >= merged[1].score
