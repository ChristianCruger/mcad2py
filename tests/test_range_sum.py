"""``references/range_sum.mcdx`` -- Mathcad's three ``Σ`` forms, side by side.

Prime writes all three with the same ``<ml:summation>`` head and tells them
apart by the lambda's bound variable and the bounds. The sheet puts one of each
over the same data, so a mix-up between them shows as a wrong number rather
than as a parse failure:

* no bound variable, no bounds -> the bare ``Σ`` over a vector (``total``);
* a bound variable, no bounds -> **range summation** over that range variable;
* a bound variable with both bounds -> the ordinary indexed sum.

The middle one is what this fixture exists to pin. It was implemented from the
XML shape alone, because the worksheet that first produced it could not be
executed; these cached numbers are the confirmation.
"""

from __future__ import annotations

import pytest

from conftest import cached_results, flat, reference, run_sheet
from mcad2py import ir
from mcad2py.emit.codegen import expr_to_str
from mcad2py.parser.expressions import parse_expr

SHEET = reference("range_sum")


@pytest.fixture(scope="module")
def sheet():
    return run_sheet(SHEET)


@pytest.fixture(scope="module")
def cache():
    return cached_results(SHEET)


def test_generated_source_shape(sheet):
    """Each ``Σ`` reaches a different helper."""
    source, _ns, _echoed = sheet
    assert "total(X)" in source
    assert "A = range_sum(i, lambda i: X[i])" in source
    assert "summation(lambda j: X[j], 1, 4)" in source
    assert "range_sum(i, lambda i: f(2 * i))" in source


def test_the_indexed_vector_matches(sheet, cache):
    """``X[i] := mod(2i, 7)`` over ``i := 0..10``."""
    _source, _ns, echoed = sheet
    assert flat(echoed[0]).tolist() == cache["1"]


def test_a_bare_sigma_totals_the_vector(sheet, cache):
    _source, _ns, echoed = sheet
    assert flat(echoed[1]).tolist() == cache["2"]


def test_a_range_sum_covers_the_whole_range_variable(sheet, cache):
    """The point of the sheet: ``Σ_i X[i]`` with no bounds equals ``total(X)``.

    Both cache as 33, which is what settles the semantics -- an empty bound is
    the *whole* range variable, not an unfinished slot and not a zero-length
    sum.
    """
    _source, ns, echoed = sheet
    assert flat(echoed[2]).tolist() == cache["3"]
    assert cache["3"] == cache["2"]
    assert ns["A"] == pytest.approx(33.0)


def test_an_indexed_sum_still_honours_its_bounds(sheet, cache):
    """``Σ_{j=1}^{4} X[j]`` is 13, not the whole vector's 33."""
    _source, _ns, echoed = sheet
    assert flat(echoed[3]).tolist() == cache["4"]
    assert cache["4"] != cache["2"]


def test_an_indexed_sum_over_a_function(sheet, cache):
    _source, _ns, echoed = sheet
    assert flat(echoed[4]).tolist() == cache["6"]


def test_a_range_sum_over_an_expression_in_the_index(sheet, cache):
    """``Σ_i f(2i)`` -- the index is used, not just passed through.

    1551 is ``Σ(4i² + 1)`` for ``i = 0..10``, so this pins both the domain and
    that the body sees each index value rather than the range as a whole.
    """
    _source, _ns, echoed = sheet
    assert flat(echoed[5]).tolist() == cache["7"]


# ---------------------------------------------------------------------------
# The three XML shapes, straight from the parser. The fixture proves the
# numbers; these prove that each shape is told apart in the first place, which
# a value check cannot do on its own -- ``total`` and ``range_sum`` agree on
# this data by design.


def _element(inner: str):
    """One ``math50`` element, namespaced the way ``worksheet.xml`` has it."""
    import xml.etree.ElementTree as ET

    return ET.fromstring(
        f'<ml:root xmlns:ml="http://schemas.mathsoft.com/math50">{inner}</ml:root>'
    )[0]


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


# ---------------------------------------------------------------------------
# Arms the worksheet never reaches. It sums dimensionless integers over a
# dimensionless range, so units on either side, and ``mod``'s sign rule, are
# untested by the checks above.


def test_range_sum_keeps_a_unit_on_the_domain():
    """A dimensioned range must reach the body with its unit intact."""
    import numpy as np

    from mcad2py.runtime import range_sum
    from mcad2py.units import ureg

    domain = ureg.Quantity(np.array([1.0, 2.0, 3.0]), "m")
    assert range_sum(domain, lambda x: x * 2).to("mm").magnitude == pytest.approx(12000.0)


def test_range_sum_keeps_a_unit_on_the_result():
    import numpy as np

    from mcad2py.runtime import range_sum
    from mcad2py.units import ureg

    domain = np.array([0.0, 1.0, 2.0])
    total = range_sum(domain, lambda i: (i + 1) * ureg.Quantity(1.0, "kN"))
    assert total.to("N").magnitude == pytest.approx(6000.0)


def test_mod_carries_the_sign_of_the_first_argument():
    """Mathcad follows C's ``fmod``; Python's ``%`` follows the divisor.

    The sheet only calls ``mod`` on non-negative values, where the two agree, so
    this is the arm that would otherwise go untested. The rule itself is PTC's
    documented one, not a cached number -- one negative ``mod`` region on the
    sheet would upgrade it.
    """
    from mcad2py.runtime import mod

    assert mod(5, 3) == pytest.approx(2.0)
    assert mod(-5, 3) == pytest.approx(-2.0)
    assert mod(5, -3) == pytest.approx(2.0)
    assert (-5) % 3 == 1  # what Python would have given


def test_mod_converts_a_dimensioned_divisor_before_taking_the_remainder():
    """``mod(2.5 m, 300 mm)`` must not read 300 as metres."""
    from mcad2py.runtime import mod
    from mcad2py.units import ureg

    result = mod(ureg.Quantity(2.5, "m"), ureg.Quantity(300.0, "mm"))
    assert result.to("mm").magnitude == pytest.approx(100.0)


def test_mod_reduces_an_unreduced_ratio():
    """A ``mm/m`` ratio must reduce before ``fmod``, not read its magnitude."""
    from mcad2py.runtime import mod
    from mcad2py.units import ureg

    ratio = ureg.Quantity(7000.0, "mm") / ureg.Quantity(1.0, "m")
    assert mod(ratio, 3) == pytest.approx(1.0)


def test_mod_applies_element_wise_to_a_vector():
    """Mathcad applies ``mod`` per element with no vectorize arrow."""
    import numpy as np

    from mcad2py.runtime import mod

    assert np.asarray(mod(np.array([2.0, 4.0, 8.0]), 7)).tolist() == [2.0, 4.0, 1.0]
