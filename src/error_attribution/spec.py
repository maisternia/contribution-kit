"""Typed configuration objects for error attribution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

HypothesisKind = Literal["continuous", "categorical"]


@dataclass(slots=True)
class Hypothesis:
    """A single declarative hypothesis about what may contribute to formula error.

    Callers describe each hypothesis with one boolean ``condition`` DSL string.
    The estimator privately decides how to analyse it, based on the shape of the
    condition:

    * A top-level equality (``actual == baseline``) declares a *formula feature*.
      The left operand is the model-produced value, the right operand is the
      ground-truth baseline, and the feature joins the Shapley attribution of the
      prediction-formula error. The feature ``name`` must appear in
      ``AttributionSpec.prediction_expr``.
    * Any other boolean expression declares an *error regime*: the rows where the
      condition holds form a subset whose observed-error share and mismatch risk
      (versus the remaining rows) are reported.

    Callers never declare regimes or binary tests directly; they only declare
    conditions.
    """

    name: str
    condition: str
    label: str | None = None
    kind: HypothesisKind = "continuous"


@dataclass(slots=True)
class ContinuousHypothesis(Hypothesis):
    kind: HypothesisKind = "continuous"


@dataclass(slots=True)
class CategoricalHypothesis(Hypothesis):
    kind: HypothesisKind = "categorical"


@dataclass(slots=True)
class AttributionSpec:
    """Single declarative entry point for an attribution analysis.

    Callers declare the prediction formula (``prediction_expr`` versus
    ``target_expr``), an optional mismatch indicator (``mismatch_expr``), and one
    flat list of ``hypotheses``. The estimator privately derives feature Shapley
    attribution, error-regime shares, and binary mismatch risk from that list.
    """

    target_expr: str
    prediction_expr: str
    hypotheses: list[Hypothesis] = field(default_factory=list)
    mismatch_expr: str | None = None
    scope: str = "global"
    score_mode: Literal["absolute_error", "signed_error"] = "absolute_error"
