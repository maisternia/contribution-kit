"""Result objects and exports."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FeatureAttribution:
    name: str
    label: str
    mean_abs_shapley: float
    mean_signed_shapley: float
    total_signed_shapley: float
    net_error_share_pct: float


@dataclass(slots=True)
class AssessmentResult:
    feature_attributions: list[FeatureAttribution]
    n_rows: int
    mean_observed_error: float
    metadata: dict[str, Any] = field(default_factory=dict)

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
        lines.append("")
        lines.append(f"Rows: {self.n_rows}")
        lines.append(f"Mean observed error: {self.mean_observed_error:.6f}")
        return "\n".join(lines)

    def to_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "feature_attributions": [asdict(row) for row in self.feature_attributions],
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
