from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from contribution import cli, stats as stats_mod
from contribution.expr import evaluate_expression
from contribution.hypothesis import BinaryHypothesisResult
from contribution.results import (
    AssessmentResult,
    BurdenRankingEntry,
    BurdenRankingResult,
    FeatureAttribution,
    PartitionWarning,
    RegimeAssessment,
    RegimeSummary,
    _format_rd,
    _format_rr,
)
from contribution.stats import OddsRatioResult, RiskDifferenceResult


def _base_config() -> dict:
    return {
        "target": "1",
        "prediction": "1",
        "prediction_expr": "1",
        "prediction_features": {"f": {"actual": "1", "baseline": "0"}},
    }


def test_result_from_run_full_payload() -> None:
    feature = FeatureAttribution("f", "F", 1.0, 1.0, 1.0, 100.0)
    regime = RegimeSummary("r", 1, 1.0, 1.0, 100.0)
    risk = BinaryHypothesisResult(
        scope="s",
        test_name="r",
        group_a="A",
        group_b="B",
        mismatch_rate_a_pct=10.0,
        mismatch_rate_b_pct=5.0,
        mismatch_count_a=1,
        total_count_a=10,
        mismatch_count_b=1,
        total_count_b=20,
        risk_ratio=2.0,
        rr_ci_low=1.0,
        rr_ci_high=3.0,
        odds_ratio=2.0,
        or_ci_low=1.0,
        or_ci_high=3.0,
    )
    payload = {
        "regimes": [
            {
                "name": "r",
                "label": "R",
                "analysis": "regime",
                "feature": {
                    "name": feature.name,
                    "label": feature.label,
                    "mean_abs_shapley": feature.mean_abs_shapley,
                    "mean_signed_shapley": feature.mean_signed_shapley,
                    "total_signed_shapley": feature.total_signed_shapley,
                    "net_contribution_share_pct": feature.net_contribution_share_pct,
                },
                "regime": {
                    "name": regime.name,
                    "count": regime.count,
                    "mean_contribution": regime.mean_contribution,
                    "total_contribution": regime.total_contribution,
                    "contribution_share_pct": regime.contribution_share_pct,
                },
                "risk": {
                    "scope": risk.scope,
                    "test_name": risk.test_name,
                    "group_a": risk.group_a,
                    "group_b": risk.group_b,
                    "mismatch_rate_a_pct": risk.mismatch_rate_a_pct,
                    "mismatch_rate_b_pct": risk.mismatch_rate_b_pct,
                    "mismatch_count_a": risk.mismatch_count_a,
                    "total_count_a": risk.total_count_a,
                    "mismatch_count_b": risk.mismatch_count_b,
                    "total_count_b": risk.total_count_b,
                    "risk_ratio": risk.risk_ratio,
                    "rr_ci_low": risk.rr_ci_low,
                    "rr_ci_high": risk.rr_ci_high,
                    "odds_ratio": risk.odds_ratio,
                    "or_ci_low": risk.or_ci_low,
                    "or_ci_high": risk.or_ci_high,
                },
            }
        ],
        "factorial_matrices": [
            {
                "label": "M",
                "cells": [
                    {
                        "name": "c",
                        "row_level": "a",
                        "column_level": "b",
                        "count": 1,
                        "mismatch_rate_pct": 10.0,
                        "risk_ratio": 2.0,
                        "rr_ci_low": 1.0,
                        "rr_ci_high": 3.0,
                    }
                ],
                "row_marginals": [
                    {
                        "level": "a",
                        "count": 1,
                        "mismatch_rate_pct": 10.0,
                        "risk_ratio": 2.0,
                        "rr_ci_low": 1.0,
                        "rr_ci_high": 3.0,
                    }
                ],
                "column_marginals": [
                    {
                        "level": "b",
                        "count": 1,
                        "mismatch_rate_pct": 10.0,
                        "risk_ratio": 2.0,
                        "rr_ci_low": 1.0,
                        "rr_ci_high": 3.0,
                    }
                ],
            }
        ],
        "contrast_results": [
            {
                "factorial": "M",
                "stratum": "rows=a",
                "level_a": "a",
                "level_b": "b",
                "mismatch_rate_a_pct": 10.0,
                "mismatch_rate_b_pct": 5.0,
                "mismatch_count_a": 1,
                "total_count_a": 10,
                "mismatch_count_b": 1,
                "total_count_b": 20,
                "risk_ratio": 2.0,
                "rr_ci_low": 1.0,
                "rr_ci_high": 3.0,
                "odds_ratio": 2.0,
                "or_ci_low": 1.0,
                "or_ci_high": 3.0,
            }
        ],
        "partition_warnings": [{"axis": "rows=a", "overlap_count": 1, "gap_count": 0}],
        "burden_rankings": [
            {
                "crossing_label": "B",
                "baseline_cell": "a & b",
                "entries": [
                    {
                        "rank": 1,
                        "cell": "a & b",
                        "row_level": "a",
                        "column_level": "b",
                        "count": 1,
                        "mismatch_count": 1,
                        "mismatch_rate_pct": 10.0,
                        "baseline_rate_pct": 5.0,
                        "recoverable_mismatches": 1.0,
                        "share_total_mismatches_pct": 50.0,
                        "risk_difference": 0.1,
                        "rd_ci_low": 0.0,
                        "rd_ci_high": 0.2,
                        "cumulative_accuracy_if_eliminated_pct": 99.0,
                        "recoverable": True,
                    }
                ],
                "overlap_suppressed": False,
                "coverage_gap_excluded_rows": 1,
                "baseline_sanity_warning": "warn",
                "observed_accuracy_pct": 97.0,
                "ceiling_accuracy_pct": 99.0,
                "total_mismatches": 3,
            }
        ],
        "n_rows": 1,
        "mean_observed_contribution": 1.0,
    }

    result = getattr(cli, "_result_from_run")(payload)
    assert len(result.regimes) == 1
    assert len(result.factorial_matrices) == 1
    assert len(result.contrast_results) == 1
    assert len(result.partition_warnings) == 1
    assert len(result.burden_rankings) == 1


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"regimes": []}, "must be an object mapping regime names"),
        ({"regimes": {"h": 1}}, "regime 'h' must be a condition string"),
        ({"regimes": {"h": {"condition": "1 == 1", "name": "x"}}}, "must not redeclare 'name'"),
        ({"regimes": {"h": {"label": "missing condition"}}}, "must declare a 'condition' string"),
        ({"regimes": {"h": [1]}}, "must be a condition string or an object"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": []}, "must be an object mapping feature names"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": ""}}, "non-empty top-level '==' equality"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": "col('A'"}}, "single top-level 'actual == baseline' equality"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": "col('A') == col('B') == col('C')"}}, "single top-level 'actual == baseline' equality"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": []}}, "must be an object with required 'actual' and 'baseline'"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": 1, "baseline": "0"}}}, "key 'actual' must be a non-empty string"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": 0}}}, "key 'baseline' must be a non-empty string"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0", "label": 1}}}, "key 'label' must be a string when provided"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": {}}, "must be a list of crossing objects"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [1]}, r"factorials\[0\] must be an object"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": [], "columns": {"b": "1 == 1"}}]}, "must declare 'rows' as an object"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {}, "columns": {"b": "1 == 1"}}]}, "'rows' axis must declare at least one level"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": 1}, "columns": {"b": "1 == 1"}}]}, "rows level 'a' must have a non-empty condition string"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": []}]}, "must declare 'columns' as an object"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {}}]}, "'columns' axis must declare at least one level"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": 1}}]}, "columns level 'b' must have a non-empty condition string"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "label": 1}]}, "'label' must be a non-empty string when provided"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "baseline": []}]}, "'baseline' must be an object with keys 'rows' and 'columns'"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "baseline": {"rows": "a", "columns": "b", "extra": "x"}}]}, r"'baseline' has unknown key\(s\)"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "baseline": {"rows": "a"}}]}, "must include both 'rows' and 'columns'"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "baseline": {"rows": 1, "columns": "b"}}]}, "baseline 'rows' must be a non-empty string"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "baseline": {"rows": "a", "columns": 1}}]}, "baseline 'columns' must be a non-empty string"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "baseline": {"rows": "missing", "columns": "b"}}]}, "baseline rows level 'missing' is not declared on rows axis"),
        ({"regimes": {"h": "1 == 1"}, "prediction_features": {"f": {"actual": "1", "baseline": "0"}}, "factorials": [{"rows": {"a": "1 == 1"}, "columns": {"b": "1 == 1"}, "baseline": {"rows": "a", "columns": "missing"}}]}, "baseline columns level 'missing' is not declared on columns axis"),
    ],
)
def test_load_spec_covering_errors(tmp_path: Path, payload: dict, match: str) -> None:
    cfg = tmp_path / "cfg.json"
    base = _base_config()
    base.update(payload)
    cfg.write_text(json.dumps(base), encoding="utf-8")

    with pytest.raises(ValueError, match=match):
        getattr(cli, "_load_spec")(cfg)


def test_results_private_helpers_and_sections(tmp_path: Path) -> None:
    feature = FeatureAttribution("f", "F", 1.0, 1.0, 1.0, 100.0)
    regime = RegimeSummary("r", 1, 1.0, 1.0, 100.0)
    risk_visible = BinaryHypothesisResult(
        scope="s",
        test_name="risk",
        group_a="A",
        group_b="B",
        mismatch_rate_a_pct=10.0,
        mismatch_rate_b_pct=5.0,
        mismatch_count_a=1,
        total_count_a=10,
        mismatch_count_b=1,
        total_count_b=20,
        risk_ratio=2.0,
        rr_ci_low=1.0,
        rr_ci_high=3.0,
        odds_ratio=2.0,
        or_ci_low=1.0,
        or_ci_high=3.0,
    )
    risk_hidden = BinaryHypothesisResult(
        scope="s",
        test_name="hidden",
        group_a="A",
        group_b="B",
        mismatch_rate_a_pct=0.0,
        mismatch_rate_b_pct=5.0,
        mismatch_count_a=0,
        total_count_a=10,
        mismatch_count_b=1,
        total_count_b=20,
        risk_ratio=0.0,
        rr_ci_low=None,
        rr_ci_high=None,
        odds_ratio=0.0,
        or_ci_low=0.0,
        or_ci_high=0.0,
    )
    result = AssessmentResult(
        regimes=[
            RegimeAssessment(name="f", label="F", analysis="feature", feature=feature),
            RegimeAssessment(name="r", label="R", analysis="regime", regime=regime, risk=risk_visible),
            RegimeAssessment(name="hidden", label="H", analysis="regime", regime=regime, risk=risk_hidden),
        ],
        n_rows=2,
        mean_observed_contribution=1.0,
        metadata={"target": "t", "prediction": "p", "prediction_expr": "x", "score_mode": "signed"},
        partition_warnings=[PartitionWarning(axis="rows=a", overlap_count=1, gap_count=0)],
        burden_rankings=[
            BurdenRankingResult(
                crossing_label="B",
                baseline_cell="a & b",
                entries=[
                    BurdenRankingEntry(
                        rank=1,
                        cell="a & b",
                        row_level="a",
                        column_level="b",
                        count=1,
                        mismatch_count=1,
                        mismatch_rate_pct=10.0,
                        baseline_rate_pct=5.0,
                        recoverable_mismatches=1.0,
                        share_total_mismatches_pct=50.0,
                        risk_difference=0.1,
                        rd_ci_low=0.0,
                        rd_ci_high=0.2,
                        cumulative_accuracy_if_eliminated_pct=99.0,
                        recoverable=True,
                    )
                ],
                overlap_suppressed=False,
                coverage_gap_excluded_rows=1,
                baseline_sanity_warning="warn",
                observed_accuracy_pct=97.0,
                ceiling_accuracy_pct=99.0,
                total_mismatches=3,
            )
        ],
    )

    assert _format_rr(None, None, None) == "n/a"
    assert _format_rr(float("inf"), 1.0, 2.0) == "inf (n/a)"
    assert _format_rr(1.23, 1.0, 2.0) == "1.23 (1.00 to 2.00)"
    assert _format_rd(0.5, None, None) == "0.500 (n/a)"
    assert _format_rd(0.5, 0.1, 0.2) == "0.500 (0.100 to 0.200)"

    assert getattr(result, "_input_lines")() == [
        "- **Target (`target`):** `t`",
        "- **Prediction (`prediction`):** `p`",
        "- **Shapley formula (`prediction_expr`):** `x`",
        "- **Scoring mode:** signed",
    ]
    assert getattr(result, "_shapley_formula")() == "outcome = (x) - (t)"
    result.metadata.pop("score_mode")
    assert getattr(result, "_shapley_formula")() == "outcome = |(x) - (t)|"
    assert getattr(result, "_include_risk_row")(risk_visible) is True
    assert getattr(result, "_include_risk_row")(risk_hidden) is False

    markdown = result.to_markdown()
    assert "## Partition Warnings" in markdown
    assert "## Attributable burden" in markdown
    assert "Risk difference CI: Miettinen & Nurminen (1985)" in markdown
    assert "Coverage gap note:" in markdown
    assert "Baseline sanity warning: warn" in markdown

    target_only = AssessmentResult(
        regimes=result.regimes,
        n_rows=result.n_rows,
        mean_observed_contribution=result.mean_observed_contribution,
        metadata={"target": "t"},
        burden_rankings=result.burden_rankings,
    )
    assert "- Target (`target`): `t`" in target_only.to_markdown()

    prediction_only = AssessmentResult(
        regimes=result.regimes,
        n_rows=result.n_rows,
        mean_observed_contribution=result.mean_observed_contribution,
        metadata={"prediction": "p"},
        burden_rankings=result.burden_rankings,
    )
    assert "- Observed prediction (`prediction`): `p`" in prediction_only.to_markdown()

    suppressed_rankings = AssessmentResult(
        regimes=result.regimes,
        n_rows=result.n_rows,
        mean_observed_contribution=result.mean_observed_contribution,
        metadata={"target": "t", "prediction": "p"},
        burden_rankings=[
            BurdenRankingResult(
                crossing_label="Suppressed",
                baseline_cell="a & b",
                entries=[],
                overlap_suppressed=True,
            )
        ],
    )
    assert "Ranking suppressed due to overlapping axis levels in this crossing." in suppressed_rankings.to_markdown()

    result.metadata.clear()
    assert getattr(result, "_input_lines")() == []
    assert getattr(result, "_shapley_formula")() is None

    json_path = tmp_path / "run.json"
    result.to_json(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "burden_rankings" in payload


def test_expr_greater_than_branch() -> None:
    assert evaluate_expression("col('x') > col('y')", {"x": 2, "y": 1}) is True
    assert evaluate_expression("col('x') > col('y')", {"x": 1, "y": 2}) is False


def test_estimator_validation_and_factorial_branches() -> None:
    from contribution import Estimator
    from contribution.spec import AttributionSpec, FactorialCrossing, PredictionFeature, Regime

    empty_axes = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="1", baseline="0")},
        regimes=[Regime(name="r", condition="1 == 1")],
        factorials=[FactorialCrossing(rows={}, columns={})],
    )
    with pytest.raises(ValueError, match="Factorial crossing 'rows' axis must declare at least one level"):
        Estimator(rows=[{}], spec=empty_axes).assess(exact=True)

    regime_only_spec = AttributionSpec(
        target="f",
        prediction="f",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="1", baseline="0")},
        regimes=[Regime(name="r", condition="1 == 1")],
    )
    estimator = Estimator(rows=[{"f": 1}], spec=regime_only_spec)
    assert estimator._regime_risk(Regime(name="r", condition="1 == 1"), None, ci_method="wald") is None

    empty_columns = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="1", baseline="0")},
        regimes=[Regime(name="r", condition="1 == 1")],
        factorials=[FactorialCrossing(rows={"a": "1 == 1"}, columns={}, label="C")],
    )
    with pytest.raises(ValueError, match="Factorial crossing 'columns' axis must declare at least one level"):
        Estimator(rows=[{}], spec=empty_columns).assess(exact=True)

    bad_baseline = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="1", baseline="0")},
        regimes=[Regime(name="r", condition="1 == 1")],
        factorials=[FactorialCrossing(rows={"a": "1 == 1"}, columns={"b": "1 == 1"}, baseline={"rows": "missing", "columns": "b"}, label="C")],
    )
    with pytest.raises(ValueError, match="baseline rows level 'missing' is not declared on rows axis"):
        Estimator(rows=[{}], spec=bad_baseline).assess(exact=True)

    bad_baseline_column = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="1", baseline="0")},
        regimes=[Regime(name="r", condition="1 == 1")],
        factorials=[FactorialCrossing(rows={"a": "1 == 1"}, columns={"b": "1 == 1"}, baseline={"rows": "a", "columns": "missing"}, label="C")],
    )
    with pytest.raises(ValueError, match="baseline columns level 'missing' is not declared on columns axis"):
        Estimator(rows=[{}], spec=bad_baseline_column).assess(exact=True)

    overlapping_columns = AttributionSpec(
        target="1",
        prediction="1",
        prediction_expr="f",
        prediction_features={"f": PredictionFeature(actual="1", baseline="0")},
        regimes=[Regime(name="r", condition="1 == 1")],
        factorials=[FactorialCrossing(rows={"a": "1 == 1"}, columns={"x": "1 == 1", "y": "1 == 1"}, label="Overlap columns")],
    )
    Estimator(rows=[{}], spec=overlapping_columns).assess(exact=True)

    estimator = Estimator(rows=[{}], spec=empty_axes)
    assert getattr(estimator, "_union_masks")([]) == [False]


def test_stats_private_branches_and_fallbacks(monkeypatch) -> None:
    assert getattr(stats_mod, "_mn_constrained_p0")(0, 1, 1, 0, 0.0) > 0.0
    assert getattr(stats_mod, "_mn_constrained_p0")(1, 0, 1, 0, 0.0) > 0.0

    monkeypatch.setattr(stats_mod, "_risk_difference_value", lambda *args: 1.0)
    monkeypatch.setattr(stats_mod, "_mn_constrained_p0", lambda *args: 0.0)
    assert getattr(stats_mod, "_mn_score_z")(1, 0, 0, 1, 1.0) == 0.0
    monkeypatch.setattr(stats_mod, "_risk_difference_value", lambda *args: 2.0)
    assert getattr(stats_mod, "_mn_score_z")(1, 0, 0, 1, 1.0) == float("inf")
    monkeypatch.setattr(stats_mod, "_risk_difference_value", lambda *args: 0.0)
    assert getattr(stats_mod, "_mn_score_z")(1, 0, 0, 1, 1.0) == float("-inf")

    monkeypatch.setattr(stats_mod, "_mn_score_z", lambda *args, **kwargs: 1.0)
    assert getattr(stats_mod, "_solve_mn_bound")(1, 1, 1, 1, 1.0, lower=True) == -1.0

    seq = iter([2.0, 0.0])

    def score_with_root(*args, **kwargs):
        try:
            return next(seq)
        except StopIteration:
            return 0.0

    monkeypatch.setattr(stats_mod, "_mn_score_z", score_with_root)
    monkeypatch.setattr(stats_mod, "_bisect_root", lambda func, lo, hi: 0.123)
    assert getattr(stats_mod, "_solve_mn_bound")(1, 1, 1, 1, 1.0, lower=True) == 0.123

    calls = iter([math.nan])

    def score_with_nan(*args, **kwargs):
        try:
            return next(calls)
        except StopIteration:
            return 2.0

    monkeypatch.setattr(stats_mod, "_mn_score_z", score_with_nan)
    assert getattr(stats_mod, "_solve_mn_bound")(1, 1, 1, 1, 1.0, lower=True) == -1.0

    monkeypatch.setattr(stats_mod, "_mn_score_z", lambda *args, **kwargs: 2.0)
    assert getattr(stats_mod, "_solve_mn_bound")(1, 1, 1, 1, 1.0, lower=True) == -1.0

    monkeypatch.setattr(stats_mod, "_mn_score_z", lambda *args, **kwargs: 2.0)
    assert getattr(stats_mod, "_solve_mn_bound")(1, 1, 1, 1, 1.0, lower=True) == -1.0

    seq = iter([2.0, 1.0])

    def score_with_zero(*args, **kwargs):
        try:
            return next(seq)
        except StopIteration:
            return 1.0

    monkeypatch.setattr(stats_mod, "_mn_score_z", score_with_zero)
    assert getattr(stats_mod, "_solve_mn_bound")(1, 1, 1, 1, 1.0, lower=True) == pytest.approx(-0.998046875)

    monkeypatch.setattr(stats_mod, "_solve_mn_bound", lambda *args, **kwargs: 0.5)
    bounded = getattr(stats_mod, "miettinen_nurminen_risk_difference")(1, 1, 1, 1)
    assert bounded.ci_low == 0.5 and bounded.ci_high == 0.5

    def flipped_bounds(*args, **kwargs):
        return 0.5 if kwargs.get("lower") else -0.5

    monkeypatch.setattr(stats_mod, "_solve_mn_bound", flipped_bounds)
    flipped = getattr(stats_mod, "miettinen_nurminen_risk_difference")(1, 1, 1, 1)
    assert flipped.ci_low is None and flipped.ci_high is None

    monkeypatch.setattr(
        stats_mod,
        "miettinen_nurminen_risk_difference",
        lambda *args, **kwargs: RiskDifferenceResult(value=1.0, ci_low=None, ci_high=None),
    )
    monkeypatch.setattr(
        stats_mod,
        "agresti_caffo_risk_difference",
        lambda *args, **kwargs: RiskDifferenceResult(value=1.0, ci_low=None, ci_high=None),
    )
    guarded = getattr(stats_mod, "risk_difference_with_guardrail")(1, 1, 1, 1)
    assert guarded.ci_low is None and guarded.ci_high is None

    assert getattr(stats_mod, "_tail_probability")(0, 0, 1, 0, 1.0, tail="lower") == 1.0
    assert getattr(stats_mod, "_tail_probability")(0, 1, 1, 1, 0.0, tail="upper") == 0.0
    assert getattr(stats_mod, "_tail_probability")(1, 1, 1, 1, float("inf"), tail="lower") == 1.0
    assert getattr(stats_mod, "_tail_probability")(1, 1, 1, 1, 1.0, tail="lower") > 0.0
    with pytest.raises(ValueError, match="tail must be 'lower' or 'upper'"):
        getattr(stats_mod, "_tail_probability")(1, 1, 1, 1, 1.0, tail="bad")

    monkeypatch.setattr(stats_mod, "_invert_monotone_tail", lambda *args, **kwargs: 2.0)
    monkeypatch.setattr(
        stats_mod,
        "haldane_anscombe_odds_ratio",
        lambda *args, **kwargs: OddsRatioResult(value=1.0, ci_low=1.5, ci_high=2.5),
    )
    odds = getattr(stats_mod, "baptista_pike_odds_ratio")(1, 1, 1, 1)
    assert odds.ci_low == 2.0 and odds.ci_high == 2.0

    monkeypatch.setattr(stats_mod, "_invert_monotone_tail", lambda *args, **kwargs: float("inf"))
    fallback_odds = getattr(stats_mod, "baptista_pike_odds_ratio")(1, 1, 1, 1)
    assert fallback_odds.ci_low == 1.5 and fallback_odds.ci_high == 2.5

    monkeypatch.setattr(
        stats_mod,
        "haldane_anscombe_odds_ratio",
        lambda *args, **kwargs: OddsRatioResult(value=1.0, ci_low=float("inf"), ci_high=float("inf")),
    )
    nonfinite_fallback_odds = getattr(stats_mod, "baptista_pike_odds_ratio")(1, 1, 1, 1)
    assert nonfinite_fallback_odds.ci_low == float("inf") and nonfinite_fallback_odds.ci_high == float("inf")