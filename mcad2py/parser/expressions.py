"""Walk a Mathcad ``math50`` expression tree into IR expression nodes."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .. import ir
from ..mapping import GREEK, OPERATOR_TAGS
from .namespaces import localname


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


def read_identifier(elem: ET.Element) -> str:
    """Read the display text of an ``<ml:id>`` (handling XAML subscripts).

    ``f<pw:Subscript>cd</pw:Subscript>`` -> ``"f_cd"``.
    """
    parts: list[str] = []
    _collect_identifier(elem, parts)
    return "".join(parts).strip()


def _collect_identifier(elem: ET.Element, parts: list[str]) -> None:
    if localname(elem.tag).endswith("Subscript"):
        parts.append("_")
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        _collect_identifier(child, parts)
        if child.tail:
            parts.append(child.tail)


def sanitize(name: str) -> str:
    """Turn a Mathcad display name into a valid Python identifier."""
    out: list[str] = []
    for ch in name:
        if ch in GREEK:
            out.append(GREEK[ch])
        elif ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    result = "".join(out)
    if not result:
        result = "_"
    if result[0].isdigit():
        result = "_" + result
    return result


# ---------------------------------------------------------------------------
# Expression walk
# ---------------------------------------------------------------------------


def parse_expr(elem: ET.Element) -> ir.Expr:
    tag = localname(elem.tag)

    if tag == "real":
        return ir.Number((elem.text or "0").strip())

    if tag == "id":
        return _parse_id(elem)

    if tag == "parens":
        # Parens are cosmetic; the tree already encodes precedence, and the
        # code generator re-inserts parentheses as needed.
        children = list(elem)
        return parse_expr(children[0]) if children else ir.Placeholder()

    if tag == "placeholder":
        return ir.Placeholder()

    if tag == "apply":
        return _parse_apply(elem)

    if tag == "eval":
        # An eval nested inside an expression: take its value part.
        value, _unit = parse_eval(elem)
        return value

    return ir.Unsupported(note=tag, raw=_summarize(elem))


def _parse_id(elem: ET.Element) -> ir.Expr:
    display = read_identifier(elem)
    role = elem.get("labels", "VARIABLE")
    if role == "UNIT":
        return ir.UnitRef(name=display)
    return ir.Name(py=sanitize(display), original=display, role=role)


def _parse_apply(elem: ET.Element) -> ir.Expr:
    children = list(elem)
    if not children:
        return ir.Unsupported(note="empty apply")
    head, rest = children[0], children[1:]
    head_tag = localname(head.tag)

    # Function application: <apply><id labels="FUNCTION">tan</id> <arg/> ...
    if head_tag == "id":
        name = read_identifier(head)
        args = [parse_expr(c) for c in rest]
        return ir.Call(func=name, args=args, role=head.get("labels", "FUNCTION"))

    # Unit scaling: <apply><scale/> <value/> <unit/>
    if head_tag == "scale":
        value = parse_expr(rest[0])
        unit = parse_expr(rest[1])
        return ir.Quantity(value=value, unit=unit)

    # nth root: <apply><nthRoot/> <degree-or-placeholder/> <operand/>
    if head_tag == "nthRoot":
        degree_elem, operand_elem = rest[0], rest[1]
        degree = None
        if localname(degree_elem.tag) != "placeholder":
            degree = parse_expr(degree_elem)
        return ir.Root(operand=parse_expr(operand_elem), degree=degree)

    # Arithmetic operators.
    if head_tag in OPERATOR_TAGS:
        op = OPERATOR_TAGS[head_tag]
        operands = [parse_expr(c) for c in rest]
        if op == "neg":
            return ir.UnaryOp(op="neg", operand=operands[0])
        if len(operands) == 2:
            return ir.BinOp(op=op, left=operands[0], right=operands[1])
        return ir.Unsupported(note=f"{head_tag}/arity={len(operands)}")

    return ir.Unsupported(note=f"apply/{head_tag}", raw=_summarize(elem))


def parse_eval(elem: ET.Element) -> tuple[ir.Expr, str | None]:
    """Parse an ``<ml:eval>``: returns (value expr, display unit or None)."""
    children = list(elem)
    value = parse_expr(children[0])
    display_unit: str | None = None
    for child in children[1:]:
        if localname(child.tag) == "unitOverride":
            for sub in child:
                if localname(sub.tag) == "id":
                    display_unit = read_identifier(sub)
                    break
    return value, display_unit


def _summarize(elem: ET.Element) -> str:
    return localname(elem.tag) + "(" + ",".join(localname(c.tag) for c in elem) + ")"
