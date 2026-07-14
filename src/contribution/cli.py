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
from .expr import build_row_context, evaluate_expression, parse_feature_equality_shorthand
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
    FactorialCrossing,
    Hypothesis,
    PredictionFeature,
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
                label=item["label"],
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
    hypotheses_payload = payload.get("hypotheses", {})
    if not isinstance(hypotheses_payload, dict):
        raise ValueError("'hypotheses' must be an object mapping hypothesis names to condition strings or objects")

    hypotheses: list[Hypothesis] = []
    for hypothesis_name, hypothesis_value in hypotheses_payload.items():
        if isinstance(hypothesis_value, str):
            hypotheses.append(Hypothesis(name=hypothesis_name, condition=hypothesis_value))
            continue

        if isinstance(hypothesis_value, dict):
            if "condition" not in hypothesis_value:
                raise ValueError(f"hypothesis '{hypothesis_name}' must declare a 'condition' string")
            if "name" in hypothesis_value:
                raise ValueError(
                    f"hypothesis '{hypothesis_name}' must not redeclare 'name'; the mapping key is the name"
                )
            hypotheses.append(Hypothesis(name=hypothesis_name, **hypothesis_value))
            continue

        raise ValueError(
            f"hypothesis '{hypothesis_name}' must be a condition string or an object with 'condition' and optional 'label'"
        )

    prediction_features_payload = payload.get("prediction_features", {})
    if not isinstance(prediction_features_payload, dict):
        raise ValueError("'prediction_features' must be an object mapping feature names to {actual, baseline, label?}")
    prediction_features: dict[str, PredictionFeature] = {}
    allowed_feature_keys = {"actual", "baseline", "label"}
    for feature_name, feature_payload in prediction_features_payload.items():
        if isinstance(feature_payload, str):
            shorthand = feature_payload.strip()
            if not shorthand:
                raise ValueError(
                    f"prediction feature '{feature_name}' string shorthand must be a non-empty top-level '==' equality"
                )
            try:
                parsed = parse_feature_equality_shorthand(shorthand)
            except (SyntaxError, ValueError) as error:
                raise ValueError(
                    f"prediction feature '{feature_name}' string shorthand must be a single top-level 'actual == baseline' equality"
                ) from error
            if parsed is None:
                raise ValueError(
                    f"prediction feature '{feature_name}' string shorthand must be a single top-level 'actual == baseline' equality"
                )
            actual, baseline = parsed
            prediction_features[feature_name] = PredictionFeature(actual=actual, baseline=baseline)
            continue
        if not isinstance(feature_payload, dict):
            raise ValueError(
                f"prediction feature '{feature_name}' must be an object with required 'actual' and 'baseline' or a top-level 'actual == baseline' string shorthand"
            )
        missing_keys = [key for key in ("actual", "baseline") if key not in feature_payload]
        if missing_keys:
            raise ValueError(
                f"prediction feature '{feature_name}' is missing required key(s): {', '.join(missing_keys)}"
            )
        unknown_keys = sorted(set(feature_payload).difference(allowed_feature_keys))
        if unknown_keys:
            raise ValueError(
                f"prediction feature '{feature_name}' has unknown key(s): {', '.join(unknown_keys)}"
            )
        actual = feature_payload["actual"]
        baseline = feature_payload["baseline"]
        label = feature_payload.get("label")
        if not isinstance(actual, str) or not actual.strip():
            raise ValueError(f"prediction feature '{feature_name}' key 'actual' must be a non-empty string")
        if not isinstance(baseline, str) or not baseline.strip():
            raise ValueError(f"prediction feature '{feature_name}' key 'baseline' must be a non-empty string")
        if label is not None and not isinstance(label, str):
            raise ValueError(f"prediction feature '{feature_name}' key 'label' must be a string when provided")
        prediction_features[feature_name] = PredictionFeature(actual=actual, baseline=baseline, label=label)

    factorials_payload = payload.get("factorials", [])
    if not isinstance(factorials_payload, list):
        raise ValueError("'factorials' must be a list of crossing objects")
    factorials: list[FactorialCrossing] = []
    for index, item in enumerate(factorials_payload):
        if not isinstance(item, dict):
            raise ValueError(f"factorials[{index}] must be an object")
        
        # Validate known keys
        allowed_crossing_keys = {"rows", "columns", "label"}
        unknown_keys = sorted(set(item).difference(allowed_crossing_keys))
        if unknown_keys:
            raise ValueError(f"factorials[{index}] has unknown key(s): {', '.join(unknown_keys)}")
        
        # Parse rows axis
        rows_payload = item.get("rows")
        if not isinstance(rows_payload, dict):
            raise ValueError(f"factorials[{index}] must declare 'rows' as an object mapping level names to conditions")
        if not rows_payload:
            raise ValueError(f"factorials[{index}] 'rows' axis must declare at least one level")
        rows: dict[str, str] = {}
        for level_name, condition in rows_payload.items():
            if not isinstance(condition, str) or not condition.strip():
                raise ValueError(f"factorials[{index}] rows level '{level_name}' must have a non-empty condition string")
            rows[level_name] = condition
        
        # Parse columns axis
        columns_payload = item.get("columns")
        if not isinstance(columns_payload, dict):
            raise ValueError(f"factorials[{index}] must declare 'columns' as an object mapping level names to conditions")
        if not columns_payload:
            raise ValueError(f"factorials[{index}] 'columns' axis must declare at least one level")
        columns: dict[str, str] = {}
        for level_name, condition in columns_payload.items():
            if not isinstance(condition, str) or not condition.strip():
                raise ValueError(f"factorials[{index}] columns level '{level_name}' must have a non-empty condition string")
            columns[level_name] = condition
        
        # Parse optional label
        label = item.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise ValueError(f"factorials[{index}] 'label' must be a non-empty string when provided")
        
        factorials.append(FactorialCrossing(rows=rows, columns=columns, label=label))

    return AttributionSpec(
        target=payload["target"],
        prediction=payload["prediction"],
        prediction_expr=payload["prediction_expr"],
        prediction_features=prediction_features,
        hypotheses=hypotheses,
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
