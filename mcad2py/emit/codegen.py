"""Turn IR nodes into Python source fragments.

Shared by the notebook and ``.py`` backends. The core is a precedence-aware
expression printer so we emit only the parentheses Python actually needs.
"""

from __future__ import annotations

from .. import ir
from ..mapping import (
    BINARY_OPS,
    CONSTANTS,
    FUNCTIONS,
    RUNTIME_IMPORTS,
    UNARY_PREC,
    unit_attr,
)

_ATOM = 100


def expr_to_str(node: ir.Expr) -> str:
    """Render an expression with no unnecessary outer parentheses."""
    return _emit(node)[0]


def _emit(node: ir.Expr) -> tuple[str, int]:
    if isinstance(node, ir.Number):
        return node.value, _ATOM

    if isinstance(node, ir.Name):
        if node.role == "CONSTANT":
            return CONSTANTS.get(node.original, node.py), _ATOM
        return node.py, _ATOM

    if isinstance(node, ir.UnitRef):
        return f"ureg.{unit_attr(node.name)}", _ATOM

    if isinstance(node, ir.Quantity):
        left = _wrap(node.value, 2, is_left=True, right_assoc=False)
        right = _wrap(node.unit, 2, is_left=False, right_assoc=False)
        return f"{left} * {right}", 2

    if isinstance(node, ir.BinOp):
        sym, prec = BINARY_OPS[node.op]
        right_assoc = node.op == "pow"
        left = _wrap(node.left, prec, is_left=True, right_assoc=right_assoc)
        right = _wrap(node.right, prec, is_left=False, right_assoc=right_assoc)
        joiner = sym if node.op == "pow" else f" {sym} "
        return f"{left}{joiner}{right}", prec

    if isinstance(node, ir.UnaryOp):
        operand = _wrap(node.operand, UNARY_PREC, is_left=True, right_assoc=False)
        return f"-{operand}", UNARY_PREC

    if isinstance(node, ir.Call):
        func = FUNCTIONS.get(node.func, node.func)
        args = ", ".join(expr_to_str(a) for a in node.args)
        return f"{func}({args})", _ATOM

    if isinstance(node, ir.Root):
        operand = expr_to_str(node.operand)
        if node.degree is None:
            return f"math.sqrt({operand})", _ATOM
        degree = expr_to_str(node.degree)
        return f"({operand}) ** (1 / ({degree}))", _ATOM

    if isinstance(node, ir.Placeholder):
        return "None  # placeholder", _ATOM

    if isinstance(node, ir.Unsupported):
        return f"None  # TODO unsupported: {node.note}", _ATOM

    return f"None  # TODO unknown node: {type(node).__name__}", _ATOM


def _wrap(node: ir.Expr, parent_prec: int, *, is_left: bool, right_assoc: bool) -> str:
    text, prec = _emit(node)
    if prec < parent_prec:
        need = True
    elif prec == parent_prec:
        need = right_assoc if is_left else not right_assoc
    else:
        need = False
    return f"({text})" if need else text


# ---------------------------------------------------------------------------
# Region-level rendering
# ---------------------------------------------------------------------------


def assignment_line(define: ir.Define) -> str:
    """The ``target = value`` line for a Define."""
    return f"{define.target.py} = {expr_to_str(define.value)}"


def echo_expr(region: ir.Region) -> str | None:
    """The expression to display for an evaluated region, or None.

    Applies the worksheet's display-unit override via ``.to(ureg.<unit>)``.
    """
    if isinstance(region, ir.Define):
        if not region.evaluate:
            return None
        target = region.target.py
        if region.display_unit:
            return f"{target}.to(ureg.{unit_attr(region.display_unit)})"
        return target
    if isinstance(region, ir.Evaluate):
        base = expr_to_str(region.value)
        if region.display_unit:
            return f"({base}).to(ureg.{unit_attr(region.display_unit)})"
        return base
    return None


# ---------------------------------------------------------------------------
# Imports needed by a worksheet
# ---------------------------------------------------------------------------


def header_lines(ws: ir.Worksheet) -> list[str]:
    """Import/setup lines for the generated module, tailored to what's used."""
    used_runtime = _used_runtime(ws)
    lines = ["import math", "import pint", ""]
    if used_runtime:
        names = ", ".join(n for n in RUNTIME_IMPORTS if n in used_runtime)
        lines.append(f"from mcad2py.runtime import {names}")
    lines.append("ureg = pint.UnitRegistry()")
    return lines


def _used_runtime(ws: ir.Worksheet) -> set[str]:
    found: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, ir.Call) and node.func in RUNTIME_IMPORTS:
            found.add(node.func)
        for child in _children(node):
            visit(child)

    for region in ws.regions:
        if isinstance(region, ir.Define):
            visit(region.value)
        elif isinstance(region, ir.Evaluate):
            visit(region.value)
    return found


def _children(node: object) -> list[ir.Expr]:
    if isinstance(node, ir.Quantity):
        return [node.value, node.unit]
    if isinstance(node, ir.BinOp):
        return [node.left, node.right]
    if isinstance(node, ir.UnaryOp):
        return [node.operand]
    if isinstance(node, ir.Call):
        return list(node.args)
    if isinstance(node, ir.Root):
        return [node.operand] + ([node.degree] if node.degree is not None else [])
    return []
