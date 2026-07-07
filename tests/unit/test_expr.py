from __future__ import annotations

import pytest

from contribution.expr import build_row_context, compile_expression, evaluate_expression, split_equality


def test_build_row_context_with_extra() -> None:
    ctx = build_row_context({"a": 1}, {"b": 2})
    assert ctx["a"] == 1
    assert ctx["b"] == 2
    assert ctx["col"]("a") == 1


def test_evaluate_all_core_nodes() -> None:
    ctx = {"a": 5, "b": 2, "c": True}
    assert evaluate_expression("a + b * 3", ctx) == 11
    assert evaluate_expression("a // b", ctx) == 2
    assert evaluate_expression("a % b", ctx) == 1
    assert evaluate_expression("b ** 3", ctx) == 8
    assert evaluate_expression("+a", ctx) == 5
    assert evaluate_expression("-a", ctx) == -5
    assert evaluate_expression("not c", ctx) is False
    assert evaluate_expression("a > b and c", ctx) is True
    assert evaluate_expression("a < b or c", ctx) is True
    assert evaluate_expression("a == 5", ctx) is True
    assert evaluate_expression("a != 4", ctx) is True
    assert evaluate_expression("a >= 5", ctx) is True
    assert evaluate_expression("a <= 5", ctx) is True
    assert evaluate_expression("a if c else b", ctx) == 5
    assert evaluate_expression("(a, b)", ctx) == (5, 2)
    assert evaluate_expression("[a, b]", ctx) == [5, 2]
    assert evaluate_expression("round(log2(8))", ctx) == 3


def test_col_helper_and_arity_error() -> None:
    assert evaluate_expression("col('x') + 1", {"x": 2}) == 3
    with pytest.raises(ValueError, match=r"col\(\) requires one argument"):
        evaluate_expression("col('x', 'y')", {"x": 2, "y": 1})


def test_split_equality() -> None:
    split = split_equality(compile_expression("col('a') == col('b')"))
    assert split is not None
    left, right = split
    assert left.source == "col('a')"
    assert right.source == "col('b')"
    assert split_equality(compile_expression("col('a') > col('b')")) is None


def test_unsupported_function_and_node_raise() -> None:
    with pytest.raises(ValueError, match="Unsupported function"):
        compile_expression("eval('1+1')")
    with pytest.raises(ValueError, match="Unsupported expression node"):
        compile_expression("x.__class__")
    with pytest.raises(ValueError, match="Unsupported expression node"):
        compile_expression("lambda x: x")


def test_unknown_variable_raises() -> None:
    with pytest.raises(KeyError, match="Unknown variable"):
        evaluate_expression("missing + 1", {})


def test_non_direct_function_call_rejected() -> None:
    with pytest.raises(ValueError, match="Only direct function calls are allowed"):
        compile_expression("(min)(1, 2)")
