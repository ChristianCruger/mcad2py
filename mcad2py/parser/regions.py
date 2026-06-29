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

    for region in sorted(regions_elem, key=position):
        parsed = _parse_region(region, text_resolver, image_resolver)
        if parsed is not None:
            ws.regions.append(parsed)
    _inject_symbol_declarations(ws)
    return ws


def _parse_region(
    region: ET.Element,
    text_resolver: TextResolver | None,
    image_resolver: ImageResolver | None,
) -> ir.Region | None:
    for child in region:
        tag = localname(child.tag)
        if tag == "math":
            return _parse_math(child)
        if tag == "text":
            return _parse_text(child, text_resolver)
        if tag == "picture":
            return _parse_picture(child, image_resolver)
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

    # ``f(x) := ...``: the target is <ml:function> with a name and bound vars.
    if localname(target_elem.tag) == "function":
        target, params = _parse_function_header(target_elem)
    else:
        target = _parse_target(target_elem)
        params = []

    if localname(value_elem.tag) == "eval":
        value, unit = parse_eval(value_elem)
        return ir.Define(
            target=target, value=value, evaluate=True, display_unit=unit, params=params
        )
    return ir.Define(
        target=target, value=parse_expr(value_elem), evaluate=False, params=params
    )


def _parse_target(id_elem: ET.Element) -> ir.Name:
    display = read_identifier(id_elem)
    return ir.Name(
        py=sanitize(display),
        original=display,
        role=id_elem.get("labels", "VARIABLE"),
    )


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
