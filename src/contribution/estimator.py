"""Estimator API for contribution attribution."""

from __future__ import annotations

import csv
import itertools
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .expr import CompiledExpression, build_row_context, compile_expression, evaluate_expression, split_equality
from .hypothesis import BinaryHypothesisResult, evaluate_binary_hypothesis
from .results import AssessmentResult, RegimeSummary, FeatureAttribution, HypothesisAssessment
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

    def assess(self, *, spec: AttributionSpec | None = None, exact: bool = True, max_exact_features: int = 12, n_samples: int = 512, seed: int = 0) -> AssessmentResult:
        if spec is not None:
            self.spec = spec
        self._validate_spec()
        assert self.spec is not None

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
        for hypothesis in self.spec.hypotheses:
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
                        risk=self._regime_risk(hypothesis, mismatch_fn),
                    )
                )

        return AssessmentResult(
            hypotheses=assessments,
            n_rows=n_rows,
            mean_observed_contribution=observed_contribution_total / n_rows if n_rows else 0.0,
            metadata={"exact": exact, "n_samples": n_samples, "seed": seed},
        )

    def _formula_features(self) -> list[_Feature]:
        assert self.spec is not None
        features: list[_Feature] = []
        for hypothesis in self.spec.hypotheses:
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

    def _regime_risk(self, hypothesis: Hypothesis, mismatch_fn) -> BinaryHypothesisResult | None:
        assert self.spec is not None
        if mismatch_fn is None:
            return None
        predicate = compile_expression(hypothesis.condition)
        matches = [bool(predicate.evaluate(build_row_context(row))) for row in self.rows]
        group_a_rows = [row for row, matched in zip(self.rows, matches) if matched]
        group_b_rows = [row for row, matched in zip(self.rows, matches) if not matched]
        if not group_a_rows or not group_b_rows:
            return None
        return evaluate_binary_hypothesis(
            scope=self.spec.scope,
            test_name=hypothesis.name,
            group_a_label=hypothesis.label or hypothesis.name,
            group_b_label="rest",
            group_a_rows=group_a_rows,
            group_b_rows=group_b_rows,
            mismatch_fn=mismatch_fn,
        )

    def _mismatch_fn(self):
        assert self.spec is not None
        if self.spec.mismatch_expr is None:
            return None
        mismatch = compile_expression(self.spec.mismatch_expr)

        def predicate(row: Mapping[str, Any]) -> bool:
            return bool(mismatch.evaluate(build_row_context(row)))

        return predicate

    def _observed_contribution(self, row: Mapping[str, Any], features: Sequence[_Feature]) -> float:
        assert self.spec is not None
        prediction = float(self._evaluate_prediction(row, self._feature_values(row, features, actual=True)))
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

    def _evaluate_target(self, row: Mapping[str, Any]) -> Any:
        return evaluate_expression(self.spec.target_expr, build_row_context(row))

    def _feature_values(self, row: Mapping[str, Any], features: Sequence[_Feature], *, actual: bool) -> dict[str, Any]:
        context = build_row_context(row)
        return {feature.name: (feature.actual if actual else feature.baseline).evaluate(context) for feature in features}

    def _evaluate_prediction(self, row: Mapping[str, Any], values: Mapping[str, Any]) -> float:
        return float(evaluate_expression(self.spec.prediction_expr, build_row_context(row, values)))

    def _coalition_score(self, row: Mapping[str, Any], features: Sequence[_Feature], subset: frozenset[str]) -> float:
        actual = self._feature_values(row, features, actual=True)
        baseline = self._feature_values(row, features, actual=False)
        mixed = {name: actual[name] if name in subset else baseline[name] for name in actual}
        prediction = self._evaluate_prediction(row, mixed)
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
