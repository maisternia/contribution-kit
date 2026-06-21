"""Estimator API for error attribution."""

from __future__ import annotations

import csv
import itertools
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .expr import build_row_context, evaluate_expression
from .results import AssessmentResult, FeatureAttribution
from .spec import AttributionSpec


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
    return prediction - target if score_mode == "signed_error" else abs(prediction - target)


@dataclass(slots=True)
class Estimator:
    rows: list[dict[str, Any]]
    spec: AttributionSpec

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

    def assess(self, *, exact: bool = True, max_exact_features: int = 12, n_samples: int = 512, seed: int = 0) -> AssessmentResult:
        self._validate_spec()
        totals = {hypothesis.name: 0.0 for hypothesis in self.spec.hypotheses}
        abs_totals = {hypothesis.name: 0.0 for hypothesis in self.spec.hypotheses}
        observed_error_total = 0.0
        for row in self.rows:
            row_result = self._assess_row(row, exact=exact, max_exact_features=max_exact_features, n_samples=n_samples, seed=seed)
            prediction = float(self._evaluate_prediction(row, self._actual_values(row)))
            target = float(self._evaluate_target(row))
            observed_error_total += _score(prediction, target, self.spec.score_mode)
            for name, value in row_result.items():
                totals[name] += value
                abs_totals[name] += abs(value)
        n_rows = len(self.rows)
        feature_rows = []
        for hypothesis in self.spec.hypotheses:
            signed_total = totals[hypothesis.name]
            feature_rows.append(
                FeatureAttribution(
                    name=hypothesis.name,
                    label=hypothesis.label or hypothesis.name,
                    mean_abs_shapley=abs_totals[hypothesis.name] / n_rows if n_rows else 0.0,
                    mean_signed_shapley=signed_total / n_rows if n_rows else 0.0,
                    total_signed_shapley=signed_total,
                    net_error_share_pct=(signed_total / observed_error_total * 100.0) if observed_error_total else 0.0,
                )
            )
        feature_rows.sort(key=lambda row: row.net_error_share_pct, reverse=True)
        return AssessmentResult(feature_attributions=feature_rows, n_rows=n_rows, mean_observed_error=observed_error_total / n_rows if n_rows else 0.0, metadata={"exact": exact, "n_samples": n_samples, "seed": seed})

    def _validate_spec(self) -> None:
        if not self.spec.hypotheses:
            raise ValueError("At least one hypothesis is required")
        names = [hypothesis.name for hypothesis in self.spec.hypotheses]
        if len(names) != len(set(names)):
            raise ValueError("Hypothesis names must be unique")

    def _evaluate_target(self, row: Mapping[str, Any]) -> Any:
        return evaluate_expression(self.spec.target_expr, build_row_context(row))

    def _actual_values(self, row: Mapping[str, Any]) -> dict[str, Any]:
        return {hypothesis.name: evaluate_expression(hypothesis.actual_expr, build_row_context(row)) for hypothesis in self.spec.hypotheses}

    def _baseline_values(self, row: Mapping[str, Any]) -> dict[str, Any]:
        return {hypothesis.name: evaluate_expression(hypothesis.baseline_expr, build_row_context(row)) for hypothesis in self.spec.hypotheses}

    def _evaluate_prediction(self, row: Mapping[str, Any], values: Mapping[str, Any]) -> float:
        return float(evaluate_expression(self.spec.prediction_expr, build_row_context(row, values)))

    def _coalition_score(self, row: Mapping[str, Any], subset: frozenset[str]) -> float:
        actual = self._actual_values(row)
        baseline = self._baseline_values(row)
        mixed = {name: actual[name] if name in subset else baseline[name] for name in actual}
        prediction = self._evaluate_prediction(row, mixed)
        target = float(self._evaluate_target(row))
        return _score(prediction, target, self.spec.score_mode)

    def _assess_row(self, row: Mapping[str, Any], *, exact: bool, max_exact_features: int, n_samples: int, seed: int) -> dict[str, float]:
        names = [hypothesis.name for hypothesis in self.spec.hypotheses]
        if exact and len(names) <= max_exact_features:
            return self._exact_shapley(row, names)
        return self._sample_shapley(row, names, n_samples=n_samples, seed=seed)

    def _exact_shapley(self, row: Mapping[str, Any], names: list[str]) -> dict[str, float]:
        n = len(names)
        factorial_n = math.factorial(n)
        values = {name: 0.0 for name in names}
        for name in names:
            others = [other for other in names if other != name]
            for subset_size in range(len(others) + 1):
                weight = math.factorial(subset_size) * math.factorial(n - subset_size - 1) / factorial_n
                for subset in itertools.combinations(others, subset_size):
                    coalition = frozenset(subset)
                    values[name] += weight * (self._coalition_score(row, coalition | {name}) - self._coalition_score(row, coalition))
        return values

    def _sample_shapley(self, row: Mapping[str, Any], names: list[str], *, n_samples: int, seed: int) -> dict[str, float]:
        rng = random.Random(seed)
        values = {name: 0.0 for name in names}
        for _ in range(max(1, n_samples)):
            order = names[:]
            rng.shuffle(order)
            coalition: set[str] = set()
            previous = self._coalition_score(row, frozenset())
            for name in order:
                coalition.add(name)
                current = self._coalition_score(row, frozenset(coalition))
                values[name] += current - previous
                previous = current
        scale = 1.0 / max(1, n_samples)
        return {name: value * scale for name, value in values.items()}
