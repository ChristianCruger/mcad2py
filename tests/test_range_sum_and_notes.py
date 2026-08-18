"""Two defects a wide interpolation worksheet exposed, both general.

Neither has a reference fixture behind it: the sheet that surfaced them calls
several functions it never defines (a Mathcad add-in library), so it cannot be
executed end to end and cannot be compared against ``result.xml``. These pin
the two fixes directly instead.
"""

from __future__ import annotations

import ast

import numpy as np
import pytest

from mcad2py import ir
from mcad2py.emit.codegen import expr_to_str
from mcad2py.parser.expressions import parse_expr
from mcad2py.runtime import range_sum
from mcad2py.units import ureg

MATH = "http://schemas.mathsoft.com/math50"


def _element(inner: str):
    """One ``math50`` element, namespaced the way ``worksheet.xml`` has it."""
    import xml.etree.ElementTree as ET

    return ET.fromstring(f'<ml:root xmlns:ml="{MATH}">{inner}</ml:root>')[0]


# ---------------------------------------------------------------------------
# A note nested in an expression must not close the line.


def test_a_nested_placeholder_still_parses():
    """``f(a, None  # placeholder)`` would put the ``)`` inside the comment.

    That is the one outcome the "unknown constructs stay visible but the output
    still loads" convention exists to prevent, and a trailing-note check only
    catches it when the note is the whole expression.
    """
    node = ir.Call(
        func="summation",
        args=[ir.Name(py="f", original="f"), ir.Placeholder(), ir.Placeholder()],
    )
    rendered = expr_to_str(node)
    ast.parse(rendered)  # the assertion: it is Python at all
    assert "placeholder" in rendered
    assert rendered.index("#") > rendered.index(")")


def test_a_nested_unsupported_note_survives_to_the_end_of_the_line():
    """The note is lifted, not dropped -- a silent ``None`` would be worse."""
    node = ir.Call(
        func="foo",
        args=[ir.Unsupported(note="apply/derivative"), ir.Number(value="2")],
    )
    rendered = expr_to_str(node)
    ast.parse(rendered)
    assert rendered == "foo(None, 2)  # TODO unsupported: apply/derivative"


def test_two_notes_in_one_expression_are_both_reported():
    node = ir.Call(func="foo", args=[ir.Placeholder(), ir.Unsupported(note="x")])
    rendered = expr_to_str(node)
    ast.parse(rendered)
    assert rendered == "foo(None, None)  # placeholder; TODO unsupported: x"


def test_a_top_level_note_is_unchanged():
    """The common case must render exactly as it did before the fix."""
    assert expr_to_str(ir.Unsupported(note="apply/derivative")) == (
        "None  # TODO unsupported: apply/derivative"
    )


def test_notes_do_not_leak_between_expressions():
    """The collector is per outermost call, not per module."""
    expr_to_str(ir.Unsupported(note="first"))
    assert expr_to_str(ir.Number(value="1")) == "1"


# ---------------------------------------------------------------------------
# Mathcad's Σ over a range variable.


def test_a_summation_with_an_index_but_no_bounds_is_a_range_sum():
    """``<ml:summation>`` + a bound variable + an empty ``<upperBound>``.

    Distinct from the bare ``Σ`` over a vector, where the bound variable is
    empty too and the IR is a ``VectorSum``.
    """
    node = parse_expr(
        _element(
            "<ml:apply><ml:summation/>"
            "<ml:lambda><ml:boundVars><ml:id>i</ml:id></ml:boundVars>"
            "<ml:apply><ml:indexer/><ml:id>c</ml:id><ml:id>i</ml:id></ml:apply>"
            "</ml:lambda>"
            "<ml:upperBound><ml:placeholder/></ml:upperBound>"
            "</ml:apply>"
        )
    )
    assert isinstance(node, ir.RangeSum)
    assert expr_to_str(node) == "range_sum(i, lambda i: c[i])"


def test_a_summation_with_real_bounds_is_still_an_indexed_sum():
    node = parse_expr(
        _element(
            "<ml:apply><ml:summation/>"
            "<ml:lambda><ml:boundVars><ml:id>i</ml:id></ml:boundVars>"
            "<ml:id>i</ml:id></ml:lambda>"
            "<ml:lowerBound><ml:real>0</ml:real></ml:lowerBound>"
            "<ml:upperBound><ml:real>4</ml:real></ml:upperBound>"
            "</ml:apply>"
        )
    )
    assert isinstance(node, ir.Summation)
    assert expr_to_str(node) == "summation(lambda i: i, 0, 4)"


def test_a_bare_summation_is_still_a_vector_sum():
    node = parse_expr(
        _element(
            "<ml:apply><ml:summation/>"
            "<ml:lambda><ml:boundVars/><ml:id>v</ml:id></ml:lambda>"
            "<ml:upperBound><ml:placeholder/></ml:upperBound>"
            "</ml:apply>"
        )
    )
    assert isinstance(node, ir.VectorSum)
    assert expr_to_str(node) == "total(v)"


def test_range_sum_runs_over_every_value_in_the_domain():
    domain = np.array([0.0, 1.0, 2.0, 3.0])
    assert range_sum(domain, lambda i: i**2) == pytest.approx(14.0)


def test_range_sum_keeps_units_on_the_domain():
    """A dimensioned range must reach the body with its unit intact.

    Stripping to magnitudes would make ``Σ x`` over a millimetre range come out
    a thousand times off against the same range in metres.
    """
    domain = ureg.Quantity(np.array([1.0, 2.0, 3.0]), "m")
    total = range_sum(domain, lambda x: x * 2)
    assert total.to("mm").magnitude == pytest.approx(12000.0)


def test_range_sum_keeps_units_on_the_result():
    domain = np.array([0.0, 1.0, 2.0])
    total = range_sum(domain, lambda i: (i + 1) * ureg.Quantity(1.0, "kN"))
    assert total.to("N").magnitude == pytest.approx(6000.0)


def test_range_sum_of_an_empty_domain_is_zero():
    assert range_sum(np.array([]), lambda i: i) == 0


def test_range_sum_accepts_a_scalar_domain():
    """``np.atleast_1d`` guards the one-element case Mathcad allows."""
    assert range_sum(2.0, lambda i: i * 3) == pytest.approx(6.0)
