"""Python source -> IR: the front end of the write path (stage B).

An agent reads a worksheet as the Python this project generates, so the
smallest thing it can be asked to type back is that same Python. This module
reads it with Python's own ``ast`` and builds IR, which
:mod:`mcad2py.emit.mcdx_backend` then writes as Mathcad XML.

Two rules keep it safe:

* **The subset mirrors the backend's** -- numbers, units, ``+ - * / **``,
  negation and names. Anything else raises :class:`InvalidExpression`, so a
  construct we cannot write into a worksheet is refused while it is still
  text.
* **Every name must already exist in the sheet.** ``sanitize()`` is not
  reversible (``sigma_c`` could have been ``σ_c`` or ``sigma_c``), and a unit
  goes through ``unit_attr`` on the way out. Rather than invert either table,
  the caller passes a :func:`symbol_table` built from the worksheet's own IR:
  it maps the exact Python text of each name back to the node that produced
  it. A name the sheet has never used cannot be resolved, and is refused --
  which is also the behaviour we want, since inventing a new Mathcad
  identifier is a separate job.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping

from .. import ir

# Python operator -> canonical IR op. The same five the backend can write.
BIN_OPS = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
    ast.Pow: "pow",
}


class InvalidExpression(Exception):
    """The text is not an expression this project can write to a worksheet."""


def symbol_table(worksheet: ir.Worksheet) -> dict[str, ir.Expr]:
    """Map the generated Python for each name in ``worksheet`` to its IR node.

    Built from the sheet rather than by inverting ``sanitize``/``unit_attr``,
    so the mapping is exact by construction: the key is literally what the
    code generator printed for that node.
    """
    from ..emit.codegen import _walk_expr_tree, expr_to_str  # noqa: PLC0415

    table: dict[str, ir.Expr] = {}
    for region in worksheet.regions:
        for node in _walk_expr_tree(region):
            if isinstance(node, (ir.Name, ir.UnitRef)):
                table.setdefault(expr_to_str(node), node)
    return table


def parse_python(text: str, symbols: Mapping[str, ir.Expr],
                 like: ir.Expr | None = None) -> ir.Expr:
    """IR for the Python expression ``text``.

    ``symbols`` comes from :func:`symbol_table`. ``like`` is the expression
    being replaced, if any: where the generated Python cannot tell two Mathcad
    constructs apart, the one already in the sheet wins -- see
    :func:`reconcile`. Raises :class:`InvalidExpression` for anything outside
    the subset.
    """
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as exc:
        raise InvalidExpression(f"{text!r} is not a Python expression: {exc}") from exc
    built = _build(tree.body, symbols, text)
    return reconcile(built, like) if like is not None else built


def reconcile(new: ir.Expr, old: ir.Expr) -> ir.Expr:
    """``new``, but keeping ``old``'s form wherever the Python was ambiguous.

    The generated Python is not a faithful picture of the worksheet. Mathcad
    has two ways to write ``30 * ureg.MPa`` -- ``<ml:scale/>`` (a number
    carrying a unit, shown ``30 MPa``) and ``<ml:mult/>`` (shown ``30·MPa``) --
    and a sheet converted from ``.xmcd`` labels its names ``*`` rather than
    ``VARIABLE``. Neither difference reaches the text.

    So the rule is: **where two nodes print the same Python, the sheet's own
    node wins.** An edit to one operand of a formula then cannot restyle the
    rest of it. Below that, the walk descends in step through matching
    structure, so the untouched branches keep their exact nodes.
    """
    from ..emit.codegen import expr_to_str  # noqa: PLC0415

    if expr_to_str(new) == expr_to_str(old):
        return old
    if isinstance(new, ir.BinOp) and isinstance(old, ir.BinOp) and new.op == old.op:
        return ir.BinOp(op=new.op,
                        left=reconcile(new.left, old.left),
                        right=reconcile(new.right, old.right))
    if isinstance(new, ir.BinOp) and new.op == "mul" and isinstance(old, ir.Quantity):
        return ir.Quantity(value=reconcile(new.left, old.value),
                           unit=reconcile(new.right, old.unit))
    if isinstance(new, ir.Quantity) and isinstance(old, ir.BinOp) and old.op == "mul":
        return ir.BinOp(op="mul",
                        left=reconcile(new.value, old.left),
                        right=reconcile(new.unit, old.right))
    if isinstance(new, ir.Quantity) and isinstance(old, ir.Quantity):
        return ir.Quantity(value=reconcile(new.value, old.value),
                           unit=reconcile(new.unit, old.unit))
    if isinstance(new, ir.UnaryOp) and isinstance(old, ir.UnaryOp) and new.op == old.op:
        return ir.UnaryOp(op=new.op, operand=reconcile(new.operand, old.operand))
    return new


# ---------------------------------------------------------------------------


def _build(node: ast.expr, symbols: Mapping[str, ir.Expr], text: str) -> ir.Expr:
    if isinstance(node, ast.Constant):
        return _number(node, text)

    if isinstance(node, (ast.Name, ast.Attribute)):
        return _symbol(node, symbols)

    if isinstance(node, ast.BinOp):
        return _binop(node, symbols, text)

    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ast.USub):
            raise InvalidExpression(f"{_source(node, text)!r}: only unary - is supported")
        operand = _build(node.operand, symbols, text)
        if isinstance(operand, ir.Number) and not operand.value.startswith("-"):
            # Prime writes a negative literal straight into <ml:real> (the
            # ``-34`` of ``10**-34``), with no <ml:neg/> wrapper, so folding
            # here is what makes such a number round-trip.
            return ir.Number("-" + operand.value)
        return ir.UnaryOp(op="neg", operand=operand)

    if isinstance(node, ast.Call):
        # ``power(a, b)`` is what the code generator prints for a *fractional*
        # exponent (an integer one stays an inline ``**``), so reading it back
        # as a power is what makes a generated line round-trip.
        if isinstance(node.func, ast.Name) and node.func.id == "power" and (
                len(node.args) == 2 and not node.keywords):
            return ir.BinOp(
                op="pow",
                left=_build(node.args[0], symbols, text),
                right=_build(node.args[1], symbols, text),
            )
        raise InvalidExpression(
            f"{_source(node, text)!r}: a function call cannot be written to a "
            "worksheet yet")

    raise InvalidExpression(
        f"{_source(node, text)!r}: {type(node).__name__} is outside the subset")


def _binop(node: ast.BinOp, symbols: Mapping[str, ir.Expr], text: str) -> ir.Expr:
    op = BIN_OPS.get(type(node.op))
    if op is None:
        raise InvalidExpression(
            f"{_source(node, text)!r}: only + - * / ** are supported")
    left = _build(node.left, symbols, text)
    right = _build(node.right, symbols, text)
    if op == "mul" and isinstance(left, ir.Number) and _is_unit_expr(right):
        # ``30 * ureg.MPa`` is Mathcad's <ml:scale/> -- one *literal* carrying
        # a unit. The literal is what separates it from a multiplication:
        # ``alpha * ureg.deg`` and ``10**-34 * (ureg.kg * ureg.m**2 / ureg.s)``
        # are both <ml:mult/> in the fixtures, and across every reference sheet
        # no <ml:mult/> has a literal on the left and a bare unit on the right.
        # Where the sheet disagrees anyway, ``reconcile`` restores its form.
        return ir.Quantity(value=left, unit=right)
    return ir.BinOp(op=op, left=left, right=right)


def _is_unit_expr(node: ir.Expr) -> bool:
    """Whether ``node`` is what Mathcad's ``<ml:scale/>`` puts in its unit
    slot: one unit, or units combined by ``*``, ``/`` and a power.

    A number is allowed *inside* one (the exponent of ``ureg.cm**2``, the ``1``
    of ``1 / ureg.m``) but a unit has to be there: ``500 * 1000`` is not a
    scaled quantity.
    """
    return _unit_shaped(node) and _carries_a_unit(node)


def _unit_shaped(node: ir.Expr) -> bool:
    if isinstance(node, (ir.UnitRef, ir.Number)):
        return True
    if isinstance(node, ir.BinOp) and node.op in ("mul", "div", "pow"):
        return _unit_shaped(node.left) and _unit_shaped(node.right)
    return False


def _carries_a_unit(node: ir.Expr) -> bool:
    from ..emit.codegen import _has_unit  # noqa: PLC0415

    return _has_unit(node)


def _number(node: ast.Constant, text: str) -> ir.Expr:
    if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
        raise InvalidExpression(
            f"{node.value!r} is not a number Mathcad can store")
    # The typed text, not ``repr`` of the parsed value: ``30`` must stay ``30``
    # and ``.87`` must stay ``.87`` (Prime's own form), so that setting a
    # number to what it already was rewrites no bytes.
    source = _source(node, text)
    return ir.Number(source if source else repr(node.value))


def _symbol(node: ast.expr, symbols: Mapping[str, ir.Expr]) -> ir.Expr:
    name = ast.unparse(node)
    found = symbols.get(name)
    if found is None:
        raise InvalidExpression(
            f"{name!r} is not a name this worksheet uses. Only a name (or unit) "
            "already on the sheet can be written into a formula.")
    return found


def _source(node: ast.expr, text: str) -> str:
    return ast.get_source_segment(text, node) or ast.unparse(node)
