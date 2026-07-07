"""Contribution analysis toolkit public API."""

from .contributor import ContributorRow, combine_contributors, rank_contributors
from .estimator import Estimator
from .hypothesis import (
    BinaryHypothesisResult,
    BinaryHypothesisTest,
    evaluate_binary_hypotheses,
    evaluate_binary_hypothesis,
)
from .results import AssessmentResult, RegimeSummary, FeatureAttribution, HypothesisAssessment
from .spec import (
    AttributionSpec,
    Hypothesis,
)
from .stats import OddsRatioResult, RiskRatioResult, haldane_anscombe_odds_ratio, katz_risk_ratio

__all__ = [
    "AssessmentResult",
    "AttributionSpec",
    "BinaryHypothesisResult",
    "BinaryHypothesisTest",
    "ContributorRow",
    "RegimeSummary",
    "Estimator",
    "FeatureAttribution",
    "Hypothesis",
    "HypothesisAssessment",
    "OddsRatioResult",
    "RiskRatioResult",
    "combine_contributors",
    "evaluate_binary_hypotheses",
    "evaluate_binary_hypothesis",
    "haldane_anscombe_odds_ratio",
    "katz_risk_ratio",
    "rank_contributors",
]
