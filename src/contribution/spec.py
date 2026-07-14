"""Typed configuration objects for factor-contribution analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class Hypothesis:
    """A single declarative hypothesis about what may contribute to a formula outcome.

        ``Hypothesis`` is the one type callers need to construct for regime analysis.
        Each hypothesis is a ``name`` plus one boolean ``condition`` DSL string.
        Every hypothesis is treated as a regime: rows where the condition holds form a
        subset whose observed-contribution share and mismatch risk (versus the
        remaining rows) are reported.

        Shapley features are declared separately through
        ``AttributionSpec.prediction_features``. Equality conditions remain
        regimes when declared here; the config-only ``actual == baseline``
        shorthand is reserved for ``prediction_features``.
    """

    name: str
    condition: str
    label: str | None = None


@dataclass(slots=True)
class CategoricalHypothesis(Hypothesis):
    """Backward-compatible alias for category-focused hypothesis declarations."""


@dataclass(slots=True)
class ContinuousHypothesis(Hypothesis):
    """Backward-compatible alias for continuous-value hypothesis declarations."""


@dataclass(slots=True)
class FactorialCrossing:
    """Two-axis crossing declaration used to generate factorial cells.
    
    Axes are declared inline as maps of level name to boolean condition DSL strings.
    An optional label provides the human-readable display identity for the crossing.
    """

    rows: dict[str, str]
    columns: dict[str, str]
    label: str | None = None
    baseline: dict[str, str] | None = None


@dataclass(slots=True)
class PredictionFeature:
    """Canonical actual/baseline pair for a prediction-formula feature.

    Python callers construct ``PredictionFeature`` explicitly. Config files may
    also use a string shorthand whose top-level expression is exactly
    ``actual == baseline``; the CLI loader normalizes that shorthand into this
    dataclass before estimator code runs.
    """

    actual: str
    baseline: str
    label: str | None = None


@dataclass(slots=True)
class AttributionSpec:
    """Single declarative entry point for an attribution analysis.

    Callers declare the observed target expression (``target``), observed
    prediction expression (``prediction``), and a formula expression
    (``prediction_expr``) used only for Shapley decomposition.

    ``prediction_features`` explicitly declares the formula variables used for
    Shapley attribution as named ``actual``/``baseline`` pairs. When loaded
    from JSON/YAML, those entries may also use a config-only top-level
    ``actual == baseline`` shorthand that is normalized to the same canonical
    ``PredictionFeature`` form.
    ``hypotheses`` is a flat list of regime conditions.
    """

    target: str
    prediction: str
    prediction_expr: str
    prediction_features: dict[str, PredictionFeature] = field(default_factory=dict)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    factorials: list[FactorialCrossing] = field(default_factory=list)
    scope: str = "global"
    score_mode: Literal["absolute", "signed"] = "absolute"
