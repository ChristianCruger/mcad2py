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
        # (A ``*`` that is a matrix/dot product has already been rewritten into
        # a ``matmul`` Call by the shape pass -- see mcad2py/shapes.py.)
        # A *fractional* power reduces a dimensionless base first (so ``ρ**(1/3)``
        # on an unreduced ``mm²/mm²`` ratio doesn't leave fractional-unit noise);
        # an integer power (``x**2``) stays a clean inline ``**``.
        if node.op == "pow" and not _is_int_literal(node.right):
            return (
                f"power({expr_to_str(node.left)}, {expr_to_str(node.right)})",
                _ATOM,
            )
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
        # Mathcad ``min``/``max`` are always a *reduction*: they flatten every
        # argument (scalars and vectors) and return the single min/max
        # (``mc_min``/``mc_max``). Element-wise behaviour comes from the
        # vectorize *arrow* applying a function per element, not from min/max --
        # so there's no ``np.minimum``/``np.maximum`` here.
        if node.func in ("min", "max"):
            func = "mc_min" if node.func == "min" else "mc_max"
        else:
            func = FUNCTIONS.get(node.func, node.func)
        args = ", ".join(expr_to_str(a) for a in node.args)
        return f"{func}({args})", _ATOM

    if isinstance(node, ir.Root):
        # ``nth_root`` (not ``math.sqrt``/inline ``**``) so Pint handles a
        # unit-bearing radicand (``√(m²) = m``) and a dimensionless radicand is
        # reduced first (no fractional ``mm ** 0.5`` unit noise).
        operand = expr_to_str(node.operand)
        degree = "2" if node.degree is None else expr_to_str(node.degree)
        return f"nth_root({operand}, {degree})", _ATOM

    if isinstance(node, ir.Equation):
        return f"Eq({expr_to_str(node.lhs)}, {expr_to_str(node.rhs)})", _ATOM

    if isinstance(node, ir.MatrixLiteral):
        elems = ", ".join(expr_to_str(e) for e in node.elements)
        if node.cols <= 1:  # vector -> 1-D array
            return f"col({elems})", _ATOM
        return f"matrix({node.rows}, {node.cols}, {elems})", _ATOM

    if isinstance(node, ir.Index):
        base = _wrap(node.base, _ATOM, is_left=True, right_assoc=False)
        return f"{base}[{expr_to_str(node.index)}]", _ATOM

    if isinstance(node, ir.Index2D):
        # ``matelem``, not ``base[i, j]``: a Mathcad row/column vector is stored
        # here as a 1-D array, which NumPy won't accept two subscripts for.
        return (
            f"matelem({expr_to_str(node.base)}, "
            f"{expr_to_str(node.row)}, {expr_to_str(node.col)})",
            _ATOM,
        )

    if isinstance(node, ir.MatCol):
        return f"matcol({expr_to_str(node.base)}, {expr_to_str(node.index)})", _ATOM

    if isinstance(node, ir.ProgramBlock):
        # A ProgramBlock is only ever a Define/MultiAssign value (emitted as a
        # ``def`` by assignment_line/multi_assign_lines), never inline.
        return "None  # TODO: program block used inline", _ATOM

    if isinstance(node, ir.VectorSum):
        return f"total({expr_to_str(node.operand)})", _ATOM

    if isinstance(node, ir.Vectorize):
        return f"vectorize({expr_to_str(node.operand)})", _ATOM

    if isinstance(node, ir.Transpose):
        return f"transpose({expr_to_str(node.operand)})", _ATOM

    if isinstance(node, ir.Lambda):
        return f"lambda {', '.join(node.params)}: {expr_to_str(node.body)}", 0

    if isinstance(node, ir.Integral):
        inner = _nested_double_integral(node)
        if inner is not None:
            outer_param = node.func.params[0]  # type: ignore[union-attr]
            inner_param = inner.func.params[0]  # type: ignore[union-attr]
            return (
                f"double_integral(lambda {inner_param}, {outer_param}: "
                f"{expr_to_str(inner.func.body)}, "  # type: ignore[union-attr]
                f"{expr_to_str(inner.lower)}, {expr_to_str(inner.upper)}, "
                f"{expr_to_str(node.lower)}, {expr_to_str(node.upper)})",
                _ATOM,
            )
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


def _is_int_literal(node: ir.Expr) -> bool:
    """True if ``node`` is an integer numeric literal (optionally negated)."""
    if isinstance(node, ir.UnaryOp) and node.op == "neg":
        return _is_int_literal(node.operand)
    if isinstance(node, ir.Number):
        try:
            return float(node.value).is_integer()
        except ValueError:
            return False
    return False


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
        return prefix + _program_def(define) + _elementwise_wrap(define)
    # An imperative multi-line program (loops/return/tryCatch) -> a ``def``:
    # a function (``Neutral(e,kx,ky) := …``) keeps its params; a plain variable
    # (``As := …``) is a nullary helper whose result is bound to the name.
    if isinstance(define.value, ir.ProgramBlock):
        if define.params:
            return prefix + "\n".join(
                _program_block_def(define.target.py, define.params, define.value)
            ) + _elementwise_wrap(define)
        helper = f"_{define.target.py}"
        lines = _program_block_def(helper, [], define.value)
        lines.append(f"{define.target.py} = {helper}()")
        return prefix + "\n".join(lines)
    rhs = expr_to_str(define.value)
    if define.params:
        return (
            f"{prefix}{define.target.py} = lambda {', '.join(define.params)}: {rhs}"
            + _elementwise_wrap(define)
        )
    return f"{prefix}{define.target.py} = {rhs}"


def status_control_line(region: ir.StatusControl) -> str:
    """``print("<expr>", <expr>, "<message>")`` for a scriptable status widget.

    Prints the expression's source, its live value, and the message Mathcad
    cached -- the JScript that would pick the message from the value isn't
    transpiled, so we surface both so the reader can see how they relate.
    """
    expr_s = expr_to_str(region.value)
    return f"print({expr_s!r}, {expr_s}, {region.message!r})"


def multi_assign_lines(region: ir.MultiAssign) -> list[str]:
    """``a, b, c = tuple(<value>)`` for a destructuring assignment.

    ``tuple(...)`` unpacks the returned vector (NumPy/Pint/object array) element
    by element, so each target binds one component (units preserved). When the
    value is an imperative program, it's emitted as a nullary helper ``def`` and
    its returned vector destructured. A 2-D target (``[a b; c d] := M``) names
    every element of a matrix; ``unpack`` flattens it column-major first -- the
    order Mathcad lists the target ids in.
    """
    names = ", ".join(t.py for t in region.targets)
    if isinstance(region.value, ir.ProgramBlock):
        helper = "_" + "_".join(t.py for t in region.targets)
        lines = _program_block_def(helper, [], region.value)
        lines.append(f"{names} = tuple({helper}())")
        return lines
    value = expr_to_str(region.value)
    if region.matrix_target:
        value = f"unpack({value})"
    return [f"{names} = tuple({value})"]


def _program_block_def(name: str, params: list[str], block: ir.ProgramBlock) -> list[str]:
    """A ``def name(params):`` whose body is an imperative ProgramBlock.

    Any name written as a vector/matrix element (``X[i] := …``) is pre-declared
    ``= None`` so the growable ``vec_set`` helper can create it on first write.
    """
    lines = [f"def {name}({', '.join(params)}):"]
    lines += [f"    {n} = None" for n in _growable_names(block)]
    body = _block_lines(block, 1)
    lines += body if body else ["    pass"]
    return lines


def _block_lines(block: ir.ProgramBlock, indent: int) -> list[str]:
    out: list[str] = []
    for stmt in block.statements:
        out += _stmt_lines(stmt, indent)
    return out


def _stmt_lines(stmt: ir.Stmt, indent: int) -> list[str]:
    pad = "    " * indent
    if isinstance(stmt, ir.LocalAssign):
        target, value = stmt.target, stmt.value
        if isinstance(target, ir.Name):
            return [f"{pad}{target.py} = {expr_to_str(value)}"]
        if isinstance(target, ir.Index):
            base = expr_to_str(target.base)
            return [
                f"{pad}{base} = vec_set({base}, {expr_to_str(target.index)}, "
                f"{expr_to_str(value)})"
            ]
        if isinstance(target, ir.Index2D):
            base = expr_to_str(target.base)
            return [
                f"{pad}{base} = vec_set({base}, "
                f"({expr_to_str(target.row)}, {expr_to_str(target.col)}), "
                f"{expr_to_str(value)})"
            ]
        return [f"{pad}{expr_to_str(target)} = {expr_to_str(value)}"]
    if isinstance(stmt, ir.ForLoop):
        lines = [f"{pad}for {stmt.var.py} in {expr_to_str(stmt.iterable)}:"]
        inner = _block_lines(stmt.body, indent + 1)
        return lines + (inner if inner else [f"{pad}    pass"])
    if isinstance(stmt, ir.IfStmt):
        lines = []
        for i, (test, body) in enumerate(stmt.branches):
            if test is None:
                lines.append(f"{pad}else:")
            else:
                lines.append(f"{pad}{'if' if i == 0 else 'elif'} {expr_to_str(test)}:")
            inner = _block_lines(body, indent + 1)
            lines += inner if inner else [f"{pad}    pass"]
        return lines
    if isinstance(stmt, ir.Return):
        return [f"{pad}return {expr_to_str(stmt.value)}"]
    if isinstance(stmt, ir.TryCatch):
        lines = [f"{pad}try:"]
        inner = _block_lines(stmt.body, indent + 1)
        lines += inner if inner else [f"{pad}    pass"]
        lines.append(f"{pad}except Exception:")
        inner = _block_lines(stmt.handler, indent + 1)
        lines += inner if inner else [f"{pad}    pass"]
        return lines
    return [f"{pad}pass  # TODO unsupported statement"]


def _growable_names(block: ir.ProgramBlock) -> list[str]:
    """Names written via ``X[i] := …`` anywhere in ``block`` (first-seen order);
    these are pre-declared ``= None`` so ``vec_set`` can create them."""
    names: list[str] = []

    def scan(b: ir.ProgramBlock) -> None:
        for stmt in b.statements:
            if isinstance(stmt, ir.LocalAssign) and isinstance(
                stmt.target, (ir.Index, ir.Index2D)
            ):
                base = stmt.target.base
                if isinstance(base, ir.Name) and base.py not in names:
                    names.append(base.py)
            elif isinstance(stmt, ir.ForLoop):
                scan(stmt.body)
            elif isinstance(stmt, ir.IfStmt):
                for _test, body in stmt.branches:
                    scan(body)
            elif isinstance(stmt, ir.TryCatch):
                scan(stmt.body)
                scan(stmt.handler)

    scan(block)
    return names


def combobox_assign_lines(region: ir.ComboBoxAssign) -> list[str]:
    """Emit the selected-row assignment(s) for a ComboBox, documenting the pick."""
    lines = [f"# {line}" for line in (region.comment or "").splitlines()]
    for target, value in zip(region.targets, region.values):
        lines.append(f"{target.py} = {expr_to_str(value)}")
    return lines


def index_assign_line(region: ir.IndexAssign) -> str:
    """``X = index_build(i, lambda i: expr)`` for a range-indexed assignment.

    The lambda parameter reuses the index variable's name so ``X[i]`` reads in
    the right-hand side resolve against the *scalar* loop index. The
    two-subscript form ``X[i, j] :=`` builds a matrix over both ranges'
    outer product instead (``index_build_2d``).
    """
    idx = region.index.py
    body = expr_to_str(region.value)
    if region.col_index is not None:
        jdx = region.col_index.py
        return (
            f"{region.target.py} = index_build_2d({idx}, {jdx}, "
            f"lambda {idx}, {jdx}: {body})"
        )
    return f"{region.target.py} = index_build({idx}, lambda {idx}: {body})"


def _needs_elementwise(define: ir.Define) -> bool:
    """True for a *single-argument* scalar function that Mathcad's vectorize
    arrow applies per element: a branching program (``σ_c``) or a *clamp* built
    from a two-argument ``min``/``max`` (``σ_s`` = ``min(f, max(-f, E·ε))``).
    Wrapping it in ``elementwise`` lets it accept a whole strain vector (mapped
    per element), since a program ``if`` can't take an array and min/max reduce;
    it's a pass-through for scalar calls. A *single*-argument min/max is instead
    a reduction of the argument vector (e.g. ``UR(ε) := min(ε)/ε_cu``) -- that
    function must stay a reduction, so it is not wrapped."""
    if len(define.params) != 1:
        return False
    if isinstance(define.value, (ir.Program, ir.ProgramBlock)):
        return True
    return _contains_minmax_clamp(define.value)


def _contains_minmax_clamp(node: ir.Expr) -> bool:
    """A two-argument ``min``/``max`` (a clamp/comparison), not a single-argument
    reduction, anywhere in ``node``."""
    if isinstance(node, ir.Call) and node.func in ("min", "max") and len(node.args) >= 2:
        return True
    return any(_contains_minmax_clamp(c) for c in ir.child_exprs(node))


def _elementwise_wrap(define: ir.Define) -> str:
    """A trailing ``name = elementwise(name)`` line (or ``""``) -- see
    :func:`_needs_elementwise`."""
    if _needs_elementwise(define):
        return f"\n{define.target.py} = elementwise({define.target.py})"
    return ""


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
        return _auto(target, region)
    if isinstance(region, ir.Evaluate):
        base = expr_to_str(region.value)
        if region.display_unit is not None:
            return _display(f"({base})", region.display_unit)
        return _auto(base, region)
    if isinstance(region, ir.MultiAssign):
        if not region.evaluate:
            return None
        inner = "[" + ", ".join(t.py for t in region.targets) + "]"
        if region.display_unit is not None:
            return _display(f"({inner})", region.display_unit)
        return inner
    if isinstance(region, ir.IndexAssign):
        if not region.evaluate:
            return None
        # Mathcad's inline ``=`` after ``X[i] := …`` shows the vector read at the
        # range index -- a sub-vector (``X[i]`` with ``i`` the integer range).
        # The two-subscript form covers the whole matrix, so it echoes bare.
        base = (
            region.target.py
            if region.col_index is not None
            else f"{region.target.py}[{region.index.py}]"
        )
        if region.display_unit is not None:
            return _display(f"({base})", region.display_unit)
        return _auto(base, region)
    return None


def _auto(value: str, region: ir.Region) -> str:
    """An echo with no display override -- Mathcad's *automatic* display.

    Wrapped in ``disp(...)`` only when the value came from a division, the one
    place Pint can leave a dimensionless result unreduced (``sin(θ)/θ`` as
    ``1/degree``, ``l/s`` as ``m/mm``) where Mathcad shows the plain number.
    Everything else echoes bare, so generated cells stay readable.
    """
    return f"disp({value})" if _has_division(getattr(region, "value", None)) else value


def _has_division(node: ir.Expr | None) -> bool:
    """True if ``node`` divides anywhere (including a reciprocal ``x**-n``)."""
    if node is None:
        return False
    for sub in _walk(node):
        if isinstance(sub, ir.BinOp) and sub.op == "div":
            return True
        if (
            isinstance(sub, ir.BinOp)
            and sub.op == "pow"
            and isinstance(sub.right, ir.UnaryOp)
        ):
            return True
    return False


def _display(value: str, unit: ir.Expr) -> str:
    """Render a value in its display unit.

    A real unit (``mm``, ``kN*m``) uses ``.to(<unit>)``; a pure numeric scale
    (Mathcad showing a dimensionless result as e.g. ``×10**-6``) divides instead,
    since ``.to`` only applies to a dimensioned quantity.
    """
    unit_s = expr_to_str(unit)
    if _has_unit(unit):
        # ``disp`` converts if compatible, else divides (residual-unit display),
        # so a loose override (a moment shown in ``kN``) can't crash the echo.
        return f"disp({value}, {unit_s})"
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

    An *implicit* domain (a plot of a free variable, with no ``x :=`` in the
    sheet) is built here from Mathcad's default interval. It goes into a
    private ``_domain_<name>`` rather than the name itself, since Mathcad
    invents the variable for the plot alone -- it must not leak into the
    regions below.
    """
    domain = region.domain
    lines: list[str] = []
    if region.implicit_domain is not None:
        start, stop, num = region.implicit_domain
        lines.append(f"{_domain_var(region)} = plot_domain({start}, {stop}, {num})")
    lines.append("_fig, _ax = plt.subplots()")
    for trace in region.traces:
        x = _plot_axis_call(trace.x, trace.x_unit, domain, _domain_var(region))
        y = _plot_axis_call(trace.y, trace.y_unit, domain, _domain_var(region))
        label = expr_to_str(_trace_series(trace, region))
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


def grid_plot_lines(region: ir.GridPlot) -> list[str]:
    """Emit a matplotlib figure for a contour (``<contourPlot>``) or 3D
    (``<plot3D>``) plot.

    The plot equation resolves to ``(X, Y, Z, kind)`` at runtime via
    ``resolve_plot_grid`` -- ``kind`` is ``"grid"`` (a regular surface:
    ``contourf``/``plot_surface``) or ``"scatter"`` (an irregular ``(x,y,z)``
    point list -- Mathcad's 3-column-matrix convention -- rendered with
    ``tricontourf``/a bare 3D scatter). An expression over two *ranges*
    (``mesh_names`` set) is wrapped in a lambda over those two names and
    passed to ``mesh_grid``, which takes their outer product first, since
    Mathcad doesn't zip ranges elementwise -- this covers both a direct call
    (``f(x0, y0)``) and a composition (``sigma(epsilon(x0*mm, y0*mm))``).
    """
    if region.mesh_names is not None:
        x_name, y_name = region.mesh_names
        value = (
            f"mesh_grid(lambda {x_name}, {y_name}: {expr_to_str(region.expr)}, "
            f"{x_name}, {y_name})"
        )
    else:
        value = expr_to_str(region.expr)
    z_unit = expr_to_str(region.z_unit) if region.z_unit is not None else "None"

    lines = [
        f"_X, _Y, _Z, _kind = resolve_plot_grid({value})",
        f"_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, {z_unit})",
    ]
    if region.threed:
        lines += [
            "_fig = plt.figure()",
            "_ax = _fig.add_subplot(projection='3d')",
            "if _kind == 'scatter':",
            "    _ax.scatter(_Xs, _Ys, _Zs)",
            "else:",
            "    _ax.plot_surface(_Xs, _Ys, _Zs, cmap='viridis')",
        ]
    else:
        lines += [
            "_fig, _ax = plt.subplots()",
            "if _kind == 'scatter':",
            "    _cs = _ax.tricontourf(_Xs, _Ys, _Zs)",
            "    _ax.tricontour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)",
            "else:",
            "    _cs = _ax.contourf(_Xs, _Ys, _Zs)",
            "    _ax.contour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)",
            "plt.colorbar(_cs, ax=_ax)",
        ]
    lines.append("plt.show()")
    return lines


def _is_domain(expr: ir.Expr, domain: str | None) -> bool:
    return isinstance(expr, ir.Name) and expr.py == domain


def _domain_var(region: ir.Plot) -> str:
    """The Python variable holding the domain array -- the sheet's own name,
    or a private one when the domain is implicit (invented for this plot)."""
    if region.implicit_domain is None:
        return region.domain or ""
    return f"_domain_{region.domain}"


def _trace_series(trace: ir.PlotTrace, region: ir.Plot) -> ir.Expr:
    """The expression a trace is named after in the legend: the *dependent*
    axis, i.e. whichever one isn't the domain itself.

    With an implicit domain neither axis need be the bare variable (``x/2``
    against ``cos(x)``), so y -- the function being plotted -- always wins. A
    parametric plot has no domain at all and keeps x, which is how a section
    outline reads (``matcol(Contour, 0)``).
    """
    if region.implicit_domain is not None or _is_domain(trace.x, region.domain):
        return trace.y
    return trace.x


def _plot_axis_call(
    expr: ir.Expr, unit: ir.Expr | None, domain: str | None, domain_var: str
) -> str:
    """``plot_axis(<data>, <unit>)`` where data is the domain array directly or
    the expression sampled element-wise over the domain.

    An expression that never mentions the domain variable is **not** a function
    of it, so it isn't sampled: one plot may carry both a parametric trace (two
    data vectors, cached ``TraceType="Vector"``) and a function trace (cached
    ``TraceType="Range"``), and the parametric one keeps its own length rather
    than being evaluated once per domain point. ``static_axis`` settles the one
    ambiguous case at runtime -- a *scalar* that ignores the domain is a
    reference line and does span it.
    """
    if _is_domain(expr, domain):
        data = domain_var
    elif domain is None:
        data = expr_to_str(expr)
    elif not _references(expr, domain):
        data = f"static_axis({expr_to_str(expr)}, {domain_var})"
    else:
        data = f"sample(lambda {domain}: {expr_to_str(expr)}, {domain_var})"
    unit_s = expr_to_str(unit) if unit is not None else "None"
    return f"plot_axis({data}, {unit_s})"


def _references(expr: ir.Expr, name: str) -> bool:
    """True if ``expr`` reads the variable ``name`` anywhere inside it."""
    return any(
        isinstance(sub, ir.Name) and sub.py == name for sub in _walk(expr)
    )


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
    if any(isinstance(r, (ir.Plot, ir.GridPlot)) for r in ws.regions):
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
            "col", "matrix", "arange", "index_build", "index_build_2d",
            "vectorize", "transpose", "matmul", "matcol", "total", "vec_set",
            "unpack", "integral", "double_integral", "summation", "solve_block",
            "sample", "static_axis", "plot_domain", "plot_axis", "mesh_grid",
            "resolve_plot_grid",
        ]
        seen: set[str] = set()
        names = ", ".join(
            n for n in order if n in runtime and not (n in seen or seen.add(n))
        )
        lines.append(f"from mcad2py.runtime import {names}")
    lines.append("ureg = pint.UnitRegistry()")
    return lines


def source_comment(region: ir.Region) -> str | None:
    """``# mcdx region <id>`` back-reference, for ``--trace-source``.

    ``<id>`` is the originating ``<region>``'s ``region-id`` attribute in
    ``worksheet.xml``. Any defined target whose sanitized Python name differs
    from Mathcad's original display name is listed too, since that's the name
    Prime's UI (or MathcadPy) actually knows the value by.
    """
    if region.source_id is None:
        return None
    text = f"# mcdx region {region.source_id}"
    renamed = _renamed_targets(region)
    if renamed:
        text += ", " + ", ".join(f'"{n.original}" -> {n.py}' for n in renamed)
    return text


def _renamed_targets(region: ir.Region) -> list[ir.Name]:
    targets: list[ir.Name] = []
    single = getattr(region, "target", None)
    if isinstance(single, ir.Name):
        targets.append(single)
    targets.extend(getattr(region, "targets", None) or [])
    return [n for n in targets if n.original != n.py]


def _uses_numpy(ws: ir.Worksheet) -> bool:
    """True if the generated module needs ``np`` directly (``np.*`` calls).

    Matrices/vectors/ranges go through the ``matrix()``/``col()``/``arange()``
    runtime helpers, which hide NumPy internally -- the generated script only
    needs a bare ``np.`` for things like the ``min``/``max`` builtins mapping
    to ``np.minimum``/``np.maximum``.
    """
    for region in ws.regions:
        for node in _region_exprs(region):
            for sub in _walk(node):
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
    integrals: list[ir.Integral] = []
    for region in ws.regions:
        du = getattr(region, "display_unit", None)
        if du is not None and _has_unit(du):
            found.add("disp")
        elif du is None and echo_expr(region) is not None and _has_division(
            getattr(region, "value", None)
        ):
            found.add("disp")  # automatic display of a possibly-unreduced ratio
        if isinstance(region, ir.Define) and _needs_elementwise(region):
            found.add("elementwise")
        if isinstance(region, ir.SolveBlock):
            found.add("solve_block")
        if isinstance(region, ir.IndexAssign):
            found.add("index_build_2d" if region.col_index is not None else "index_build")
        if isinstance(region, ir.MultiAssign) and region.matrix_target:
            found.add("unpack")
        if isinstance(region, ir.Plot):
            found.update(("sample", "plot_axis"))
            if region.implicit_domain is not None:
                found.add("plot_domain")
            if region.domain and any(
                not _is_domain(e, region.domain)
                and not _references(e, region.domain)
                for t in region.traces
                for e in (t.x, t.y)
            ):
                found.add("static_axis")
        if isinstance(region, ir.GridPlot):
            found.update(("resolve_plot_grid", "plot_axis"))
            if region.mesh_names is not None:
                found.add("mesh_grid")
        for node in _region_exprs(region):
            for sub in _walk(node):
                if isinstance(sub, ir.Call) and sub.func in ("min", "max"):
                    found.add("mc_min" if sub.func == "min" else "mc_max")
            for sub in _walk(node):
                if isinstance(sub, ir.Call) and FUNCTIONS.get(sub.func, sub.func) in RUNTIME_IMPORTS:
                    found.add(FUNCTIONS.get(sub.func, sub.func))
                elif isinstance(sub, ir.MatrixLiteral):
                    found.add("col" if sub.cols <= 1 else "matrix")
                elif isinstance(sub, ir.Range):
                    found.add("arange")
                elif isinstance(sub, ir.Vectorize):
                    found.add("vectorize")
                elif isinstance(sub, ir.Transpose):
                    found.add("transpose")
                elif isinstance(sub, ir.Root):
                    found.add("nth_root")
                elif (
                    isinstance(sub, ir.BinOp)
                    and sub.op == "pow"
                    and not _is_int_literal(sub.right)
                ):
                    found.add("power")
                elif isinstance(sub, ir.MatCol):
                    found.add("matcol")
                elif isinstance(sub, ir.Index2D):
                    found.add("matelem")
                elif isinstance(sub, ir.VectorSum):
                    found.add("total")
                elif isinstance(sub, ir.ProgramBlock):
                    if _growable_names(sub):
                        found.add("vec_set")
                elif isinstance(sub, ir.Integral):
                    integrals.append(sub)
                elif isinstance(sub, ir.Summation):
                    found.add("summation")
    # A nested (rectangular double) Integral emits one double_integral() call,
    # not two integral() calls -- so its inner Integral isn't independently used.
    nested = {id(n): _nested_double_integral(n) for n in integrals}
    absorbed = {id(inner) for inner in nested.values() if inner is not None}
    for n in integrals:
        if nested[id(n)] is not None:
            found.add("double_integral")
        elif id(n) not in absorbed:
            found.add("integral")
    return found


def _region_exprs(region: ir.Region) -> list[ir.Expr]:
    if isinstance(region, ir.Define):
        return [region.value]
    if isinstance(region, (ir.Evaluate, ir.IndexAssign)):
        return [region.value]
    if isinstance(region, ir.MultiAssign):
        return [region.value]
    if isinstance(region, ir.StatusControl):
        return [region.value]
    if isinstance(region, ir.ComboBoxAssign):
        return list(region.values)
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
    if isinstance(region, ir.GridPlot):
        return [region.expr]
    return []


def _walk(node: ir.Expr) -> list[ir.Expr]:
    """The node and all of its descendant expressions (pre-order)."""
    out = [node]
    for child in ir.child_exprs(node):
        out.extend(_walk(child))
    return out


def _nested_double_integral(node: ir.Integral) -> ir.Integral | None:
    """If ``node`` is a rectangular double integral -- its integrand is itself
    a definite :class:`ir.Integral` whose bounds don't reference the outer
    integration variable -- return that inner ``Integral``; else ``None``.

    Mathcad's nested-``∫`` UI can only express constant (variable-independent)
    bounds for the inner integral, so this is the only shape a nested Integral
    can take; when it holds we emit a single ``double_integral(...)`` call
    (``scipy.integrate.dblquad``) instead of nested ``integral(lambda …)``.
    """
    if not isinstance(node.func, ir.Lambda) or len(node.func.params) != 1:
        return None
    inner = node.func.body
    if not isinstance(inner, ir.Integral):
        return None
    if not isinstance(inner.func, ir.Lambda) or len(inner.func.params) != 1:
        return None
    outer_var = node.func.params[0]
    if _references_name(inner.lower, outer_var) or _references_name(
        inner.upper, outer_var
    ):
        return None
    return inner


def _references_name(node: ir.Expr, name: str) -> bool:
    return any(isinstance(n, ir.Name) and n.py == name for n in _walk(node))
