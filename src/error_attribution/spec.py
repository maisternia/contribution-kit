"""Typed configuration objects for error attribution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

HypothesisKind = Literal["continuous", "categorical"]


@dataclass(slots=True)
class HypothesisSpec:
    name: str
    actual_expr: str
    baseline_expr: str
    kind: HypothesisKind = "continuous"
    label: str | None = None


@dataclass(slots=True)
class ContinuousHypothesis(HypothesisSpec):
    kind: HypothesisKind = "continuous"


@dataclass(slots=True)
class CategoricalHypothesis(HypothesisSpec):
    kind: HypothesisKind = "categorical"


@dataclass(slots=True)
class AttributionSpec:
    target_expr: str
    prediction_expr: str
    hypotheses: list[HypothesisSpec] = field(default_factory=list)
    stratify_by: list[str] = field(default_factory=list)
    score_mode: Literal["absolute_error", "signed_error"] = "absolute_error"
