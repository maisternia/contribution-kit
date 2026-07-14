"""Factor-contribution analysis toolkit public API."""

from .contributor import ContributorRow, combine_contributors, rank_contributors
from .estimator import Estimator
from .hypothesis import (
    BinaryHypothesisResult,
    BinaryHypothesisTest,
    evaluate_binary_hypotheses,
    evaluate_binary_hypothesis,
)
from .results import (
    AssessmentResult,
    ContrastResult,
    FactorialCellResult,
    FactorialMarginalResult,
    FactorialMatrixResult,
    FeatureAttribution,
    HypothesisAssessment,
    PartitionWarning,
    RegimeSummary,
)
from .spec import (
    AttributionSpec,
    CategoricalHypothesis,
    ContinuousHypothesis,
    Factor,
    FactorialCrossing,
    Hypothesis,
)
from .stats import OddsRatioResult, RiskRatioResult, baptista_pike_odds_ratio, haldane_anscombe_odds_ratio, katz_risk_ratio, koopman_risk_ratio

__all__ = [
    "AssessmentResult",
    "AttributionSpec",
    "BinaryHypothesisResult",
    "BinaryHypothesisTest",
    "CategoricalHypothesis",
    "ContributorRow",
    "ContinuousHypothesis",
    "ContrastResult",
    "RegimeSummary",
    "Estimator",
    "Factor",
    "FactorialCellResult",
    "FactorialCrossing",
    "FactorialMarginalResult",
    "FactorialMatrixResult",
    "FeatureAttribution",
    "Hypothesis",
    "HypothesisAssessment",
    "OddsRatioResult",
    "RiskRatioResult",
    "baptista_pike_odds_ratio",
    "combine_contributors",
    "evaluate_binary_hypotheses",
    "evaluate_binary_hypothesis",
    "haldane_anscombe_odds_ratio",
    "katz_risk_ratio",
    "koopman_risk_ratio",
    "PartitionWarning",
    "rank_contributors",
]
