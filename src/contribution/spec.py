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

    ``description`` is optional prose explaining the crossing's axes and what
    distinguishes their levels. Level names are deliberately terse -- they are
    the identity that composes cell names, resolves ``baseline``, and keys every
    marginal, contrast, and burden record -- so the explanation is written once
    per crossing rather than once per level, keeping the axis maps one line per
    level. It is display-only: it never affects level names, generated cell
    names, partition validation, or any computed statistic.
    """

    rows: dict[str, str]
    columns: dict[str, str]
    label: str | None = None
    baseline: dict[str, str] | None = None
    description: str | None = None


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

    Requiring an explicit reference value per feature makes this a *baseline*
    Shapley value (BShap): absent features take a declared reference rather than
    being marginalized out or replaced by a conditional expectation.
    @cite: Sundararajan & Najmi, 2020

    References:
        Sundararajan, M., & Najmi, A. (2020). The many Shapley values for model
        explanation. Proceedings of the 37th International Conference on Machine
        Learning (ICML), PMLR 119, 9269-9278.
    """

    actual: str
    baseline: str
    label: str | None = None
    independent: bool = False


@dataclass(slots=True)
class FeatureGroup:
    """A set of prediction features that form a single decision.

    A group is one **atomic** Shapley player: its members enter and leave every
    coalition together, so no coalition ever holds one member at its actual
    value while another sits at its baseline. Declare a group when the members
    cannot be manipulated independently -- for example a detector that emits a
    nominal ``(bandwidth, spreading factor)`` class as one choice, reported in
    two columns.

    The group's contribution is reported as a single number. No per-member
    split is computed: an internal decomposition would have to score exactly
    the split states the grouping exists to exclude. That per-member split is
    the Owen value, which this kit deliberately does not compute; nothing is
    lost at the group level, since the Owen value satisfies the quotient game
    property and members' Owen values sum to the group figure reported here.

    References:
        Aumann, R. J., & Drèze, J. H. (1974). Cooperative games with coalition
        structures. International Journal of Game Theory, 3(4), 217-237.

        Owen, G. (1977). Values of games with a priori unions. In R. Henn &
        O. Moeschlin (Eds.), Mathematical Economics and Game Theory (pp. 76-88).
        Springer.

        Jullum, M., Redelmeier, A., & Aas, K. (2021). groupShapley: Efficient
        prediction explanation with Shapley values for feature groups.
        arXiv:2106.12228.
    """

    members: tuple[str, ...]
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
    ``feature_groups`` optionally partitions those features into named groups,
    each of which acts as one atomic Shapley player. Features left out of every
    group remain players in their own right; a spec declaring no groups has one
    player per feature.
    ``regimes`` is a flat list of regime conditions.
    """

    target: str
    prediction: str
    prediction_expr: str
    prediction_features: dict[str, PredictionFeature] = field(default_factory=dict)
    feature_groups: dict[str, FeatureGroup] = field(default_factory=dict)
    regimes: list[Regime] = field(default_factory=list)
    factorials: list[FactorialCrossing] = field(default_factory=list)
    scope: str = "global"
    score_mode: Literal["absolute", "signed"] = "absolute"
