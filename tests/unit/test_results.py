from __future__ import annotations

import json

from contribution.hypothesis import BinaryHypothesisResult
from contribution.results import (
    AssessmentResult,
    BurdenRankingEntry,
    BurdenRankingResult,
    FeatureAttribution,
    HypothesisAssessment,
    RegimeSummary,
    _format_effect_ci,
)


def _sample_result(include_risk: bool = True) -> AssessmentResult:
    feature_a = FeatureAttribution("a", "A", 1.0, 0.5, 1.0, 25.0)
    feature_b = FeatureAttribution("b", "B", 2.0, 1.5, 3.0, 75.0)
    regime = RegimeSummary("reg", 2, 0.5, 1.0, 10.0)
    risk = (
        BinaryHypothesisResult(
            scope="s",
            test_name="reg",
            group_a="A",
            group_b="B",
            mismatch_rate_a_pct=10.0,
            mismatch_rate_b_pct=5.0,
            mismatch_count_a=1,
            total_count_a=10,
            mismatch_count_b=1,
            total_count_b=20,
            risk_ratio=2.0,
            rr_ci_low=1.1,
            rr_ci_high=3.3,
            odds_ratio=2.2,
            or_ci_low=1.0,
            or_ci_high=4.0,
        )
        if include_risk
        else None
    )
    return AssessmentResult(
        hypotheses=[
            HypothesisAssessment(name="a", label="A", analysis="feature", feature=feature_a),
            HypothesisAssessment(name="b", label="B", analysis="feature", feature=feature_b),
            HypothesisAssessment(name="reg", label="Reg", analysis="regime", regime=regime, risk=risk),
        ],
        n_rows=2,
        mean_observed_contribution=0.5,
    )


def test_format_effect_ci() -> None:
    assert _format_effect_ci(2.0, 1.0, 3.0) == "2.00 (1.00 to 3.00)"
    assert _format_effect_ci(float("inf"), 1.0, 3.0) == "inf (n/a)"
    assert _format_effect_ci(2.0, None, None) == "2.00 (n/a)"


def test_properties_and_markdown_sections() -> None:
    result = _sample_result(include_risk=True)
    features = result.feature_attributions
    assert [f.name for f in features] == ["b", "a"]
    assert features[0].net_error_share_pct == features[0].net_contribution_share_pct
    assert len(result.regime_summaries) == 1
    assert result.regime_summaries[0].mean_error == result.regime_summaries[0].mean_contribution
    assert result.regime_summaries[0].total_error == result.regime_summaries[0].total_contribution
    assert result.regime_summaries[0].error_share_pct == result.regime_summaries[0].contribution_share_pct
    assert len(result.binary_results) == 1
    assert result.mean_observed_error == result.mean_observed_contribution

    markdown = result.to_markdown()
    assert "| Regime | Count |" in markdown
    assert "| Hypothesis | Regime mismatch rate |" in markdown

    no_risk_markdown = _sample_result(include_risk=False).to_markdown()
    assert "| Hypothesis | Regime mismatch rate |" not in no_risk_markdown


def test_csv_json_and_save(tmp_path) -> None:
    result = _sample_result(include_risk=True)

    csv_path = tmp_path / "out.csv"
    json_path = tmp_path / "out.json"
    result.to_csv(csv_path)
    result.to_json(json_path)
    assert csv_path.exists()
    assert json_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["n_rows"] == 2

    save_dir = tmp_path / "save"
    result.save(save_dir)
    assert (save_dir / "contribution.csv").exists()
    assert (save_dir / "run.json").exists()
    assert (save_dir / "report.md").exists()


def test_to_csv_empty_records_header_fallback(tmp_path) -> None:
    result = AssessmentResult(hypotheses=[], n_rows=0, mean_observed_contribution=0.0)
    target = tmp_path / "empty.csv"
    result.to_csv(target)
    text = target.read_text(encoding="utf-8")
    assert "name,label,mean_abs_shapley" in text


def test_markdown_without_regimes_section() -> None:
    result = AssessmentResult(
        hypotheses=[
            HypothesisAssessment(
                name="f",
                label="F",
                analysis="feature",
                feature=FeatureAttribution("f", "F", 0.1, 0.1, 0.1, 100.0),
            )
        ],
        n_rows=1,
        mean_observed_contribution=0.1,
    )
    markdown = result.to_markdown()
    assert "| Regime | Count |" not in markdown


def test_markdown_accessible_presentation() -> None:
    result = _sample_result(include_risk=True)
    result.metadata.update(
        {
            "target": "col('GT SF')",
            "prediction": "col('Measured SF')",
            "prediction_expr": "class_sf + round(2 * log2(measured_bw / class_bw))",
            "score_mode": "absolute",
        }
    )
    markdown = result.to_markdown()

    # Section titles name each analysis.
    assert "## Shapley Value Contributions" in markdown
    assert "## Error Regimes" in markdown
    assert "## Mismatch Risk" in markdown

    # Inputs live in an Inputs subsection inside each relevant analysis section.
    assert "\n## Inputs\n" not in markdown
    assert "### Inputs" in markdown
    assert "- Shapley formula (`prediction_expr`):" in markdown
    assert "- Target (`target`):" in markdown
    assert markdown.count("- Observed prediction (`prediction`):") == 2
    assert "- Scoring mode (`score_mode`):" in markdown
    assert "- Mismatch definition: `prediction != target`" in markdown
    assert "- Formula apportioned across features:" in markdown
    assert markdown.count("- Shapley formula (`prediction_expr`):") == 1
    assert markdown.count("- Scoring mode (`score_mode`):") == 1

    # Human-readable Shapley column names instead of raw field identifiers.
    assert "| Feature | Description | Mean absolute | Mean signed | Total signed | Net share (%) |" in markdown
    assert "mean_abs_shapley" not in markdown
    assert "net_contribution_share_pct" not in markdown

    # Per-table conclusions and preserved CI labels/footnotes.
    assert markdown.count("**In short:**") == 3
    assert "`b` (B) carries the largest net contribution share at 75.00%." in markdown
    assert "Risk ratio (95% CI)" in markdown
    assert "Odds ratio (95% CI)" in markdown
    assert "| Hypothesis | Regime mismatch rate | Rest mismatch rate |" in markdown
    assert "Koopman (1984)" in markdown


def test_markdown_omits_missing_input_line() -> None:
    result = _sample_result(include_risk=False)
    result.metadata.update(
        {
            "target": "gt",
            "prediction": "pred",
            "prediction_expr": "a + b",
            "score_mode": "absolute",
        }
    )
    markdown = result.to_markdown()
    assert "- Shapley formula (`prediction_expr`):" in markdown
    assert "- Mismatch definition: `prediction != target`" not in markdown


def test_markdown_omits_zero_mismatch_risk_row() -> None:
    visible_risk = BinaryHypothesisResult(
        scope="s",
        test_name="visible-risk",
        group_a="A",
        group_b="rest",
        mismatch_rate_a_pct=20.0,
        mismatch_rate_b_pct=5.0,
        mismatch_count_a=2,
        total_count_a=10,
        mismatch_count_b=1,
        total_count_b=20,
        risk_ratio=4.0,
        rr_ci_low=1.0,
        rr_ci_high=8.0,
        odds_ratio=4.5,
        or_ci_low=1.1,
        or_ci_high=9.0,
    )
    hidden_risk = BinaryHypothesisResult(
        scope="s",
        test_name="baseline-hidden",
        group_a="A",
        group_b="rest",
        mismatch_rate_a_pct=0.0,
        mismatch_rate_b_pct=25.0,
        mismatch_count_a=0,
        total_count_a=10,
        mismatch_count_b=5,
        total_count_b=20,
        risk_ratio=0.0,
        rr_ci_low=None,
        rr_ci_high=None,
        odds_ratio=0.0,
        or_ci_low=0.0,
        or_ci_high=0.0,
    )
    result = AssessmentResult(
        hypotheses=[
            HypothesisAssessment(
                name="f",
                label="F",
                analysis="feature",
                feature=FeatureAttribution("f", "F", 0.1, 0.1, 0.1, 100.0),
            ),
            HypothesisAssessment(
                name="visible-risk",
                label="Visible",
                analysis="regime",
                regime=RegimeSummary("visible-risk", 10, 0.2, 2.0, 66.0),
                risk=visible_risk,
            ),
            HypothesisAssessment(
                name="baseline-hidden",
                label="Hidden",
                analysis="regime",
                regime=RegimeSummary("baseline-hidden", 10, 0.0, 0.0, 0.0),
                risk=hidden_risk,
            ),
        ],
        n_rows=20,
        mean_observed_contribution=0.1,
    )

    markdown = result.to_markdown()
    risk_section = markdown.split("## Mismatch Risk", maxsplit=1)[1]

    assert "visible-risk" in risk_section
    assert "baseline-hidden" not in risk_section
    assert markdown.count("baseline-hidden") == 1


def test_markdown_risk_counts_show_mismatch_and_match_split() -> None:
    result = _sample_result(include_risk=True)
    markdown = result.to_markdown()

    # For group A: mismatch_count_a=1, total_count_a=10 => 1:9
    # For group B: mismatch_count_b=1, total_count_b=20 => 1:19
    assert "10.00% (1:9)" in markdown
    assert "5.00% (1:19)" in markdown


def test_csv_json_keep_raw_field_names(tmp_path) -> None:
    result = _sample_result(include_risk=True)
    csv_path = tmp_path / "out.csv"
    json_path = tmp_path / "out.json"
    result.to_csv(csv_path)
    result.to_json(json_path)

    csv_header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert csv_header == "name,label,mean_abs_shapley,mean_signed_shapley,total_signed_shapley,net_contribution_share_pct"

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "mean_abs_shapley" in payload["feature_attributions"][0]
    assert "net_contribution_share_pct" in payload["feature_attributions"][0]
    assert "contribution_share_pct" in payload["regime_summaries"][0]


def test_markdown_and_json_include_burden_when_present(tmp_path) -> None:
    result = _sample_result(include_risk=False)
    result.burden_rankings = [
        BurdenRankingResult(
            crossing_label="BW quality × scaling direction",
            baseline_cell="class_ok & measured_ok",
            entries=[
                BurdenRankingEntry(
                    rank=1,
                    cell="class_ok & measured_off",
                    row_level="class_ok",
                    column_level="measured_off",
                    count=10,
                    mismatch_count=5,
                    mismatch_rate_pct=50.0,
                    baseline_rate_pct=5.0,
                    recoverable_mismatches=4.5,
                    share_total_mismatches_pct=45.0,
                    risk_difference=0.45,
                    rd_ci_low=0.30,
                    rd_ci_high=0.58,
                    cumulative_accuracy_if_eliminated_pct=91.0,
                    recoverable=True,
                )
            ],
            overlap_suppressed=False,
            coverage_gap_excluded_rows=2,
            baseline_sanity_warning="Declared baseline is not the minimum-rate cell.",
            observed_accuracy_pct=86.0,
            ceiling_accuracy_pct=91.0,
            total_mismatches=10,
        )
    ]

    markdown = result.to_markdown()
    assert "## Attributable burden" in markdown
    assert "Counterfactual caveat" in markdown
    assert "Risk difference CI: Miettinen & Nurminen (1985)" in markdown

    json_path = tmp_path / "run.json"
    result.to_json(json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "burden_rankings" in payload


def test_markdown_omits_burden_reference_without_burden_table() -> None:
    markdown = _sample_result(include_risk=False).to_markdown()
    assert "Risk difference CI: Miettinen & Nurminen (1985)" not in markdown
