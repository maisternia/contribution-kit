"""Safe expression utilities for row-wise formulas."""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping

_ALLOWED_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "bool": bool,
    "ceil": math.ceil,
    "float": float,
    "floor": math.floor,
    "int": int,
    "log2": math.log2,
    "max": max,
    "min": min,
    "round": round,
    "str": str,
}


@dataclass(slots=True)
class CompiledExpression:
    source: str
    tree: ast.Expression

    def evaluate(self, context: Mapping[str, Any]) -> Any:
        return _eval_node(self.tree.body, context)


def compile_expression(source: str) -> CompiledExpression:
    tree = ast.parse(source, mode="eval")
    _validate_node(tree)
    return CompiledExpression(source=source, tree=tree)


def evaluate_expression(source: str, context: Mapping[str, Any]) -> Any:
    return compile_expression(source).evaluate(context)


def split_equality(expression: CompiledExpression) -> tuple[CompiledExpression, CompiledExpression] | None:
    """Split a top-level equality into its two operands.

    ``a == b`` returns compiled expressions for ``a`` (the model-produced value)
    and ``b`` (the ground-truth baseline). Any other expression returns ``None``.
    """

    body = expression.tree.body
    if isinstance(body, ast.Compare) and len(body.ops) == 1 and isinstance(body.ops[0], ast.Eq):
        left = ast.Expression(body=body.left)
        right = ast.Expression(body=body.comparators[0])
        ast.fix_missing_locations(left)
        ast.fix_missing_locations(right)
        return (
            CompiledExpression(source=ast.unparse(body.left), tree=left),
            CompiledExpression(source=ast.unparse(body.comparators[0]), tree=right),
        )
    return None


def build_row_context(row: Mapping[str, Any], extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = dict(row)
    if extra:
        context.update(extra)
    context["col"] = lambda name: context[name]
    return context


def _validate_node(node: ast.AST) -> None:
    if isinstance(node, ast.Expression):
        _validate_node(node.body)
        return
    if isinstance(node, ast.Constant):
        return
    if isinstance(node, ast.Name):
        return
    if isinstance(node, ast.BinOp):
        _validate_node(node.left)
        _validate_node(node.right)
        return
    if isinstance(node, ast.UnaryOp):
        _validate_node(node.operand)
        return
    if isinstance(node, ast.BoolOp):
        for value in node.values:
            _validate_node(value)
        return
    if isinstance(node, ast.Compare):
        _validate_node(node.left)
        for comparator in node.comparators:
            _validate_node(comparator)
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are allowed")
        if node.func.id not in _ALLOWED_FUNCTIONS and node.func.id != "col":
            raise ValueError(f"Unsupported function: {node.func.id}")
        for arg in node.args:
            _validate_node(arg)
        for keyword in node.keywords:
            _validate_node(keyword.value)
        return
    if isinstance(node, ast.IfExp):
        _validate_node(node.test)
        _validate_node(node.body)
        _validate_node(node.orelse)
        return
    if isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            _validate_node(element)
        return
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def _eval_node(node: ast.AST, context: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in context:
            raise KeyError(f"Unknown variable: {node.id}")
        return context[node.id]
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
    if isinstance(node, ast.UnaryOp):
        value = _eval_node(node.operand, context)
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.Not):
            return not value
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(value, context) for value in node.values]
        if isinstance(node.op, ast.And):
            result = True
            for value in values:
                result = result and bool(value)
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for value in values:
                result = result or bool(value)
            return result
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, context)
            if isinstance(op, ast.Eq) and not (left == right):
                return False
            if isinstance(op, ast.NotEq) and not (left != right):
                return False
            if isinstance(op, ast.Lt) and not (left < right):
                return False
            if isinstance(op, ast.LtE) and not (left <= right):
                return False
            if isinstance(op, ast.Gt) and not (left > right):
                return False
            if isinstance(op, ast.GtE) and not (left >= right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are allowed")
        if node.func.id == "col":
            if len(node.args) != 1:
                raise ValueError("col() requires one argument")
            name = _eval_node(node.args[0], context)
            return context[name]
        func = _ALLOWED_FUNCTIONS[node.func.id]
        args = [_eval_node(arg, context) for arg in node.args]
        kwargs = {keyword.arg: _eval_node(keyword.value, context) for keyword in node.keywords}
        return func(*args, **kwargs)
    if isinstance(node, ast.IfExp):
        return _eval_node(node.body, context) if _eval_node(node.test, context) else _eval_node(node.orelse, context)
    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(element, context) for element in node.elts)
    if isinstance(node, ast.List):
        return [_eval_node(element, context) for element in node.elts]
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")
