from __future__ import annotations

import ast

import pytest

from contribution.expr import build_row_context, compile_expression, evaluate_expression, free_variables


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


def test_free_variables() -> None:
    expression = compile_expression("class_sf + round(2 * log2(measured_bw / class_bw))")
    assert free_variables(expression) == {"class_sf", "measured_bw", "class_bw"}


def test_free_variables_excludes_allowed_function_names_and_col() -> None:
    expression = compile_expression("col('x') + max(1, 2)")
    assert free_variables(expression) == set()


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
        compile_expression("math.sqrt(4)")


def test_eval_keyword_args_and_extra_compare_paths() -> None:
    ctx = {"a": 2, "b": 2}
    assert evaluate_expression("round(1.2345, ndigits=2)", ctx) == 1.23
    assert evaluate_expression("a - b", ctx) == 0
    assert evaluate_expression("a <= b", ctx) is True
    assert evaluate_expression("a >= b", ctx) is True
    assert evaluate_expression("a <= 1", ctx) is False
    assert evaluate_expression("a >= 3", ctx) is False


def test_eval_rejects_non_direct_call_node() -> None:
    from contribution import expr as expr_module

    bad_call = ast.Call(
        func=ast.Attribute(value=ast.Name(id="obj", ctx=ast.Load()), attr="m", ctx=ast.Load()),
        args=[],
        keywords=[],
    )
    with pytest.raises(ValueError, match="Only direct function calls are allowed"):
        expr_module._eval_node(bad_call, {})


def test_eval_unsupported_node_raises() -> None:
    from contribution import expr as expr_module

    with pytest.raises(ValueError, match="Unsupported expression node"):
        expr_module._eval_node(ast.Dict(keys=[], values=[]), {})


def test_eval_unsupported_binop_and_unaryop_raise() -> None:
    from contribution import expr as expr_module

    bad_bin = ast.BinOp(left=ast.Constant(1), op=ast.MatMult(), right=ast.Constant(2))
    bad_unary = ast.UnaryOp(op=ast.Invert(), operand=ast.Constant(1))
    with pytest.raises(ValueError, match="Unsupported expression node"):
        expr_module._eval_node(bad_bin, {})
    with pytest.raises(ValueError, match="Unsupported expression node"):
        expr_module._eval_node(bad_unary, {})


def test_eval_unsupported_boolop_operator_raises() -> None:
    from contribution import expr as expr_module

    bad_bool = ast.BoolOp(op=ast.BitAnd(), values=[ast.Constant(True), ast.Constant(False)])
    with pytest.raises(ValueError, match="Unsupported expression node"):
        expr_module._eval_node(bad_bool, {})
