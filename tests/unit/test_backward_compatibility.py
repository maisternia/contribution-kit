"""Pins the bundled example's attributions against pre-change snapshots.

Two capabilities are pinned here, both additive:

- Dependent baselines: a spec whose baselines reference no sibling feature
  must resolve exactly as it did before dependency-ordered resolution.
- Feature grouping: a spec declaring no groups must have one player per
  feature and resolve exactly as it did before grouping existed.

Each golden file was captured from the bundled config before the
corresponding code changed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contribution import Estimator
from contribution import cli

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden_continuous_lora_pre_dependent_baselines.json"
GOLDEN_DEPENDENT = ROOT / "tests" / "fixtures" / "golden_continuous_lora_dependent_baseline.json"
# A frozen copy of the bundled config as it stood before feature grouping:
# a dependent baseline, but one player per feature. The live example has since
# grouped the class decision.
UNGROUPED_DEPENDENT_CONFIG = ROOT / "tests" / "fixtures" / "continuous_lora_ungrouped_dependent_config.json"
# A frozen copy of the bundled config as it stood before dependent baselines;
# the live example has since migrated to one, so it is no longer sibling-free.
CONFIG = ROOT / "tests" / "fixtures" / "continuous_lora_sibling_free_config.json"
MEASUREMENTS = ROOT / "examples" / "continuous_lora" / "measurements.csv"


@pytest.fixture(scope="module")
def assessed():
    spec = cli._load_spec(CONFIG)
    return Estimator.from_csv(MEASUREMENTS, spec).assess()


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_feature_attributions_match_the_pre_change_snapshot(assessed, golden) -> None:
    actual = {
        item.name: {
            "mean_abs_shapley": item.feature.mean_abs_shapley,
            "mean_signed_shapley": item.feature.mean_signed_shapley,
            "total_signed_shapley": item.feature.total_signed_shapley,
            "net_contribution_share_pct": item.feature.net_contribution_share_pct,
        }
        for item in assessed.regimes
        if item.analysis == "feature"
    }
    assert actual == golden["features"]


def test_row_count_and_observed_contribution_match(assessed, golden) -> None:
    assert assessed.n_rows == golden["n_rows"]
    assert assessed.mean_observed_contribution == golden["mean_observed_contribution"]


def test_burden_ranking_matches(assessed, golden) -> None:
    actual = [
        {
            "crossing": ranking.crossing_label,
            "baseline_cell": ranking.baseline_cell,
            "observed_accuracy_pct": ranking.observed_accuracy_pct,
            "ceiling_accuracy_pct": ranking.ceiling_accuracy_pct,
            "total_mismatches": ranking.total_mismatches,
            "entries": [
                {
                    "rank": entry.rank,
                    "cell": entry.cell,
                    "count": entry.count,
                    "mismatch_count": entry.mismatch_count,
                    "mismatch_rate_pct": entry.mismatch_rate_pct,
                    "recoverable_mismatches": entry.recoverable_mismatches,
                    "cumulative_accuracy_if_eliminated_pct": entry.cumulative_accuracy_if_eliminated_pct,
                }
                for entry in ranking.entries
            ],
        }
        for ranking in assessed.burden_rankings
    ]
    assert actual == golden["burden"]


def test_regime_summaries_match(assessed, golden) -> None:
    actual = {
        item.name: {
            "count": item.regime.count,
            "total_contribution": item.regime.total_contribution,
            "contribution_share_pct": item.regime.contribution_share_pct,
        }
        for item in assessed.regimes
        if item.analysis == "regime" and item.regime is not None
    }
    assert actual == golden["regimes"]


def test_sibling_free_config_emits_no_attribution_warnings(assessed) -> None:
    assert assessed.attribution_warnings == []


# --- Ungrouped specs are unaffected by feature grouping -------------------
#
# A spec with a dependent baseline but no feature_groups must keep one player
# per feature and resolve exactly as it did before grouping existed.


@pytest.fixture(scope="module")
def assessed_live():
    return Estimator.from_csv(MEASUREMENTS, cli._load_spec(UNGROUPED_DEPENDENT_CONFIG)).assess()


@pytest.fixture(scope="module")
def golden_dependent() -> dict:
    return json.loads(GOLDEN_DEPENDENT.read_text(encoding="utf-8"))


def test_ungrouped_dependent_baseline_attributions_are_unchanged(assessed_live, golden_dependent) -> None:
    actual = {
        item.name: {
            "mean_abs_shapley": item.feature.mean_abs_shapley,
            "mean_signed_shapley": item.feature.mean_signed_shapley,
            "total_signed_shapley": item.feature.total_signed_shapley,
            "net_contribution_share_pct": item.feature.net_contribution_share_pct,
        }
        for item in assessed_live.regimes
        if item.analysis == "feature"
    }
    assert actual == golden_dependent["features"]


def test_ungrouped_dependent_baseline_burden_is_unchanged(assessed_live, golden_dependent) -> None:
    actual = [
        {
            "crossing": ranking.crossing_label,
            "baseline_cell": ranking.baseline_cell,
            "observed_accuracy_pct": ranking.observed_accuracy_pct,
            "ceiling_accuracy_pct": ranking.ceiling_accuracy_pct,
            "total_mismatches": ranking.total_mismatches,
            "entries": [
                {
                    "rank": entry.rank,
                    "cell": entry.cell,
                    "count": entry.count,
                    "mismatch_count": entry.mismatch_count,
                    "mismatch_rate_pct": entry.mismatch_rate_pct,
                    "recoverable_mismatches": entry.recoverable_mismatches,
                    "cumulative_accuracy_if_eliminated_pct": entry.cumulative_accuracy_if_eliminated_pct,
                }
                for entry in ranking.entries
            ],
        }
        for ranking in assessed_live.burden_rankings
    ]
    assert actual == golden_dependent["burden"]


# --- Coalition-scored conditions are additive ----------------------------
#
# The live example now declares a second, coalition-scored crossing beside its
# original direction crossing. Adding it must not disturb the direction
# crossing, the feature attributions, or any regime that existed before.

# A frozen copy of the bundled config as it stood before coalition scores,
# carrying the direction crossing alone.
DIRECTION_ONLY_CONFIG = ROOT / "tests" / "fixtures" / "continuous_lora_direction_only_config.json"
LIVE_CONFIG = ROOT / "examples" / "continuous_lora" / "config.json"

_DIRECTION_CROSSING = "BW quality"


@pytest.fixture(scope="module")
def assessed_direction_only():
    return Estimator.from_csv(MEASUREMENTS, cli._load_spec(DIRECTION_ONLY_CONFIG)).assess()


@pytest.fixture(scope="module")
def assessed_both_crossings():
    return Estimator.from_csv(MEASUREMENTS, cli._load_spec(LIVE_CONFIG)).assess()


def _matrix(result, crossing: str) -> dict:
    matrix = next(m for m in result.factorial_matrices if crossing in m.label)
    return {
        cell.name: (cell.count, cell.mismatch_rate_pct, cell.risk_ratio)
        for cell in matrix.cells
    }


def _burden(result, crossing: str) -> list[tuple]:
    ranking = next(r for r in result.burden_rankings if crossing in r.crossing_label)
    return [
        (entry.rank, entry.cell, entry.count, entry.mismatch_rate_pct, entry.recoverable_mismatches)
        for entry in ranking.entries
    ]


def test_direction_crossing_is_unchanged_by_the_added_decision_crossing(
    assessed_direction_only, assessed_both_crossings
) -> None:
    assert _matrix(assessed_both_crossings, _DIRECTION_CROSSING) == _matrix(
        assessed_direction_only, _DIRECTION_CROSSING
    )
    assert _burden(assessed_both_crossings, _DIRECTION_CROSSING) == _burden(
        assessed_direction_only, _DIRECTION_CROSSING
    )


def test_direction_only_contrasts_are_unchanged(
    assessed_direction_only, assessed_both_crossings
) -> None:
    def contrasts(result):
        return [
            (c.factorial, c.stratum, c.level_a, c.level_b, c.risk_ratio)
            for c in result.contrast_results
            if _DIRECTION_CROSSING in c.factorial
        ]

    assert contrasts(assessed_both_crossings) == contrasts(assessed_direction_only)


def test_feature_attributions_survive_the_added_crossing(
    assessed_direction_only, assessed_both_crossings
) -> None:
    def features(result):
        return {
            item.name: item.feature.net_contribution_share_pct
            for item in result.regimes
            if item.analysis == "feature"
        }

    assert features(assessed_both_crossings) == features(assessed_direction_only)


def test_pre_existing_regimes_and_cells_survive_the_added_crossing(
    assessed_direction_only, assessed_both_crossings
) -> None:
    def regimes(result):
        return {
            item.name: (item.regime.count, item.regime.contribution_share_pct)
            for item in result.regimes
            if item.analysis == "regime" and item.regime is not None
        }

    before, after = regimes(assessed_direction_only), regimes(assessed_both_crossings)
    assert all(after[name] == value for name, value in before.items())


def test_no_partition_warning_from_either_crossing(assessed_both_crossings) -> None:
    assert assessed_both_crossings.partition_warnings == []
