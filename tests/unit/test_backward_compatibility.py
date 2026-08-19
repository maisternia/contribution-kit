"""Pins the bundled example's attributions against a pre-change snapshot.

The dependent-baseline capability is additive: a spec whose baselines
reference no sibling feature must resolve exactly as it did before
dependency-ordered resolution existed. The golden file was captured from the
bundled config before any resolution code changed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contribution import Estimator
from contribution import cli

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden_continuous_lora_pre_dependent_baselines.json"
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
