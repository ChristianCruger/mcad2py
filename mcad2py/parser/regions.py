"""Parse a Mathcad Prime ``worksheet.xml`` into an ordered IR worksheet."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Callable

from .. import ir
from ..mapping import SYMBOLIC_COMMANDS
from .expressions import parse_eval, parse_expr, read_identifier, sanitize
from .namespaces import localname

# A callable that resolves a text region's ``item-idref`` to its plain text.
TextResolver = Callable[[str], str]


def parse_worksheet(
    worksheet_xml: str,
    text_resolver: TextResolver | None = None,
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

    for region in sorted(regions_elem, key=position):
        parsed = _parse_region(region, text_resolver)
        if parsed is not None:
            ws.regions.append(parsed)
    _inject_symbol_declarations(ws)
    return ws


def _parse_region(
    region: ET.Element, text_resolver: TextResolver | None
) -> ir.Region | None:
    for child in region:
        tag = localname(child.tag)
        if tag == "math":
            return _parse_math(child)
        if tag == "text":
            return _parse_text(child, text_resolver)
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

    # Bare symbolic equation (no define/eval wrapper): <apply><equal/> ...>.
    if tag == "apply":
        head = next(iter(inner), None)
        if head is not None and localname(head.tag) == "equal":
            return ir.SymbolicEquation(equation=parse_expr(inner))

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
            # The first non-command/result child is the input expression.
            expr = parse_expr(child)

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
    target = ir.Name(
        py=sanitize(read_identifier(target_elem)),
        original=read_identifier(target_elem),
        role=target_elem.get("labels", "VARIABLE"),
    )
    if localname(value_elem.tag) == "eval":
        value, unit = parse_eval(value_elem)
        return ir.Define(target=target, value=value, evaluate=True, display_unit=unit)
    return ir.Define(
        target=target, value=parse_expr(value_elem), evaluate=False, display_unit=None
    )


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
