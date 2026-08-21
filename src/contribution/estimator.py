"""Estimator API for factor-contribution analysis."""

from __future__ import annotations

import csv
import itertools
import math
import random
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .expr import (
    COALITION_SCORE,
    CompiledExpression,
    build_row_context,
    coalition_score_arguments,
    compile_expression,
    evaluate_expression,
    free_variables,
)
from .hypothesis import BinaryHypothesisResult, evaluate_binary_hypothesis
from .results import (
    AssessmentResult,
    AttributionWarning,
    BurdenRankingEntry,
    BurdenRankingResult,
    ContrastResult,
    FactorialCellResult,
    FactorialMarginalResult,
    FactorialMatrixResult,
    FeatureAttribution,
    PartitionWarning,
    RegimeAssessment,
    RegimeSummary,
)
from .spec import AttributionSpec, Regime
from .stats import risk_difference_with_guardrail


# Coalition scores are float comparisons against an exact-zero invariant;
# tolerate accumulated rounding without masking a real gap.
_ZERO_TOLERANCE = 1e-9


def _parse_scalar(value: str) -> Any:
    text = value.strip()
    if text == "":
        return None
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    try:
        if "." not in text and "e" not in text.lower():
            return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _score(prediction: float, target: float, score_mode: str) -> float:
    return prediction - target if score_mode == "signed" else abs(prediction - target)


@dataclass(slots=True)
class _Feature:
    """A compiled formula feature defined by explicit actual/baseline expressions.

    ``baseline_deps`` holds the declared feature names referenced by the
    baseline expression. Features are ordered so that every dependency is
    resolved before the feature referencing it.
    """

    name: str
    label: str
    actual: CompiledExpression
    baseline: CompiledExpression
    independent: bool = False
    baseline_deps: tuple[str, ...] = ()


@dataclass(slots=True)
class _Player:
    """One atomic unit of the Shapley game.

    A player is either a lone prediction feature or a declared group of them.
    Its ``feature_names`` all take their actual values when the player is in a
    coalition, and all resolve their baselines when it is not, so a group's
    members never separate.
    """

    name: str
    label: str
    feature_names: tuple[str, ...]
    is_group: bool


@dataclass(slots=True)
class _FactorialPlan:
    label: str
    description: str | None
    row_levels: list[str]
    column_levels: list[str]
    cell_names: dict[tuple[str, str], str]
    cell_masks: dict[tuple[str, str], list[bool]]
    baseline: tuple[str, str] | None


@dataclass(slots=True)
class Estimator:
    rows: list[dict[str, Any]]
    spec: AttributionSpec | None = None

    @classmethod
    def from_csv(cls, path: str | Path, spec: AttributionSpec, encoding: str = "utf-8") -> "Estimator":
        with Path(path).open("r", encoding=encoding, newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [{key: _parse_scalar(value) for key, value in row.items()} for row in reader]
        return cls(rows=rows, spec=spec)

    @classmethod
    def from_dataframe(cls, dataframe: Any, spec: AttributionSpec) -> "Estimator":
        if hasattr(dataframe, "to_dict"):
            rows = list(dataframe.to_dict(orient="records"))
        elif isinstance(dataframe, Sequence):
            rows = [dict(row) for row in dataframe]
        else:
            raise TypeError("Unsupported dataframe-like object")
        return cls(rows=rows, spec=spec)

    def assess(self, *, spec: AttributionSpec | None = None, exact: bool = True, max_exact_features: int = 12, n_samples: int = 512, seed: int = 0, ci_method: str = "score-exact") -> AssessmentResult:
        if spec is not None:
            self.spec = spec
        self._validate_spec()
        assert self.spec is not None

        # Players are built before factorials expand: axis level conditions may
        # call coalition_score(), and expansion already evaluates them per row
        # for partition checking.
        features = self._formula_features()
        players = self._build_players(features)
        player_names = [player.name for player in players]
        feature_player = {
            feature_name: player.name for player in players for feature_name in player.feature_names
        }

        coalition_scores = self._coalition_score_table(
            features, feature_player, self._referenced_coalitions(players)
        )
        binders = self._coalition_binders(coalition_scores)

        generated_regimes, factorial_plans, partition_warnings = self._expand_factorials(binders)
        effective_regimes = [*self.spec.regimes, *generated_regimes]

        totals = {name: 0.0 for name in player_names}
        abs_totals = {name: 0.0 for name in player_names}
        observed_contributions: list[float] = []
        observed_contribution_total = 0.0
        full_coalition = frozenset(player_names)
        baseline_target_gap_rows = 0
        baseline_target_gap_example: int | None = None
        # Only a baseline reaching outside its own player can absorb the
        # formula; a plain column baseline scoring zero everywhere is
        # small-sample luck, and an intra-player reference never crosses a
        # coalition boundary.
        absorbing_players = {
            player.name: any(
                dependency not in player.feature_names
                for feature in features
                if feature.name in player.feature_names
                for dependency in feature.baseline_deps
            )
            for player in players
        }
        for row_index, row in enumerate(self.rows):
            if player_names:
                score = self._row_scorer(row, features, feature_player)
                row_result = self._assess_row(score, player_names, exact=exact, max_exact_features=max_exact_features, n_samples=n_samples, seed=seed)
                for name, value in row_result.items():
                    totals[name] += value
                    abs_totals[name] += abs(value)
                # The empty coalition must reproduce `target`; otherwise the
                # per-feature contributions do not sum to the observed one.
                if abs(score(frozenset())) > _ZERO_TOLERANCE:
                    baseline_target_gap_rows += 1
                    if baseline_target_gap_example is None:
                        baseline_target_gap_example = row_index
                # A baseline that inverts the formula leaves every coalition
                # excluding its own feature scoring zero.
                for name, still_absorbing in absorbing_players.items():
                    if still_absorbing and abs(score(full_coalition - {name})) > _ZERO_TOLERANCE:
                        absorbing_players[name] = False
            observed_contribution = self._observed_contribution(row, features)
            observed_contributions.append(observed_contribution)
            observed_contribution_total += observed_contribution

        attribution_warnings = self._attribution_warnings(
            features=features,
            players=players,
            baseline_target_gap_rows=baseline_target_gap_rows,
            baseline_target_gap_example=baseline_target_gap_example,
            absorbing_players=absorbing_players,
        )

        n_rows = len(self.rows)
        player_attr: dict[str, FeatureAttribution] = {}
        for player in players:
            signed_total = totals[player.name]
            player_attr[player.name] = FeatureAttribution(
                name=player.name,
                label=player.label,
                mean_abs_shapley=abs_totals[player.name] / n_rows if n_rows else 0.0,
                mean_signed_shapley=signed_total / n_rows if n_rows else 0.0,
                total_signed_shapley=signed_total,
                net_contribution_share_pct=(signed_total / observed_contribution_total * 100.0) if observed_contribution_total else 0.0,
                # One entry per player. A group reports a single contribution
                # and names its members; the per-member split (the Owen value)
                # is deliberately not computed, since its inner step scores the
                # split states grouping exists to remove. Group totals are
                # unaffected: Owen values sum to the quotient-game Shapley value
                # reported here. @cite: Owen, 1977
                members=player.feature_names if player.is_group else (),
            )

        mismatch_fn = self._mismatch_fn()
        assessments: list[RegimeAssessment] = []
        for player in players:
            assessments.append(
                RegimeAssessment(
                    name=player.name,
                    label=player.label,
                    analysis="feature",
                    feature=player_attr[player.name],
                )
            )
        for regime in effective_regimes:
            assessments.append(
                RegimeAssessment(
                    name=regime.name,
                    label=regime.label or regime.name,
                    analysis="regime",
                    regime=self._regime_summary(regime, observed_contributions, observed_contribution_total, binders),
                    risk=self._regime_risk(regime, mismatch_fn, ci_method=ci_method, binders=binders),
                )
            )

        factorial_matrices = self._build_factorial_matrices(factorial_plans, mismatch_fn, ci_method=ci_method)
        contrast_results = self._build_contrast_results(factorial_plans, mismatch_fn, ci_method=ci_method)
        burden_rankings = self._build_burden_rankings(factorial_plans, mismatch_fn, partition_warnings)

        return AssessmentResult(
            regimes=assessments,
            n_rows=n_rows,
            mean_observed_contribution=observed_contribution_total / n_rows if n_rows else 0.0,
            factorial_matrices=factorial_matrices,
            contrast_results=contrast_results,
            partition_warnings=partition_warnings,
            burden_rankings=burden_rankings,
            attribution_warnings=attribution_warnings,
            metadata={
                "exact": exact,
                "n_samples": n_samples,
                "seed": seed,
                "ci_method": ci_method,
                "target": self.spec.target,
                "prediction": self.spec.prediction,
                "prediction_expr": self.spec.prediction_expr,
                "score_mode": self.spec.score_mode,
            },
        )

    def _attribution_warnings(
        self,
        *,
        features: Sequence[_Feature],
        players: Sequence[_Player],
        baseline_target_gap_rows: int,
        baseline_target_gap_example: int | None,
        absorbing_players: Mapping[str, bool],
    ) -> list[AttributionWarning]:
        warnings_out: list[AttributionWarning] = []

        column_names = self._column_names()
        shadowed = sorted({
            dependency
            for feature in features
            for dependency in feature.baseline_deps
            if dependency in column_names
        })
        if shadowed:
            message = (
                f"baseline reference(s) {', '.join(shadowed)} name both a prediction feature and "
                "an input column; the feature binding wins"
            )
            warnings.warn(message, stacklevel=3)
            warnings_out.append(AttributionWarning(kind="feature_shadows_column", message=message))

        if baseline_target_gap_rows:
            message = (
                f"baselines do not reproduce the target on {baseline_target_gap_rows} row(s) "
                f"(first at index {baseline_target_gap_example}); per-feature contributions do "
                "not sum to the observed contribution, so the reported shares are unsound"
            )
            warnings.warn(message, stacklevel=3)
            warnings_out.append(AttributionWarning(kind="baseline_target_mismatch", message=message))

        for player in players:
            if not absorbing_players.get(player.name):
                continue
            others = [
                name
                for other in players
                if other.name != player.name
                for name in other.feature_names
            ]
            if not others:
                continue
            message = (
                f"every coalition excluding '{player.name}' scores zero on all rows, so its "
                f"baseline absorbs the prediction formula; {', '.join(others)} can only be "
                f"attributed in interaction with '{player.name}'. Check whether its baseline "
                "references more features than it conditions on."
            )
            warnings.warn(message, stacklevel=3)
            warnings_out.append(AttributionWarning(kind="formula_absorption", message=message))

        return warnings_out

    def _build_players(self, features: Sequence[_Feature]) -> list[_Player]:
        """Partition features into Shapley players, validating the grouping.

        The partition turns the game into a *coalition structure* game: each
        group is a block of a priori united players, and the Shapley value is
        then taken over the quotient game, in which every block acts as one
        player. @cite: Aumann & Drèze, 1974; Owen, 1977

        A group takes the declaration position of its first member, so player
        order still tracks ``prediction_features`` order.

        References:
            Aumann, R. J., & Drèze, J. H. (1974). Cooperative games with
            coalition structures. International Journal of Game Theory, 3(4),
            217-237.

            Owen, G. (1977). Values of games with a priori unions. In R. Henn &
            O. Moeschlin (Eds.), Mathematical Economics and Game Theory
            (pp. 76-88). Springer.

            Jullum, M., Redelmeier, A., & Aas, K. (2021). groupShapley:
            Efficient prediction explanation with Shapley values for feature
            groups. arXiv:2106.12228.
        """
        assert self.spec is not None
        feature_names = [feature.name for feature in features]
        labels = {feature.name: feature.label for feature in features}
        groups = self.spec.feature_groups

        owner: dict[str, str] = {}
        for group_name, group in groups.items():
            if not group.members:
                raise ValueError(f"feature group '{group_name}' declares no members")
            if group_name in labels:
                raise ValueError(
                    f"feature group '{group_name}' collides with a prediction feature of the same name"
                )
            if any(regime.name == group_name for regime in self.spec.regimes):
                raise ValueError(
                    f"feature group '{group_name}' collides with a regime of the same name"
                )
            for member in group.members:
                if member not in labels:
                    raise ValueError(
                        f"feature group '{group_name}' lists member '{member}', which is not a "
                        "declared prediction feature"
                    )
                if member in owner:
                    raise ValueError(
                        f"prediction feature '{member}' is listed in more than one feature group: "
                        f"{owner[member]}, {group_name}"
                    )
                owner[member] = group_name

        players: list[_Player] = []
        seen_groups: set[str] = set()
        for name in feature_names:
            group_name = owner.get(name)
            if group_name is None:
                players.append(
                    _Player(name=name, label=labels[name], feature_names=(name,), is_group=False)
                )
                continue
            if group_name in seen_groups:
                continue
            seen_groups.add(group_name)
            group = groups[group_name]
            members = tuple(member for member in feature_names if owner.get(member) == group_name)
            players.append(
                _Player(
                    name=group_name,
                    label=group.label or group_name,
                    feature_names=members,
                    is_group=True,
                )
            )
        return players

    def _condition_sources(self) -> list[tuple[str, str]]:
        """Every expression a coalition score may legally appear in.

        Returns ``(description, source)`` pairs, where the description names
        the condition well enough for a validation error to point at it.
        """
        assert self.spec is not None
        sources = [(f"regime '{regime.name}'", regime.condition) for regime in self.spec.regimes]
        for index, crossing in enumerate(self.spec.factorials):
            label = crossing.label or f"Factorial {index + 1}"
            for axis, levels in (("rows", crossing.rows), ("columns", crossing.columns)):
                for level_name, condition in levels.items():
                    sources.append((f"factorial '{label}' {axis} level '{level_name}'", condition))
        return sources

    def _referenced_coalitions(self, players: Sequence[_Player]) -> set[frozenset[str]]:
        """Collect and validate every coalition named by a condition.

        Runs before any row is read, so a misspelled player fails once with the
        valid names rather than once per row. Arguments name *players*: a
        grouped feature is reachable only through its group, because a coalition
        holding one member without its siblings is a state the modelled system
        cannot produce.
        """
        player_names = [player.name for player in players]
        valid = set(player_names)
        member_owner = {
            member: player.name
            for player in players
            if player.is_group
            for member in player.feature_names
        }

        referenced: set[frozenset[str]] = set()
        for description, source in self._condition_sources():
            for arguments in coalition_score_arguments(compile_expression(source)):
                seen: set[str] = set()
                for name in arguments:
                    if name in seen:
                        raise ValueError(
                            f"{description} names player '{name}' more than once in one "
                            f"{COALITION_SCORE}() call"
                        )
                    seen.add(name)
                    if name in valid:
                        continue
                    if name in member_owner:
                        raise ValueError(
                            f"{description} names '{name}' in {COALITION_SCORE}(), which is a "
                            f"member of feature group '{member_owner[name]}'. Name the group "
                            "instead: a coalition holding one member of a group while its "
                            "siblings sit at baseline is not a state the modelled system can "
                            "produce."
                        )
                    raise ValueError(
                        f"{description} names unknown player '{name}' in {COALITION_SCORE}(). "
                        f"Valid players: {', '.join(player_names)}"
                    )
                referenced.add(frozenset(arguments))
        return referenced

    def _coalition_score_table(
        self,
        features: Sequence[_Feature],
        feature_player: Mapping[str, str],
        coalitions: set[frozenset[str]],
    ) -> dict[frozenset[str], list[float]]:
        """Score each referenced coalition once per row.

        Work is bounded by the number of *referenced* coalitions, not by the
        size of the lattice, so repeating ``coalition_score('class')`` across a
        declared regime, an axis level, and every generated cell derived from
        it costs one resolution per row in total.
        """
        assert self.spec is not None
        table: dict[frozenset[str], list[float]] = {coalition: [] for coalition in coalitions}
        if not coalitions:
            return table
        for row in self.rows:
            actual_values = self._actual_values(row, features)
            target = float(self._evaluate_target(row))
            for coalition in coalitions:
                values = self._resolve_coalition_values(
                    row, features, coalition, actual_values, feature_player
                )
                prediction = self._evaluate_prediction_formula(row, values)
                table[coalition].append(_score(prediction, target, self.spec.score_mode))
        return table

    @staticmethod
    def _coalition_binders(
        table: Mapping[frozenset[str], Sequence[float]],
    ) -> list[Callable[[tuple[str, ...]], float]] | None:
        """One lookup closure per row, or ``None`` when no condition asked."""
        if not table:
            return None
        n_rows = len(next(iter(table.values())))

        def binder(row_index: int) -> Callable[[tuple[str, ...]], float]:
            # Every referenced coalition is in the table by construction, so a
            # missing key would be an internal error, not an author error.
            return lambda names: table[frozenset(names)][row_index]

        return [binder(row_index) for row_index in range(n_rows)]

    @staticmethod
    def _condition_context(
        row_index: int,
        row: Mapping[str, Any],
        binders: Sequence[Callable[[tuple[str, ...]], float]] | None,
    ) -> dict[str, Any]:
        if binders is None:
            return build_row_context(row)
        return build_row_context(row, coalition_score=binders[row_index])

    def _reject_coalition_score(self, description: str, source: str) -> None:
        """Forbid coalition scores in the expressions that define the game."""
        if not coalition_score_arguments(compile_expression(source)):
            return
        raise ValueError(
            f"{description} uses {COALITION_SCORE}(), which is not permitted there: a "
            "coalition score is computed by evaluating that very expression. "
            f"{COALITION_SCORE}() is available only in regime conditions and factorial axis "
            "level conditions."
        )

    def _column_names(self) -> set[str]:
        names: set[str] = set()
        for row in self.rows:
            names.update(row)
        return names

    def _classify_variables(
        self,
        expression: CompiledExpression,
        feature_names: Sequence[str],
        column_names: set[str],
        owner: str,
    ) -> tuple[set[str], set[str]]:
        """Split free variables into declared-feature references and unknown names.

        A bare identifier is a legal column reference in the DSL, so a name is
        only a feature reference when it matches a *different* declared
        feature. A feature commonly carries the name of the column it reads
        (``PredictionFeature(actual="x", ...)`` for a feature named ``x``), so
        the owner's own name resolves to a column whenever one exists; a
        feature can never usefully reference itself. Among other names,
        features win over columns, matching how ``prediction_expr`` bindings
        already shadow row values.
        """
        variables = free_variables(expression)
        references = {
            name
            for name in variables
            if name in feature_names and not (name == owner and name in column_names)
        }
        unknown = {name for name in variables if name not in references and name not in column_names}
        return references, unknown

    def _formula_features(self) -> list[_Feature]:
        assert self.spec is not None
        feature_names = list(self.spec.prediction_features)
        column_names = self._column_names()

        features: dict[str, _Feature] = {}
        for feature_name, feature_spec in self.spec.prediction_features.items():
            self._reject_coalition_score(
                f"prediction feature '{feature_name}' actual expression", feature_spec.actual
            )
            self._reject_coalition_score(
                f"prediction feature '{feature_name}' baseline expression", feature_spec.baseline
            )
            actual = compile_expression(feature_spec.actual)
            baseline = compile_expression(feature_spec.baseline)

            actual_refs, actual_unknown = self._classify_variables(actual, feature_names, column_names, feature_name)
            if actual_refs:
                raise ValueError(
                    f"prediction feature '{feature_name}' actual expression references "
                    f"prediction feature(s): {', '.join(sorted(actual_refs))}. An actual "
                    "expression may reference only input columns."
                )
            if actual_unknown:
                raise ValueError(
                    f"prediction feature '{feature_name}' actual expression references unknown "
                    f"name(s): {', '.join(sorted(actual_unknown))}"
                )

            baseline_refs, baseline_unknown = self._classify_variables(baseline, feature_names, column_names, feature_name)
            if baseline_unknown:
                raise ValueError(
                    f"prediction feature '{feature_name}' baseline expression references unknown "
                    f"name(s): {', '.join(sorted(baseline_unknown))}"
                )

            features[feature_name] = _Feature(
                name=feature_name,
                label=feature_spec.label or feature_name,
                actual=actual,
                baseline=baseline,
                independent=feature_spec.independent,
                baseline_deps=tuple(name for name in feature_names if name in baseline_refs),
            )

        self._validate_independence(features)
        return self._ordered_features(features)

    def _validate_independence(self, features: Mapping[str, _Feature]) -> None:
        """Enforce that an independent feature sits in no dependency edge.

        The flag name does not carry direction, so each error states which
        direction was violated and names both features.
        """
        for feature in features.values():
            if feature.independent and feature.baseline_deps:
                raise ValueError(
                    f"prediction feature '{feature.name}' is declared independent but its own "
                    f"baseline references prediction feature(s): "
                    f"{', '.join(feature.baseline_deps)}. An independent feature may not depend "
                    "on another feature."
                )
            for dependency in feature.baseline_deps:
                if features[dependency].independent:
                    raise ValueError(
                        f"prediction feature '{feature.name}' baseline references "
                        f"'{dependency}', which is declared independent and may not be "
                        "referenced by another feature's baseline."
                    )

    def _ordered_features(self, features: Mapping[str, _Feature]) -> list[_Feature]:
        """Return features in dependency order, rejecting cycles.

        Declaration order is preserved among independent siblings so that
        report ordering stays stable.
        """
        ordered: list[_Feature] = []
        placed: set[str] = set()
        visiting: list[str] = []

        def visit(name: str) -> None:
            if name in placed:
                return
            if name in visiting:
                cycle = visiting[visiting.index(name):] + [name]
                raise ValueError(
                    "prediction feature baseline references form a cycle: " + " -> ".join(cycle)
                )
            visiting.append(name)
            for dependency in features[name].baseline_deps:
                visit(dependency)
            visiting.pop()
            placed.add(name)
            ordered.append(features[name])

        for name in features:
            visit(name)
        return ordered

    def _regime_summary(
        self,
        regime: Regime,
        observed_contributions: Sequence[float],
        observed_contribution_total: float,
        binders: Sequence[Callable[[tuple[str, ...]], float]] | None = None,
    ) -> RegimeSummary:
        predicate = compile_expression(regime.condition)
        group_total_contribution = 0.0
        count = 0
        for row_index, (row, observed_contribution) in enumerate(zip(self.rows, observed_contributions)):
            if bool(predicate.evaluate(self._condition_context(row_index, row, binders))):
                group_total_contribution += observed_contribution
                count += 1
        return RegimeSummary(
            name=regime.name,
            count=count,
            mean_contribution=(group_total_contribution / count) if count else 0.0,
            total_contribution=group_total_contribution,
            contribution_share_pct=(group_total_contribution / observed_contribution_total * 100.0) if observed_contribution_total else 0.0,
        )

    def _regime_risk(
        self,
        regime: Regime,
        mismatch_fn,
        *,
        ci_method: str,
        binders: Sequence[Callable[[tuple[str, ...]], float]] | None = None,
    ) -> BinaryHypothesisResult | None:
        assert self.spec is not None
        if mismatch_fn is None:
            return None
        predicate = compile_expression(regime.condition)
        matches = [
            bool(predicate.evaluate(self._condition_context(row_index, row, binders)))
            for row_index, row in enumerate(self.rows)
        ]
        return self._evaluate_binary_from_masks(
            test_name=regime.name,
            group_a_label=regime.label or regime.name,
            group_b_label="rest",
            group_a_matches=matches,
            group_b_matches=None,
            mismatch_fn=mismatch_fn,
            ci_method=ci_method,
        )

    def _evaluate_binary_from_masks(
        self,
        *,
        test_name: str,
        group_a_label: str,
        group_b_label: str,
        group_a_matches: Sequence[bool],
        group_b_matches: Sequence[bool] | None,
        mismatch_fn,
        ci_method: str,
    ) -> BinaryHypothesisResult | None:
        assert self.spec is not None
        if group_b_matches is None:
            group_b_matches = [not matched for matched in group_a_matches]
        group_a_rows = [row for row, matched in zip(self.rows, group_a_matches) if matched]
        group_b_rows = [row for row, matched in zip(self.rows, group_b_matches) if matched]
        if not group_a_rows or not group_b_rows:
            return None
        return evaluate_binary_hypothesis(
            scope=self.spec.scope,
            test_name=test_name,
            group_a_label=group_a_label,
            group_b_label=group_b_label,
            group_a_rows=group_a_rows,
            group_b_rows=group_b_rows,
            mismatch_fn=mismatch_fn,
            ci_method=ci_method,
        )

    def _mismatch_fn(self):
        assert self.spec is not None
        def predicate(row: Mapping[str, Any]) -> bool:
            prediction = self._evaluate_prediction_observed(row)
            target = self._evaluate_target(row)
            return prediction != target

        return predicate

    def _observed_contribution(self, row: Mapping[str, Any], _features: Sequence[_Feature]) -> float:
        assert self.spec is not None
        prediction = float(self._evaluate_prediction_observed(row))
        target = float(self._evaluate_target(row))
        return _score(prediction, target, self.spec.score_mode)

    def _validate_spec(self) -> None:
        if self.spec is None:
            raise ValueError("Attribution spec is required for assess()")
        if not self.spec.regimes and not self.spec.factorials:
            raise ValueError("At least one regime or factorial crossing is required")
        # The observed mismatch predicate is `prediction != target`, so guarding
        # these three guards it too.
        self._reject_coalition_score("target expression", self.spec.target)
        self._reject_coalition_score("prediction expression", self.spec.prediction)
        self._reject_coalition_score("prediction_expr", self.spec.prediction_expr)
        prediction_expression = compile_expression(self.spec.prediction_expr)
        formula_variables = free_variables(prediction_expression)
        declared_features = set(self.spec.prediction_features)
        undeclared_variables = sorted(formula_variables.difference(declared_features))
        if undeclared_variables:
            raise ValueError(
                "prediction_expr references undeclared prediction feature(s): "
                + ", ".join(undeclared_variables)
            )
        unused_features = sorted(declared_features.difference(formula_variables))
        if unused_features:
            raise ValueError(
                "prediction_features declared but unused by prediction_expr: "
                + ", ".join(unused_features)
            )
        names = [regime.name for regime in self.spec.regimes]
        if len(names) != len(set(names)):
            raise ValueError("Regime names must be unique")
        colliding_names = sorted(set(names).intersection(declared_features))
        if colliding_names:
            raise ValueError(
                "prediction_features names must not collide with regime names: "
                + ", ".join(colliding_names)
            )
        for crossing in self.spec.factorials:
            if not crossing.rows:
                raise ValueError("Factorial crossing 'rows' axis must declare at least one level")
            if not crossing.columns:
                raise ValueError("Factorial crossing 'columns' axis must declare at least one level")
            if crossing.baseline is not None:
                baseline_row = crossing.baseline.get("rows")
                baseline_column = crossing.baseline.get("columns")
                crossing_name = crossing.label or "unnamed"
                if baseline_row not in crossing.rows:
                    raise ValueError(
                        f"crossing '{crossing_name}' baseline rows level '{baseline_row}' is not declared on rows axis"
                    )
                if baseline_column not in crossing.columns:
                    raise ValueError(
                        f"crossing '{crossing_name}' baseline columns level '{baseline_column}' is not declared on columns axis"
                    )

    def _expand_factorials(
        self,
        binders: Sequence[Callable[[tuple[str, ...]], float]] | None = None,
    ) -> tuple[list[Regime], list[_FactorialPlan], list[PartitionWarning]]:
        assert self.spec is not None
        if not self.spec.factorials:
            return [], [], []

        declared_names = {regime.name for regime in self.spec.regimes}
        generated_names: set[str] = set()
        generated_regimes: list[Regime] = []
        plans: list[_FactorialPlan] = []
        partition_warnings: list[PartitionWarning] = []

        for crossing_index, crossing in enumerate(self.spec.factorials):
            # Compute effective label (1-based position as fallback)
            effective_label = crossing.label if crossing.label else f"Factorial {crossing_index + 1}"

            # Evaluate rows axis
            row_levels = list(crossing.rows)
            row_level_matches: dict[str, list[bool]] = {}
            for level_name, condition in crossing.rows.items():
                compiled = compile_expression(condition)
                row_level_matches[level_name] = [
                    bool(compiled.evaluate(self._condition_context(row_index, row, binders)))
                    for row_index, row in enumerate(self.rows)
                ]

            # Check for partition violations in rows
            rows_overlap_count = 0
            rows_gap_count = 0
            for row_index in range(len(self.rows)):
                match_count = sum(1 for matches in row_level_matches.values() if matches[row_index])
                if match_count > 1:
                    rows_overlap_count += 1
                elif match_count == 0:
                    rows_gap_count += 1
            if rows_overlap_count or rows_gap_count:
                warnings.warn(
                    f"factorial '{effective_label}' rows axis is not a strict partition: overlap_rows={rows_overlap_count}, gap_rows={rows_gap_count}",
                    stacklevel=2,
                )
                partition_warnings.append(
                    PartitionWarning(axis=f"{effective_label}: rows", overlap_count=rows_overlap_count, gap_count=rows_gap_count)
                )

            # Evaluate columns axis
            column_levels = list(crossing.columns)
            column_level_matches: dict[str, list[bool]] = {}
            for level_name, condition in crossing.columns.items():
                compiled = compile_expression(condition)
                column_level_matches[level_name] = [
                    bool(compiled.evaluate(self._condition_context(row_index, row, binders)))
                    for row_index, row in enumerate(self.rows)
                ]

            # Check for partition violations in columns
            columns_overlap_count = 0
            columns_gap_count = 0
            for row_index in range(len(self.rows)):
                match_count = sum(1 for matches in column_level_matches.values() if matches[row_index])
                if match_count > 1:
                    columns_overlap_count += 1
                elif match_count == 0:
                    columns_gap_count += 1
            if columns_overlap_count or columns_gap_count:
                warnings.warn(
                    f"factorial '{effective_label}' columns axis is not a strict partition: overlap_rows={columns_overlap_count}, gap_rows={columns_gap_count}",
                    stacklevel=2,
                )
                partition_warnings.append(
                    PartitionWarning(axis=f"{effective_label}: columns", overlap_count=columns_overlap_count, gap_count=columns_gap_count)
                )

            # Expand cells
            cell_names: dict[tuple[str, str], str] = {}
            cell_masks: dict[tuple[str, str], list[bool]] = {}
            for row_level in row_levels:
                row_matches = row_level_matches[row_level]
                for column_level in column_levels:
                    column_matches = column_level_matches[column_level]
                    name = f"{row_level} & {column_level}"
                    if name in declared_names or name in generated_names:
                        raise ValueError(f"Generated factorial cell name collision: '{name}'")
                    generated_names.add(name)
                    # Get the conditions from the crossing
                    row_condition = crossing.rows[row_level]
                    column_condition = crossing.columns[column_level]
                    condition = f"({row_condition}) and ({column_condition})"
                    generated_regimes.append(Regime(name=name, condition=condition))
                    cell_names[(row_level, column_level)] = name
                    cell_masks[(row_level, column_level)] = [
                        row_match and column_match
                        for row_match, column_match in zip(row_matches, column_matches)
                    ]

            plans.append(
                _FactorialPlan(
                    label=effective_label,
                    description=crossing.description,
                    row_levels=row_levels,
                    column_levels=column_levels,
                    cell_names=cell_names,
                    cell_masks=cell_masks,
                    baseline=(crossing.baseline["rows"], crossing.baseline["columns"]) if crossing.baseline else None,
                )
            )

        return generated_regimes, plans, partition_warnings

    def _mask_mismatch_stats(self, mask: Sequence[bool], mismatch_fn) -> tuple[int, float]:
        rows = [row for row, matched in zip(self.rows, mask) if matched]
        count = len(rows)
        mismatch_count = sum(1 for row in rows if mismatch_fn(row))
        mismatch_rate = (mismatch_count / count * 100.0) if count else 0.0
        return count, mismatch_rate

    def _mask_mismatch_count(self, mask: Sequence[bool], mismatch_fn) -> tuple[int, int]:
        rows = [row for row, matched in zip(self.rows, mask) if matched]
        count = len(rows)
        mismatch_count = sum(1 for row in rows if mismatch_fn(row))
        return count, mismatch_count

    def _union_masks(self, masks: Sequence[Sequence[bool]]) -> list[bool]:
        if not masks:
            return [False for _ in self.rows]
        return [any(values) for values in zip(*masks)]

    def _build_factorial_matrices(
        self,
        plans: Sequence[_FactorialPlan],
        mismatch_fn,
        *,
        ci_method: str,
    ) -> list[FactorialMatrixResult]:
        matrices: list[FactorialMatrixResult] = []
        for plan in plans:
            matrix = FactorialMatrixResult(label=plan.label, description=plan.description)
            for row_level in plan.row_levels:
                for column_level in plan.column_levels:
                    mask = plan.cell_masks[(row_level, column_level)]
                    count, mismatch_rate = self._mask_mismatch_stats(mask, mismatch_fn)
                    risk = self._evaluate_binary_from_masks(
                        test_name=plan.cell_names[(row_level, column_level)],
                        group_a_label=plan.cell_names[(row_level, column_level)],
                        group_b_label="rest",
                        group_a_matches=mask,
                        group_b_matches=None,
                        mismatch_fn=mismatch_fn,
                        ci_method=ci_method,
                    )
                    matrix.cells.append(
                        FactorialCellResult(
                            name=plan.cell_names[(row_level, column_level)],
                            row_level=row_level,
                            column_level=column_level,
                            count=count,
                            mismatch_rate_pct=mismatch_rate,
                            risk_ratio=risk.risk_ratio if risk is not None else None,
                            rr_ci_low=risk.rr_ci_low if risk is not None else None,
                            rr_ci_high=risk.rr_ci_high if risk is not None else None,
                        )
                    )

            for row_level in plan.row_levels:
                union_mask = self._union_masks([plan.cell_masks[(row_level, column_level)] for column_level in plan.column_levels])
                count, mismatch_rate = self._mask_mismatch_stats(union_mask, mismatch_fn)
                risk = self._evaluate_binary_from_masks(
                    test_name=f"{row_level} marginal",
                    group_a_label=row_level,
                    group_b_label="rest",
                    group_a_matches=union_mask,
                    group_b_matches=None,
                    mismatch_fn=mismatch_fn,
                    ci_method=ci_method,
                )
                matrix.row_marginals.append(
                    FactorialMarginalResult(
                        level=row_level,
                        count=count,
                        mismatch_rate_pct=mismatch_rate,
                        risk_ratio=risk.risk_ratio if risk is not None else None,
                        rr_ci_low=risk.rr_ci_low if risk is not None else None,
                        rr_ci_high=risk.rr_ci_high if risk is not None else None,
                    )
                )

            for column_level in plan.column_levels:
                union_mask = self._union_masks([plan.cell_masks[(row_level, column_level)] for row_level in plan.row_levels])
                count, mismatch_rate = self._mask_mismatch_stats(union_mask, mismatch_fn)
                risk = self._evaluate_binary_from_masks(
                    test_name=f"{column_level} marginal",
                    group_a_label=column_level,
                    group_b_label="rest",
                    group_a_matches=union_mask,
                    group_b_matches=None,
                    mismatch_fn=mismatch_fn,
                    ci_method=ci_method,
                )
                matrix.column_marginals.append(
                    FactorialMarginalResult(
                        level=column_level,
                        count=count,
                        mismatch_rate_pct=mismatch_rate,
                        risk_ratio=risk.risk_ratio if risk is not None else None,
                        rr_ci_low=risk.rr_ci_low if risk is not None else None,
                        rr_ci_high=risk.rr_ci_high if risk is not None else None,
                    )
                )

            matrices.append(matrix)
        return matrices

    def _build_contrast_results(
        self,
        plans: Sequence[_FactorialPlan],
        mismatch_fn,
        *,
        ci_method: str,
    ) -> list[ContrastResult]:
        contrasts: list[ContrastResult] = []
        for plan in plans:
            for row_level in plan.row_levels:
                for level_a, level_b in itertools.combinations(plan.column_levels, 2):
                    risk = self._evaluate_binary_from_masks(
                        test_name=f"{plan.label}: rows={row_level} [{level_a} vs {level_b}]",
                        group_a_label=level_a,
                        group_b_label=level_b,
                        group_a_matches=plan.cell_masks[(row_level, level_a)],
                        group_b_matches=plan.cell_masks[(row_level, level_b)],
                        mismatch_fn=mismatch_fn,
                        ci_method=ci_method,
                    )
                    if risk is None:
                        continue
                    contrasts.append(
                        ContrastResult(
                            factorial=plan.label,
                            stratum=f"rows={row_level}",
                            level_a=level_a,
                            level_b=level_b,
                            mismatch_rate_a_pct=risk.mismatch_rate_a_pct,
                            mismatch_rate_b_pct=risk.mismatch_rate_b_pct,
                            mismatch_count_a=risk.mismatch_count_a,
                            total_count_a=risk.total_count_a,
                            mismatch_count_b=risk.mismatch_count_b,
                            total_count_b=risk.total_count_b,
                            risk_ratio=risk.risk_ratio,
                            rr_ci_low=risk.rr_ci_low,
                            rr_ci_high=risk.rr_ci_high,
                            odds_ratio=risk.odds_ratio,
                            or_ci_low=risk.or_ci_low,
                            or_ci_high=risk.or_ci_high,
                        )
                    )

            for column_level in plan.column_levels:
                for level_a, level_b in itertools.combinations(plan.row_levels, 2):
                    risk = self._evaluate_binary_from_masks(
                        test_name=f"{plan.label}: columns={column_level} [{level_a} vs {level_b}]",
                        group_a_label=level_a,
                        group_b_label=level_b,
                        group_a_matches=plan.cell_masks[(level_a, column_level)],
                        group_b_matches=plan.cell_masks[(level_b, column_level)],
                        mismatch_fn=mismatch_fn,
                        ci_method=ci_method,
                    )
                    if risk is None:
                        continue
                    contrasts.append(
                        ContrastResult(
                            factorial=plan.label,
                            stratum=f"columns={column_level}",
                            level_a=level_a,
                            level_b=level_b,
                            mismatch_rate_a_pct=risk.mismatch_rate_a_pct,
                            mismatch_rate_b_pct=risk.mismatch_rate_b_pct,
                            mismatch_count_a=risk.mismatch_count_a,
                            total_count_a=risk.total_count_a,
                            mismatch_count_b=risk.mismatch_count_b,
                            total_count_b=risk.total_count_b,
                            risk_ratio=risk.risk_ratio,
                            rr_ci_low=risk.rr_ci_low,
                            rr_ci_high=risk.rr_ci_high,
                            odds_ratio=risk.odds_ratio,
                            or_ci_low=risk.or_ci_low,
                            or_ci_high=risk.or_ci_high,
                        )
                    )
        return contrasts

    def _build_burden_rankings(
        self,
        plans: Sequence[_FactorialPlan],
        mismatch_fn,
        partition_warnings: Sequence[PartitionWarning],
    ) -> list[BurdenRankingResult]:
        rankings: list[BurdenRankingResult] = []
        total_rows = len(self.rows)
        total_mismatches = sum(1 for row in self.rows if mismatch_fn(row))
        observed_accuracy_pct = ((total_rows - total_mismatches) / total_rows * 100.0) if total_rows else 0.0

        for plan in plans:
            if plan.baseline is None:
                continue

            overlap_suppressed = any(
                warning.axis.startswith(f"{plan.label}:") and warning.overlap_count > 0
                for warning in partition_warnings
            )
            union_mask = self._union_masks(list(plan.cell_masks.values()))
            coverage_gap_excluded_rows = sum(1 for matched in union_mask if not matched)

            baseline_row, baseline_column = plan.baseline
            baseline_cell_name = plan.cell_names[(baseline_row, baseline_column)]
            baseline_count, baseline_mismatches = self._mask_mismatch_count(
                plan.cell_masks[(baseline_row, baseline_column)], mismatch_fn
            )
            if baseline_count == 0:
                raise ValueError(
                    f"crossing '{plan.label}' baseline cell '{baseline_cell_name}' matches zero rows"
                )

            baseline_rate = baseline_mismatches / baseline_count

            baseline_sanity_warning: str | None = None
            all_cell_rates: list[float] = []
            for row_level in plan.row_levels:
                for column_level in plan.column_levels:
                    cell_count, cell_mismatches = self._mask_mismatch_count(
                        plan.cell_masks[(row_level, column_level)], mismatch_fn
                    )
                    rate = (cell_mismatches / cell_count) if cell_count else 0.0
                    all_cell_rates.append(rate)
            if any(rate < baseline_rate for rate in all_cell_rates):
                baseline_sanity_warning = (
                    f"Declared baseline '{baseline_cell_name}' is not the lowest mismatch-rate cell in '{plan.label}'."
                )

            if overlap_suppressed:
                rankings.append(
                    BurdenRankingResult(
                        crossing_label=plan.label,
                        baseline_cell=baseline_cell_name,
                        entries=[],
                        overlap_suppressed=True,
                        coverage_gap_excluded_rows=coverage_gap_excluded_rows,
                        baseline_sanity_warning=baseline_sanity_warning,
                        observed_accuracy_pct=observed_accuracy_pct,
                        ceiling_accuracy_pct=observed_accuracy_pct,
                        total_mismatches=total_mismatches,
                    )
                )
                continue

            ranked_candidates: list[dict[str, Any]] = []
            for row_index, row_level in enumerate(plan.row_levels):
                for column_index, column_level in enumerate(plan.column_levels):
                    if (row_level, column_level) == plan.baseline:
                        continue
                    cell_name = plan.cell_names[(row_level, column_level)]
                    cell_count, cell_mismatches = self._mask_mismatch_count(
                        plan.cell_masks[(row_level, column_level)], mismatch_fn
                    )
                    cell_rate = (cell_mismatches / cell_count) if cell_count else 0.0
                    excess = cell_count * (cell_rate - baseline_rate)
                    risk_difference = risk_difference_with_guardrail(
                        cell_mismatches,
                        cell_count - cell_mismatches,
                        baseline_mismatches,
                        baseline_count - baseline_mismatches,
                    )
                    ranked_candidates.append(
                        {
                            "row_index": row_index,
                            "column_index": column_index,
                            "cell_name": cell_name,
                            "row_level": row_level,
                            "column_level": column_level,
                            "count": cell_count,
                            "mismatch_count": cell_mismatches,
                            "cell_rate": cell_rate,
                            "excess": excess,
                            "share": (excess / total_mismatches * 100.0) if total_mismatches else 0.0,
                            "rd": risk_difference,
                        }
                    )

            ranked_candidates.sort(
                key=lambda entry: (
                    0 if entry["excess"] > 0.0 else 1,
                    -entry["excess"] if entry["excess"] > 0.0 else 0.0,
                    entry["row_index"],
                    entry["column_index"],
                )
            )

            entries: list[BurdenRankingEntry] = []
            cumulative_recovered = 0.0
            for position, entry in enumerate(ranked_candidates, start=1):
                recoverable = entry["excess"] > 0.0
                if recoverable:
                    cumulative_recovered += entry["excess"]
                cumulative_accuracy_pct = (
                    ((total_rows - total_mismatches + cumulative_recovered) / total_rows) * 100.0
                    if total_rows
                    else 0.0
                )
                entries.append(
                    BurdenRankingEntry(
                        rank=position,
                        cell=entry["cell_name"],
                        row_level=entry["row_level"],
                        column_level=entry["column_level"],
                        count=entry["count"],
                        mismatch_count=entry["mismatch_count"],
                        mismatch_rate_pct=entry["cell_rate"] * 100.0,
                        baseline_rate_pct=baseline_rate * 100.0,
                        recoverable_mismatches=entry["excess"] if recoverable else None,
                        share_total_mismatches_pct=entry["share"] if recoverable else None,
                        risk_difference=entry["rd"].value,
                        rd_ci_low=entry["rd"].ci_low,
                        rd_ci_high=entry["rd"].ci_high,
                        cumulative_accuracy_if_eliminated_pct=cumulative_accuracy_pct,
                        recoverable=recoverable,
                    )
                )

            rankings.append(
                BurdenRankingResult(
                    crossing_label=plan.label,
                    baseline_cell=baseline_cell_name,
                    entries=entries,
                    overlap_suppressed=False,
                    coverage_gap_excluded_rows=coverage_gap_excluded_rows,
                    baseline_sanity_warning=baseline_sanity_warning,
                    observed_accuracy_pct=observed_accuracy_pct,
                    ceiling_accuracy_pct=(
                        entries[-1].cumulative_accuracy_if_eliminated_pct if entries else observed_accuracy_pct
                    ),
                    total_mismatches=total_mismatches,
                )
            )

        return rankings

    def _evaluate_target(self, row: Mapping[str, Any]) -> Any:
        return evaluate_expression(self.spec.target, build_row_context(row))

    def _evaluate_prediction_observed(self, row: Mapping[str, Any]) -> Any:
        return evaluate_expression(self.spec.prediction, build_row_context(row))

    def _actual_values(self, row: Mapping[str, Any], features: Sequence[_Feature]) -> dict[str, Any]:
        """Evaluate every feature's actual expression once for this row.

        Actual expressions may not reference sibling features, so these values
        are the same for every coalition.
        """
        context = build_row_context(row)
        return {feature.name: feature.actual.evaluate(context) for feature in features}

    def _resolve_coalition_values(
        self,
        row: Mapping[str, Any],
        features: Sequence[_Feature],
        subset: frozenset[str],
        actual_values: Mapping[str, Any],
        feature_player: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Resolve every feature for one coalition, walking dependency order.

        ``subset`` names the *players* in the coalition. A feature whose player
        is present takes its actual value; otherwise its baseline is evaluated
        against the row plus the already-resolved values of the features it
        references, so a dependent baseline sees the coalition-resolved sibling
        rather than the raw observed column. Grouped features share a player, so
        they enter and leave together.
        """
        resolved: dict[str, Any] = {}
        for feature in features:
            # Membership is tested on the feature's *player*, which is what
            # makes a group atomic: every member of a block flips together, so
            # only whole blocks are ever scored — the quotient game.
            # @cite: Aumann & Drèze, 1974; Owen, 1977
            player = feature_player[feature.name] if feature_player else feature.name
            if player in subset:
                resolved[feature.name] = actual_values[feature.name]
                continue
            # An absent feature falls back to an explicit, author-declared
            # reference value rather than a marginalized or conditional
            # expectation — i.e. baseline Shapley (BShap), extended here so the
            # reference may itself be a function of coalition-resolved siblings.
            # @cite: Sundararajan & Najmi, 2020
            context = build_row_context(row, resolved) if feature.baseline_deps else build_row_context(row)
            resolved[feature.name] = feature.baseline.evaluate(context)
        return resolved

    def _evaluate_prediction_formula(self, row: Mapping[str, Any], values: Mapping[str, Any]) -> float:
        return float(evaluate_expression(self.spec.prediction_expr, build_row_context(row, values)))

    def _row_scorer(
        self,
        row: Mapping[str, Any],
        features: Sequence[_Feature],
        feature_player: Mapping[str, str] | None = None,
    ):
        """Build a memoized coalition scorer for one row.

        Coalitions are subsets of the *player* names. The exact Shapley pass
        visits most coalitions many times, so caching by coalition keeps
        dependency-ordered resolution off the hot path.
        """
        actual_values = self._actual_values(row, features)
        target = float(self._evaluate_target(row))
        cache: dict[frozenset[str], float] = {}

        def score(subset: frozenset[str]) -> float:
            cached = cache.get(subset)
            if cached is None:
                values = self._resolve_coalition_values(row, features, subset, actual_values, feature_player)
                prediction = self._evaluate_prediction_formula(row, values)
                cached = _score(prediction, target, self.spec.score_mode)
                cache[subset] = cached
            return cached

        return score

    def _assess_row(self, score, names: list[str], *, exact: bool, max_exact_features: int, n_samples: int, seed: int) -> dict[str, float]:
        # `names` are players, so the exact-path cap is compared against the
        # player count: grouping shrinks it and can restore the exact path.
        # Cutting the exponent by grouping is groupShapley's stated motivation
        # @cite: Jullum et al., 2021
        if exact and len(names) <= max_exact_features:
            return self._exact_shapley(score, names)
        return self._sample_shapley(score, names, n_samples=n_samples, seed=seed)

    def _exact_shapley(self, score, names: list[str]) -> dict[str, float]:
        # Closed-form Shapley value computation @cite: Shapley, 1953
        # For each feature, sum weighted marginal contributions over all
        # coalitions — exact for small feature sets @cite: Lundberg & Lee, 2017
        n = len(names)
        factorial_n = math.factorial(n)
        values = {name: 0.0 for name in names}
        for name in names:
            others = [other for other in names if other != name]
            for subset_size in range(len(others) + 1):
                # Shapley weight: |S|! * (n - |S| - 1)! / n! @cite: Shapley, 1953
                weight = math.factorial(subset_size) * math.factorial(n - subset_size - 1) / factorial_n
                for subset in itertools.combinations(others, subset_size):
                    coalition = frozenset(subset)
                    values[name] += weight * (score(coalition | {name}) - score(coalition))
        return values

    def _sample_shapley(self, score, names: list[str], *, n_samples: int, seed: int) -> dict[str, float]:
        # Monte-Carlo permutation sampling approximation of Shapley values
        # @cite: Lundberg & Lee, 2017 — used when the feature count exceeds
        # max_exact_features.
        rng = random.Random(seed)
        values = {name: 0.0 for name in names}
        for _ in range(max(1, n_samples)):
            order = names[:]
            rng.shuffle(order)
            coalition: set[str] = set()
            previous = score(frozenset())
            for name in order:
                coalition.add(name)
                current = score(frozenset(coalition))
                values[name] += current - previous
                previous = current
        scale = 1.0 / max(1, n_samples)
        return {name: value * scale for name, value in values.items()}
