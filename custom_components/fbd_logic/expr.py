"""Safe arithmetic/logic expression evaluator for the Formula block.

Only a small, whitelisted subset of Python expression syntax is accepted.
The expression is compiled once into nested closures, so evaluation each
scan cycle is cheap and never touches eval().
"""

from __future__ import annotations

import ast
import math
from typing import Any, Callable

from .i18n import tr

Compiled = Callable[[dict[str, float]], Any]


class ExpressionError(ValueError):
    """Raised for invalid expressions or evaluation errors."""


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sel(cond: Any, a: Any, b: Any) -> Any:
    return a if cond else b


FUNCTIONS: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sqrt": math.sqrt,
    "floor": math.floor,
    "ceil": math.ceil,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "clamp": _clamp,
    "limit": _clamp,
    "sel": _sel,
}

CONSTANTS: dict[str, float | bool] = {
    "pi": math.pi,
    "e": math.e,
    "true": True,
    "false": False,
    "True": True,
    "False": False,
}

_BINOPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
}

_CMPOPS: dict[type, Callable[[Any, Any], bool]] = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}


def _pow(a: Any, b: Any) -> Any:
    if abs(b) > 1000 or abs(a) > 1e100:
        raise ExpressionError(tr("Potens utenfor gyldig område"))
    return a**b


def compile_expression(source: str, variables: list[str]) -> Compiled:
    """Compile an expression string into a callable taking a vars dict."""
    source = (source or "").strip()
    if not source:
        raise ExpressionError(tr("Tomt uttrykk"))
    if len(source) > 500:
        raise ExpressionError(tr("Uttrykket er for langt"))
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as err:
        raise ExpressionError(tr("Syntaksfeil: {msg}", msg=err.msg)) from err

    allowed_vars = set(variables)

    def build(node: ast.AST) -> Compiled:
        if isinstance(node, ast.Expression):
            return build(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool)):
                value = node.value
                return lambda v: value
            raise ExpressionError(tr("Bare tall er tillatt som konstanter"))
        if isinstance(node, ast.Name):
            name = node.id
            if name in allowed_vars:
                return lambda v: v[name]
            if name in CONSTANTS:
                value = CONSTANTS[name]
                return lambda v: value
            raise ExpressionError(tr("Ukjent navn: {name}", name=name))
        if isinstance(node, ast.BinOp):
            left, right = build(node.left), build(node.right)
            if isinstance(node.op, ast.Pow):
                return lambda v: _pow(left(v), right(v))
            op = _BINOPS.get(type(node.op))
            if op is None:
                raise ExpressionError(tr("Operator ikke tillatt"))
            return lambda v: op(left(v), right(v))
        if isinstance(node, ast.UnaryOp):
            operand = build(node.operand)
            if isinstance(node.op, ast.USub):
                return lambda v: -operand(v)
            if isinstance(node.op, ast.UAdd):
                return lambda v: +operand(v)
            if isinstance(node.op, ast.Not):
                return lambda v: not operand(v)
            raise ExpressionError(tr("Operator ikke tillatt"))
        if isinstance(node, ast.BoolOp):
            parts = [build(x) for x in node.values]
            if isinstance(node.op, ast.And):
                return lambda v: all(p(v) for p in parts)
            return lambda v: any(p(v) for p in parts)
        if isinstance(node, ast.Compare):
            left = build(node.left)
            ops = []
            for op_node, comp in zip(node.ops, node.comparators):
                op = _CMPOPS.get(type(op_node))
                if op is None:
                    raise ExpressionError(tr("Sammenligning ikke tillatt"))
                ops.append((op, build(comp)))

            def compare(v: dict[str, float]) -> bool:
                current = left(v)
                for op, comp in ops:
                    nxt = comp(v)
                    if not op(current, nxt):
                        return False
                    current = nxt
                return True

            return compare
        if isinstance(node, ast.IfExp):
            test, body, orelse = build(node.test), build(node.body), build(node.orelse)
            return lambda v: body(v) if test(v) else orelse(v)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
                raise ExpressionError(tr("Ukjent funksjon"))
            if node.keywords:
                raise ExpressionError(tr("Navngitte argumenter er ikke tillatt"))
            func = FUNCTIONS[node.func.id]
            args = [build(a) for a in node.args]
            return lambda v: func(*(a(v) for a in args))
        raise ExpressionError(tr("Ikke tillatt i uttrykk: {kind}", kind=type(node).__name__))

    return build(tree)
