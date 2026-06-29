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

    if isinstance(node, ir.Equation):
        return f"Eq({expr_to_str(node.lhs)}, {expr_to_str(node.rhs)})", _ATOM

    if isinstance(node, ir.MatrixLiteral):
        elems = ", ".join(expr_to_str(e) for e in node.elements)
        if node.rows <= 1 or node.cols <= 1:  # vector -> 1-D array
            return f"col({elems})", _ATOM
        return f"np.array([{elems}])  # TODO {node.rows}x{node.cols} matrix", _ATOM

    if isinstance(node, ir.Index):
        base = _wrap(node.base, _ATOM, is_left=True, right_assoc=False)
        return f"{base}[{expr_to_str(node.index)}]", _ATOM

    if isinstance(node, ir.Vectorize):
        return f"vectorize({expr_to_str(node.operand)})", _ATOM

    if isinstance(node, ir.Range):
        start = expr_to_str(node.start)
        stop = expr_to_str(node.stop)
        if node.step is None:
            return f"np.arange({start}, ({stop}) + 1)", _ATOM
        step = expr_to_str(node.step)
        # +step makes the inclusive Mathcad endpoint land in the array.
        return f"np.arange({start}, ({stop}) + ({step}), {step})", _ATOM

    if isinstance(node, ir.Program):
        # Inline fallback (a chain of ternaries); a Program that is a Define's
        # value is emitted as a multi-line ``def`` by ``assignment_line``.
        return _program_ternary(node.branches), _ATOM

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
    """The ``target = value`` line(s) for a Define.

    A function whose body is a Mathcad program (if/elif/else) becomes a
    multi-line ``def`` so the branching is preserved; other functions become a
    ``lambda``; plain definitions become an assignment.
    """
    if isinstance(define.value, ir.Program):
        return _program_def(define)
    rhs = expr_to_str(define.value)
    if define.params:
        return f"{define.target.py} = lambda {', '.join(define.params)}: {rhs}"
    return f"{define.target.py} = {rhs}"


def _program_def(define: ir.Define) -> str:
    """Emit a ``def`` with if/elif/else returns for a program-bodied function."""
    params = ", ".join(define.params)
    lines = [f"def {define.target.py}({params}):"]
    for i, (test, result) in enumerate(define.value.branches):
        if test is None:
            lines.append(f"    return {expr_to_str(result)}")
        else:
            keyword = "if" if i == 0 else "elif"
            lines.append(f"    {keyword} {expr_to_str(test)}:")
            lines.append(f"        return {expr_to_str(result)}")
    return "\n".join(lines)


def _program_ternary(branches: list[tuple[ir.Expr | None, ir.Expr]]) -> str:
    """A chain of conditional expressions for an inline program."""
    expr = "None  # no else branch"
    for test, result in reversed(branches):
        if test is None:
            expr = expr_to_str(result)
        else:
            expr = f"{expr_to_str(result)} if {expr_to_str(test)} else {expr}"
    return expr


def echo_expr(region: ir.Region) -> str | None:
    """The expression to display for an evaluated region, or None.

    Applies the worksheet's display-unit override via ``.to(ureg.<unit>)``.
    """
    if isinstance(region, ir.Define):
        if not region.evaluate:
            return None
        target = region.target.py
        if region.display_unit is not None:
            return f"{target}.to({expr_to_str(region.display_unit)})"
        return target
    if isinstance(region, ir.Evaluate):
        base = expr_to_str(region.value)
        if region.display_unit is not None:
            return f"({base}).to({expr_to_str(region.display_unit)})"
        return base
    return None


def declaration_lines(region: ir.SymbolDeclarations) -> list[str]:
    """``x = Symbol('x')`` lines for a symbol-declaration region."""
    return [f"{name} = Symbol('{name}')" for name in region.names]


def symbolic_eval_expr(region: ir.SymbolicEval) -> str:
    """The ``solve(Eq(...), C)``-style call for a symbolic evaluation."""
    parts = [expr_to_str(region.expr)] + [expr_to_str(a) for a in region.args]
    return f"{region.command}({', '.join(parts)})"


# ---------------------------------------------------------------------------
# Imports needed by a worksheet
# ---------------------------------------------------------------------------


def header_lines(ws: ir.Worksheet) -> list[str]:
    """Import/setup lines for the generated module, tailored to what's used."""
    lines = ["import math"]
    if _uses_numpy(ws):
        lines.append("import numpy as np")
    lines.append("import pint")
    sympy_names = _sympy_imports(ws)
    if sympy_names:
        order = ["Eq", "Symbol", "solve", "simplify", "factor", "expand"]
        ordered = [n for n in order if n in sympy_names]
        ordered += sorted(sympy_names - set(order))
        lines.append(f"from sympy import {', '.join(ordered)}")
    lines.append("")
    runtime = _used_runtime(ws)
    if runtime:
        order = [*RUNTIME_IMPORTS, "col", "vectorize"]
        names = ", ".join(n for n in order if n in runtime)
        lines.append(f"from mcad2py.runtime import {names}")
    lines.append("ureg = pint.UnitRegistry()")
    return lines


def _uses_numpy(ws: ir.Worksheet) -> bool:
    """True if the generated module needs ``np`` (arrays, ranges, np.* calls)."""
    for region in ws.regions:
        for node in _region_exprs(region):
            for sub in _walk(node):
                if isinstance(sub, (ir.MatrixLiteral, ir.Range)):
                    return True
                if isinstance(sub, ir.Call) and FUNCTIONS.get(sub.func, "").startswith("np."):
                    return True
    return False


def _sympy_imports(ws: ir.Worksheet) -> set[str]:
    """SymPy names the generated module needs (``Eq``/``Symbol``/commands)."""
    names: set[str] = set()
    for region in ws.regions:
        if isinstance(region, ir.SymbolDeclarations):
            names.add("Symbol")
        elif isinstance(region, ir.SymbolicEquation):
            names.add("Eq")
        elif isinstance(region, ir.SymbolicEval):
            names.add(region.command)
            if any(isinstance(e, ir.Equation) for e in _walk(region.expr)):
                names.add("Eq")
    return names


def _used_runtime(ws: ir.Worksheet) -> set[str]:
    """Runtime-helper names the generated module imports (trig, col, vectorize)."""
    found: set[str] = set()
    for region in ws.regions:
        for node in _region_exprs(region):
            for sub in _walk(node):
                if isinstance(sub, ir.Call) and sub.func in RUNTIME_IMPORTS:
                    found.add(sub.func)
                elif isinstance(sub, ir.MatrixLiteral):
                    found.add("col")
                elif isinstance(sub, ir.Vectorize):
                    found.add("vectorize")
    return found


def _region_exprs(region: ir.Region) -> list[ir.Expr]:
    if isinstance(region, ir.Define):
        return [region.value]
    if isinstance(region, ir.Evaluate):
        return [region.value]
    if isinstance(region, ir.SymbolicEquation):
        return [region.equation]
    if isinstance(region, ir.SymbolicEval):
        return [region.expr, *region.args]
    return []


def _walk(node: ir.Expr) -> list[ir.Expr]:
    """The node and all of its descendant expressions (pre-order)."""
    out = [node]
    for child in ir.child_exprs(node):
        out.extend(_walk(child))
    return out
