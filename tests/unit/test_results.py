from __future__ import annotations

import json

from contribution.hypothesis import BinaryHypothesisResult
from contribution.results import AssessmentResult, FeatureAttribution, HypothesisAssessment, RegimeSummary, _format_effect_ci


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
    assert "| regime | count |" in markdown
    assert "| hypothesis | match mismatch rate |" in markdown

    no_risk_markdown = _sample_result(include_risk=False).to_markdown()
    assert "| hypothesis | match mismatch rate |" not in no_risk_markdown


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
    assert "| regime | count |" not in markdown


def test_markdown_references_default_to_score_exact() -> None:
    markdown = _sample_result(include_risk=True).to_markdown()
    assert "Risk ratio CI: Koopman (1984)" in markdown
    assert "Odds ratio CI: Baptista & Pike (1977)" in markdown


def test_markdown_references_switch_for_wald() -> None:
    result = _sample_result(include_risk=True)
    result.metadata = {"ci_method": "wald"}
    markdown = result.to_markdown()
    assert "Risk ratio CI: Katz, Baptista, Azen & Pike (1978)" in markdown
    assert "Odds ratio CI: Haldane (1956)" in markdown
    assert "Koopman (1984)" not in markdown
