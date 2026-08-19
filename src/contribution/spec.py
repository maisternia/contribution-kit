"""Typed configuration objects for factor-contribution analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class Regime:
    """A single declarative regime about what may contribute to a formula outcome.

        ``Regime`` is the one type callers need to construct for regime analysis.
        Each regime is a ``name`` plus one boolean ``condition`` DSL string.
        Every regime is treated as a subset of rows where the condition holds,
        and the observed-contribution share and mismatch risk versus the rest of
        the rows are reported.

        Shapley features are declared separately through
        ``AttributionSpec.prediction_features``. Equality conditions remain
        regimes when declared here; the config-only ``actual == baseline``
        shorthand is reserved for ``prediction_features``.
    """

    name: str
    condition: str
    label: str | None = None


Hypothesis = Regime
CategoricalHypothesis = Regime
ContinuousHypothesis = Regime


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

    ``baseline`` may reference other declared feature names as free variables.
    Each reference resolves to the coalition-resolved value of that feature:
    its ``actual`` value when the referenced feature is in the coalition being
    scored, and its own resolved ``baseline`` value otherwise. This lets a
    baseline state a conditional ideal ("what this feature should have been,
    given what the features it depends on actually did"). The reference graph
    must be acyclic.

    ``actual`` may reference only input columns, never another feature: an
    ``actual`` that depended on a sibling would stop the full coalition from
    reproducing the observed prediction.

    ``independent`` forbids dependency edges on this feature in **both**
    directions -- no other feature's ``baseline`` may reference it, and its own
    ``baseline`` may not reference another feature. Use it to declare that a
    feature is determined independently of the others, so that an
    over-referencing baseline fails validation instead of silently absorbing
    the prediction formula.
    """

    actual: str
    baseline: str
    label: str | None = None
    independent: bool = False


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
    ``regimes`` is a flat list of regime conditions.
    """

    target: str
    prediction: str
    prediction_expr: str
    prediction_features: dict[str, PredictionFeature] = field(default_factory=dict)
    regimes: list[Regime] = field(default_factory=list)
    factorials: list[FactorialCrossing] = field(default_factory=list)
    scope: str = "global"
    score_mode: Literal["absolute", "signed"] = "absolute"
