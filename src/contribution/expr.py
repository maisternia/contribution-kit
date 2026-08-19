"""Safe expression utilities for row-wise formulas."""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping

#: Name of the coalition-score function in the DSL. It is not in
#: ``_ALLOWED_FUNCTIONS`` because it is not a pure function of its arguments:
#: it reads a per-row table bound into the evaluation context by the caller.
COALITION_SCORE = "coalition_score"

#: Private context key holding the bound coalition scorer. Using a key that
#: cannot collide with a CSV header keeps an input column literally named
#: ``coalition_score`` from being mistaken for the function.
_COALITION_SCORE_KEY = "__coalition_score__"

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


def parse_feature_equality_shorthand(source: str) -> tuple[str, str] | None:
    tree = ast.parse(source, mode="eval")
    _validate_node(tree)
    body = tree.body
    if not isinstance(body, ast.Compare):
        return None
    if len(body.ops) != 1 or len(body.comparators) != 1:
        return None
    if not isinstance(body.ops[0], ast.Eq):
        return None
    return ast.unparse(body.left), ast.unparse(body.comparators[0])


def free_variables(expression: CompiledExpression) -> set[str]:
    names = {node.id for node in ast.walk(expression.tree) if isinstance(node, ast.Name)}
    return names.difference(_ALLOWED_FUNCTIONS).difference({"col", COALITION_SCORE})


def coalition_score_arguments(expression: CompiledExpression) -> list[tuple[str, ...]]:
    """Return the argument tuple of every ``coalition_score`` call, in source order.

    Arguments are string literals by construction (``_validate_node`` rejects
    anything else), so every referenced coalition is known before a single row
    is read. Callers use this both to validate player names up front and to
    size the per-row score table.
    """
    return [tuple(arg.value for arg in call.args) for call in _iter_coalition_calls(expression.tree)]


def build_row_context(
    row: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
    *,
    coalition_score: Callable[[tuple[str, ...]], float] | None = None,
) -> dict[str, Any]:
    context = dict(row)
    if extra:
        context.update(extra)
    context["col"] = lambda name: context[name]
    if coalition_score is not None:
        context[_COALITION_SCORE_KEY] = coalition_score
    return context


def _iter_coalition_calls(node: ast.AST):
    """Yield ``coalition_score`` call nodes depth-first in child order."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == COALITION_SCORE:
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _iter_coalition_calls(child)


def _validate_coalition_score_call(node: ast.Call) -> None:
    if node.keywords:
        raise ValueError(f"{COALITION_SCORE}() takes no keyword arguments")
    for arg in node.args:
        if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
            raise ValueError(
                f"{COALITION_SCORE}() arguments must be string literals naming players, got: "
                f"{ast.unparse(arg)}"
            )


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
        if node.func.id == COALITION_SCORE:
            _validate_coalition_score_call(node)
            return
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
        if node.func.id == COALITION_SCORE:
            scorer = context.get(_COALITION_SCORE_KEY)
            if scorer is None:
                raise ValueError(
                    f"{COALITION_SCORE}() is not available in this expression. It reads the "
                    "Shapley game's coalition scores, so it is available only in regime "
                    "conditions and factorial axis level conditions of a spec that declares "
                    "prediction_features -- not in the expressions that define the game "
                    "(a feature's actual or baseline, prediction_expr, target, or prediction)."
                )
            return scorer(tuple(arg.value for arg in node.args))
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
