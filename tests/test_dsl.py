"""Tests for the safe expression DSL."""

from __future__ import annotations

import pytest

from error_attribution.expr import compile_expression, evaluate_expression


def test_arithmetic() -> None:
    assert evaluate_expression("2 + 3 * 4", {}) == 14


def test_col_helper() -> None:
    ctx = {"x": 5}
    assert evaluate_expression("col('x') + 1", ctx) == 6


def test_log2() -> None:
    import math
    result = evaluate_expression("log2(8)", {})
    assert abs(result - 3.0) < 1e-12


def test_round() -> None:
    assert evaluate_expression("round(2 * log2(125000 / 125000))", {}) == 0


def test_comparison_returns_bool() -> None:
    ctx = {"a": 10, "b": 11}
    assert evaluate_expression("a < b", ctx) is True
    assert evaluate_expression("a > b", ctx) is False


def test_nested_col_comparison() -> None:
    ctx = {"detected_bw": 110000, "gt_bw": 125000}
    result = evaluate_expression("(col('detected_bw') * 1.10) < col('gt_bw')", ctx)
    assert result is True


def test_disallowed_function_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported function"):
        compile_expression("exec('rm -rf /')")


def test_disallowed_attribute_access_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported expression node"):
        compile_expression("x.__class__")


def test_disallowed_lambda_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported expression node"):
        compile_expression("lambda x: x")
