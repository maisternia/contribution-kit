"""Command line interface for error attribution."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contributor import combine_contributors, rank_contributors
from .estimator import Estimator
from .expr import build_row_context, evaluate_expression
from .hypothesis import evaluate_binary_hypothesis
from .spec import (
    AttributionSpec,
    Hypothesis,
)


def _load_spec(path: str | Path) -> AttributionSpec:
    spec_path = Path(path)
    raw_text = spec_path.read_text(encoding="utf-8")
    if spec_path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        payload = yaml.safe_load(raw_text)
    else:
        payload = json.loads(raw_text)
    hypotheses: list[Hypothesis] = []
    for item in payload.get("hypotheses", []):
        hypotheses.append(Hypothesis(**item))
    return AttributionSpec(
        target_expr=payload["target_expr"],
        prediction_expr=payload["prediction_expr"],
        hypotheses=hypotheses,
        mismatch_expr=payload.get("mismatch_expr"),
        scope=payload.get("scope", "global"),
        score_mode=payload.get("score_mode", "absolute_error"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="error-attrib")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_parser = subcommands.add_parser("init-config", help="Write a starter configuration file")
    init_parser.add_argument("--out", required=True)
    init_parser.add_argument("--template", default="ungated_sf")

    validate_parser = subcommands.add_parser("validate", help="Validate config and input")
    validate_parser.add_argument("--config", required=True)
    validate_parser.add_argument("--input", required=True)

    run_parser = subcommands.add_parser("run", help="Run attribution")
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)

    report_parser = subcommands.add_parser("report", help="Write a markdown report")
    report_parser.add_argument("--run", required=True)
    report_parser.add_argument("--out", required=True)

    contributor_parser = subcommands.add_parser("contributor", help="Run contributor bucket ranking")
    contributor_parser.add_argument("--input", required=True)
    contributor_parser.add_argument("--mismatch-expr", required=True)
    contributor_parser.add_argument("--feature", action="append", required=True, help="feature_name:row_expression")
    contributor_parser.add_argument("--out", required=True)
    contributor_parser.add_argument("--min-count", type=int, default=20)

    hypothesis_parser = subcommands.add_parser("hypothesis", help="Run a binary hypothesis test")
    hypothesis_parser.add_argument("--input", required=True)
    hypothesis_parser.add_argument("--mismatch-expr", required=True)
    hypothesis_parser.add_argument("--name", required=True)
    hypothesis_parser.add_argument("--group-a", required=True)
    hypothesis_parser.add_argument("--group-b", required=True)
    hypothesis_parser.add_argument("--group-a-label", required=True)
    hypothesis_parser.add_argument("--group-b-label", required=True)
    hypothesis_parser.add_argument("--scope", default="global")
    hypothesis_parser.add_argument("--out", required=True)

    return parser


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


def _load_rows(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: _parse_scalar(value) for key, value in row.items()} for row in reader]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "init-config":
        sample = {
            "target_expr": "col('GT SF')",
            "prediction_expr": "class_sf + round(2 * log2(measured_bw / class_bw))",
            "mismatch_expr": "col('Measured SF (ungated)') != col('GT SF')",
            "scope": "sobel",
            "hypotheses": [
                {"name": "class_bw < gt_bw (beyond tol)", "condition": "col('Detected BW (Hz)') < col('GT BW (Hz)') * (1 - 0.10)"},
                {"name": "class_bw > gt_bw (beyond tol)", "condition": "col('Detected BW (Hz)') > col('GT BW (Hz)') * (1 + 0.10)"},
                {"name": "class_bw within tol & sf wrong", "condition": "abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 and col('Detected SF') != col('GT SF')"},
                {"name": "class_bw & sf ok, measured_bw off", "condition": "abs(col('Detected BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') <= 0.10 and col('Detected SF') == col('GT SF') and abs(col('Measured BW (Hz)') - col('GT BW (Hz)')) / col('GT BW (Hz)') > 0.10"},
                {"name": "class_sf", "condition": "col('Detected SF') == col('GT SF')"},
                {"name": "class_bw", "condition": "col('Detected BW (Hz)') == col('GT BW (Hz)')"},
                {"name": "measured_bw", "condition": "col('Measured BW (Hz)') == col('GT BW (Hz)')"},
            ],
            "score_mode": "absolute_error",
        }
        Path(args.out).write_text(json.dumps(sample, indent=2), encoding="utf-8")
        return 0

    if args.command == "validate":
        spec = _load_spec(args.config)
        Estimator.from_csv(args.input, spec=spec).assess(exact=True)
        print("configuration and input validated")
        return 0

    if args.command == "run":
        spec = _load_spec(args.config)
        result = Estimator.from_csv(args.input, spec=spec).assess(exact=True)
        result.save(args.out)
        return 0

    if args.command == "report":
        payload = json.loads(Path(args.run).read_text(encoding="utf-8"))
        lines = ["# Error Attribution Report", "", f"Rows: {payload['n_rows']}", f"Mean observed error: {payload['mean_observed_error']:.6f}", "", "| name | label | mean_abs_shapley | mean_signed_shapley | total_signed_shapley | net_error_share_pct |", "|---|---:|---:|---:|---:|---:|"]
        for row in payload["feature_attributions"]:
            lines.append(f"| {row['name']} | {row['label']} | {row['mean_abs_shapley']:.6f} | {row['mean_signed_shapley']:.6f} | {row['total_signed_shapley']:.6f} | {row['net_error_share_pct']:.2f} |")
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 0

    if args.command == "contributor":
        rows = _load_rows(args.input)

        def mismatch_fn_contributor(row: dict[str, Any]) -> bool:
            return bool(evaluate_expression(args.mismatch_expr, build_row_context(row)))

        groups = []
        for item in args.feature:
            if ":" not in item:
                raise ValueError("--feature entries must be in format feature_name:row_expression")
            feature_name, feature_expr = item.split(":", 1)
            groups.append(
                rank_contributors(
                    rows,
                    feature=feature_name,
                    value_fn=lambda row, expr=feature_expr: str(evaluate_expression(expr, build_row_context(row))),
                    mismatch_fn=mismatch_fn_contributor,
                    min_count=args.min_count,
                )
            )
        combined = combine_contributors(groups)
        payload = [
            {
                "feature": row.feature,
                "value": row.value,
                "count": row.count,
                "mismatches": row.mismatches,
                "mismatch_rate": row.mismatch_rate,
                "lift": row.lift,
                "mismatch_share": row.mismatch_share,
                "score": row.score,
            }
            for row in combined
        ]
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return 0

    if args.command == "hypothesis":
        rows = _load_rows(args.input)

        def mismatch_fn_hypothesis(row: dict[str, Any]) -> bool:
            return bool(evaluate_expression(args.mismatch_expr, build_row_context(row)))

        group_a_rows = [row for row in rows if bool(evaluate_expression(args.group_a, build_row_context(row)))]
        group_b_rows = [row for row in rows if bool(evaluate_expression(args.group_b, build_row_context(row)))]
        result = evaluate_binary_hypothesis(
            scope=args.scope,
            test_name=args.name,
            group_a_label=args.group_a_label,
            group_b_label=args.group_b_label,
            group_a_rows=group_a_rows,
            group_b_rows=group_b_rows,
            mismatch_fn=mismatch_fn_hypothesis,
        )
        Path(args.out).write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
