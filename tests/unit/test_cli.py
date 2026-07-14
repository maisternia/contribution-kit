from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from contribution import cli


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _rows() -> list[dict[str, str]]:
    return [
        {
            "GT SF": "9",
            "Detected SF": "9",
            "Measured SF (ungated)": "9",
            "GT BW (Hz)": "125000",
            "Detected BW (Hz)": "125000",
            "Measured BW (Hz)": "125000",
            "mismatch": "false",
            "group": "A",
        },
        {
            "GT SF": "9",
            "Detected SF": "10",
            "Measured SF (ungated)": "10",
            "GT BW (Hz)": "125000",
            "Detected BW (Hz)": "100000",
            "Measured BW (Hz)": "100000",
            "mismatch": "true",
            "group": "B",
        },
    ]


def _config(path: Path) -> Path:
    payload = {
        "target": "col('GT SF')",
        "prediction": "col('Measured SF (ungated)')",
        "prediction_expr": "class_sf + round(2 * log2(measured_bw / class_bw))",
        "hypotheses": {
            "class_sf": "col('Detected SF') == col('GT SF')",
            "class_bw": "col('Detected BW (Hz)') == col('GT BW (Hz)')",
            "measured_bw": "col('Measured BW (Hz)') == col('GT BW (Hz)')",
            "under": "col('Detected BW (Hz)') < col('GT BW (Hz)')",
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_build_parser_help_command() -> None:
    parser = cli.build_parser()
    parsed = parser.parse_args(["help"])
    assert parsed.command == "help"


def test_load_spec_json_and_yaml(tmp_path: Path) -> None:
    json_cfg = _config(tmp_path / "cfg.json")
    loaded = cli._load_spec(json_cfg)
    assert loaded.target.startswith("col")

    yaml_cfg = tmp_path / "cfg.yaml"
    yaml_cfg.write_text(
        "target: \"1\"\nprediction: \"1\"\nprediction_expr: \"1\"\nhypotheses:\n  h: \"1 == 1\"\n",
        encoding="utf-8",
    )
    loaded_yaml = cli._load_spec(yaml_cfg)
    assert loaded_yaml.hypotheses[0].name == "h"


def test_load_rows_scalar_parsing(tmp_path: Path) -> None:
    data = tmp_path / "in.csv"
    _write_csv(data, _rows())
    rows = cli._load_rows(data)
    assert isinstance(rows[0]["GT SF"], int)
    assert isinstance(rows[0]["mismatch"], bool)


def test_parse_scalar_empty_and_non_numeric_text() -> None:
    assert cli._parse_scalar("   ") is None
    assert cli._parse_scalar("1.5") == 1.5
    assert cli._parse_scalar("abc") == "abc"


def test_main_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["help"]) == 0
    out = capsys.readouterr().out
    assert "Available commands" in out
    assert "run" in out
    assert "Minimal path" in out
    assert "Recommended path" in out
    assert "Other commands" in out
    assert "CI method options" in out
    assert "score-exact" in out
    assert "wald" in out


def test_main_validate_run_report(tmp_path: Path) -> None:
    data = tmp_path / "in.csv"
    _write_csv(data, _rows())
    cfg = _config(tmp_path / "cfg.json")

    assert cli.main(["validate", "--config", str(cfg), "--input", str(data)]) == 0

    out_dir = tmp_path / "run-out"
    assert cli.main(["run", "--config", str(cfg), "--input", str(data), "--out", str(out_dir)]) == 0
    assert (out_dir / "run.json").exists()

    report_path = tmp_path / "report.md"
    assert cli.main(["report", "--run", str(out_dir / "run.json"), "--out", str(report_path)]) == 0
    regenerated = report_path.read_text(encoding="utf-8")
    assert "Factor-Contribution Analysis Report" in regenerated
    assert "## Shapley Value Contributions" in regenerated
    # Regenerated report matches the accessible layout saved by `run`.
    assert regenerated.rstrip("\n") == (out_dir / "report.md").read_text(encoding="utf-8").rstrip("\n")


def test_main_contributor_and_hypothesis(tmp_path: Path) -> None:
    data = tmp_path / "in.csv"
    _write_csv(data, _rows())

    contrib_out = tmp_path / "contrib.json"
    assert (
        cli.main(
            [
                "contributor",
                "--input",
                str(data),
                "--mismatch-expr",
                "mismatch",
                "--feature",
                "group:group",
                "--out",
                str(contrib_out),
                "--min-count",
                "1",
            ]
        )
        == 0
    )
    assert contrib_out.exists()

    hyp_out = tmp_path / "hyp.json"
    assert (
        cli.main(
            [
                "hypothesis",
                "--input",
                str(data),
                "--mismatch-expr",
                "mismatch",
                "--name",
                "gA",
                "--group-a",
                "group == 'A'",
                "--group-b",
                "group == 'B'",
                "--group-a-label",
                "A",
                "--group-b-label",
                "B",
                "--out",
                str(hyp_out),
            ]
        )
        == 0
    )
    assert hyp_out.exists()


def test_main_contributor_feature_format_error(tmp_path: Path) -> None:
    data = tmp_path / "in.csv"
    _write_csv(data, _rows())
    with pytest.raises(ValueError, match="format feature_name:row_expression"):
        cli.main(
            [
                "contributor",
                "--input",
                str(data),
                "--mismatch-expr",
                "mismatch",
                "--feature",
                "bad-format",
                "--out",
                str(tmp_path / "x.json"),
            ]
        )


def test_main_returns_one_for_unrecognized_command(monkeypatch) -> None:
    class _Args:
        command = "unknown"

    class _Parser:
        def parse_args(self, argv):
            return _Args()

    monkeypatch.setattr(cli, "build_parser", lambda: _Parser())
    assert cli.main([]) == 1


def test_load_spec_parses_factors_and_factorials(tmp_path: Path) -> None:
    cfg = tmp_path / "factorial.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "target",
                "prediction": "prediction",
                "prediction_expr": "f",
                "hypotheses": {"f": "1 == 1"},
                "factors": {
                    "row_axis": {"up": "row == 'up'", "down": "row == 'down'"},
                    "col_axis": {"ok": "col == 'ok'", "off": "col == 'off'"},
                },
                "factorials": [{"rows": "row_axis", "columns": "col_axis"}],
            }
        ),
        encoding="utf-8",
    )
    loaded = cli._load_spec(cfg)
    assert sorted(loaded.factors) == ["col_axis", "row_axis"]
    assert loaded.factorials[0].rows == "row_axis"
    assert loaded.factorials[0].columns == "col_axis"


def test_load_spec_factorial_unknown_axis_error(tmp_path: Path) -> None:
    cfg = tmp_path / "bad_axis.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "1",
                "prediction": "1",
                "prediction_expr": "1",
                "hypotheses": {"h": "1 == 1"},
                "factors": {"known": {"a": "1 == 1"}},
                "factorials": [{"rows": "known", "columns": "missing"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown axis 'missing'"):
        cli._load_spec(cfg)


def test_load_spec_empty_factor_axis_error(tmp_path: Path) -> None:
    cfg = tmp_path / "empty_factor.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "1",
                "prediction": "1",
                "prediction_expr": "1",
                "hypotheses": {"h": "1 == 1"},
                "factors": {"empty": {}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must declare at least one level"):
        cli._load_spec(cfg)


def test_load_spec_hypotheses_mapping_string_shorthand(tmp_path: Path) -> None:
    cfg = tmp_path / "mapping_string.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "1",
                "prediction": "1",
                "prediction_expr": "h",
                "hypotheses": {"h": "1 == 1"},
            }
        ),
        encoding="utf-8",
    )

    loaded = cli._load_spec(cfg)
    assert loaded.hypotheses[0].name == "h"
    assert loaded.hypotheses[0].condition == "1 == 1"
    assert loaded.hypotheses[0].label is None


def test_load_spec_hypotheses_mapping_object_explicit_label(tmp_path: Path) -> None:
    cfg = tmp_path / "mapping_object.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "1",
                "prediction": "1",
                "prediction_expr": "h",
                "hypotheses": {"h": {"condition": "1 == 1", "label": "Hypothesis H"}},
            }
        ),
        encoding="utf-8",
    )

    loaded = cli._load_spec(cfg)
    assert loaded.hypotheses[0].name == "h"
    assert loaded.hypotheses[0].condition == "1 == 1"
    assert loaded.hypotheses[0].label == "Hypothesis H"


def test_load_spec_hypotheses_object_missing_condition_error(tmp_path: Path) -> None:
    cfg = tmp_path / "missing_condition.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "1",
                "prediction": "1",
                "prediction_expr": "h",
                "hypotheses": {"h": {"label": "no condition"}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hypothesis 'h' must declare a 'condition' string"):
        cli._load_spec(cfg)


def test_load_spec_hypotheses_object_redundant_name_error(tmp_path: Path) -> None:
    cfg = tmp_path / "redundant_name.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "1",
                "prediction": "1",
                "prediction_expr": "h",
                "hypotheses": {"h": {"name": "other", "condition": "1 == 1"}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hypothesis 'h' must not redeclare 'name'"):
        cli._load_spec(cfg)


def test_load_spec_hypotheses_mapping_order_is_preserved(tmp_path: Path) -> None:
    cfg = tmp_path / "ordered.json"
    cfg.write_text(
        json.dumps(
            {
                "target": "1",
                "prediction": "1",
                "prediction_expr": "a + b + c",
                "hypotheses": {
                    "first": "1 == 1",
                    "second": {"condition": "2 == 2", "label": "Second"},
                    "third": "3 == 3",
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = cli._load_spec(cfg)
    assert [hypothesis.name for hypothesis in loaded.hypotheses] == ["first", "second", "third"]


def test_load_spec_migrated_example_matches_legacy_list_hypotheses() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cfg_path = repo_root / "examples" / "continuous_lora" / "config.json"
    payload = json.loads(cfg_path.read_text(encoding="utf-8"))

    old_style_hypotheses = []
    for hypothesis_name, hypothesis_value in payload["hypotheses"].items():
        if isinstance(hypothesis_value, str):
            old_style_hypotheses.append({"name": hypothesis_name, "condition": hypothesis_value})
        else:
            old_style_hypotheses.append(
                {
                    "name": hypothesis_name,
                    "condition": hypothesis_value["condition"],
                    **({"label": hypothesis_value["label"]} if "label" in hypothesis_value else {}),
                }
            )

    migrated = cli._load_spec(cfg_path)
    legacy_tuples = [
        (item["name"], item["condition"], item.get("label")) for item in old_style_hypotheses
    ]
    assert [(hypothesis.name, hypothesis.condition, hypothesis.label) for hypothesis in migrated.hypotheses] == legacy_tuples
