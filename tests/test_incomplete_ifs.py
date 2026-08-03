"""Blank lines inside a Mathcad **program**, and programs that don't cover
every case (``references/incomplete_ifs.mcdx``).

A blank line in a program is a bare ``<ml:placeholder/>`` child of
``<ml:program>``. Mathcad ignores it. We must too: a bare expression line is an
*implicit return*, so parsing the blank as a statement emitted ``return None``
in the middle of the function and swallowed every branch below it -- the sheet's
``σ_cI`` has a blank line after its first ``if``, and the whole rest of the
piecewise stress curve became unreachable.

The sheet is also deliberately *incomplete*: neither program has an else, so
some arguments match no branch at all. Mathcad reports "This program has no
return value" (cached as an ``<engineError>``); we return ``None``.
"""

import contextlib
import io
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mcad2py import ir
from mcad2py.convert import convert_file
from mcad2py.emit.codegen import expr_to_str
from mcad2py.loader import load_mcdx
from mcad2py.parser.expressions import parse_expr

REFERENCE = Path(__file__).parent.parent / "references" / "incomplete_ifs.mcdx"


@pytest.fixture(scope="module")
def sheet() -> tuple[str, dict, list[str]]:
    """The generated source, the namespace after running it, and its output."""
    src = convert_file(REFERENCE, fmt="py")
    namespace: dict = {}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(src, "<generated>", "exec"), namespace)  # noqa: S102
    return src, namespace, out.getvalue().splitlines()


def test_blank_program_line_is_not_a_return(sheet):
    """The regression: no ``return None`` where the blank line was."""
    src, _, _ = sheet
    assert "None  # placeholder" not in src


def test_every_branch_below_the_blank_line_survives(sheet):
    """``σ_cI``'s blank line sits after the first ``if``; all six branches of
    the piecewise curve must still be emitted (the bug left only the first)."""
    src, _, _ = sheet
    body = src.split("def sigma_cI(epsilon):")[1].split("sigma_cI = elementwise")[0]
    assert body.count("        return ") == 6
    # ...and no statement between the first and second branch swallowing them.
    assert body.split("return -f_ck")[1].lstrip().startswith("if epsilon_cu2 <=")


def test_matches_cached_results(sheet):
    """Mathcad's cached ``result.xml`` for the sheet's three evaluations."""
    _, ns, printed = sheet
    ureg = ns["ureg"]
    P3 = ns["P3"]

    # -28125000 Pa: the quadratic branch, from a program with no blank line.
    assert ns["sigma_c"](P3).to(ureg.Pa).magnitude == pytest.approx(-28125000)
    # -30000000 Pa: the branch *directly below* σ_cI's blank line. This is the
    # value the bug destroyed -- it returned None here.
    assert ns["sigma_cI"](-0.003).to(ureg.Pa).magnitude == pytest.approx(-30000000)
    assert printed == ["-28.125 megapascal", "None", "-30 megapascal"]


def test_uncovered_case_returns_none(sheet):
    """A documented divergence: for ``σ_c(-P3)`` (+0.0015, outside every test)
    Mathcad caches an engineError, "This program has no return value. You must
    account for all cases when using conditional statements in a Mathcad
    program." We fall off the end of the ``def`` and return ``None`` instead.
    """
    _, ns, _ = sheet
    assert ns["sigma_c"](-ns["P3"]) is None


# --- The placement cases the fixture is too simple to show -------------------

_IF = (
    "<if><test><apply><lessThan/>"
    '<id labels="VARIABLE">x</id><real>1</real>'
    "</apply></test><then><program>{body}</program></then></if>"
)
_THEN = _IF.format(body="<real>7</real>")


def _program(*lines: str) -> ir.Expr:
    return parse_expr(ET.fromstring("<program>" + "".join(lines) + "</program>"))


@pytest.mark.parametrize(
    "lines",
    [
        pytest.param(("<placeholder/>", _THEN), id="leading"),
        pytest.param((_THEN, "<placeholder/>"), id="trailing"),
        pytest.param(
            (_IF.format(body="<placeholder/><real>7</real>"),), id="inside-then"
        ),
    ],
)
def test_blank_line_leaves_a_one_line_program_inline(lines):
    """A one-line program reduces to a ternary rather than becoming a ``def``.

    A blank line must not change that -- the emptiness is counted *before* the
    "more than one line" test, or a trailing blank alone would turn a plain
    ``σ := if …`` into a function definition.
    """
    node = _program(*lines)
    assert isinstance(node, ir.Program)
    assert expr_to_str(node).startswith("7 if x < 1 else")


def test_blank_line_between_two_lines_keeps_both_statements():
    node = _program(_THEN, "<placeholder/>", _THEN)
    assert isinstance(node, ir.ProgramBlock)
    assert [type(s).__name__ for s in node.statements] == ["IfStmt", "IfStmt"]


def test_program_of_only_a_blank_line_is_empty():
    assert isinstance(_program("<placeholder/>"), ir.Placeholder)


def test_the_fixture_really_contains_a_blank_program_line():
    """Guard the fixture: if a re-save ever dropped the blank line, the tests
    above would all still pass while testing nothing."""
    root = ET.fromstring(load_mcdx(REFERENCE).worksheet_xml)
    blanks = [
        c
        for e in root.iter()
        if e.tag.rsplit("}", 1)[-1] == "program"
        for c in e
        if c.tag.rsplit("}", 1)[-1] == "placeholder"
    ]
    assert blanks, "fixture no longer has a blank line inside a program"
