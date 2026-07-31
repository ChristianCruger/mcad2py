"""Parse a Mathcad Prime ``worksheet.xml`` into an ordered IR worksheet."""

from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from typing import Callable

from .. import ir
from ..mapping import SYMBOLIC_COMMANDS
from ..shapes import annotate_products
from .expressions import parse_eval, parse_expr, read_identifier, sanitize
from .namespaces import localname

# A callable that resolves a text region's ``item-idref`` to its plain text.
TextResolver = Callable[[str], str]
# Resolves a picture region's ``item-idref`` to (basename, bytes).
ImageResolver = Callable[[str], "tuple[str, bytes] | None"]

# Image basename extension -> MIME type for embedding.
_MIME_BY_EXT = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "svg": "image/svg+xml",
}


def parse_worksheet(
    worksheet_xml: str,
    text_resolver: TextResolver | None = None,
    image_resolver: ImageResolver | None = None,
) -> ir.Worksheet:
    root = ET.fromstring(worksheet_xml)
    regions_elem = next(
        (e for e in root.iter() if localname(e.tag) == "regions"), None
    )
    ws = ir.Worksheet()
    if regions_elem is None:
        return ws

    # Sort by visual position (top, then left) to get reading order.
    def position(region: ET.Element) -> tuple[float, float]:
        return (_to_float(region.get("top")), _to_float(region.get("left")))

    # Names defined as a Mathcad *range* (``x0 := -50, -49 .. 50``), tracked as
    # we go so a later contour/3D plot equation can tell "``f(x0, y0)`` over two
    # ranges" (needs an outer-product grid) apart from a plain call.
    range_names: set[str] = set()
    for region in sorted(regions_elem, key=position):
        parsed = _parse_region(region, text_resolver, image_resolver, range_names)
        # A data table (<spec-table>) expands to one region per column.
        for item in parsed if isinstance(parsed, list) else [parsed]:
            if item is None:
                continue
            if isinstance(item, ir.Define) and isinstance(item.value, ir.Range):
                range_names.add(item.target.py)
            ws.regions.append(item)
    _inject_symbol_declarations(ws)
    # Mathcad spells scalar, matrix and dot products all as ``·``; deciding
    # which is which needs the whole sheet's shapes, so it runs as a pass.
    annotate_products(ws)
    return ws


def _parse_region(
    region: ET.Element,
    text_resolver: TextResolver | None,
    image_resolver: ImageResolver | None,
    range_names: set[str],
) -> "ir.Region | list[ir.Region] | None":
    for child in region:
        tag = localname(child.tag)
        if tag == "math":
            return _parse_math(child)
        if tag == "text":
            return _parse_text(child, text_resolver)
        if tag == "picture":
            return _parse_picture(child, image_resolver)
        if tag == "solveblock":
            return _parse_solveblock(child)
        if tag == "plot":
            return _parse_plot(child, range_names)
        if tag == "spec-table":
            # A data table: one <math> per column, each a define. Mathcad names
            # the resulting vectors by their column headers -- expand to one
            # region per column.
            return [
                _parse_math(m) for m in child if localname(m.tag) == "math" and len(m)
            ]
    return None


def _parse_math(math_elem: ET.Element) -> ir.Region:
    children = list(math_elem)
    if not children:
        return ir.UnsupportedRegion(note="empty math")
    inner = children[0]
    tag = localname(inner.tag)

    if tag == "define":
        return _parse_define(inner)

    if tag == "eval":
        value, unit = parse_eval(inner)
        return ir.Evaluate(value=value, display_unit=unit)

    if tag == "symEval":
        return _parse_sym_eval(inner)

    # A standalone scriptable status control (e.g. a TextBoxScriptableControl
    # displaying "OK!"/"All loadcases pass!"): the JScript isn't transpiled, but
    # its PiggybackNode holds the real boolean expression that drives the
    # message -- evaluate that, documenting the cached message.
    if tag.endswith("ScriptableControl"):
        return _parse_status_control(inner)

    # Bare symbolic equation (no define/eval wrapper): <apply><equal/> ...>.
    if tag == "apply":
        head = next(iter(inner), None)
        if head is not None and localname(head.tag) == "equal":
            return ir.SymbolicEquation(equation=_to_equation(parse_expr(inner)))

    # Other bare expression region -> treat as evaluation.
    return ir.Evaluate(value=parse_expr(inner), display_unit=None)


def _parse_sym_eval(elem: ET.Element) -> ir.Region:
    """Parse an ``<ml:symEval>``: an input expr, a command, a cached result."""
    expr: ir.Expr | None = None
    command_name = ""
    args: list[ir.Expr] = []
    result: ir.Expr | None = None

    for child in elem:
        ctag = localname(child.tag)
        if ctag == "command":
            command_name, args = _parse_command(child)
        elif ctag == "symResult":
            res = next(iter(child), None)
            result = parse_expr(res) if res is not None else None
        elif expr is None:
            # The first non-command/result child is the input expression; a
            # top-level equality is a symbolic equation (e.g. for ``solve``).
            expr = _to_equation(parse_expr(child))

    canonical = SYMBOLIC_COMMANDS.get(command_name)
    if expr is None or canonical is None:
        return ir.UnsupportedRegion(note=f"symbolic command: {command_name or '?'}")
    return ir.SymbolicEval(expr=expr, command=canonical, args=args, result=result)


def _parse_command(elem: ET.Element) -> tuple[str, list[ir.Expr]]:
    """Read a ``<ml:command><ml:sequence> name, arg, ... </>``."""
    seq = next((c for c in elem if localname(c.tag) == "sequence"), None)
    parts = list(seq) if seq is not None else []
    if not parts:
        return "", []
    name = read_identifier(parts[0])
    return name, [parse_expr(p) for p in parts[1:]]


def _parse_define(define_elem: ET.Element) -> ir.Region:
    children = list(define_elem)
    target_elem, value_elem = children[0], children[1]

    # ``X[i] := ...``: the target is <apply><indexer/> base index> -- a
    # range-indexed vector assignment (Mathcad iterates the index range and
    # builds the vector). Routes to IndexAssign, not a scalar Define.
    indexed = _parse_index_target(target_elem)
    if indexed is not None:
        base, index, col_index = indexed
        if localname(value_elem.tag) == "eval":
            value, unit = parse_eval(value_elem)
            return ir.IndexAssign(
                target=base,
                index=index,
                value=value,
                evaluate=True,
                display_unit=unit,
                col_index=col_index,
            )
        return ir.IndexAssign(
            target=base,
            index=index,
            value=parse_expr(value_elem),
            col_index=col_index,
        )

    # ``[a; b; c] := <expr>``: a matrix of ids on the left destructures a returned
    # vector (a plain value, not a native control -- those are handled below).
    if localname(target_elem.tag) == "matrix" and not localname(
        value_elem.tag
    ).endswith("Control"):
        return _parse_multi_assign(target_elem, value_elem)

    # ``f(x) := ...``: the target is <ml:function> with a name and bound vars.
    if localname(target_elem.tag) == "function":
        target, params = _parse_function_header(target_elem)
    else:
        target = _parse_target(target_elem)
        params = []

    # A native ComboBox row-selector: assign the selected row's value(s) to the
    # target(s) (a single id or a matrix of ids).
    if localname(value_elem.tag).endswith("ComboBoxControl"):
        return _parse_combobox(target_elem, value_elem)

    # A scriptable control (e.g. a ListBox) drives the value via an embedded
    # JScript we don't transpile -- we emit its cached output value instead.
    if localname(value_elem.tag).endswith("ScriptableControl"):
        return _parse_scriptable_control(target, value_elem, params)

    if localname(value_elem.tag) == "eval":
        value, unit = parse_eval(value_elem)
        return ir.Define(
            target=target, value=value, evaluate=True, display_unit=unit, params=params
        )
    return ir.Define(
        target=target, value=parse_expr(value_elem), evaluate=False, params=params
    )


def _parse_status_control(control: ET.Element) -> ir.Region:
    """A standalone scriptable status control (``<ml:...ScriptableControl>``).

    Unlike a control that *drives a define's value* (see
    :func:`_parse_scriptable_control`), this one stands alone and shows a
    message. We don't transpile its JScript; instead we evaluate the expression
    it carries in ``PiggybackNode > inputControlInputField`` -- any expression,
    often a boolean like ``λ < λlim`` but possibly a plain variable the JScript
    inspects -- and pair it with the cached ``vals`` message (see
    :class:`ir.StatusControl`).
    """
    piggyback = next(
        (c for c in control if localname(c.tag) == "PiggybackNode"), None
    )
    field = (
        next(
            (c for c in piggyback if localname(c.tag) == "inputControlInputField"),
            None,
        )
        if piggyback is not None
        else None
    )
    expr = (
        parse_expr(list(field)[0])
        if field is not None and len(field)
        else None
    )
    if expr is None:
        return ir.UnsupportedRegion(
            note=f"{localname(control.tag)} (no piggyback expression)"
        )

    vals_elem = next((c for c in control if localname(c.tag) == "vals"), None)
    messages = (
        [(v.text or "").strip() for v in vals_elem if localname(v.tag) == "val"]
        if vals_elem is not None
        else []
    )
    try:
        sel = int(control.get("SelectedIndex", "0") or 0)
    except ValueError:
        sel = 0
    message = messages[sel] if 0 <= sel < len(messages) else (messages[0] if messages else "")
    return ir.StatusControl(value=expr, message=message)


def _parse_multi_assign(target_elem: ET.Element, value_elem: ET.Element) -> ir.Region:
    """``[a; b; c] := <expr>`` -> a :class:`ir.MultiAssign` destructuring.

    A target with more than one row *and* column (``[a b; c d] := M``) names the
    elements of a whole matrix; like ``<ml:matrix>`` itself the ids are listed
    column-major, so the value has to be flattened that way before unpacking.
    """
    targets = [_parse_target(c) for c in target_elem if localname(c.tag) == "id"]
    matrix_target = (
        int(target_elem.get("rows", "1") or 1) > 1
        and int(target_elem.get("cols", "1") or 1) > 1
    )
    if localname(value_elem.tag) == "eval":
        value, unit = parse_eval(value_elem)
        return ir.MultiAssign(
            targets=targets,
            value=value,
            evaluate=True,
            display_unit=unit,
            matrix_target=matrix_target,
        )
    return ir.MultiAssign(
        targets=targets,
        value=parse_expr(value_elem),
        matrix_target=matrix_target,
    )


def _parse_scriptable_control(
    target: ir.Name, control: ET.Element, params: list[str]
) -> ir.Region:
    """A Mathcad scriptable control (``<ml:...ScriptableControl>``).

    The control's behaviour is an embedded JScript (the ``Script`` attribute) we
    deliberately don't transpile -- it can be arbitrarily complex. Instead we
    emit the control's *cached output value* (the ``RL`` attribute, the same
    result downstream cells consume), documenting the selection in a comment.
    """
    value = _decode_control_result(control.get("RL"))
    if value is None:
        return ir.UnsupportedRegion(
            note=f"{localname(control.tag)} (no cached value to recover)"
        )

    vals_elem = next((c for c in control if localname(c.tag) == "vals"), None)
    options = (
        [(v.text or "").strip() for v in vals_elem if localname(v.tag) == "val"]
        if vals_elem is not None
        else []
    )
    try:
        sel = int(control.get("SelectedIndex", "0") or 0)
    except ValueError:
        sel = 0

    kind = localname(control.tag)
    comment = f"Mathcad {kind}: not transpiled; using its cached output value."
    if options:
        chosen = options[sel] if 0 <= sel < len(options) else "?"
        comment = (
            f'Mathcad {kind}: selected "{chosen}" '
            f"(options: {', '.join(options)}).\n"
            "Embedded JScript not transpiled; using the cached output value."
        )
    return ir.Define(
        target=target, value=value, evaluate=False, params=params, comment=comment
    )


def _parse_combobox(target_elem: ET.Element, control: ET.Element) -> ir.Region:
    """A ``<ml:ComboBoxControl>``: assign the selected row's value(s).

    The control is a ``rows×cols`` table (``<ml:ComboBoxValues>``, row-major)
    with named rows (``<ml:ComboBoxRowNames>``); ``SelectedRow`` (0-based, per the
    worksheet's ``array-origin``) picks the row. Its ``cols`` value(s) map onto
    the LHS target(s) -- a single id or a ``<ml:matrix>`` of ids. A control with
    no values yields the selected row *name* as a string (e.g. a Yes/No flag).
    """
    if localname(target_elem.tag) == "matrix":
        targets = [_parse_target(c) for c in target_elem if localname(c.tag) == "id"]
    else:
        targets = [_parse_target(target_elem)]

    cols = int(control.get("cols", "1") or 1)
    sel = int(control.get("SelectedRow", "0") or 0)

    def _children(suffix: str) -> list[ET.Element]:
        parent = next(
            (c for c in control if localname(c.tag).endswith(suffix)), None
        )
        return list(parent) if parent is not None else []

    names = [
        (n.text or "").strip()
        for n in _children("RowNames")
        if localname(n.tag) == "rowName"
    ]
    reals = [
        (v.text or "").strip()
        for v in _children("Values")
        if localname(v.tag) == "real"
    ]
    chosen = names[sel] if 0 <= sel < len(names) else "?"

    if reals:
        row = reals[sel * cols : sel * cols + cols]
        values: list[ir.Expr] = [ir.Number(v) for v in row]
    else:
        # No value table -> the selected row name is the (string) output.
        values = [ir.Str(chosen)]

    comment = (
        f'Mathcad ComboBoxControl: selected "{chosen}"'
        + (f" (options: {', '.join(names)})." if names else ".")
    )
    return ir.ComboBoxAssign(targets=targets, values=values, comment=comment)


def _to_equation(expr: ir.Expr) -> ir.Expr:
    """Coerce a top-level equality into an :class:`ir.Equation` (SymPy ``Eq``).

    ``<ml:equal/>`` parses as a ``==`` comparison (``BinOp`` ``eq``) for boolean
    use in program tests; when it heads a *symbolic* region (a standalone
    equation, a ``solve`` input, or a solve-block constraint) it means an
    equation instead, so the symbolic parsers route it through here.
    """
    if isinstance(expr, ir.BinOp) and expr.op == "eq":
        return ir.Equation(lhs=expr.left, rhs=expr.right)
    return expr


def _decode_control_result(rl: str | None) -> ir.Expr | None:
    """Decode a control's base64 ``RL`` cached result into an IR value.

    The payload is an s-expression, e.g. a 2x1 matrix
    ``(op_matrix:0x.. (unboxed 2) (unboxed 1) (list (number 3:0x..) (number 0.13:0x..)))``
    or a bare ``(number 0.8:0x..)``. Returns a :class:`ir.MatrixLiteral` (vector)
    or :class:`ir.Number`, or None when there is nothing to recover.
    """
    if not rl:
        return None
    try:
        raw = base64.b64decode(rl).decode("ascii", "replace")
    except Exception:
        return None
    nums = re.findall(r"\(number\s+([-+0-9.eE]+)", raw)
    if not nums:
        return None
    if "op_matrix" in raw:
        dims = re.findall(r"\(unboxed\s+(\d+)\)", raw)
        rows = int(dims[0]) if len(dims) > 0 else len(nums)
        cols = int(dims[1]) if len(dims) > 1 else 1
        return ir.MatrixLiteral(
            rows=rows, cols=cols, elements=[ir.Number(n) for n in nums]
        )
    return ir.Number(nums[0])


def _parse_plot(plot_elem: ET.Element, range_names: set[str]) -> ir.Region:
    """Parse a ``<plot>``: ``<xyPlot>``, ``<contourPlot>``, or ``<plot3D>``."""
    xy = next((c for c in plot_elem if localname(c.tag) == "xyPlot"), None)
    if xy is not None:
        return _parse_xy_plot(xy, range_names)

    contour = next((c for c in plot_elem if localname(c.tag) == "contourPlot"), None)
    if contour is not None:
        return _parse_grid_plot(contour, range_names, threed=False)

    plot3d = next((c for c in plot_elem if localname(c.tag) == "plot3D"), None)
    if plot3d is not None:
        return _parse_grid_plot(plot3d, range_names, threed=True)

    return ir.UnsupportedRegion(note="plot (unrecognized structure)")


def _parse_xy_plot(xy: ET.Element, range_names: set[str]) -> ir.Region:
    """Parse an ``<xyPlot>``: x/y axis equations paired into traces.

    Each axis carries ``<plotEquations>``; each ``<plotEquation>`` is an
    expression ``<math>`` plus a unit/scale ``<math>``. Traces pair the x and y
    equations by index (the single-equation axis is shared across traces).

    Two flavours: a **function plot** ``y = f(x)`` where one axis is a bare
    *range* variable (the domain, sampled element-wise), and a **parametric
    plot** where both axes are data vectors (a section outline, a rebar
    scatter) plotted point-by-point -- the latter has no scalar domain.
    """
    axes = next((c for c in xy if localname(c.tag) == "axes"), None)
    if axes is None:
        return ir.UnsupportedRegion(note="plot (unrecognized structure)")

    x_axis = next((c for c in axes if localname(c.tag) == "xAxis"), None)
    y_axis = next((c for c in axes if localname(c.tag) == "yAxis"), None)
    x_eqs = _parse_plot_equations(x_axis)
    y_eqs = _parse_plot_equations(y_axis)
    colors = _parse_trace_colors(xy)
    if not x_eqs or not y_eqs:
        return ir.UnsupportedRegion(note="plot (no equations)")

    count = max(len(x_eqs), len(y_eqs))
    traces: list[ir.PlotTrace] = []
    for i in range(count):
        xe, xu = x_eqs[i] if i < len(x_eqs) else x_eqs[0]
        ye, yu = y_eqs[i] if i < len(y_eqs) else y_eqs[0]
        color = colors[i] if i < len(colors) else None
        traces.append(ir.PlotTrace(x=xe, y=ye, x_unit=xu, y_unit=yu, color=color))

    domain = _detect_domain(x_eqs + y_eqs, range_names)
    return ir.Plot(traces=traces, domain=domain)


def _parse_grid_plot(
    elem: ET.Element, range_names: set[str], *, threed: bool
) -> ir.Region:
    """Parse a ``<contourPlot>``/``<plot3D>``'s single plot equation.

    ``<contourPlot>`` has one ``<plotEquation>`` directly inside it;
    ``<plot3D>`` wraps it (and, in principle, siblings for multiple traces --
    not seen in practice) in ``<plotEquations>``. Either way there's a single
    expression plus an optional unit-override ``<math>``, unlike ``<xyPlot>``'s
    per-axis equations.
    """
    pe = next((c for c in elem if localname(c.tag) == "plotEquation"), None)
    if pe is None:
        container = next(
            (c for c in elem if localname(c.tag) == "plotEquations"), None
        )
        pe = (
            next((c for c in container if localname(c.tag) == "plotEquation"), None)
            if container is not None
            else None
        )
    if pe is None:
        return ir.UnsupportedRegion(note="plot (no equation)")

    maths = [c for c in pe if localname(c.tag) == "math"]
    if not maths or not len(maths[0]):
        return ir.UnsupportedRegion(note="plot (no equation)")
    expr = parse_expr(maths[0][0])
    z_unit: ir.Expr | None = None
    if len(maths) > 1 and len(maths[1]):
        sub = maths[1][0]
        if localname(sub.tag) != "placeholder":
            z_unit = parse_expr(sub)

    # An expression referencing exactly two ranges anywhere in it -- a direct
    # call (f(x0, y0)) or a composition (sigma(epsilon(x0*mm, y0*mm))) alike
    # -- needs a grid built from their outer product, not a plain call/zip.
    free_ranges = _free_range_names(expr, range_names)
    mesh_names: tuple[str, str] | None = (
        (free_ranges[0], free_ranges[1]) if len(free_ranges) == 2 else None
    )

    # Anything besides the two shapes we actually know how to resolve at
    # runtime -- an expression over exactly two ranges, or a bare Name (a
    # matrix/Mesh variable, for resolve_plot_grid) -- is a plot equation we
    # can't safely turn into a grid.
    if mesh_names is None and not isinstance(expr, ir.Name):
        return ir.UnsupportedRegion(note="plot (unrecognized structure)")

    return ir.GridPlot(
        expr=expr, z_unit=z_unit, mesh_names=mesh_names, threed=threed
    )


def _free_range_names(expr: ir.Expr, range_names: set[str]) -> list[str]:
    """Distinct range-typed ``Name``s referenced in ``expr``, in order of
    first appearance (pre-order) -- e.g. ``sigma(epsilon(x0*mm, y0*mm))``
    over ``range_names={"x0", "y0"}`` -> ``["x0", "y0"]``.
    """
    seen: list[str] = []

    def walk(node: ir.Expr) -> None:
        if isinstance(node, ir.Name) and node.py in range_names and node.py not in seen:
            seen.append(node.py)
        for child in ir.child_exprs(node):
            walk(child)

    walk(expr)
    return seen


def _parse_plot_equations(
    axis_elem: ET.Element | None,
) -> list[tuple[ir.Expr, ir.Expr | None]]:
    """Read an axis's ``<plotEquations>`` -> list of (expr, unit-or-None)."""
    if axis_elem is None:
        return []
    container = next(
        (c for c in axis_elem if localname(c.tag) == "plotEquations"), None
    )
    out: list[tuple[ir.Expr, ir.Expr | None]] = []
    for pe in container if container is not None else []:
        if localname(pe.tag) != "plotEquation":
            continue
        maths = [c for c in pe if localname(c.tag) == "math"]
        expr = parse_expr(maths[0][0]) if maths and len(maths[0]) else ir.Placeholder()
        unit: ir.Expr | None = None
        if len(maths) > 1 and len(maths[1]):
            sub = maths[1][0]
            if localname(sub.tag) != "placeholder":
                unit = parse_expr(sub)
        out.append((expr, unit))
    return out


def _parse_trace_colors(xy_elem: ET.Element) -> list[str | None]:
    """The trace line colors (Mathcad ``#AARRGGBB`` -> ``#RRGGBB``)."""
    traces = next((c for c in xy_elem if localname(c.tag) == "traces"), None)
    colors: list[str | None] = []
    for tr in traces if traces is not None else []:
        style = next((c for c in tr if localname(c.tag) == "traceStyle"), None)
        argb = style.get("color") if style is not None else None
        colors.append(_argb_to_rgb(argb))
    return colors


def _argb_to_rgb(argb: str | None) -> str | None:
    """``#FF00008B`` -> ``#00008B`` (drop the alpha byte)."""
    if not argb or not argb.startswith("#"):
        return argb
    digits = argb[1:]
    if len(digits) == 8:
        digits = digits[2:]
    return "#" + digits


def _detect_domain(
    eqs: list[tuple[ir.Expr, ir.Expr | None]], range_names: set[str]
) -> str | None:
    """The independent variable = the first bare-``Name`` axis that is a *range*.

    Only a range variable is a sampling domain (``y = f(x)`` over ``x``). A bare
    ``Name`` that is a plain data vector (e.g. ``X_s`` in a parametric section
    outline) is *not* a domain -- both axes there are vectors plotted directly.
    """
    for expr, _unit in eqs:
        if isinstance(expr, ir.Name) and expr.py in range_names:
            return expr.py
    return None


def _parse_solveblock(elem: ET.Element) -> ir.Region:
    """Parse a ``<solveblock>``: guess values, constraints, and the solver.

    Sub-regions are tagged ``solve-block-category`` = ``guess-value`` /
    ``constraint`` / ``solver``. The solver region is ``[targets] := find(unknowns)``.
    """
    guesses: list[ir.Define] = []
    constraints: list[ir.Equation] = []
    unknowns: list[ir.Name] = []
    targets: list[ir.Name] = []
    command = "find"
    display_unit: ir.Expr | None = None
    params: list[str] = []

    regions_elem = next((c for c in elem if localname(c.tag) == "regions"), None)
    for sub in regions_elem if regions_elem is not None else []:
        category = sub.get("solve-block-category")
        math = next((c for c in sub if localname(c.tag) == "math"), None)
        if math is None or not len(math):
            continue
        inner = list(math)[0]
        if category == "guess-value":
            parsed = _parse_define(inner)
            if isinstance(parsed, ir.Define):
                guesses.append(parsed)
        elif category == "constraint":
            eq = _to_equation(parse_expr(inner))
            if isinstance(eq, ir.Equation):
                constraints.append(eq)
        elif category == "solver":
            command, unknowns, targets, display_unit, params = _parse_solver(inner)

    if not targets:
        return ir.UnsupportedRegion(note="solve block (no solver region)")
    return ir.SolveBlock(
        guesses=guesses,
        constraints=constraints,
        unknowns=unknowns,
        targets=targets,
        command=command,
        display_unit=display_unit,
        params=params,
    )


def _parse_solver(
    define_elem: ET.Element,
) -> tuple[str, list[ir.Name], list[ir.Name], ir.Expr | None, list[str]]:
    """Parse the solver region of a solve block.

    Two forms: ``[targets] := find(unknowns)`` (targets is a matrix of ids) and
    ``f(a, b) := find(unknowns)`` (the target is an ``<ml:function>`` header, so
    the solve block defines a function -- ``targets`` is just ``[f]`` and the
    bound vars become ``params``). The ``find(...)`` value may be wrapped in an
    ``<ml:eval>`` (with a display unit) or be a bare ``<ml:apply>``.
    """
    children = list(define_elem)
    target_elem, value_elem = children[0], children[1]

    params: list[str] = []
    if localname(target_elem.tag) == "function":
        fname, params = _parse_function_header(target_elem)
        targets = [fname]
    else:
        targets = [_parse_target(c) for c in target_elem if localname(c.tag) == "id"]

    if localname(value_elem.tag) == "eval":
        value, display_unit = parse_eval(value_elem)
    else:
        value, display_unit = parse_expr(value_elem), None

    command = "find"
    unknowns: list[ir.Name] = []
    if isinstance(value, ir.Call):
        command = value.func
        unknowns = [a for a in value.args if isinstance(a, ir.Name)]
    return command, unknowns, targets, display_unit, params


def _parse_target(id_elem: ET.Element) -> ir.Name:
    display = read_identifier(id_elem)
    return ir.Name(
        py=sanitize(display),
        original=display,
        role=id_elem.get("labels", "VARIABLE"),
    )


def _parse_index_target(
    elem: ET.Element,
) -> "tuple[ir.Name, ir.Name, ir.Name | None] | None":
    """If ``elem`` is an indexed-assignment target, return ``(X, i, j-or-None)``.

    The target is ``<apply><indexer/> <id base> <index>``; the index is a plain
    id for the vector form ``X[i] := …`` and a ``<sequence>`` of two ids for the
    matrix form ``X[i, j] := …``. Returns None for any other shape.
    """
    if localname(elem.tag) != "apply":
        return None
    kids = list(elem)
    if len(kids) < 3 or localname(kids[0].tag) != "indexer":
        return None
    base, index_elem = _parse_target(kids[1]), kids[2]
    if localname(index_elem.tag) == "sequence":
        parts = [p for p in index_elem if localname(p.tag) == "id"]
        if len(parts) != 2:
            return None
        return base, _parse_target(parts[0]), _parse_target(parts[1])
    if localname(index_elem.tag) != "id":
        return None
    return base, _parse_target(index_elem), None


def _parse_function_header(func_elem: ET.Element) -> tuple[ir.Name, list[str]]:
    """Read ``<ml:function>``: the function name and its bound-variable names."""
    name_elem = next((c for c in func_elem if localname(c.tag) == "id"), None)
    target = _parse_target(name_elem) if name_elem is not None else ir.Name("_", "_")
    params: list[str] = []
    bound = next((c for c in func_elem if localname(c.tag) == "boundVars"), None)
    if bound is not None:
        params = [
            sanitize(read_identifier(p)) for p in bound if localname(p.tag) == "id"
        ]
    return target, params


def _parse_picture(
    pic_elem: ET.Element, image_resolver: ImageResolver | None
) -> ir.Region:
    sub = next((c for c in pic_elem if c.get("item-idref")), None)
    idref = sub.get("item-idref") if sub is not None else None
    if idref and image_resolver is not None:
        resolved = image_resolver(idref)
        if resolved is not None:
            name, data = resolved
            return ir.ImageRegion(data=data, mime=_image_mime(name, data), name=name)
    return ir.UnsupportedRegion(note="picture (image could not be resolved)")


def _image_mime(name: str, data: bytes) -> str:
    """MIME type from the image's magic bytes (Mathcad mislabels extensions:
    its ``.png`` media are often actually BMP), falling back to the extension.
    """
    if data[:8].startswith(b"\x89PNG"):
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] in (b"GIF8",):
        return "image/gif"
    if data[:2] == b"BM":
        return "image/bmp"
    if data[:5] == b"<?xml" or b"<svg" in data[:256]:
        return "image/svg+xml"
    ext = name.rsplit(".", 1)[-1].lower()
    return _MIME_BY_EXT.get(ext, "application/octet-stream")


def _parse_text(
    text_elem: ET.Element, text_resolver: TextResolver | None
) -> ir.Region | None:
    idref = text_elem.get("item-idref")
    text = ""
    if idref and text_resolver is not None:
        text = text_resolver(idref)
    if not text.strip():
        return None
    return ir.TextRegion(text=text)


def _inject_symbol_declarations(ws: ir.Worksheet) -> None:
    """Declare free identifiers as SymPy Symbols ahead of the first symbolic region.

    Symbolic regions reference variables that have no numeric value yet (the
    "show the steps" equations). We collect those free names and emit
    ``x = Symbol('x')`` for each, skipping any already defined numerically
    above the first symbolic region.
    """
    symbolic = (ir.SymbolicEquation, ir.SymbolicEval)
    first = next(
        (i for i, r in enumerate(ws.regions) if isinstance(r, symbolic)), None
    )
    if first is None:
        return

    defined_before = {
        r.target.py for r in ws.regions[:first] if isinstance(r, ir.Define)
    }

    names: list[str] = []
    for region in ws.regions:
        if isinstance(region, ir.SymbolicEquation):
            _collect_var_names(region.equation, names)
        elif isinstance(region, ir.SymbolicEval):
            _collect_var_names(region.expr, names)
            for arg in region.args:
                _collect_var_names(arg, names)

    decl = [n for n in names if n not in defined_before]
    if decl:
        ws.regions.insert(first, ir.SymbolDeclarations(names=decl))


def _collect_var_names(node: ir.Expr, acc: list[str]) -> None:
    """Append distinct VARIABLE identifier names in first-seen order."""
    if isinstance(node, ir.Name) and node.role == "VARIABLE" and node.py not in acc:
        acc.append(node.py)
    for child in ir.child_exprs(node):
        _collect_var_names(child, acc)


def _to_float(value: str | None) -> float:
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0
