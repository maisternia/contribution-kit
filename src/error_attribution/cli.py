"""Command line interface for error attribution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .estimator import Estimator
from .spec import AttributionSpec, CategoricalHypothesis, ContinuousHypothesis, HypothesisSpec


def _load_spec(path: str | Path) -> AttributionSpec:
    spec_path = Path(path)
    raw_text = spec_path.read_text(encoding="utf-8")
    if spec_path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        payload = yaml.safe_load(raw_text)
    else:
        payload = json.loads(raw_text)
    hypotheses: list[HypothesisSpec] = []
    for item in payload.get("hypotheses", []):
        hypothesis_cls = CategoricalHypothesis if item.get("kind", "continuous") == "categorical" else ContinuousHypothesis
        hypotheses.append(hypothesis_cls(**item))
    return AttributionSpec(
        target_expr=payload["target_expr"],
        prediction_expr=payload["prediction_expr"],
        hypotheses=hypotheses,
        stratify_by=list(payload.get("stratify_by", [])),
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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "init-config":
        sample = {
            "target_expr": "col('GT SF')",
            "prediction_expr": "class_sf + round(2 * log2(measured_bw / class_bw))",
            "hypotheses": [
                {"name": "class_sf", "actual_expr": "col('Detected SF')", "baseline_expr": "col('GT SF')", "kind": "categorical"},
                {"name": "class_bw", "actual_expr": "col('Detected BW (Hz)')", "baseline_expr": "col('GT BW (Hz)')", "kind": "continuous"},
                {"name": "measured_bw", "actual_expr": "col('Measured BW (Hz)')", "baseline_expr": "col('GT BW (Hz)')", "kind": "continuous"},
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

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
