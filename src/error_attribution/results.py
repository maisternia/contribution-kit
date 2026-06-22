"""Result objects and exports."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .hypothesis import BinaryHypothesisResult


@dataclass(slots=True)
class FeatureAttribution:
    name: str
    label: str
    mean_abs_shapley: float
    mean_signed_shapley: float
    total_signed_shapley: float
    net_error_share_pct: float


@dataclass(slots=True)
class ErrorRegimeSummary:
    name: str
    count: int
    mean_error: float
    total_error: float
    error_share_pct: float


@dataclass(slots=True)
class HypothesisAssessment:
    """Unified per-hypothesis assessment.

    Each input hypothesis produces exactly one assessment. ``analysis`` is either
    ``"feature"`` (a Shapley contribution to the prediction-formula error) or
    ``"regime"`` (an error-share plus mismatch-risk view of the rows matching the
    condition). Only the sub-results that apply are populated.
    """

    name: str
    label: str
    analysis: str
    feature: FeatureAttribution | None = None
    regime: ErrorRegimeSummary | None = None
    risk: BinaryHypothesisResult | None = None


@dataclass(slots=True)
class AssessmentResult:
    hypotheses: list[HypothesisAssessment]
    n_rows: int
    mean_observed_error: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_attributions(self) -> list[FeatureAttribution]:
        features = [item.feature for item in self.hypotheses if item.feature is not None]
        return sorted(features, key=lambda row: row.net_error_share_pct, reverse=True)

    @property
    def regime_summaries(self) -> list[ErrorRegimeSummary]:
        return [item.regime for item in self.hypotheses if item.regime is not None]

    @property
    def binary_results(self) -> list[BinaryHypothesisResult]:
        return [item.risk for item in self.hypotheses if item.risk is not None]

    def to_csv(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        records = [asdict(row) for row in self.feature_attributions]
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()) if records else ["name", "label", "mean_abs_shapley", "mean_signed_shapley", "total_signed_shapley", "net_error_share_pct"])
            writer.writeheader()
            writer.writerows(records)

    def to_markdown(self) -> str:
        lines = [
            "| name | label | mean_abs_shapley | mean_signed_shapley | total_signed_shapley | net_error_share_pct |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for row in self.feature_attributions:
            lines.append(
                f"| {row.name} | {row.label} | {row.mean_abs_shapley:.6f} | {row.mean_signed_shapley:.6f} | {row.total_signed_shapley:.6f} | {row.net_error_share_pct:.2f} |"
            )

        regimes = self.regime_summaries
        if regimes:
            lines.append("")
            lines.append("| regime | count | mean_error | total_error | error_share_pct |")
            lines.append("|---|---:|---:|---:|---:|")
            for regime in regimes:
                lines.append(
                    f"| {regime.name} | {regime.count} | {regime.mean_error:.4f} | {regime.total_error:.2f} | {regime.error_share_pct:.2f} |"
                )

        risks = self.binary_results
        if risks:
            lines.append("")
            lines.append("| hypothesis | match mismatch rate | rest mismatch rate | risk ratio | odds ratio |")
            lines.append("|---|---:|---:|---:|---:|")
            for risk in risks:
                rr = "inf" if risk.risk_ratio == float("inf") else f"{risk.risk_ratio:.2f}"
                lines.append(
                    f"| {risk.test_name} | {risk.mismatch_rate_a_pct:.2f}% ({risk.mismatch_count_a}/{risk.total_count_a}) | "
                    f"{risk.mismatch_rate_b_pct:.2f}% ({risk.mismatch_count_b}/{risk.total_count_b}) | {rr} | {risk.odds_ratio:.2f} |"
                )

        lines.append("")
        lines.append(f"Rows: {self.n_rows}")
        lines.append(f"Mean observed error: {self.mean_observed_error:.6f}")
        lines.append("")
        lines.append("---")
        lines.append("**References**")
        lines.append(
            "Shapley values: Shapley (1953) *A value for n-person games*, Princeton UP; "
            "Lundberg & Lee (2017) *A unified approach to interpreting model predictions*, NeurIPS 30."
        )
        lines.append(
            "Risk ratio CI: Katz et al. (1978) *Biometrics* 34(3):469-474. "
            "Odds ratio CI: Haldane (1956) *Ann. Hum. Genet.* 20(4):309-311; "
            "Anscombe (1956) *Biometrika* 43(3-4):461-464; "
            "Agresti (2013) *Categorical Data Analysis* (3rd ed.), Wiley."
        )
        return "\n".join(lines)

    def to_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "hypotheses": [asdict(item) for item in self.hypotheses],
                    "feature_attributions": [asdict(row) for row in self.feature_attributions],
                    "regime_summaries": [asdict(row) for row in self.regime_summaries],
                    "binary_results": [asdict(row) for row in self.binary_results],
                    "n_rows": self.n_rows,
                    "mean_observed_error": self.mean_observed_error,
                    "metadata": self.metadata,
                },
                handle,
                indent=2,
                sort_keys=True,
            )

    def save(self, out_dir: str | Path) -> None:
        target = Path(out_dir)
        target.mkdir(parents=True, exist_ok=True)
        self.to_csv(target / "contribution.csv")
        self.to_json(target / "run.json")
        (target / "report.md").write_text(self.to_markdown(), encoding="utf-8")
