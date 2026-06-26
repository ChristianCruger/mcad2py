"""Parse a Mathcad Prime ``worksheet.xml`` into an ordered IR worksheet."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Callable

from .. import ir
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

    # Bare expression region (no define/eval wrapper) -> treat as evaluation.
    return ir.Evaluate(value=parse_expr(inner), display_unit=None)


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


def _to_float(value: str | None) -> float:
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0
