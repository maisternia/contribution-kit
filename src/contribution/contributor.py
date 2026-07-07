"""Contributor ranking helpers for categorical buckets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence


@dataclass(slots=True)
class ContributorRow:
    feature: str
    value: str
    count: int
    mismatches: int
    mismatch_rate: float
    lift: float
    mismatch_share: float
    score: float


def rank_contributors(
    rows: Sequence[dict[str, Any]],
    *,
    feature: str,
    value_fn: Callable[[dict[str, Any]], str],
    mismatch_fn: Callable[[dict[str, Any]], bool],
    min_count: int = 20,
) -> list[ContributorRow]:
    bucket_counts: dict[str, int] = {}
    bucket_mismatches: dict[str, int] = {}

    total_mismatches = 0
    for row in rows:
        key = str(value_fn(row))
        bucket_counts[key] = bucket_counts.get(key, 0) + 1
        if mismatch_fn(row):
            bucket_mismatches[key] = bucket_mismatches.get(key, 0) + 1
            total_mismatches += 1

    total_rows = len(rows)
    global_mismatch_rate = (total_mismatches / total_rows) if total_rows > 0 else 0.0

    ranked: list[ContributorRow] = []
    for key, count in bucket_counts.items():
        if count < min_count:
            continue
        mismatches = bucket_mismatches.get(key, 0)
        mismatch_rate = mismatches / count if count > 0 else 0.0
        lift = (mismatch_rate / global_mismatch_rate) if global_mismatch_rate > 0 else 0.0
        mismatch_share = (mismatches / total_mismatches) if total_mismatches > 0 else 0.0
        score = lift * mismatch_share

        ranked.append(
            ContributorRow(
                feature=feature,
                value=key,
                count=count,
                mismatches=mismatches,
                mismatch_rate=mismatch_rate,
                lift=lift,
                mismatch_share=mismatch_share,
                score=score,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def combine_contributors(groups: Iterable[list[ContributorRow]]) -> list[ContributorRow]:
    merged: list[ContributorRow] = []
    for group in groups:
        merged.extend(group)
    merged.sort(key=lambda item: item.score, reverse=True)
    return merged