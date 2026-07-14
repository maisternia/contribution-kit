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

from .expr import CompiledExpression, build_row_context, compile_expression, evaluate_expression, free_variables
from .hypothesis import BinaryHypothesisResult, evaluate_binary_hypothesis
from .results import (
    AssessmentResult,
    BurdenRankingEntry,
    BurdenRankingResult,
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
from .stats import risk_difference_with_guardrail


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
    """A compiled formula feature defined by explicit actual/baseline expressions."""

    name: str
    label: str
    actual: CompiledExpression
    baseline: CompiledExpression


@dataclass(slots=True)
class _FactorialPlan:
    label: str
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

        generated_hypotheses, factorial_plans, partition_warnings = self._expand_factorials()
        effective_hypotheses = [*self.spec.hypotheses, *generated_hypotheses]

        features = self._formula_features()
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
        for feature_name, feature_spec in self.spec.prediction_features.items():
            feature_result = feature_attr[feature_name]
            assessments.append(
                HypothesisAssessment(
                    name=feature_name,
                    label=feature_spec.label or feature_name,
                    analysis="feature",
                    feature=feature_result,
                )
            )
        for hypothesis in effective_hypotheses:
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
        burden_rankings = self._build_burden_rankings(factorial_plans, mismatch_fn, partition_warnings)

        return AssessmentResult(
            hypotheses=assessments,
            n_rows=n_rows,
            mean_observed_contribution=observed_contribution_total / n_rows if n_rows else 0.0,
            factorial_matrices=factorial_matrices,
            contrast_results=contrast_results,
            partition_warnings=partition_warnings,
            burden_rankings=burden_rankings,
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

    def _formula_features(self) -> list[_Feature]:
        assert self.spec is not None
        features: list[_Feature] = []
        for feature_name, feature_spec in self.spec.prediction_features.items():
            features.append(
                _Feature(
                    name=feature_name,
                    label=feature_spec.label or feature_name,
                    actual=compile_expression(feature_spec.actual),
                    baseline=compile_expression(feature_spec.baseline),
                )
            )
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
        names = [hypothesis.name for hypothesis in self.spec.hypotheses]
        if len(names) != len(set(names)):
            raise ValueError("Hypothesis names must be unique")
        colliding_names = sorted(set(names).intersection(declared_features))
        if colliding_names:
            raise ValueError(
                "prediction_features names must not collide with hypothesis names: "
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

    def _expand_factorials(self) -> tuple[list[Hypothesis], list[_FactorialPlan], list[PartitionWarning]]:
        assert self.spec is not None
        if not self.spec.factorials:
            return [], [], []

        declared_names = {hypothesis.name for hypothesis in self.spec.hypotheses}
        generated_names: set[str] = set()
        generated_hypotheses: list[Hypothesis] = []
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
                row_level_matches[level_name] = [bool(compiled.evaluate(build_row_context(row))) for row in self.rows]

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
                column_level_matches[level_name] = [bool(compiled.evaluate(build_row_context(row))) for row in self.rows]

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
                    generated_hypotheses.append(Hypothesis(name=name, condition=condition))
                    cell_names[(row_level, column_level)] = name
                    cell_masks[(row_level, column_level)] = [
                        row_match and column_match
                        for row_match, column_match in zip(row_matches, column_matches)
                    ]

            plans.append(
                _FactorialPlan(
                    label=effective_label,
                    row_levels=row_levels,
                    column_levels=column_levels,
                    cell_names=cell_names,
                    cell_masks=cell_masks,
                    baseline=(crossing.baseline["rows"], crossing.baseline["columns"]) if crossing.baseline else None,
                )
            )

        return generated_hypotheses, plans, partition_warnings

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
            matrix = FactorialMatrixResult(label=plan.label)
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
