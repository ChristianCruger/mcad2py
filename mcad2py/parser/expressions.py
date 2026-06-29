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

    if tag == "matrix":
        return _parse_matrix(elem)

    if tag == "if":
        return _parse_if(elem)

    if tag == "range":
        return _parse_range(elem)

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
    # Multi-argument calls wrap their args in a single <ml:sequence>.
    if head_tag == "id":
        # Sanitize so a user function called by a Greek/subscripted name
        # (``σ_s`` -> ``sigma_s``) matches its definition. Builtins are ASCII,
        # so sanitize leaves them unchanged for the FUNCTIONS lookup.
        name = sanitize(read_identifier(head))
        return ir.Call(func=name, args=_call_args(rest), role=head.get("labels", "FUNCTION"))

    # Element access: <apply><indexer/> <base/> <index/>  (0-based).
    if head_tag == "indexer":
        return ir.Index(base=parse_expr(rest[0]), index=parse_expr(rest[1]))

    # Element-wise 'arrow': <apply><vectorize/> <expr/>.
    if head_tag == "vectorize":
        return ir.Vectorize(operand=parse_expr(rest[0]))

    # Unit scaling: <apply><scale/> <value/> <unit/>
    if head_tag == "scale":
        value = parse_expr(rest[0])
        unit = parse_expr(rest[1])
        return ir.Quantity(value=value, unit=unit)

    # Symbolic equation: <apply><equal/> <lhs/> <rhs/>  (Mathcad boolean ``=``).
    if head_tag == "equal":
        return ir.Equation(lhs=parse_expr(rest[0]), rhs=parse_expr(rest[1]))

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


def parse_eval(elem: ET.Element) -> tuple[ir.Expr, ir.Expr | None]:
    """Parse an ``<ml:eval>``: returns (value expr, display-unit expr or None).

    The display unit may be a single unit (``mm``) or a compound expression
    (``kN*m`` -> ``<apply><mult/>...``); a ``<ml:placeholder/>`` means automatic
    units, which we represent as None.
    """
    children = list(elem)
    value = parse_expr(children[0])
    display_unit: ir.Expr | None = None
    for child in children[1:]:
        if localname(child.tag) == "unitOverride":
            display_unit = _parse_unit_override(child)
    return value, display_unit


def _parse_unit_override(elem: ET.Element) -> ir.Expr | None:
    """The unit expression inside ``<ml:unitOverride>``, or None for auto."""
    for sub in elem:
        if localname(sub.tag) == "placeholder":
            return None
        return parse_expr(sub)
    return None


def _call_args(rest: list[ET.Element]) -> list[ir.Expr]:
    """Call arguments, flattening a single ``<ml:sequence>`` wrapper."""
    if len(rest) == 1 and localname(rest[0].tag) == "sequence":
        return [parse_expr(c) for c in rest[0]]
    return [parse_expr(c) for c in rest]


def _parse_matrix(elem: ET.Element) -> ir.Expr:
    rows = int(elem.get("rows", "0") or 0)
    cols = int(elem.get("cols", "0") or 0)
    elements = [parse_expr(c) for c in elem]
    return ir.MatrixLiteral(rows=rows, cols=cols, elements=elements)


def _parse_if(elem: ET.Element) -> ir.Expr:
    """Parse an ``<ml:if>`` (with ``elseif``/``else``) into branch pairs."""
    branches: list[tuple[ir.Expr | None, ir.Expr]] = []
    _collect_branches(elem, branches)
    return ir.Program(branches=branches)


def _collect_branches(
    elem: ET.Element, branches: list[tuple[ir.Expr | None, ir.Expr]]
) -> None:
    test: ir.Expr | None = None
    for child in elem:
        ctag = localname(child.tag)
        if ctag == "test":
            test = parse_expr(child[0]) if len(child) else None
        elif ctag == "then":
            branches.append((test, _unwrap_program(child)))
        elif ctag == "elseif":
            _collect_branches(child, branches)
        elif ctag == "else":
            branches.append((None, _unwrap_program(child)))


def _unwrap_program(elem: ET.Element) -> ir.Expr:
    """The result expression inside a ``<ml:then>``/``<ml:else>`` wrapper.

    Bodies are wrapped in ``<ml:program>``; we take its single expression.
    """
    inner = elem[0] if len(elem) else None
    if inner is not None and localname(inner.tag) == "program":
        return parse_expr(inner[0]) if len(inner) else ir.Placeholder()
    return parse_expr(inner) if inner is not None else ir.Placeholder()


def _parse_range(elem: ET.Element) -> ir.Expr:
    """Parse ``<ml:range>``: a ``start[, next]`` sequence then a stop value.

    The step is ``next - start`` (1 if no explicit ``next``).
    """
    seq = next((c for c in elem if localname(c.tag) == "sequence"), None)
    seq_items = list(seq) if seq is not None else []
    after = [c for c in elem if localname(c.tag) != "sequence"]
    start = parse_expr(seq_items[0]) if seq_items else ir.Placeholder()
    stop = parse_expr(after[0]) if after else ir.Placeholder()
    step: ir.Expr | None = None
    if len(seq_items) > 1:
        step = ir.BinOp(op="sub", left=parse_expr(seq_items[1]), right=start)
    return ir.Range(start=start, stop=stop, step=step)


def _summarize(elem: ET.Element) -> str:
    return localname(elem.tag) + "(" + ",".join(localname(c.tag) for c in elem) + ")"
