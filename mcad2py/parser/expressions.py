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

    if tag == "str":
        return ir.Str(elem.text or "")

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

    if tag == "program":
        # A program used as a *value*. A single-expression program (e.g.
        # ``σ_nd := <program with one if>``) reduces to that expression (a
        # ternary); a genuinely imperative program (local assigns, loops,
        # ``return``, ``tryCatch``) becomes a ProgramBlock emitted as a ``def``.
        kids = list(elem)
        if any(localname(k.tag) in _STMT_TAGS for k in kids) or len(kids) > 1:
            return _parse_program_block(elem)
        if len(kids) == 1:
            return parse_expr(kids[0])
        return ir.Placeholder()

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
        # Mathcad's inline ``if(cond, then, else)`` (a KEYWORD-labelled head) is
        # a conditional *expression*, not a call -> reuse the Program/ternary IR.
        if name == "if":
            args = _call_args(rest)
            branches: list[tuple[ir.Expr | None, ir.Expr]] = [(args[0], args[1])]
            if len(args) > 2:
                branches.append((None, args[2]))
            return ir.Program(branches=branches)
        return ir.Call(func=name, args=_call_args(rest), role=head.get("labels", "FUNCTION"))

    # Element access: <apply><indexer/> <base/> <index/>  (0-based). A
    # ``<sequence>`` of two indices is a matrix element ``M[i, j]``.
    if head_tag == "indexer":
        base = parse_expr(rest[0])
        idx_elem = rest[1]
        if localname(idx_elem.tag) == "sequence":
            parts = list(idx_elem)
            if len(parts) == 2:
                return ir.Index2D(
                    base=base, row=parse_expr(parts[0]), col=parse_expr(parts[1])
                )
        return ir.Index(base=base, index=parse_expr(idx_elem))

    # Element-wise 'arrow': <apply><vectorize/> <expr/>.
    if head_tag == "vectorize":
        return ir.Vectorize(operand=parse_expr(rest[0]))

    # Matrix/vector transpose: <apply><transpose/> <operand/>.
    if head_tag == "transpose":
        return ir.Transpose(operand=parse_expr(rest[0]))

    # Column extraction A^<i>: <apply><matcol/> <base/> <index/>.
    if head_tag == "matcol":
        return ir.MatCol(base=parse_expr(rest[0]), index=parse_expr(rest[1]))

    # Percent postfix: <apply><percent/> <operand/>  ==  operand / 100.
    if head_tag == "percent":
        return ir.BinOp(op="div", left=parse_expr(rest[0]), right=ir.Number("100"))

    # Definite numeric integral / discrete summation: a <ml:lambda> integrand
    # or summand plus <ml:lowerBound>/<ml:upperBound>.
    if head_tag in ("integral", "summation"):
        return _parse_integral_like(head_tag, rest)

    # Unit scaling: <apply><scale/> <value/> <unit/>
    if head_tag == "scale":
        value = parse_expr(rest[0])
        # A placeholder unit (Mathcad's "no unit" slot, e.g. a dimensionless data
        # table column of strings/numbers) means the value stands alone -- wrapping
        # it in a Quantity would emit ``<value> * None``.
        if localname(rest[1].tag) == "placeholder":
            return value
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


def _parse_lambda(elem: ET.Element) -> ir.Lambda:
    """Parse ``<ml:lambda>``: bound-variable names and the body expression."""
    bound = next((c for c in elem if localname(c.tag) == "boundVars"), None)
    params = (
        [sanitize(read_identifier(p)) for p in bound if localname(p.tag) == "id"]
        if bound is not None
        else []
    )
    body_elem = next(
        (c for c in elem if localname(c.tag) != "boundVars"), None
    )
    body = parse_expr(body_elem) if body_elem is not None else ir.Placeholder()
    return ir.Lambda(params=params, body=body)


def _parse_integral_like(head_tag: str, rest: list[ET.Element]) -> ir.Expr:
    """Parse an integral/summation: a lambda plus lower/upper bounds."""
    func: ir.Lambda | None = None
    lower: ir.Expr = ir.Placeholder()
    upper: ir.Expr = ir.Placeholder()
    for child in rest:
        ctag = localname(child.tag)
        if ctag == "lambda":
            func = _parse_lambda(child)
        elif ctag == "lowerBound" and len(child):
            lower = parse_expr(child[0])
        elif ctag == "upperBound" and len(child):
            upper = parse_expr(child[0])
    if func is None:
        return ir.Unsupported(note=f"apply/{head_tag} (no integrand)")
    # A bare ``Σ`` with no index variable and no bounds (empty placeholders) sums
    # every element of an already-built vector -> a VectorSum, not an indexed sum.
    if head_tag == "summation" and not func.params:
        return ir.VectorSum(operand=func.body)
    cls = ir.Integral if head_tag == "integral" else ir.Summation
    return cls(func=func, lower=lower, upper=upper)


def _parse_matrix(elem: ET.Element) -> ir.Expr:
    rows = int(elem.get("rows", "0") or 0)
    cols = int(elem.get("cols", "0") or 0)
    # <ml:display> is a display-formatting hint, not a data element -- skip it.
    elements = [parse_expr(c) for c in elem if localname(c.tag) != "display"]
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
        elif ctag in ("elseif", "alsoif"):
            # ``alsoif`` is Prime's "also if" (an elif): a sibling carrying its
            # own test + then.
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
    """Parse ``<ml:range>`` into a start/stop (and optional step).

    Two XML shapes occur:
      * explicit step -- a ``<sequence>`` holding ``start, next`` followed by the
        stop value; the step is ``next - start``;
      * implicit step (``i := 1 .. n``) -- two bare children ``start, stop`` with
        no ``<sequence>``; the step defaults to 1.
    """
    seq = next((c for c in elem if localname(c.tag) == "sequence"), None)
    if seq is None:
        kids = list(elem)
        start = parse_expr(kids[0]) if kids else ir.Placeholder()
        stop = parse_expr(kids[1]) if len(kids) > 1 else ir.Placeholder()
        return ir.Range(start=start, stop=stop, step=None)
    seq_items = list(seq)
    after = [c for c in elem if localname(c.tag) != "sequence"]
    start = parse_expr(seq_items[0]) if seq_items else ir.Placeholder()
    stop = parse_expr(after[0]) if after else ir.Placeholder()
    step: ir.Expr | None = None
    if len(seq_items) > 1:
        step = ir.BinOp(op="sub", left=parse_expr(seq_items[1]), right=start)
    return ir.Range(start=start, stop=stop, step=step)


# Program-body child tags that mark an *imperative* (multi-line) program, as
# opposed to a single value expression (which reduces to a ternary).
_STMT_TAGS = frozenset({"localDefine", "for", "return", "tryCatch"})


def _parse_program_block(elem: ET.Element) -> ir.ProgramBlock:
    """Parse an imperative ``<ml:program>`` into a :class:`ir.ProgramBlock`."""
    return ir.ProgramBlock(statements=[_parse_stmt(c) for c in elem])


def _parse_stmt(child: ET.Element) -> ir.Stmt:
    tag = localname(child.tag)
    if tag == "localDefine":
        kids = list(child)
        return ir.LocalAssign(target=parse_expr(kids[0]), value=parse_expr(kids[1]))
    if tag == "for":
        kids = list(child)
        var = _parse_id(kids[0])
        return ir.ForLoop(
            var=var,  # type: ignore[arg-type]
            iterable=parse_expr(kids[1]),
            body=_parse_program_block(kids[2]),
        )
    if tag == "if":
        branches: list[tuple[ir.Expr | None, ir.ProgramBlock]] = []
        _collect_stmt_branches(child, branches)
        return ir.IfStmt(branches=branches)
    if tag == "return":
        kids = list(child)
        return ir.Return(value=parse_expr(kids[0]) if kids else ir.Placeholder())
    if tag == "tryCatch":
        kids = list(child)
        return ir.TryCatch(
            body=_parse_program_block(kids[0]),
            handler=_parse_program_block(kids[1]),
        )
    # A bare expression as a statement is the program's (or branch's) value --
    # Mathcad's implicit return.
    return ir.Return(value=parse_expr(child))


def _collect_stmt_branches(
    elem: ET.Element, branches: list[tuple[ir.Expr | None, ir.ProgramBlock]]
) -> None:
    """Collect statement-form if/elseif/else branches (bodies are blocks)."""
    test: ir.Expr | None = None
    for child in elem:
        ctag = localname(child.tag)
        if ctag == "test":
            test = parse_expr(child[0]) if len(child) else None
        elif ctag == "then":
            branches.append((test, _stmt_block(child)))
        elif ctag in ("elseif", "alsoif"):
            _collect_stmt_branches(child, branches)
        elif ctag == "else":
            branches.append((None, _stmt_block(child)))


def _stmt_block(elem: ET.Element) -> ir.ProgramBlock:
    """The block inside a ``<ml:then>``/``<ml:else>`` (wrapped in a program)."""
    inner = elem[0] if len(elem) else None
    if inner is not None and localname(inner.tag) == "program":
        return _parse_program_block(inner)
    stmts = [ir.Return(value=parse_expr(inner))] if inner is not None else []
    return ir.ProgramBlock(statements=stmts)


def _summarize(elem: ET.Element) -> str:
    return localname(elem.tag) + "(" + ",".join(localname(c.tag) for c in elem) + ")"
