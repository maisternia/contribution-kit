"""Command line interface for factor-contribution analysis."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from textwrap import dedent
from typing import Any

from .contributor import combine_contributors, rank_contributors
from .estimator import Estimator
from .expr import build_row_context, evaluate_expression
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
from .spec import (
    AttributionSpec,
    Factor,
    FactorialCrossing,
    Hypothesis,
)


def _result_from_run(payload: dict[str, Any]) -> AssessmentResult:
    """Rebuild an ``AssessmentResult`` from a saved ``run.json`` payload.

    Lets ``contrib report`` regenerate the same accessible markdown layout that
    ``AssessmentResult.to_markdown()`` produces during ``run``.
    """
    hypotheses: list[HypothesisAssessment] = []
    for item in payload.get("hypotheses", []):
        feature = FeatureAttribution(**item["feature"]) if item.get("feature") else None
        regime = RegimeSummary(**item["regime"]) if item.get("regime") else None
        risk = BinaryHypothesisResult(**item["risk"]) if item.get("risk") else None
        hypotheses.append(
            HypothesisAssessment(
                name=item["name"],
                label=item["label"],
                analysis=item["analysis"],
                feature=feature,
                regime=regime,
                risk=risk,
            )
        )
    factorial_matrices: list[FactorialMatrixResult] = []
    for item in payload.get("factorial_matrices", []):
        factorial_matrices.append(
            FactorialMatrixResult(
                rows_axis=item["rows_axis"],
                columns_axis=item["columns_axis"],
                cells=[FactorialCellResult(**cell) for cell in item.get("cells", [])],
                row_marginals=[FactorialMarginalResult(**row) for row in item.get("row_marginals", [])],
                column_marginals=[FactorialMarginalResult(**row) for row in item.get("column_marginals", [])],
            )
        )

    contrast_results = [ContrastResult(**item) for item in payload.get("contrast_results", [])]
    partition_warnings = [PartitionWarning(**item) for item in payload.get("partition_warnings", [])]

    return AssessmentResult(
        hypotheses=hypotheses,
        n_rows=payload["n_rows"],
        mean_observed_contribution=payload["mean_observed_contribution"],
        metadata=payload.get("metadata", {}),
        factorial_matrices=factorial_matrices,
        contrast_results=contrast_results,
        partition_warnings=partition_warnings,
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

    factors_payload = payload.get("factors", {})
    if not isinstance(factors_payload, dict):
        raise ValueError("'factors' must be an object mapping axis names to level conditions")
    factors: dict[str, Factor] = {}
    for axis_name, levels_payload in factors_payload.items():
        if not isinstance(levels_payload, dict):
            raise ValueError(f"factor '{axis_name}' must map level names to condition strings")
        if not levels_payload:
            raise ValueError(f"factor '{axis_name}' must declare at least one level")
        levels: dict[str, str] = {}
        for level_name, condition in levels_payload.items():
            if not isinstance(condition, str) or not condition.strip():
                raise ValueError(f"factor '{axis_name}' level '{level_name}' must have a non-empty condition string")
            levels[level_name] = condition
        factors[axis_name] = Factor(name=axis_name, levels=levels)

    factorials_payload = payload.get("factorials", [])
    if not isinstance(factorials_payload, list):
        raise ValueError("'factorials' must be a list of {'rows': <axis>, 'columns': <axis>} objects")
    factorials: list[FactorialCrossing] = []
    for index, item in enumerate(factorials_payload):
        if not isinstance(item, dict):
            raise ValueError(f"factorials[{index}] must be an object with 'rows' and 'columns'")
        rows_axis = item.get("rows")
        columns_axis = item.get("columns")
        if not isinstance(rows_axis, str) or not isinstance(columns_axis, str):
            raise ValueError(f"factorials[{index}] must declare string 'rows' and 'columns' axis names")
        for axis_name in (rows_axis, columns_axis):
            if axis_name not in factors:
                raise ValueError(f"factorials[{index}] references unknown axis '{axis_name}'")
        factorials.append(FactorialCrossing(rows=rows_axis, columns=columns_axis))

    return AttributionSpec(
        target=payload["target"],
        prediction=payload["prediction"],
        prediction_expr=payload["prediction_expr"],
        hypotheses=hypotheses,
        factors=factors,
        factorials=factorials,
        scope=payload.get("scope", "global"),
        score_mode=payload.get("score_mode", "absolute"),
    )


def _help_text() -> str:
    return dedent(
    """
    contrib CLI

        Available commands:
            validate        Validate config and input
            run             Run attribution and save outputs
            report          Regenerate markdown report from run.json
            contributor     Run contributor bucket ranking
            hypothesis      Run a binary hypothesis test
            help            Show this help text

            Quick guide

        Minimal path (get results in one command):
            contrib run --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001

        Recommended path (safer):
            contrib validate --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv
            contrib run      --config examples/continuous_lora/config.json --input examples/continuous_lora/measurements.csv --out outputs/run_001

        Other commands (optional / independent):
            contrib report --run outputs/run_001/run.json --out outputs/run_001/report.md
            contrib contributor --input <csv> --mismatch-expr <expr> --feature <name:expr> --out <json>
            contrib hypothesis --input <csv> --mismatch-expr <expr> --name <name> --group-a <expr> --group-b <expr> --group-a-label <label> --group-b-label <label> --out <json>

        CI method options (for hypothesis):
            --ci-method score-exact   Default. Uses Koopman asymptotic-score RR CI + Baptista-Pike exact OR CI.
            --ci-method wald          Legacy mode. Uses Wald-type confidence intervals: Katz RR CI + Haldane-Anscombe corrected OR CI.
        """
    ).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contrib")
    subcommands = parser.add_subparsers(dest="command", required=True)

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
    hypothesis_parser.add_argument(
        "--ci-method",
        default="score-exact",
        choices=["score-exact", "wald"],
        help=(
            "CI construction mode: score-exact (default; Koopman RR + Baptista-Pike OR) "
            "or wald (legacy; Katz RR + Haldane-Anscombe OR)."
        ),
    )
    hypothesis_parser.add_argument("--out", required=True)

    subcommands.add_parser("help", help="Show command workflow and examples")

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

    if args.command == "help":
        print(_help_text())
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
        result = _result_from_run(payload)
        Path(args.out).write_text(result.to_markdown() + "\n", encoding="utf-8")
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
            ci_method=args.ci_method,
        )
        Path(args.out).write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
