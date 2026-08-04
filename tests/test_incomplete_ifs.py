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

Its plot is where that matters. ``σ_cI(ε_con/1000)`` is drawn over a domain
running past 0, where the program has no branch -- and Mathcad's cached trace
holds a literal ``NaN`` at each such point, i.e. it draws the curve with a gap.
The plot also pins the *other* half of the implicit-domain rule: the author set
the x-axis limits to -7..1, and Mathcad sampled exactly those rather than its
default -10..10 (see test_implicit_plot_domain.py for that rule in isolation).
"""

import contextlib
import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from mcad2py import ir
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.emit.codegen import expr_to_str
from mcad2py.loader import load_mcdx
from mcad2py.parser.expressions import parse_expr

REFERENCE = Path(__file__).parent.parent / "references" / "incomplete_ifs.mcdx"


@pytest.fixture(scope="module")
def sheet() -> tuple[str, dict, list[str]]:
    """The generated source, the namespace after running it, and its output."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.close("all")
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


# --- The plot: an invented domain over a partly-undefined function -----------


def _cached_trace() -> tuple[np.ndarray, np.ndarray]:
    """The plot's cached ``<ml:Trace2dResult>`` as (x, y).

    Its two ``<ml:DataVectors>`` are the range points then the values; the
    values hold literal ``NaN`` wherever the program had no branch, which
    ``json.loads`` won't take but ``float`` will.
    """
    result_xml = load_mcdx(REFERENCE).result_xml or ""
    vectors = re.findall(
        r"<ml:DataVectors[^>]*>\[(.*?)\]</ml:DataVectors>", result_xml, re.S
    )
    assert len(vectors) == 2, "expected one cached trace"
    return tuple(  # type: ignore[return-value]
        np.array([float(v) for v in vec.split(",")]) for vec in vectors
    )


def _rendered_trace(sheet) -> tuple[np.ndarray, np.ndarray]:
    import matplotlib.pyplot as plt

    _, _, _ = sheet  # ensure the sheet has run and drawn its figure
    lines = [ln for fig in map(plt.figure, plt.get_fignums()) for ln in fig.axes[0].lines]
    curves = [ln for ln in lines if ln.get_label().startswith("sigma_cI")]
    assert len(curves) == 1
    return np.asarray(curves[0].get_xdata()), np.asarray(curves[0].get_ydata())


def test_author_set_axis_limits_are_the_invented_domain(sheet):
    """The x axis is set to -7..1, so that -- not the default -10..10 -- is
    what the free ``ε_con`` is sampled over."""
    src, _, _ = sheet
    assert "plot_domain(-7.0, 1.0, 499)" in src
    plot = next(r for r in convert_worksheet(load_mcdx(REFERENCE)).regions
                if isinstance(r, ir.Plot))
    assert plot.domain == "epsilon_con"
    assert plot.implicit_domain == (-7.0, 1.0, 499)


def test_trace_matches_the_cached_sample_point_for_point(sheet):
    x, y = _rendered_trace(sheet)
    cx, cy = _cached_trace()
    assert len(x) == len(cx) == 499
    assert np.allclose(x, cx, rtol=0, atol=1e-12)
    defined = ~np.isnan(cy)
    assert np.allclose(y[defined], cy[defined], rtol=1e-9, atol=0)


def test_undefined_points_are_gaps_exactly_where_mathcad_put_them(sheet):
    """The regression: past ε_con = 0 the program has no branch and returns
    ``None``. Mathcad caches ``NaN`` there and draws a gap; feeding ``None``
    into the axis conversion used to raise instead."""
    _, y = _rendered_trace(sheet)
    _, cy = _cached_trace()
    assert np.isnan(cy).any(), "fixture no longer plots past the defined range"
    assert np.array_equal(np.isnan(y), np.isnan(cy))


def test_gaps_keep_the_traces_units(sheet):
    """A NaN stands in for a stress, so it has to carry MPa like its
    neighbours -- otherwise the column can't fuse into one Pint array and the
    ``.to(MPa)`` axis conversion fails on a mixed object array."""
    _, ns, _ = sheet
    ureg = ns["ureg"]
    values = ns["sample"](
        lambda e: ns["sigma_cI"](e / 1000), np.array([-5.0, 0.5, -1.0])
    )
    assert values.check("[pressure]")
    magnitudes = values.to(ureg.MPa).magnitude
    assert np.isnan(magnitudes[1])
    assert not np.isnan(magnitudes[[0, 2]]).any()


def test_sample_fills_undefined_points_with_nan():
    """``sample`` in isolation: unit-bearing, plain, and all-undefined."""
    import pint

    from mcad2py.runtime import sample

    ureg = pint.UnitRegistry()
    out = sample(lambda x: None if x > 0 else x * ureg.MPa, np.array([-1.0, 1.0]))
    assert out.to(ureg.MPa).magnitude[0] == pytest.approx(-1.0)
    assert np.isnan(out.to(ureg.MPa).magnitude[1])

    plain = sample(lambda x: None if x > 0 else x, np.array([-1.0, 1.0]))
    assert np.isnan(np.asarray(plain, dtype=float)[1])

    # No defined point anywhere: nothing to take a unit from, so plain NaNs.
    blank = sample(lambda x: None, np.array([1.0, 2.0]))
    assert np.isnan(np.asarray(blank, dtype=float)).all()


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
