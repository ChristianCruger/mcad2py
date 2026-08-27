"""Tests for ``mcad2py/emit/mcdx_backend.py`` -- IR back to Mathcad XML.

This is the first thing in the package that *writes* worksheet math, so the
property that matters is a round trip: XML the parser read, emitted again and
re-read, must give the identical IR. The IR nodes are dataclasses, so ``==``
compares the whole tree.

The sweep runs over every expression in every reference worksheet, which is
what makes the proof worth having: the shapes are Prime's own, not ones a test
author invented. Anything outside the backend's subset raises ``Unsupported``
and is skipped -- that is the point of the subset, and the count assertion at
the end stops the sweep quietly skipping everything.
"""

from __future__ import annotations

import dataclasses
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import expr_to_str
from mcad2py.emit.mcdx_backend import Unsupported, emit_expr, harvest_ids
from mcad2py.emit.py_backend import to_python
from mcad2py.loader import load_mcdx
from mcad2py.parser.expressions import parse_expr
from mcad2py.parser.namespaces import MATH, localname

from conftest import REFERENCES, reference

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from _mcdx_edit import element_span, find_region  # noqa: E402

ROOT = f'<root xmlns:ml="{MATH}">'


def reparse(xml: str):
    """Read back a fragment this backend wrote, as the worksheet would."""
    return parse_expr(list(ET.fromstring(ROOT + xml + "</root>"))[0])


def roundtrip(node):
    return reparse(emit_expr(node))


def expressions(name: str):
    """Every ``<ml:apply>`` in a reference worksheet, parsed to IR."""
    with zipfile.ZipFile(reference(name)) as zf:
        root = ET.fromstring(zf.read("mathcad/worksheet.xml"))
    for elem in root.iter():
        if localname(elem.tag) == "apply":
            yield parse_expr(elem)


SHEETS = sorted(p.stem for p in REFERENCES.glob("*.mcdx"))


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", SHEETS)
def test_every_supported_expression_survives_a_round_trip(name):
    written = 0
    for node in expressions(name):
        try:
            xml = emit_expr(node)
        except Unsupported:
            continue
        again = reparse(xml)
        assert again == node, f"{name}: {expr_to_str(node)}"
        written += 1
    # Recorded per sheet so a sheet that stops being covered is visible.
    print(f"{name}: {written} expressions round-tripped")


def test_the_sweep_reaches_real_worksheet_math():
    """A guard on the sweep above: skipping everything would also pass it."""
    total = sum(
        1 for name in SHEETS for node in expressions(name)
        if _writable(node)
    )
    assert total > 1000


def _writable(node) -> bool:
    try:
        emit_expr(node)
    except Unsupported:
        return False
    return True


# ---------------------------------------------------------------------------
# The pieces, stated directly
# ---------------------------------------------------------------------------


def test_writes_a_quantity_the_way_prime_does():
    node = parse_expr(ET.fromstring(
        ROOT + "<ml:apply><ml:scale /><ml:real>30</ml:real>"
        '<ml:id labels="UNIT">MPa</ml:id></ml:apply></root>'
    )[0])
    assert emit_expr(node) == (
        "<ml:apply><ml:scale /><ml:real>30</ml:real>"
        '<ml:id labels="UNIT" label-is-contextual="true"'
        ' xml:space="preserve">MPa</ml:id></ml:apply>'
    )


def test_a_subscripted_name_becomes_a_xaml_span():
    from mcad2py import ir

    xml = emit_expr(ir.Name(py="f_cd", original="f_cd"))
    assert "<pw:Subscript>cd</pw:Subscript>" in xml
    assert roundtrip(ir.Name(py="f_cd", original="f_cd")) == ir.Name(
        py="f_cd", original="f_cd")


@pytest.mark.parametrize("text, parens", [
    ("(a + b) * c", 1),      # a lower-precedence operand is grouped
    ("a + b * c", 0),        # a tighter one is not
    ("a - (b - c)", 1),      # the right of a left-associative operator
    ("a / b / c", 0),        # ... but not its left
    ("(a ** b) ** c", 1),    # the left of a right-associative one
    ("a ** b ** c", 0),
])
def test_parentheses_are_restored_where_prime_shows_them(text, parens):
    """The parser drops <ml:parens>; Prime displays from the tree, so the
    backend puts them back exactly where Python needs them."""
    node = _from_python(text)
    assert emit_expr(node).count("<ml:parens>") == parens
    assert expr_to_str(roundtrip(node)) == expr_to_str(node)


@pytest.mark.parametrize("value", ["2j", "1e-05", "0x10", "", "1.2.3"])
def test_refuses_a_literal_prime_would_not_write(value):
    from mcad2py import ir

    with pytest.raises(Unsupported):
        emit_expr(ir.Number(value))


def test_refuses_a_node_outside_the_subset():
    from mcad2py import ir

    with pytest.raises(Unsupported, match="Call"):
        emit_expr(ir.Call(func="tan", args=[ir.Number("1")]))


def test_refuses_a_name_mathcad_cannot_display():
    from mcad2py import ir

    with pytest.raises(Unsupported, match="display"):
        emit_expr(ir.Name(py="a_b_c", original="a_b_c"))


# ---------------------------------------------------------------------------


def _from_python(text: str):
    """Build IR for a small arithmetic expression, via Python's own parser.

    Only used to state the parenthesising rule in readable form; the real
    front end is stage B.
    """
    import ast

    from mcad2py import ir

    ops = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul",
           ast.Div: "div", ast.Pow: "pow"}

    def build(node):
        if isinstance(node, ast.BinOp):
            return ir.BinOp(op=ops[type(node.op)],
                            left=build(node.left), right=build(node.right))
        if isinstance(node, ast.Name):
            return ir.Name(py=node.id, original=node.id)
        raise AssertionError(node)

    return build(ast.parse(text, mode="eval").body)


# ---------------------------------------------------------------------------
# Fidelity against Prime's own bytes
# ---------------------------------------------------------------------------


def applies(name: str):
    """Every ``<ml:apply>`` in a worksheet as ``(raw text, IR)``."""
    with zipfile.ZipFile(reference(name)) as zf:
        ws = zf.read("mathcad/worksheet.xml").decode("utf-8")
    ids = harvest_ids(ws)
    for match in re.finditer(r"<ml:apply[\s>]", ws):
        start, end = element_span(ws, "ml:apply", match.start())
        yield ws[start:end], ids


def _normalise(xml: str) -> str:
    """Drop what Prime varies by position and what the parser never sees.

    ``label-is-contextual`` is absent on a unit inside a ``<ml:unitOverride>``
    and present on the same unit in an expression; ``labels="VARIABLE"`` is
    left out entirely by some sheets; and ``<ml:parens>`` is cosmetic (see
    ``_Writer.wrap``).
    """
    xml = xml.replace(' label-is-contextual="true"', "")
    xml = xml.replace(' labels="VARIABLE"', "")
    return re.sub(r"</?ml:parens>", "", xml)


# The two constructs the IR does not carry, so a rewritten region loses them:
#   <ml:percent/>  -- parsed as ``x / 100``, so ``80%`` re-emits as ``80/100``
#                     (same value, different display);
#   split=/inline= -- Prime's line-break hints on the operator element.
KNOWN_LOSSES = re.compile(r"<ml:percent|split=\"true\"|inline=\"true\"")


@pytest.mark.parametrize("name", SHEETS)
def test_re_emission_matches_primes_own_bytes(name):
    """Emitting an expression Prime wrote reproduces Prime's XML.

    Stronger than the round trip above, and the property a rewrite tool needs:
    a region rewritten with this backend must not restyle the math around the
    part that changed.
    """
    for raw, ids in applies(name):
        try:
            node = reparse(raw)
            out = emit_expr(node, ids)
        except (Unsupported, ET.ParseError):
            continue
        if KNOWN_LOSSES.search(raw):
            continue
        assert _normalise(out) == _normalise(raw), expr_to_str(node)


def test_most_expressions_re_emit_byte_for_byte():
    """Not just structurally equal -- identical, parentheses and all."""
    identical = total = 0
    for name in SHEETS:
        for raw, ids in applies(name):
            try:
                out = emit_expr(reparse(raw), ids)
            except (Unsupported, ET.ParseError):
                continue
            total += 1
            identical += out == raw
    assert total > 1000
    assert identical / total > 0.8


def test_harvested_ids_keep_a_names_own_encoding():
    """Prime writes a subscripted name two ways and the parser reads both the
    same, so a synthesised id would restyle one of them."""
    from mcad2py import ir

    plain = '<ml:id xml:space="preserve">m_s</ml:id>'
    node = ir.Name(py="m_s", original="m_s")
    assert emit_expr(node, {("VARIABLE", "m_s"): plain}) == plain
    assert "<pw:Subscript>" in emit_expr(node)  # without the map, XAML


def test_harvest_gives_up_rather_than_guess():
    assert harvest_ids("not xml at all") == {}


@pytest.mark.parametrize("name", SHEETS)
def test_every_sheet_yields_an_id_map(name):
    """The positional pairing holds on every fixture, so the fallback above is
    a safety net rather than the normal path."""
    with zipfile.ZipFile(reference(name)) as zf:
        ws = zf.read("mathcad/worksheet.xml").decode("utf-8")
    assert harvest_ids(ws)


# ---------------------------------------------------------------------------
# Spliced back into a real worksheet
# ---------------------------------------------------------------------------


def test_emitted_xml_splices_into_a_worksheet_and_converts():
    """The end-to-end proof: rewrite a region's math with this backend's own
    output, and both the bytes and the generated Python are unchanged.

    The round trip above uses a synthetic root. This one uses Prime's, which
    pins the assumption the module rests on -- that the ``ml:`` prefix the
    backend writes is the prefix ``worksheet.xml`` binds.
    """
    pkg = load_mcdx(reference("plain_concrete_cohesion"))
    ws = pkg.worksheet_xml
    before = to_python(convert_worksheet(pkg))

    # f_cd := 30 MPa / 1.5 -- the <ml:apply> that is the define's value.
    start = ws.index("<ml:apply", ws.index("<ml:eval>", find_region(ws, 0)[0]))
    start, end = element_span(ws, "ml:apply", start)

    node = reparse(ws[start:end])
    rewritten = ws[:start] + emit_expr(node, harvest_ids(ws)) + ws[end:]
    assert rewritten == ws

    after = to_python(convert_worksheet(
        dataclasses.replace(pkg, worksheet_xml=rewritten)))
    assert after == before


def test_a_changed_expression_reaches_the_generated_python():
    """The same splice, with one operand replaced -- the write path in
    miniature, minus the zip surgery and the guards a tool will add."""
    from mcad2py import ir

    pkg = load_mcdx(reference("plain_concrete_cohesion"))
    ws = pkg.worksheet_xml
    start = ws.index("<ml:apply", ws.index("<ml:eval>", find_region(ws, 0)[0]))
    start, end = element_span(ws, "ml:apply", start)

    scaled = ir.BinOp(op="mul", left=ir.Number("0.85"), right=reparse(ws[start:end]))
    rewritten = ws[:start] + emit_expr(scaled, harvest_ids(ws)) + ws[end:]

    source = to_python(convert_worksheet(
        dataclasses.replace(pkg, worksheet_xml=rewritten)))
    assert "f_cd = 0.85 * (30 * ureg.MPa / 1.5)" in source
