"""Parse a Mathcad Prime ``worksheet.xml`` into an ordered IR worksheet."""

from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from typing import Callable

from .. import ir
from ..mapping import CONSTANTS, SYMBOLIC_COMMANDS
from ..shapes import annotate_products
from .expressions import (
    as_units,
    parse_eval,
    parse_expr,
    read_identifier,
    sanitize,
)
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
    integration_xml: str | None = None,
    result_xml: str | None = None,
) -> ir.Worksheet:
    root = ET.fromstring(worksheet_xml)
    regions_elem = next(
        (e for e in root.iter() if localname(e.tag) == "regions"), None
    )
    ws = ir.Worksheet()
    if regions_elem is None:
        return ws

    io_tags = _parse_integration(integration_xml)
    engine_errors = _parse_engine_errors(result_xml)

    # Names defined as a Mathcad *range* (``x0 := -50, -49 .. 50``), tracked as
    # we go so a later contour/3D plot equation can tell "``f(x0, y0)`` over two
    # ranges" (needs an outer-product grid) apart from a plain call.
    range_names: set[str] = set()
    for region in _ordered_regions(regions_elem):
        parsed = _parse_region(region, text_resolver, image_resolver, range_names)
        region_id_attr = region.get("region-id")
        try:
            region_id = int(region_id_attr) if region_id_attr is not None else None
        except ValueError:
            region_id = None
        io_kind, io_alias = io_tags.get(region_id, (None, None))
        source = (
            ir.SourceRef(region_id, io_kind, io_alias) if region_id is not None else None
        )
        math_elem = next((c for c in region if localname(c.tag) == "math"), None)
        error = (
            engine_errors.get(math_elem.get("resultRef", ""))
            if math_elem is not None
            else None
        )
        # A data table (<spec-table>) expands to one region per column.
        for item in parsed if isinstance(parsed, list) else [parsed]:
            if item is None:
                continue
            item.source = source
            if error is not None:
                item.cached_error = error
            if isinstance(item, ir.Define) and isinstance(item.value, ir.Range):
                range_names.add(item.target.py)
            ws.regions.append(item)
    # ``≡`` binds over the whole sheet, so it has to come first -- before the
    # passes below, which all reason about reading order.
    _hoist_global_defines(ws)
    _inject_symbol_declarations(ws)
    # A difference equation's driving range variable, and which of its target
    # vectors it is the first region to write, are only knowable from the sheet
    # above it.
    _resolve_recurrences(ws, range_names)
    # Needs the whole (ordered) sheet to know which names are ever defined.
    _infer_implicit_plot_domains(ws)
    # Mathcad spells scalar, matrix and dot products all as ``·``; deciding
    # which is which needs the whole sheet's shapes, so it runs as a pass.
    annotate_products(ws)
    return ws


def _parse_integration(integration_xml: str | None) -> dict[int | None, tuple[str | None, str | None]]:
    """Map ``region-id`` -> ``(ioTagType, alias)`` from ``mathcad/integration.xml``.

    Empty when the sheet has no Input/Output tags (the common case -- Prime
    writes this part as a bare ``<regions/>`` unless the author used the
    Input/Output panel) or when the part is missing entirely.
    """
    if not integration_xml:
        return {}
    root = ET.fromstring(integration_xml)
    tags: dict[int | None, tuple[str | None, str | None]] = {}
    for region in root:
        if localname(region.tag) != "region":
            continue
        region_id_attr = region.get("region-id")
        io_kind = region.get("ioTagType")
        if region_id_attr is None or io_kind is None:
            continue
        alias_elem = next((c for c in region.iter() if localname(c.tag) == "alias"), None)
        alias = (alias_elem.text or "").strip() if alias_elem is not None else ""
        if not alias:
            continue
        try:
            tags[int(region_id_attr)] = (io_kind, alias)
        except ValueError:
            continue
    return tags


def _parse_engine_errors(result_xml: str | None) -> dict[str, str]:
    """Map ``resultRef`` -> error message for regions **Mathcad itself** failed on.

    ``result.xml`` records a region the engine could not compute as an
    ``<engineError>`` carrying a human-readable ``<resource-string>`` (e.g.
    ``mode(v)`` on data with no repeated value). Those regions still convert --
    the Python is a faithful translation -- but running them raises, so the
    backends guard them (see :attr:`ir.Region.cached_error`) and the sheet keeps
    going, as Mathcad does below its own error markers.
    """
    if not result_xml:
        return {}
    root = ET.fromstring(result_xml)
    errors: dict[str, str] = {}
    for data in root:
        result_id = data.get("result-id")
        message = next(
            (e for e in data.iter() if localname(e.tag) == "resource-string"), None
        )
        if result_id is None or message is None or not (message.text or "").strip():
            continue
        errors[result_id] = message.text.strip()
    return errors


def _ordered_regions(regions_elem: ET.Element) -> list[ET.Element]:
    """The leaf ``<region>`` elements in reading order, flattening ``<Area>``s.

    A collapsible **area** is a container region: ``<region><Area><regions>…``.
    Collapsing it is purely presentational -- Mathcad still evaluates what's
    inside -- so we splice its contents into the stream at the area's own
    position and convert them as if the area weren't there. The nested regions'
    ``top``/``left`` are *area-relative*, so each area is sorted within itself
    rather than against its siblings. Areas nest, hence the recursion.
    """
    ordered: list[ET.Element] = []
    for region in sorted(regions_elem, key=_position):
        area = next((c for c in region if localname(c.tag) == "Area"), None)
        if area is None:
            ordered.append(region)
            continue
        inner = next((c for c in area if localname(c.tag) == "regions"), None)
        if inner is not None:
            ordered.extend(_ordered_regions(inner))
    return ordered


def _position(region: ET.Element) -> tuple[float, float]:
    """Visual position (top, then left) -- i.e. reading order."""
    return (_to_float(region.get("top")), _to_float(region.get("left")))


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


def _hoist_global_defines(ws: ir.Worksheet) -> None:
    """Move every ``≡`` definition to the top of the sheet, order preserved.

    A global definition is Mathcad's one departure from top-to-bottom reading
    order: it is in scope everywhere, so a region *above* it may use the name.
    A generated Python module has no such notion, so the faithful translation is
    to emit them first. The partition is stable, so the regions keep their
    relative order within each group -- and text regions stay where they are,
    which means the ``≡``'s own heading text is left behind (a small cost, and
    less confusing than dragging unrelated prose to the top with it).
    """
    hoisted = [r for r in ws.regions if getattr(r, "global_scope", False)]
    if not hoisted:
        return
    moved = {id(r) for r in hoisted}  # identity: two regions can compare equal
    ws.regions[:] = hoisted + [r for r in ws.regions if id(r) not in moved]


def _parse_math(math_elem: ET.Element) -> ir.Region:
    children = list(math_elem)
    if not children:
        return ir.UnsupportedRegion(note="empty math")
    inner = children[0]
    tag = localname(inner.tag)

    if tag == "define":
        return _parse_define(inner)

    if tag == "globalDefine":
        # Mathcad's ``≡``. Structurally identical to ``<ml:define>``; what
        # differs is *scope* -- it binds over the whole sheet, including the
        # regions above it -- which ``_hoist_global_defines`` then honours.
        defined = _parse_define(inner)
        if isinstance(defined, ir.Define):
            defined.global_scope = True
        return defined

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

    # A *difference equation*: the left-hand side names element slots whose
    # indices aren't bare range variables (``guess[0]``, ``guess[i+1]``), or a
    # whole system of them. Mathcad iterates these sequentially -- see
    # :class:`ir.Recurrence`. The driving range variable and which bases this
    # region creates need the whole sheet, so ``_resolve_recurrences`` fills
    # ``index``/``create`` in afterwards.
    slots = _parse_recurrence_targets(target_elem)
    if slots is not None:
        evaluate = localname(value_elem.tag) == "eval"
        if evaluate:
            value, unit = parse_eval(value_elem)
            value_elem = next(iter(value_elem))
        else:
            value, unit = parse_expr(value_elem), None
        # A right-hand side matrix that lines up with the targets feeds them one
        # for one; anything else is a single vector to destructure across them.
        values = None
        if localname(value_elem.tag) == "matrix" and len(list(value_elem)) == len(slots):
            values = [parse_expr(child) for child in value_elem]
        return ir.Recurrence(
            targets=slots,
            value=None if values is not None else value,
            values=values,
            evaluate=evaluate,
            display_unit=unit,
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
    return ir.Plot(
        traces=traces, domain=domain, x_limits=_parse_axis_limits(x_axis)
    )


def _parse_axis_limits(axis_elem: ET.Element | None) -> tuple[float, float] | None:
    """An axis's *author-set* interval, from ``<xyDomain>``'s start/end values.

    Both are ``<ml:placeholder/>`` while the axis auto-scales, in which case
    there is no author interval (the ``start``/``end`` *attributes* alongside
    them are the drawn window Mathcad computed, not a setting). Anything that
    isn't a plain number is ignored -- a limit may be an arbitrary expression,
    and we have no sample of one to pin the behaviour down.
    """
    if axis_elem is None:
        return None
    dom = next((c for c in axis_elem if localname(c.tag) == "xyDomain"), None)
    if dom is None:
        return None
    bounds: list[float] = []
    for tag in ("startValue", "endValue"):
        elem = next((c for c in dom if localname(c.tag) == tag), None)
        if elem is None or not len(elem):
            return None
        value = _const_float(parse_expr(elem[0]))
        if value is None:
            return None
        bounds.append(value)
    return (bounds[0], bounds[1])


def _const_float(node: ir.Expr) -> float | None:
    """``node`` as a float if it is a numeric literal (optionally negated)."""
    if isinstance(node, ir.UnaryOp) and node.op == "neg":
        inner = _const_float(node.operand)
        return None if inner is None else -inner
    if isinstance(node, ir.Number):
        try:
            return float(node.value)
        except ValueError:
            return None
    return None


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
            z_unit = as_units(parse_expr(sub))

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
                unit = as_units(parse_expr(sub))
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


def _parse_element_target(elem: ET.Element) -> "ir.ElementTarget | None":
    """If ``elem`` is ``<apply><indexer/> <id base> <index>``, the slot it names.

    The looser sibling of :func:`_parse_index_target`: the index may be *any*
    expression (``0``, ``i + 1``, ``i + N``), which is what a difference equation
    writes into. A ``<sequence>`` index gives the two-subscript form.
    """
    if localname(elem.tag) != "apply":
        return None
    kids = list(elem)
    if len(kids) < 3 or localname(kids[0].tag) != "indexer":
        return None
    if localname(kids[1].tag) != "id":
        return None
    base, index_elem = _parse_target(kids[1]), kids[2]
    if localname(index_elem.tag) == "sequence":
        parts = list(index_elem)
        if len(parts) != 2:
            return None
        return ir.ElementTarget(
            base=base, index=parse_expr(parts[0]), col=parse_expr(parts[1])
        )
    return ir.ElementTarget(base=base, index=parse_expr(index_elem))


def _parse_recurrence_targets(elem: ET.Element) -> "list[ir.ElementTarget] | None":
    """The element slots a difference equation's left-hand side writes.

    Either a single ``X[…]`` or a ``<ml:matrix>`` **every** one of whose entries
    is an indexer -- the system form ``[inf[τ+1]; sus[τ+1]; …] := …``. A matrix
    of plain ids is a destructuring :class:`ir.MultiAssign` instead, and a mix of
    the two isn't something Mathcad can write, so both yield None here.
    """
    single = _parse_element_target(elem)
    if single is not None:
        return [single]
    if localname(elem.tag) != "matrix":
        return None
    slots = [_parse_element_target(child) for child in elem]
    if not slots or any(slot is None for slot in slots):
        return None
    return slots  # type: ignore[return-value]


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


def _resolve_recurrences(ws: ir.Worksheet, range_names: set[str]) -> None:
    """Fill in each :class:`ir.Recurrence`'s driving range variable and ``create``.

    The *driver* is the range variable the target indices are written in terms of
    (``i`` in ``guess[i+1]``); with none -- every index is a constant -- the
    region is a **seed** that writes fixed slots once, so ``index`` stays None.

    ``create`` lists the base names this region is the first in the sheet to
    write. Those are pre-declared ``= None`` at emission so ``vec_set`` grows
    them from nothing; a base written earlier (or defined outright, as ``data``
    is before ``data[2] := 1.2·data[2]``) is updated in place instead.
    """
    written: set[str] = set()
    for region in ws.regions:
        if not isinstance(region, ir.Recurrence):
            written |= _bound_names(region)
            continue
        # The index carries the sheet's define-target label (``*``), not
        # ``VARIABLE``, so match on every identifier rather than on the role.
        drivers: list[str] = []
        for slot in region.targets:
            for part in (slot.index, slot.col):
                for sub in _walk_exprs(part) if part is not None else []:
                    if isinstance(sub, ir.Name) and sub.py not in drivers:
                        drivers.append(sub.py)
        driving = [n for n in drivers if n in range_names]
        if driving:
            region.index = ir.Name(py=driving[0], original=driving[0])
        region.create = [
            slot.base.py
            for i, slot in enumerate(region.targets)
            if slot.base.py not in written
            and slot.base.py not in {s.base.py for s in region.targets[:i]}
        ]
        written |= {slot.base.py for slot in region.targets}


def _collect_var_names(node: ir.Expr, acc: list[str]) -> None:
    """Append distinct VARIABLE identifier names in first-seen order."""
    if isinstance(node, ir.Name) and node.role == "VARIABLE" and node.py not in acc:
        acc.append(node.py)
    for child in ir.child_exprs(node):
        _collect_var_names(child, acc)


# Mathcad's default sampling interval for a plot over an *undefined* variable,
# and the number of points it takes across it. Both read off a cached
# ``<ml:Trace2dResult>``: -10..10 in 499 steps of 20/498 (the ``<trace>``
# element's own ``num-of-points`` says 500, but the data vector holds 499).
_IMPLICIT_PLOT_DOMAIN = (-10.0, 10.0, 499)
_IMPLICIT_PLOT_POINTS = _IMPLICIT_PLOT_DOMAIN[2]


def _infer_implicit_plot_domains(ws: ir.Worksheet) -> None:
    """Give an X-Y plot over a never-defined variable Mathcad's default domain.

    A plot needs no ``x := -10, -9.96 .. 10`` above it: writing ``sin(x)`` on
    the y axis against ``x`` on the x axis is enough, and Mathcad invents the
    interval -10..10 for the free variable. The *axis* expression may be any
    function of it -- ``x/2`` on the x axis plots -5..5, because it's ``x``
    that spans -10..10, not the axis.

    So: a plot with no range-typed domain whose equations reference exactly one
    variable that nothing above it defines takes that variable as its domain,
    with the default interval attached. Two free names, or none, is not a
    function plot (a parametric outline plots two data vectors directly) and is
    left alone.

    -10..10 is only the default. Setting the **x-axis limits** re-samples the
    free variable over exactly those, so author-set limits win.
    """
    defined: set[str] = set()
    for region in ws.regions:
        if isinstance(region, ir.Plot) and region.domain is None:
            free = _free_plot_names(region, defined)
            if len(free) == 1:
                region.domain = free[0]
                region.implicit_domain = (
                    _IMPLICIT_PLOT_DOMAIN
                    if region.x_limits is None
                    else (*region.x_limits, _IMPLICIT_PLOT_POINTS)
                )
        defined |= _bound_names(region)


def _free_plot_names(plot: ir.Plot, defined: set[str]) -> list[str]:
    """Distinct variables a plot's axis expressions reference and nothing has
    defined. ``π``/``e`` read as identifiers at this stage (they only become
    ``math.pi``/``math.e`` at codegen), so they're excluded -- else
    ``sin(π·x)`` would look like two free names rather than one.
    """
    names: list[str] = []
    for trace in plot.traces:
        for node in (trace.x, trace.y):
            for sub in _walk_exprs(node):
                if not isinstance(sub, ir.Name) or sub.role != "VARIABLE":
                    continue
                if sub.py in defined or sub.original in CONSTANTS:
                    continue
                if sub.py not in names:
                    names.append(sub.py)
    return names


def _walk_exprs(node: ir.Expr) -> "list[ir.Expr]":
    """``node`` and every descendant expression, pre-order."""
    out = [node]
    for child in ir.child_exprs(node):
        out.extend(_walk_exprs(child))
    return out


def _bound_names(region: ir.Region) -> set[str]:
    """The names a region binds, i.e. what is in scope below it."""
    if isinstance(region, (ir.Define, ir.IndexAssign)):
        return {region.target.py}
    if isinstance(region, ir.Recurrence):
        return {slot.base.py for slot in region.targets}
    if isinstance(region, (ir.MultiAssign, ir.ComboBoxAssign)):
        return {t.py for t in region.targets}
    if isinstance(region, ir.SolveBlock):
        return {t.py for t in region.targets} | {
            g.target.py for g in region.guesses
        }
    if isinstance(region, ir.SymbolDeclarations):
        return set(region.names)
    return set()


def _to_float(value: str | None) -> float:
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0
