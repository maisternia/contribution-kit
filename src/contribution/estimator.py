"""Estimator API for factor-contribution analysis."""

from __future__ import annotations

import csv
import itertools
import math
import random
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .expr import CompiledExpression, build_row_context, compile_expression, evaluate_expression, split_equality
from .hypothesis import BinaryHypothesisResult, evaluate_binary_hypothesis
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
from .spec import AttributionSpec, Hypothesis


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
    """A formula feature derived from an ``actual == baseline`` hypothesis."""

    name: str
    label: str
    actual: CompiledExpression
    baseline: CompiledExpression


@dataclass(slots=True)
class _FactorialPlan:
    rows_axis: str
    columns_axis: str
    row_levels: list[str]
    column_levels: list[str]
    cell_names: dict[tuple[str, str], str]
    cell_masks: dict[tuple[str, str], list[bool]]


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

        generated_hypotheses, factorial_plans, partition_warnings = self._expand_factorials()
        effective_hypotheses = [*self.spec.hypotheses, *generated_hypotheses]

        features = self._formula_features(effective_hypotheses)
        feature_names = [feature.name for feature in features]

        totals = {name: 0.0 for name in feature_names}
        abs_totals = {name: 0.0 for name in feature_names}
        observed_contributions: list[float] = []
        observed_contribution_total = 0.0
        for row in self.rows:
            if feature_names:
                row_result = self._assess_row(row, features, exact=exact, max_exact_features=max_exact_features, n_samples=n_samples, seed=seed)
                for name, value in row_result.items():
                    totals[name] += value
                    abs_totals[name] += abs(value)
            observed_contribution = self._observed_contribution(row, features)
            observed_contributions.append(observed_contribution)
            observed_contribution_total += observed_contribution

        n_rows = len(self.rows)
        feature_attr: dict[str, FeatureAttribution] = {}
        for feature in features:
            signed_total = totals[feature.name]
            feature_attr[feature.name] = FeatureAttribution(
                name=feature.name,
                label=feature.label,
                mean_abs_shapley=abs_totals[feature.name] / n_rows if n_rows else 0.0,
                mean_signed_shapley=signed_total / n_rows if n_rows else 0.0,
                total_signed_shapley=signed_total,
                net_contribution_share_pct=(signed_total / observed_contribution_total * 100.0) if observed_contribution_total else 0.0,
            )

        mismatch_fn = self._mismatch_fn()
        assessments: list[HypothesisAssessment] = []
        for hypothesis in effective_hypotheses:
            if hypothesis.name in feature_attr:
                assessments.append(
                    HypothesisAssessment(
                        name=hypothesis.name,
                        label=hypothesis.label or hypothesis.name,
                        analysis="feature",
                        feature=feature_attr[hypothesis.name],
                    )
                )
            else:
                assessments.append(
                    HypothesisAssessment(
                        name=hypothesis.name,
                        label=hypothesis.label or hypothesis.name,
                        analysis="regime",
                        regime=self._regime_summary(hypothesis, observed_contributions, observed_contribution_total),
                        risk=self._regime_risk(hypothesis, mismatch_fn, ci_method=ci_method),
                    )
                )

        factorial_matrices = self._build_factorial_matrices(factorial_plans, mismatch_fn, ci_method=ci_method)
        contrast_results = self._build_contrast_results(factorial_plans, mismatch_fn, ci_method=ci_method)

        return AssessmentResult(
            hypotheses=assessments,
            n_rows=n_rows,
            mean_observed_contribution=observed_contribution_total / n_rows if n_rows else 0.0,
            factorial_matrices=factorial_matrices,
            contrast_results=contrast_results,
            partition_warnings=partition_warnings,
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

    def _formula_features(self, hypotheses: Sequence[Hypothesis]) -> list[_Feature]:
        assert self.spec is not None
        features: list[_Feature] = []
        for hypothesis in hypotheses:
            split = split_equality(compile_expression(hypothesis.condition))
            if split is None:
                continue
            actual, baseline = split
            features.append(_Feature(name=hypothesis.name, label=hypothesis.label or hypothesis.name, actual=actual, baseline=baseline))
        return features

    def _regime_summary(self, hypothesis: Hypothesis, observed_contributions: Sequence[float], observed_contribution_total: float) -> RegimeSummary:
        predicate = compile_expression(hypothesis.condition)
        group_total_contribution = 0.0
        count = 0
        for row, observed_contribution in zip(self.rows, observed_contributions):
            if bool(predicate.evaluate(build_row_context(row))):
                group_total_contribution += observed_contribution
                count += 1
        return RegimeSummary(
            name=hypothesis.name,
            count=count,
            mean_contribution=(group_total_contribution / count) if count else 0.0,
            total_contribution=group_total_contribution,
            contribution_share_pct=(group_total_contribution / observed_contribution_total * 100.0) if observed_contribution_total else 0.0,
        )

    def _regime_risk(self, hypothesis: Hypothesis, mismatch_fn, *, ci_method: str) -> BinaryHypothesisResult | None:
        assert self.spec is not None
        if mismatch_fn is None:
            return None
        predicate = compile_expression(hypothesis.condition)
        matches = [bool(predicate.evaluate(build_row_context(row))) for row in self.rows]
        return self._evaluate_binary_from_masks(
            test_name=hypothesis.name,
            group_a_label=hypothesis.label or hypothesis.name,
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
        if not self.spec.hypotheses:
            raise ValueError("At least one hypothesis is required")
        names = [hypothesis.name for hypothesis in self.spec.hypotheses]
        if len(names) != len(set(names)):
            raise ValueError("Hypothesis names must be unique")
        for axis_name, factor in self.spec.factors.items():
            if not factor.levels:
                raise ValueError(f"factor '{axis_name}' must declare at least one level")
        used_axes: set[str] = set()
        for crossing in self.spec.factorials:
            for axis_name in (crossing.rows, crossing.columns):
                used_axes.add(axis_name)
                if axis_name not in self.spec.factors:
                    raise ValueError(f"factorial references unknown axis '{axis_name}'")
        unused_axes = sorted(set(self.spec.factors).difference(used_axes))
        if unused_axes:
            warnings.warn(
                "Declared factors are unused by any factorial crossing: " + ", ".join(unused_axes),
                stacklevel=2,
            )

    def _expand_factorials(self) -> tuple[list[Hypothesis], list[_FactorialPlan], list[PartitionWarning]]:
        assert self.spec is not None
        if not self.spec.factorials:
            return [], [], []

        axis_membership: dict[str, dict[str, list[bool]]] = {}
        partition_warnings: list[PartitionWarning] = []
        used_axes = {crossing.rows for crossing in self.spec.factorials}.union({crossing.columns for crossing in self.spec.factorials})
        for axis_name in sorted(used_axes):
            factor = self.spec.factors[axis_name]
            level_matches: dict[str, list[bool]] = {}
            for level_name, condition in factor.levels.items():
                compiled = compile_expression(condition)
                level_matches[level_name] = [bool(compiled.evaluate(build_row_context(row))) for row in self.rows]
            axis_membership[axis_name] = level_matches
            overlap_count = 0
            gap_count = 0
            for row_index in range(len(self.rows)):
                match_count = sum(1 for matches in level_matches.values() if matches[row_index])
                if match_count > 1:
                    overlap_count += 1
                elif match_count == 0:
                    gap_count += 1
            if overlap_count or gap_count:
                warnings.warn(
                    f"factor axis '{axis_name}' is not a strict partition: overlap_rows={overlap_count}, gap_rows={gap_count}",
                    stacklevel=2,
                )
                partition_warnings.append(
                    PartitionWarning(axis=axis_name, overlap_count=overlap_count, gap_count=gap_count)
                )

        declared_names = {hypothesis.name for hypothesis in self.spec.hypotheses}
        generated_names: set[str] = set()
        generated_hypotheses: list[Hypothesis] = []
        plans: list[_FactorialPlan] = []
        for crossing in self.spec.factorials:
            row_factor = self.spec.factors[crossing.rows]
            col_factor = self.spec.factors[crossing.columns]
            row_levels = list(row_factor.levels)
            column_levels = list(col_factor.levels)
            cell_names: dict[tuple[str, str], str] = {}
            cell_masks: dict[tuple[str, str], list[bool]] = {}
            for row_level in row_levels:
                row_condition = row_factor.levels[row_level]
                row_matches = axis_membership[crossing.rows][row_level]
                for column_level in column_levels:
                    column_condition = col_factor.levels[column_level]
                    column_matches = axis_membership[crossing.columns][column_level]
                    name = f"{row_level} & {column_level}"
                    if name in declared_names or name in generated_names:
                        raise ValueError(f"Generated factorial cell name collision: '{name}'")
                    generated_names.add(name)
                    condition = f"({row_condition}) and ({column_condition})"
                    generated_hypotheses.append(Hypothesis(name=name, condition=condition))
                    cell_names[(row_level, column_level)] = name
                    cell_masks[(row_level, column_level)] = [
                        row_match and column_match
                        for row_match, column_match in zip(row_matches, column_matches)
                    ]
            plans.append(
                _FactorialPlan(
                    rows_axis=crossing.rows,
                    columns_axis=crossing.columns,
                    row_levels=row_levels,
                    column_levels=column_levels,
                    cell_names=cell_names,
                    cell_masks=cell_masks,
                )
            )
        return generated_hypotheses, plans, partition_warnings

    def _mask_mismatch_stats(self, mask: Sequence[bool], mismatch_fn) -> tuple[int, float]:
        rows = [row for row, matched in zip(self.rows, mask) if matched]
        count = len(rows)
        mismatch_count = sum(1 for row in rows if mismatch_fn(row))
        mismatch_rate = (mismatch_count / count * 100.0) if count else 0.0
        return count, mismatch_rate

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
            matrix = FactorialMatrixResult(rows_axis=plan.rows_axis, columns_axis=plan.columns_axis)
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
            factorial_name = f"{plan.rows_axis} x {plan.columns_axis}"
            for row_level in plan.row_levels:
                for level_a, level_b in itertools.combinations(plan.column_levels, 2):
                    risk = self._evaluate_binary_from_masks(
                        test_name=f"{factorial_name}: {row_level} [{level_a} vs {level_b}]",
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
                            factorial=factorial_name,
                            stratum=f"{factorial_name} :: {plan.rows_axis}={row_level}",
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
                        test_name=f"{factorial_name}: {column_level} [{level_a} vs {level_b}]",
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
                            factorial=factorial_name,
                            stratum=f"{factorial_name} :: {plan.columns_axis}={column_level}",
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

    def _evaluate_target(self, row: Mapping[str, Any]) -> Any:
        return evaluate_expression(self.spec.target, build_row_context(row))

    def _evaluate_prediction_observed(self, row: Mapping[str, Any]) -> Any:
        return evaluate_expression(self.spec.prediction, build_row_context(row))

    def _feature_values(self, row: Mapping[str, Any], features: Sequence[_Feature], *, actual: bool) -> dict[str, Any]:
        context = build_row_context(row)
        return {feature.name: (feature.actual if actual else feature.baseline).evaluate(context) for feature in features}

    def _evaluate_prediction_formula(self, row: Mapping[str, Any], values: Mapping[str, Any]) -> float:
        return float(evaluate_expression(self.spec.prediction_expr, build_row_context(row, values)))

    def _coalition_score(self, row: Mapping[str, Any], features: Sequence[_Feature], subset: frozenset[str]) -> float:
        actual = self._feature_values(row, features, actual=True)
        baseline = self._feature_values(row, features, actual=False)
        mixed = {name: actual[name] if name in subset else baseline[name] for name in actual}
        prediction = self._evaluate_prediction_formula(row, mixed)
        target = float(self._evaluate_target(row))
        return _score(prediction, target, self.spec.score_mode)

    def _assess_row(self, row: Mapping[str, Any], features: Sequence[_Feature], *, exact: bool, max_exact_features: int, n_samples: int, seed: int) -> dict[str, float]:
        names = [feature.name for feature in features]
        if exact and len(names) <= max_exact_features:
            return self._exact_shapley(row, features, names)
        return self._sample_shapley(row, features, names, n_samples=n_samples, seed=seed)

    def _exact_shapley(self, row: Mapping[str, Any], features: Sequence[_Feature], names: list[str]) -> dict[str, float]:
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
                    values[name] += weight * (self._coalition_score(row, features, coalition | {name}) - self._coalition_score(row, features, coalition))
        return values

    def _sample_shapley(self, row: Mapping[str, Any], features: Sequence[_Feature], names: list[str], *, n_samples: int, seed: int) -> dict[str, float]:
        # Monte-Carlo permutation sampling approximation of Shapley values
        # @cite: Lundberg & Lee, 2017 — used when the feature count exceeds
        # max_exact_features.
        rng = random.Random(seed)
        values = {name: 0.0 for name in names}
        for _ in range(max(1, n_samples)):
            order = names[:]
            rng.shuffle(order)
            coalition: set[str] = set()
            previous = self._coalition_score(row, features, frozenset())
            for name in order:
                coalition.add(name)
                current = self._coalition_score(row, features, frozenset(coalition))
                values[name] += current - previous
                previous = current
        scale = 1.0 / max(1, n_samples)
        return {name: value * scale for name, value in values.items()}
