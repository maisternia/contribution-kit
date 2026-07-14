"""Result objects and exports."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .hypothesis import BinaryHypothesisResult


def _format_effect_ci(value: float, ci_low: float | None, ci_high: float | None) -> str:
    """Format an effect size with its confidence interval as ``value (low to high)``.

    Matches the Prism-style reporting of a point estimate alongside its range. When
    the value is infinite or a CI bound is unavailable the range is reported as n/a.
    """

    point = "inf" if value == float("inf") else f"{value:.2f}"
    if ci_low is None or ci_high is None or value == float("inf"):
        return f"{point} (n/a)"
    return f"{point} ({ci_low:.2f} to {ci_high:.2f})"


def _format_mismatch_split(mismatch_count: int, total_count: int) -> str:
    """Render mismatch and non-mismatch counts as ``mismatch:non_mismatch``."""

    matched_count = max(total_count - mismatch_count, 0)
    return f"{mismatch_count}:{matched_count}"


def _format_rr(value: float | None, ci_low: float | None, ci_high: float | None) -> str:
    if value is None:
        return "n/a"
    point = "inf" if value == float("inf") else f"{value:.2f}"
    if ci_low is None or ci_high is None or value == float("inf"):
        return f"{point} (n/a)"
    return f"{point} ({ci_low:.2f} to {ci_high:.2f})"


def _format_rd(value: float, ci_low: float | None, ci_high: float | None) -> str:
    if ci_low is None or ci_high is None:
        return f"{value:.3f} (n/a)"
    return f"{value:.3f} ({ci_low:.3f} to {ci_high:.3f})"



@dataclass(slots=True)
class FeatureAttribution:
    name: str
    label: str
    mean_abs_shapley: float
    mean_signed_shapley: float
    total_signed_shapley: float
    net_contribution_share_pct: float

    @property
    def net_error_share_pct(self) -> float:
        """Backward-compatible alias for pre-v0.2 naming."""
        return self.net_contribution_share_pct


@dataclass(slots=True)
class RegimeSummary:
    name: str
    count: int
    mean_contribution: float
    total_contribution: float
    contribution_share_pct: float

    @property
    def mean_error(self) -> float:
        """Backward-compatible alias for pre-v0.2 naming."""
        return self.mean_contribution

    @property
    def total_error(self) -> float:
        """Backward-compatible alias for pre-v0.2 naming."""
        return self.total_contribution

    @property
    def error_share_pct(self) -> float:
        """Backward-compatible alias for pre-v0.2 naming."""
        return self.contribution_share_pct


@dataclass(slots=True)
class HypothesisAssessment:
    """Unified per-hypothesis assessment.

    Each input hypothesis produces exactly one assessment. ``analysis`` is either
    ``"feature"`` (a Shapley contribution to the prediction-formula outcome) or
    ``"regime"`` (a contribution-share plus mismatch-risk view of the rows matching the
    condition). Only the sub-results that apply are populated.
    """

    name: str
    label: str
    analysis: str
    feature: FeatureAttribution | None = None
    regime: RegimeSummary | None = None
    risk: BinaryHypothesisResult | None = None


@dataclass(slots=True)
class PartitionWarning:
    axis: str
    overlap_count: int
    gap_count: int


@dataclass(slots=True)
class FactorialCellResult:
    name: str
    row_level: str
    column_level: str
    count: int
    mismatch_rate_pct: float
    risk_ratio: float | None
    rr_ci_low: float | None
    rr_ci_high: float | None


@dataclass(slots=True)
class FactorialMarginalResult:
    level: str
    count: int
    mismatch_rate_pct: float
    risk_ratio: float | None
    rr_ci_low: float | None
    rr_ci_high: float | None


@dataclass(slots=True)
class FactorialMatrixResult:
    label: str
    cells: list[FactorialCellResult] = field(default_factory=list)
    row_marginals: list[FactorialMarginalResult] = field(default_factory=list)
    column_marginals: list[FactorialMarginalResult] = field(default_factory=list)


@dataclass(slots=True)
class ContrastResult:
    factorial: str
    stratum: str
    level_a: str
    level_b: str
    mismatch_rate_a_pct: float
    mismatch_rate_b_pct: float
    mismatch_count_a: int
    total_count_a: int
    mismatch_count_b: int
    total_count_b: int
    risk_ratio: float
    rr_ci_low: float | None
    rr_ci_high: float | None
    odds_ratio: float
    or_ci_low: float
    or_ci_high: float


@dataclass(slots=True)
class BurdenRankingEntry:
    rank: int
    cell: str
    row_level: str
    column_level: str
    count: int
    mismatch_count: int
    mismatch_rate_pct: float
    baseline_rate_pct: float
    recoverable_mismatches: float | None
    share_total_mismatches_pct: float | None
    risk_difference: float
    rd_ci_low: float | None
    rd_ci_high: float | None
    cumulative_accuracy_if_eliminated_pct: float
    recoverable: bool


@dataclass(slots=True)
class BurdenRankingResult:
    crossing_label: str
    baseline_cell: str
    entries: list[BurdenRankingEntry] = field(default_factory=list)
    overlap_suppressed: bool = False
    coverage_gap_excluded_rows: int = 0
    baseline_sanity_warning: str | None = None
    observed_accuracy_pct: float = 0.0
    ceiling_accuracy_pct: float = 0.0
    total_mismatches: int = 0


@dataclass(slots=True)
class AssessmentResult:
    hypotheses: list[HypothesisAssessment]
    n_rows: int
    mean_observed_contribution: float
    metadata: dict[str, Any] = field(default_factory=dict)
    factorial_matrices: list[FactorialMatrixResult] = field(default_factory=list)
    contrast_results: list[ContrastResult] = field(default_factory=list)
    partition_warnings: list[PartitionWarning] = field(default_factory=list)
    burden_rankings: list[BurdenRankingResult] = field(default_factory=list)

    @property
    def mean_observed_error(self) -> float:
        """Backward-compatible alias for pre-v0.2 naming."""
        return self.mean_observed_contribution

    @property
    def feature_attributions(self) -> list[FeatureAttribution]:
        features = [item.feature for item in self.hypotheses if item.feature is not None]
        return sorted(features, key=lambda row: row.net_contribution_share_pct, reverse=True)

    @property
    def regime_summaries(self) -> list[RegimeSummary]:
        return [item.regime for item in self.hypotheses if item.regime is not None]

    @property
    def binary_results(self) -> list[BinaryHypothesisResult]:
        return [item.risk for item in self.hypotheses if item.risk is not None]

    def to_csv(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        records = [asdict(row) for row in self.feature_attributions]
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()) if records else ["name", "label", "mean_abs_shapley", "mean_signed_shapley", "total_signed_shapley", "net_contribution_share_pct"])
            writer.writeheader()
            writer.writerows(records)

    def _input_lines(self) -> list[str]:
        """Echo the analysis inputs, skipping any that are absent from metadata."""
        meta = self.metadata
        lines: list[str] = []
        target = meta.get("target")
        prediction = meta.get("prediction")
        prediction_expr = meta.get("prediction_expr")
        score_mode = meta.get("score_mode")
        if target:
            lines.append(f"- **Target (`target`):** `{target}`")
        if prediction:
            lines.append(f"- **Prediction (`prediction`):** `{prediction}`")
        if prediction_expr:
            lines.append(f"- **Shapley formula (`prediction_expr`):** `{prediction_expr}`")
        if score_mode:
            lines.append(f"- **Scoring mode:** {score_mode}")
        return lines

    def _shapley_formula(self) -> str | None:
        """Render the outcome formula that the Shapley values apportion."""
        meta = self.metadata
        target = meta.get("target")
        prediction_expr = meta.get("prediction_expr")
        if not prediction_expr or not target:
            return None
        if meta.get("score_mode") == "signed":
            return f"outcome = ({prediction_expr}) - ({target})"
        return f"outcome = |({prediction_expr}) - ({target})|"

    @staticmethod
    def _include_risk_row(risk: BinaryHypothesisResult) -> bool:
        """Hide degenerate baseline rows from the risk section."""
        return risk.mismatch_count_a > 0

    def to_markdown(self) -> str:
        lines: list[str] = ["# Factor-Contribution Analysis Report", ""]

        features = self.feature_attributions
        lines.append("## Shapley Value Contributions")
        lines.append("")
        lines.append(
            "How much each feature contributes to the gap between the formula output "
            "(`prediction_expr`) and the target (`target`). Bigger values mean that feature has "
            "a stronger influence on the final result."
        )
        meta = self.metadata
        target = meta.get("target")
        prediction = meta.get("prediction")
        prediction_expr = meta.get("prediction_expr")
        score_mode = meta.get("score_mode")
        formula = self._shapley_formula()
        shapley_inputs: list[str] = []
        if target:
            shapley_inputs.append(
                f"- Target (`target`): `{target}`"
            )
        if prediction_expr:
            shapley_inputs.append(
                f"- Shapley formula (`prediction_expr`): `{prediction_expr}`"
            )
        if score_mode:
            shapley_inputs.append(f"- Scoring mode (`score_mode`): `{score_mode}`")
        if formula is not None:
            shapley_inputs.append(
                f"- Formula apportioned across features: `{formula}`"
            )
        if shapley_inputs:
            lines.append("")
            lines.append("### Inputs")
            lines.append("")
            lines.extend(shapley_inputs)
        lines.append("")
        lines.append("| Feature | Description | Mean absolute | Mean signed | Total signed | Net share (%) |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for row in features:
            lines.append(
                f"| {row.name} | {row.label} | {row.mean_abs_shapley:.6f} | {row.mean_signed_shapley:.6f} | {row.total_signed_shapley:.6f} | {row.net_contribution_share_pct:.2f} |"
            )
        if features:
            top = features[0]
            lines.append("")
            lines.append(
                f"**In short:** `{top.name}` ({top.label}) carries the largest net contribution "
                f"share at {top.net_contribution_share_pct:.2f}%."
            )

        regimes = self.regime_summaries
        if regimes:
            lines.append("")
            lines.append("## Error Regimes")
            lines.append("")
            lines.append(
                "How much each condition (regime) contributes to the total observed prediction error. "
                "Here, prediction is the value from `prediction`, and target is the reference "
                "value from `target`. Share (%) shows what fraction of the total error comes "
                "from rows in that condition."
            )
            regime_inputs: list[str] = []
            if target:
                regime_inputs.append(
                    f"- Target (`target`): `{target}`"
                )
            if prediction:
                regime_inputs.append(
                    f"- Observed prediction (`prediction`): `{prediction}`"
                )
            if regime_inputs:
                lines.append("")
                lines.append("### Inputs")
                lines.append("")
                lines.extend(regime_inputs)
            lines.append("")
            lines.append("| Regime | Count | Mean contribution | Total contribution | Share (%) |")
            lines.append("|---|---:|---:|---:|---:|")
            for regime in regimes:
                lines.append(
                    f"| {regime.name} | {regime.count} | {regime.mean_contribution:.4f} | {regime.total_contribution:.2f} | {regime.contribution_share_pct:.2f} |"
                )
            top_regime = max(regimes, key=lambda r: r.contribution_share_pct)
            lines.append("")
            lines.append(
                f"**In short:** the `{top_regime.name}` regime accounts for the largest share "
                f"at {top_regime.contribution_share_pct:.2f}%."
            )

        risks = [risk for risk in self.binary_results if self._include_risk_row(risk)]
        if risks:
            lines.append("")
            lines.append("## Mismatch Risk")
            lines.append("")
            lines.append(
                "How much more often rows matching each condition have prediction different from "
                "target (`prediction != target`) compared with all other rows. A risk ratio above "
                "1 means the condition is linked to more mismatches."
            )
            if target or prediction:
                lines.append("")
                lines.append("### Inputs")
                lines.append("")
                if target:
                    lines.append(f"- Target (`target`): `{target}`")
                if prediction:
                    lines.append(f"- Observed prediction (`prediction`): `{prediction}`")
                lines.append("- Mismatch definition: `prediction != target`")
            lines.append("")
            lines.append("| Hypothesis | Regime mismatch rate | Rest mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |")
            lines.append("|---|---:|---:|---:|---:|")
            for risk in risks:
                rr = _format_effect_ci(risk.risk_ratio, risk.rr_ci_low, risk.rr_ci_high)
                or_ = _format_effect_ci(risk.odds_ratio, risk.or_ci_low, risk.or_ci_high)
                lines.append(
                    f"| {risk.test_name} | {risk.mismatch_rate_a_pct:.2f}% ({_format_mismatch_split(risk.mismatch_count_a, risk.total_count_a)}) | "
                    f"{risk.mismatch_rate_b_pct:.2f}% ({_format_mismatch_split(risk.mismatch_count_b, risk.total_count_b)}) | {rr} | {or_} |"
                )
            finite_risks = [risk for risk in risks if risk.risk_ratio != float("inf")]
            if finite_risks:
                top_risk = max(finite_risks, key=lambda r: r.risk_ratio)
                lines.append("")
                lines.append(
                    f"**In short:** `{top_risk.test_name}` carries the highest mismatch risk "
                    f"(risk ratio {top_risk.risk_ratio:.2f})."
                )

        if self.partition_warnings:
            lines.append("")
            lines.append("## Partition Warnings")
            lines.append("")
            lines.append(
                "Some factorial axes are not strict partitions over the loaded rows. "
                "Overlaps and gaps are reported below."
            )
            lines.append("")
            lines.append("| Axis | Overlap rows | Gap rows |")
            lines.append("|---|---:|---:|")
            for warning in self.partition_warnings:
                lines.append(f"| {warning.axis} | {warning.overlap_count} | {warning.gap_count} |")

        if self.factorial_matrices:
            lines.append("")
            lines.append("## Factorial Matrices")
            lines.append("")
            lines.append(
                "Each matrix cell reports row count, mismatch rate, and mismatch risk ratio versus "
                "the rest of the dataset. Row/column marginals are computed over unions of member cells."
            )
            for matrix in self.factorial_matrices:
                lines.append("")
                lines.append(f"### {matrix.label}")
                lines.append("")
                column_levels = [m.level for m in matrix.column_marginals]
                header = "| Row level | " + " | ".join(column_levels) + " | Row marginal |"
                lines.append(header)
                lines.append("|---|" + "|".join(["---" for _ in column_levels]) + "|---|")
                cell_lookup = {(cell.row_level, cell.column_level): cell for cell in matrix.cells}
                row_lookup = {marginal.level: marginal for marginal in matrix.row_marginals}
                for row_marginal in matrix.row_marginals:
                    row_cells: list[str] = []
                    for column_level in column_levels:
                        cell = cell_lookup[(row_marginal.level, column_level)]
                        row_cells.append(
                            f"n={cell.count}, mismatch={cell.mismatch_rate_pct:.2f}%, RR={_format_rr(cell.risk_ratio, cell.rr_ci_low, cell.rr_ci_high)}"
                        )
                    marginal = row_lookup[row_marginal.level]
                    marginal_text = (
                        f"n={marginal.count}, mismatch={marginal.mismatch_rate_pct:.2f}%, "
                        f"RR={_format_rr(marginal.risk_ratio, marginal.rr_ci_low, marginal.rr_ci_high)}"
                    )
                    lines.append(f"| {row_marginal.level} | " + " | ".join(row_cells) + f" | {marginal_text} |")
                col_cells: list[str] = []
                for column_marginal in matrix.column_marginals:
                    col_cells.append(
                        f"n={column_marginal.count}, mismatch={column_marginal.mismatch_rate_pct:.2f}%, "
                        f"RR={_format_rr(column_marginal.risk_ratio, column_marginal.rr_ci_low, column_marginal.rr_ci_high)}"
                    )
                lines.append("| Column marginal | " + " | ".join(col_cells) + " | n/a |")

        if self.contrast_results:
            lines.append("")
            lines.append("## Within-stratum contrasts")
            lines.append("")
            lines.append(
                "Sibling-level contrasts within each stratum reuse Koopman risk-ratio and "
                "Baptista-Pike odds-ratio intervals."
            )
            grouped: dict[tuple[str, str], list[ContrastResult]] = {}
            for contrast in self.contrast_results:
                key = (contrast.factorial, contrast.stratum)
                grouped.setdefault(key, []).append(contrast)
            for (factorial, stratum) in sorted(grouped):
                lines.append("")
                lines.append(f"### {factorial} :: {stratum}")
                lines.append("")
                lines.append("| Comparison | A mismatch rate | B mismatch rate | Risk ratio (95% CI) | Odds ratio (95% CI) |")
                lines.append("|---|---:|---:|---:|---:|")
                for contrast in grouped[(factorial, stratum)]:
                    rr = _format_effect_ci(contrast.risk_ratio, contrast.rr_ci_low, contrast.rr_ci_high)
                    or_ = _format_effect_ci(contrast.odds_ratio, contrast.or_ci_low, contrast.or_ci_high)
                    lines.append(
                        f"| {contrast.level_a} vs {contrast.level_b} | "
                        f"{contrast.mismatch_rate_a_pct:.2f}% ({_format_mismatch_split(contrast.mismatch_count_a, contrast.total_count_a)}) | "
                        f"{contrast.mismatch_rate_b_pct:.2f}% ({_format_mismatch_split(contrast.mismatch_count_b, contrast.total_count_b)}) | "
                        f"{rr} | {or_} |"
                    )

        if self.burden_rankings:
            lines.append("")
            lines.append("## Attributable burden")
            lines.append("")
            lines.append(
                "Per baselined factorial crossing, rows are ranked by recoverable mismatches relative to the declared baseline cell."
            )
            for ranking in self.burden_rankings:
                lines.append("")
                lines.append(f"### {ranking.crossing_label}")
                lines.append("")
                lines.append(f"Baseline cell: `{ranking.baseline_cell}`")
                if ranking.overlap_suppressed:
                    lines.append("")
                    lines.append("Ranking suppressed due to overlapping axis levels in this crossing.")
                else:
                    lines.append("")
                    lines.append(
                        "| Rank | Cell | n | Mismatch rate | Baseline rate | Recoverable mismatches | Share of all mismatches | Risk difference (95% CI) | Accuracy if eliminated |"
                    )
                    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|")
                    for entry in ranking.entries:
                        recoverable = "-" if entry.recoverable_mismatches is None else f"{entry.recoverable_mismatches:.2f}"
                        share = "-" if entry.share_total_mismatches_pct is None else f"{entry.share_total_mismatches_pct:.2f}%"
                        rd = _format_rd(entry.risk_difference, entry.rd_ci_low, entry.rd_ci_high)
                        lines.append(
                            f"| {entry.rank} | {entry.cell} | {entry.count} | {entry.mismatch_rate_pct:.2f}% | "
                            f"{entry.baseline_rate_pct:.2f}% | {recoverable} | {share} | {rd} | "
                            f"{entry.cumulative_accuracy_if_eliminated_pct:.2f}% |"
                        )
                if ranking.coverage_gap_excluded_rows > 0:
                    lines.append("")
                    lines.append(
                        f"Coverage gap note: {ranking.coverage_gap_excluded_rows} rows were outside all crossing cells and were excluded from ranking, but kept in the accuracy denominator."
                    )
                if ranking.baseline_sanity_warning:
                    lines.append("")
                    lines.append(f"Baseline sanity warning: {ranking.baseline_sanity_warning}")
                lines.append("")
                lines.append(
                    "Counterfactual caveat: recoverable mismatches assume rows in a fixed regime revert to the baseline mismatch rate."
                )
                lines.append("")
                lines.append(
                    f"Observed accuracy: {ranking.observed_accuracy_pct:.2f}% | Ceiling accuracy after ranked eliminations: {ranking.ceiling_accuracy_pct:.2f}% | Total observed mismatches: {ranking.total_mismatches}"
                )

        lines.append("")
        lines.append(f"Rows: {self.n_rows}")
        lines.append(f"Mean observed contribution: {self.mean_observed_contribution:.6f}")
        lines.append("")
        lines.append("---")
        lines.append("**References**")
        lines.append(
            "Shapley values: Shapley (1953) *A value for n-person games*, Princeton UP; "
            "Lundberg & Lee (2017) *A unified approach to interpreting model predictions*, NeurIPS 30."
        )
        lines.append(
            "Risk ratio CI: Koopman (1984) *Biometrics* 40(2):513-517. "
            "Odds ratio CI: Baptista & Pike (1977) *J. Roy. Statist. Soc. C* 26(2):214-220. "
            "Small-sample recommendation: Fagerland, Lydersen & Laake (2015, 2017)."
        )
        if self.burden_rankings:
            lines.append(
                "Risk difference CI: Miettinen & Nurminen (1985) *Statistics in Medicine* 4(2):213-226. "
                "Guardrail: Agresti & Caffo (2000) *Amer. Statist.* 54(4):280-288."
            )
        return "\n".join(lines)

    def to_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "hypotheses": [asdict(item) for item in self.hypotheses],
            "feature_attributions": [asdict(row) for row in self.feature_attributions],
            "regime_summaries": [asdict(row) for row in self.regime_summaries],
            "binary_results": [asdict(row) for row in self.binary_results],
            "n_rows": self.n_rows,
            "mean_observed_contribution": self.mean_observed_contribution,
            "metadata": self.metadata,
        }
        if self.factorial_matrices:
            payload["factorial_matrices"] = [asdict(row) for row in self.factorial_matrices]
        if self.contrast_results:
            payload["contrast_results"] = [asdict(row) for row in self.contrast_results]
        if self.partition_warnings:
            payload["partition_warnings"] = [asdict(row) for row in self.partition_warnings]
        if self.burden_rankings:
            payload["burden_rankings"] = [asdict(row) for row in self.burden_rankings]
        with target.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def save(self, out_dir: str | Path) -> None:
        target = Path(out_dir)
        target.mkdir(parents=True, exist_ok=True)
        self.to_csv(target / "contribution.csv")
        self.to_json(target / "run.json")
        (target / "report.md").write_text(self.to_markdown(), encoding="utf-8")
