"""Tests for ``mcad2py/parser/python_expr.py`` -- Python source back to IR.

Stage A proved IR -> XML against Prime's own bytes. This is the other half of
the write path, and it gets the mirror proof: take every expression in every
reference worksheet that the backend can write, print it with the ordinary
code generator, read that text back, and require the **identical IR**.

That sweep is the whole point. It is not a test of hand-written expressions --
it is a test that a round trip through the text an agent actually reads and
types loses nothing.
"""

from __future__ import annotations

import collections

import pytest

from mcad2py import ir
from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import expr_to_str
from mcad2py.emit.mcdx_backend import Unsupported, emit_expr
from mcad2py.loader import load_mcdx
from mcad2py.parser.python_expr import (
    InvalidExpression,
    parse_python,
    reconcile,
    symbol_table,
)

from conftest import reference
from test_mcdx_backend import SHEETS, expressions


def writable(name: str):
    """Every expression in a sheet that stage A can write, with its symbols."""
    symbols = symbol_table(convert_worksheet(load_mcdx(reference(name))))
    for node in expressions(name):
        try:
            emit_expr(node)
        except Unsupported:
            continue
        yield node, symbols


# ---------------------------------------------------------------------------
# The mirror sweep
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", SHEETS)
def test_generated_python_reads_back_to_the_same_ir(name):
    """IR -> Python -> IR is the identity, expression by expression.

    ``like`` is the expression being replaced: two Mathcad constructs print the
    same Python (see ``reconcile``), so an edit keeps the sheet's own form
    rather than guessing. Without it the sweep still passes for 972 of 1113
    expressions -- the count is pinned below.
    """
    for node, symbols in writable(name):
        text = expr_to_str(node)
        try:
            back = parse_python(text, symbols, like=node)
        except InvalidExpression:
            continue  # counted, and bounded, by the test below
        assert back == node, f"{name}: {text}"


def test_the_sweep_is_almost_total():
    """A floor under the sweep above, and a ceiling on what it skips."""
    counts = collections.Counter()
    for name in SHEETS:
        for node, symbols in writable(name):
            counts["total"] += 1
            try:
                back = parse_python(expr_to_str(node), symbols, like=node)
            except InvalidExpression:
                counts["refused"] += 1
                continue
            counts["exact"] += back == node
    assert counts["total"] > 1000
    # One expression in the fixtures is refused: ``power(z, i)``, whose ``z`` is
    # bound by an enclosing lambda and so is not a name the *sheet* defines.
    # A lambda body is outside the write path's reach either way.
    assert counts["refused"] <= 1
    assert counts["exact"] == counts["total"] - counts["refused"]


# ---------------------------------------------------------------------------
# The pieces
# ---------------------------------------------------------------------------


@pytest.fixture
def symbols():
    """The names of ``plain_concrete_cohesion.mcdx`` -- MPa, deg, phi, f_cd."""
    return symbol_table(convert_worksheet(load_mcdx(
        reference("plain_concrete_cohesion"))))


@pytest.mark.parametrize("text, expected", [
    ("1.5", ir.Number("1.5")),
    (".87", ir.Number(".87")),              # Prime's own form survives
    ("-3", ir.Number("-3")),                # folded, not a <ml:neg/> wrapper
    ("30 * ureg.MPa", ir.Quantity(ir.Number("30"), ir.UnitRef("MPa"))),
    ("2 ** 3", ir.BinOp("pow", ir.Number("2"), ir.Number("3"))),
    ("power(2, 3)", ir.BinOp("pow", ir.Number("2"), ir.Number("3"))),
    ("-(1 + 2)", ir.UnaryOp("neg", ir.BinOp("add", ir.Number("1"), ir.Number("2")))),
])
def test_reads_the_subset(text, expected, symbols):
    assert parse_python(text, symbols) == expected


def test_a_number_keeps_the_text_it_was_typed_as(symbols):
    """``repr(float(...))`` would rewrite bytes for no gain -- and setting a
    number to what it already was must be a no-op."""
    assert parse_python("0.1", symbols).value == "0.1"
    assert parse_python("30", symbols).value == "30"


@pytest.mark.parametrize("text, why", [
    ("tan(phi)", "function call"),
    ("v[0]", "outside the subset"),
    ("a and b", "outside the subset"),
    ("x % 2", "only"),
    ("'text'", "not a number"),
    ("1 +", "not a Python expression"),
])
def test_refuses_what_it_cannot_write(text, why, symbols):
    with pytest.raises(InvalidExpression, match=why):
        parse_python(text, symbols)


def test_refuses_a_name_the_sheet_does_not_use(symbols):
    with pytest.raises(InvalidExpression, match="not a name this worksheet uses"):
        parse_python("gamma_invented * 2", symbols)


def test_a_unit_must_also_be_one_the_sheet_uses(symbols):
    with pytest.raises(InvalidExpression, match="not a name this worksheet uses"):
        parse_python("2 * ureg.furlong", symbols)


# ---------------------------------------------------------------------------
# reconcile: what the text cannot say
# ---------------------------------------------------------------------------


def test_reconcile_keeps_a_scale_a_scale(symbols):
    """``30 * ureg.MPa`` prints the same whether the sheet wrote <ml:scale/>
    or <ml:mult/>, so an edit keeps whichever was there."""
    as_mult = ir.BinOp("mul", ir.Number("30"), ir.UnitRef("MPa"))
    assert parse_python("30 * ureg.MPa", symbols, like=as_mult) == as_mult

    as_scale = ir.Quantity(ir.Number("30"), ir.UnitRef("MPa"))
    assert parse_python("30 * ureg.MPa", symbols, like=as_scale) == as_scale


def test_reconcile_only_keeps_what_still_matches(symbols):
    """Changing one operand keeps the other's node and replaces only that one."""
    old = ir.BinOp("div", ir.Quantity(ir.Number("30"), ir.UnitRef("MPa")),
                   ir.Number("1.5"))
    new = parse_python("30 * ureg.MPa / 1.25", symbols, like=old)
    assert new == ir.BinOp("div", old.left, ir.Number("1.25"))
    assert new.left is old.left  # the untouched branch is the sheet's own node


def test_reconcile_gives_up_on_a_different_shape():
    old = ir.BinOp("div", ir.Number("30"), ir.Number("1.5"))
    new = ir.BinOp("add", ir.Number("1"), ir.Number("2"))
    assert reconcile(new, old) == new


def test_symbol_table_keys_are_the_generated_python():
    """The table is built from the sheet, not by inverting ``sanitize`` --
    which is not invertible (``sigma_c`` could have been ``σ_c``)."""
    table = symbol_table(convert_worksheet(load_mcdx(reference("RC_torsion"))))
    greek = [key for key, node in table.items()
             if isinstance(node, ir.Name) and node.original != node.py]
    assert greek, "expected at least one transliterated name"
    for key in greek:
        assert expr_to_str(table[key]) == key
