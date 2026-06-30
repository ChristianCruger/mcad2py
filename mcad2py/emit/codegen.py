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

    if isinstance(node, ir.Transpose):
        return f"transpose({expr_to_str(node.operand)})", _ATOM

    if isinstance(node, ir.Lambda):
        return f"lambda {', '.join(node.params)}: {expr_to_str(node.body)}", 0

    if isinstance(node, ir.Integral):
        return (
            f"integral({expr_to_str(node.func)}, "
            f"{expr_to_str(node.lower)}, {expr_to_str(node.upper)})",
            _ATOM,
        )

    if isinstance(node, ir.Summation):
        return (
            f"summation({expr_to_str(node.func)}, "
            f"{expr_to_str(node.lower)}, {expr_to_str(node.upper)})",
            _ATOM,
        )

    if isinstance(node, ir.Range):
        start = expr_to_str(node.start)
        stop = expr_to_str(node.stop)
        step = expr_to_str(node.step) if node.step is not None else "1"
        # arange() is a unit-aware, inclusive range helper.
        return f"arange({start}, {stop}, {step})", _ATOM

    if isinstance(node, ir.Program):
        # Inline fallback (a chain of ternaries); a Program that is a Define's
        # value is emitted as a multi-line ``def`` by ``assignment_line``.
        return _program_ternary(node.branches), _ATOM

    if isinstance(node, ir.Str):
        return repr(node.value), _ATOM

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
    prefix = ""
    if define.comment:
        prefix = "".join(f"# {line}\n" for line in define.comment.splitlines())
    # A program-bodied *function* (``σ_c(e) := <if/elif/else>``) becomes a
    # multi-line ``def``; a program assigned to a plain variable (e.g. an inline
    # ``if(cond, a, b)``) has no params and emits an inline conditional instead.
    if isinstance(define.value, ir.Program) and define.params:
        return prefix + _program_def(define)
    rhs = expr_to_str(define.value)
    if define.params:
        return f"{prefix}{define.target.py} = lambda {', '.join(define.params)}: {rhs}"
    return f"{prefix}{define.target.py} = {rhs}"


def index_assign_line(region: ir.IndexAssign) -> str:
    """``X = index_build(i, lambda i: expr)`` for a range-indexed assignment.

    The lambda parameter reuses the index variable's name so ``X[i]`` reads in
    the right-hand side resolve against the *scalar* loop index.
    """
    idx = region.index.py
    return f"{region.target.py} = index_build({idx}, lambda {idx}: {expr_to_str(region.value)})"


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
            return _display(target, region.display_unit)
        return target
    if isinstance(region, ir.Evaluate):
        base = expr_to_str(region.value)
        if region.display_unit is not None:
            return _display(f"({base})", region.display_unit)
        return base
    if isinstance(region, ir.IndexAssign):
        if not region.evaluate:
            return None
        # Mathcad's inline ``=`` after ``X[i] := …`` shows the vector read at the
        # range index -- a sub-vector (``X[i]`` with ``i`` the integer range).
        base = f"{region.target.py}[{region.index.py}]"
        if region.display_unit is not None:
            return _display(f"({base})", region.display_unit)
        return base
    return None


def _display(value: str, unit: ir.Expr) -> str:
    """Render a value in its display unit.

    A real unit (``mm``, ``kN*m``) uses ``.to(<unit>)``; a pure numeric scale
    (Mathcad showing a dimensionless result as e.g. ``×10**-6``) divides instead,
    since ``.to`` only applies to a dimensioned quantity.
    """
    unit_s = expr_to_str(unit)
    if _has_unit(unit):
        return f"{value}.to({unit_s})"
    return f"{value} / ({unit_s})"


def _has_unit(node: ir.Expr) -> bool:
    """True if the expression references any unit (vs. a bare numeric scale)."""
    if isinstance(node, ir.UnitRef):
        return True
    return any(_has_unit(child) for child in ir.child_exprs(node))


def declaration_lines(region: ir.SymbolDeclarations) -> list[str]:
    """``x = Symbol('x')`` lines for a symbol-declaration region."""
    return [f"{name} = Symbol('{name}')" for name in region.names]


def symbolic_eval_expr(region: ir.SymbolicEval) -> str:
    """The ``solve(Eq(...), C)``-style call for a symbolic evaluation."""
    parts = [expr_to_str(region.expr)] + [expr_to_str(a) for a in region.args]
    return f"{region.command}({', '.join(parts)})"


def plot_lines(region: ir.Plot) -> list[str]:
    """Emit a matplotlib figure for an X-Y plot.

    Each trace's non-domain expression is sampled element-wise over the domain
    array (``sample(lambda d: expr, d)``) so branching programs and units work;
    ``plot_axis`` applies Mathcad's value/unit axis scaling.
    """
    domain = region.domain
    lines = ["_fig, _ax = plt.subplots()"]
    for trace in region.traces:
        x = _plot_axis_call(trace.x, trace.x_unit, domain)
        y = _plot_axis_call(trace.y, trace.y_unit, domain)
        series = trace.y if _is_domain(trace.x, domain) else trace.x
        label = expr_to_str(series)
        color = f", color={trace.color!r}" if trace.color else ""
        lines.append(f"_ax.plot({x}, {y}, label={label!r}{color})")
    lines.append("_ax.axhline(0, color='0.6', linewidth=0.8)")
    lines.append("_ax.axvline(0, color='0.6', linewidth=0.8)")
    lines.append("_ax.grid(True, alpha=0.3)")
    lines.append(f"_ax.set_xlabel({_axis_label(region, axis='x')!r})")
    lines.append(f"_ax.set_ylabel({_axis_label(region, axis='y')!r})")
    lines.append("_ax.legend()")
    lines.append("plt.show()")
    return lines


def _is_domain(expr: ir.Expr, domain: str | None) -> bool:
    return isinstance(expr, ir.Name) and expr.py == domain


def _plot_axis_call(expr: ir.Expr, unit: ir.Expr | None, domain: str | None) -> str:
    """``plot_axis(<data>, <unit>)`` where data is the domain array directly or
    the expression sampled element-wise over the domain."""
    if _is_domain(expr, domain) or domain is None:
        data = expr_to_str(expr)
    else:
        data = f"sample(lambda {domain}: {expr_to_str(expr)}, {domain})"
    unit_s = expr_to_str(unit) if unit is not None else "None"
    return f"plot_axis({data}, {unit_s})"


def _axis_label(region: ir.Plot, *, axis: str) -> str:
    """A short axis label: the domain name, or the shared unit of that axis."""
    exprs = [(t.x, t.x_unit) for t in region.traces] if axis == "x" else [
        (t.y, t.y_unit) for t in region.traces
    ]
    expr, unit = exprs[0]
    unit_text = _unit_label(unit)
    if _is_domain(expr, region.domain):
        return f"{expr_to_str(expr)} ({unit_text})" if unit_text else expr_to_str(expr)
    return f"({unit_text})" if unit_text else ""


def _unit_label(unit: ir.Expr | None) -> str:
    if unit is None:
        return ""
    if isinstance(unit, ir.UnitRef):
        return unit.name
    return expr_to_str(unit)


def solve_block_lines(region: ir.SolveBlock) -> list[str]:
    """Emit a numeric solve block: guesses, a residual function, solve_block().

    ``[e_1; k_1] := find(e, k)`` with constraints ``N_int(e,k)=N_ext`` etc.
    becomes guess assignments, a ``def`` returning the constraint residuals
    (``lhs - rhs``), and a ``solve_block`` call destructured into the targets.

    When the block *defines a function* (``f(a, b) := find(x)``, ``region.params``
    set), the same machinery is emitted inside ``def f(a, b):`` so the
    constraints close over the parameters, and the solved unknown(s) are returned.
    """
    unknowns = [u.py for u in region.unknowns]
    body = _solve_block_body(region, unknowns)
    call = f"solve_block({_resid_name(region, unknowns)}, [{', '.join(unknowns)}])"

    if region.params:
        fname = region.targets[0].py
        ret = f"{call}[0]" if len(unknowns) == 1 else call
        return (
            [f"def {fname}({', '.join(region.params)}):"]
            + [f"    {line}" for line in body]
            + [f"    return {ret}"]
        )

    targets = [t.py for t in region.targets]
    if len(targets) == 1:
        tail = f"{targets[0]} = {call}[0]"
    else:
        tail = f"{', '.join(targets)} = {call}"
    return body + [tail]


def _resid_name(region: ir.SolveBlock, unknowns: list[str]) -> str:
    """The residual function's name: from the unknowns for a function-defining
    block, from the targets otherwise (preserving the established naming)."""
    if region.params:
        return "_residuals_" + "_".join(unknowns)
    return "_residuals_" + "_".join(t.py for t in region.targets)


def _solve_block_body(region: ir.SolveBlock, unknowns: list[str]) -> list[str]:
    """Guess assignments plus the ``def _residuals(_x)`` returning lhs - rhs."""
    resid = _resid_name(region, unknowns)
    lines = [assignment_line(g) for g in region.guesses]
    lines.append(f"def {resid}(_x):")
    unpack = ", ".join(unknowns)
    lines.append(f"    {unpack}, = _x" if len(unknowns) == 1 else f"    {unpack} = _x")
    lines.append("    return [")
    for c in region.constraints:
        lines.append(f"        {expr_to_str(c.lhs)} - ({expr_to_str(c.rhs)}),")
    lines.append("    ]")
    return lines


# ---------------------------------------------------------------------------
# Imports needed by a worksheet
# ---------------------------------------------------------------------------


def header_lines(ws: ir.Worksheet) -> list[str]:
    """Import/setup lines for the generated module, tailored to what's used."""
    lines = ["import math"]
    if _uses_numpy(ws):
        lines.append("import numpy as np")
    if any(isinstance(r, ir.Plot) for r in ws.regions):
        lines.append("import matplotlib.pyplot as plt")
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
        order = [
            *RUNTIME_IMPORTS,
            "col", "arange", "index_build", "vectorize", "transpose",
            "integral", "summation", "solve_block", "sample", "plot_axis",
        ]
        names = ", ".join(n for n in order if n in runtime)
        lines.append(f"from mcad2py.runtime import {names}")
    lines.append("ureg = pint.UnitRegistry()")
    return lines


def _uses_numpy(ws: ir.Worksheet) -> bool:
    """True if the generated module needs ``np`` (arrays, ranges, np.* calls)."""
    for region in ws.regions:
        for node in _region_exprs(region):
            for sub in _walk(node):
                # General rows×cols matrices emit a bare ``np.array([...])``;
                # vectors/ranges go through the col()/arange() helpers instead.
                if isinstance(sub, ir.MatrixLiteral) and min(sub.rows, sub.cols) > 1:
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
        if isinstance(region, ir.SolveBlock):
            found.add("solve_block")
        if isinstance(region, ir.IndexAssign):
            found.add("index_build")
        if isinstance(region, ir.Plot):
            found.update(("sample", "plot_axis"))
        for node in _region_exprs(region):
            for sub in _walk(node):
                if isinstance(sub, ir.Call) and sub.func in RUNTIME_IMPORTS:
                    found.add(sub.func)
                elif isinstance(sub, ir.MatrixLiteral):
                    found.add("col")
                elif isinstance(sub, ir.Range):
                    found.add("arange")
                elif isinstance(sub, ir.Vectorize):
                    found.add("vectorize")
                elif isinstance(sub, ir.Transpose):
                    found.add("transpose")
                elif isinstance(sub, ir.Integral):
                    found.add("integral")
                elif isinstance(sub, ir.Summation):
                    found.add("summation")
    return found


def _region_exprs(region: ir.Region) -> list[ir.Expr]:
    if isinstance(region, ir.Define):
        return [region.value]
    if isinstance(region, (ir.Evaluate, ir.IndexAssign)):
        return [region.value]
    if isinstance(region, ir.SymbolicEquation):
        return [region.equation]
    if isinstance(region, ir.SymbolicEval):
        return [region.expr, *region.args]
    if isinstance(region, ir.SolveBlock):
        exprs: list[ir.Expr] = [g.value for g in region.guesses]
        for c in region.constraints:
            exprs += [c.lhs, c.rhs]
        return exprs
    if isinstance(region, ir.Plot):
        plot_exprs: list[ir.Expr] = []
        for t in region.traces:
            plot_exprs += [t.x, t.y]
        return plot_exprs
    return []


def _walk(node: ir.Expr) -> list[ir.Expr]:
    """The node and all of its descendant expressions (pre-order)."""
    out = [node]
    for child in ir.child_exprs(node):
        out.extend(_walk(child))
    return out
