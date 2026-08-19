"""``Spline2`` / ``Binterp`` / ``DWS`` -- the reproducible half of Mathcad's
least-squares B-spline family.

Only the **knot placement** is Mathcad's own undocumented rule; a call that has
to place its own knots raises, and ``mapping.UNIMPLEMENTED`` still turns those
regions into visible comments. Everything a call with an explicit knot vector
does is reproduced here to the last bit, and this module pins it against
``references/interpolation_prediction.mcdx``'s cache.

The sheet never echoes ``SplineW`` or ``SplineNW`` themselves, so the anchors
are the two ``DWS`` echoes and the cached **plot trace** of
``Binterp(range, SplineW)`` -- which carries all four rows (value and three
derivatives) at 101 points, and is therefore the only direct check of
``Binterp`` there is.

The one detail worth stating: ``Spline2`` **drops data outside the knot range**.
The sheet's ``Knots := range`` stops at 1982.96 while ``x`` reaches 1999.7, so
five of the 536 points fall out. Keeping them moves every number below by about
0.2% -- close enough to look right, which is why it is tested explicitly.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest

from mcad2py.runtime import DWS, Binterp, Spline2
from mcad2py.units import ureg

from conftest import cached_results, reference

SHEET = reference("interpolation_prediction")

# ``result-id`` of each echo this module leans on, from ``worksheet.xml``.
DWS_B = "22"  # DWS(b), the adaptive fit -- read out of the cached vector
DWS_SPLINE_W = "53"  # DWS(SplineW),  Spline2(x, y, n, w, Knots)
DWS_SPLINE_NW = "61"  # DWS(SplineNW), Spline2(x, y, n, Knots)
PACKED_B = "6"  # the whole 79-element b
TRACE_SPLINE3 = "55"  # Binterp(range, SplineW), four rows x 101 points


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


@pytest.fixture(scope="module")
def data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The sheet's ``x``, ``y`` and ``w`` columns, out of its 536x3 literal."""
    root = ET.fromstring(zipfile.ZipFile(SHEET).read("mathcad/worksheet.xml"))
    matrix = next(
        node
        for node in root.iter()
        if _local(node.tag) == "matrix" and node.get("rows") == "536"
    )
    values = [float(c.text) for c in matrix if _local(c.tag) == "real"]
    columns = np.array(values).reshape(3, 536)  # cached column-major
    return columns[0], columns[1], columns[2]


@pytest.fixture(scope="module")
def knots(data) -> np.ndarray:
    """The sheet's ``Knots := range``: 101 points, ``i*(max-min)/101 + min``.

    Note the divisor is 101 while ``i`` runs 0..100, so the last knot stops
    *short* of ``max(x)``. That is not a transcription slip -- it is what makes
    the drop-outside-the-range rule observable.
    """
    x = data[0]
    return np.arange(101) * (x.max() - x.min()) / 101 + x.min()


@pytest.fixture(scope="module")
def cache() -> dict[str, list[float]]:
    return cached_results(SHEET)


@pytest.fixture(scope="module")
def trace() -> np.ndarray:
    """The cached ``Binterp(range, SplineW)`` plot trace, as ``(4, 101)``."""
    root = ET.fromstring(zipfile.ZipFile(SHEET).read("mathcad/result.xml"))
    node = next(
        d for d in root if d.get("result-id") == TRACE_SPLINE3
    )
    vectors = [v for v in node.iter() if _local(v.tag) == "DataVectors"]
    return np.array(json.loads(vectors[1].text)).reshape(4, 101)


def test_weights_are_standard_deviations(data, knots, cache):
    """``w`` enters as ``1/w**2``. Weighting by ``w`` itself misses by 3%."""
    x, y, w = data
    fit = Spline2(x, y, 3, w, knots)
    assert DWS(fit) == pytest.approx(cache[DWS_SPLINE_W][0], rel=1e-13)


def test_an_unweighted_fit_matches_its_cached_statistic(data, knots, cache):
    x, y, _ = data
    fit = Spline2(x, y, 3, knots)
    assert DWS(fit) == pytest.approx(cache[DWS_SPLINE_NW][0], rel=1e-13)


def test_points_outside_the_knot_range_are_dropped(data, knots, cache):
    """Keeping the five points past the last knot is the plausible wrong answer.

    It moves the statistic by only 0.2%, so nothing else in the sheet would
    catch it; this asserts the difference directly rather than trusting that a
    later comparison would notice.
    """
    x, y, _ = data
    assert (x > knots[-1]).sum() == 5
    kept = Spline2(x, y, 3, knots)
    stretched = Spline2(x, y, 3, np.append(knots, x.max()))
    assert DWS(kept) == pytest.approx(cache[DWS_SPLINE_NW][0], rel=1e-13)
    assert DWS(stretched) != pytest.approx(cache[DWS_SPLINE_NW][0], rel=1e-6)


def test_binterp_returns_the_value_and_three_derivatives(data, knots, trace):
    """The value and the first two derivatives match the cached trace exactly.

    The **third** derivative is deliberately left out. It is piecewise constant,
    the trace samples it exactly *at* the knots, and Mathcad picks the left or
    the right interval there inconsistently -- its own trace repeats a value at
    samples 1, 4, 8, 16, 32, 64 and 100, which is a bisection artifact in its
    interval search rather than a property of the spline. Comparing against it
    would pin our output to Mathcad's own rounding. The next test checks the
    third derivative against Mathcad's second derivative instead.
    """
    x, y, w = data
    rows = Binterp(knots, Spline2(x, y, 3, w, knots))
    assert rows.shape == (4, 101)
    for order in range(3):
        assert rows[order] == pytest.approx(trace[order], rel=1e-9, abs=1e-9)


def test_the_third_derivative_differentiates_mathcads_own_second(
    data, knots, trace
):
    """A cubic's third derivative is constant on each knot interval, so it must
    be the difference quotient of Mathcad's cached second derivative there."""
    x, y, w = data
    step = knots[1] - knots[0]
    midpoints = (knots[1:] + knots[:-1]) / 2
    rows = Binterp(midpoints, Spline2(x, y, 3, w, knots))
    assert rows[3] == pytest.approx(np.diff(trace[2]) / step, rel=1e-9)


def test_dws_reads_the_statistic_out_of_the_packed_vector(cache):
    """``DWS(b)`` is ``b[last(b) - 2]``; the sheet echoes both."""
    packed = np.array(cache[PACKED_B])
    assert DWS(packed) == pytest.approx(cache[DWS_B][0], rel=0, abs=0)


def test_the_packed_layout_round_trips_through_a_refit(data, cache):
    """Refitting on Mathcad's own knots returns Mathcad's own coefficients.

    This is what proves the fit is a plain least-squares one: the knots are
    read straight out of the cached vector, so only the solve is under test.
    """
    x, y, _ = data
    packed = np.array(cache[PACKED_B])
    intervals = int(packed[1])
    knots = packed[2:3 + intervals]
    coefficients = packed[3 + intervals:6 + 2 * intervals]
    refit = Spline2(x, y, 3, knots)
    assert np.asarray(refit)[3 + intervals:6 + 2 * intervals] == pytest.approx(
        coefficients, rel=1e-12
    )
    assert np.asarray(refit)[2:3 + intervals] == pytest.approx(knots, rel=0)


def test_the_residual_standard_error_is_the_first_trailing_number(data, cache):
    x, y, _ = data
    packed = np.array(cache[PACKED_B])
    intervals = int(packed[1])
    refit = np.asarray(Spline2(x, y, 3, packed[2:3 + intervals]))
    assert refit[-5] == pytest.approx(packed[-5], rel=1e-12)


def test_a_query_is_converted_into_the_abscissae_unit(data, knots):
    """A fit built in metres, queried in millimetres, lands on the same curve."""
    x, y, _ = data
    plain = Binterp(knots[40], Spline2(x, y, 3, knots))
    fit = Spline2(x * ureg.m, y * ureg.kg, 3, knots * ureg.m)
    scaled = Binterp(knots[40] * 1000 * ureg.mm, fit)
    assert scaled[0].to(ureg.kg).magnitude == pytest.approx(plain[0], rel=1e-12)
    # Each derivative divides the ordinate unit by one more abscissa unit.
    assert scaled[2].units == ureg.kg / ureg.m ** 2


def test_placing_its_own_knots_raises_rather_than_guessing(data):
    """The one thing this family must never do is invent a knot set."""
    x, y, w = data
    with pytest.raises(NotImplementedError, match="knots"):
        Spline2(x, y, 3)
    with pytest.raises(NotImplementedError, match="knots"):
        Spline2(x, y, 3, 0.5)  # a scalar fourth argument is ``level``
    # An unsorted vector is no knot vector either -- Mathcad falls back to its
    # own placement there, which is exactly the case we cannot reproduce.
    with pytest.raises(NotImplementedError, match="knots"):
        Spline2(x, y, 3, w)


def test_the_two_unidentified_trailing_statistics_are_not_invented(data, knots):
    """They come back ``nan``, not a plausible wrong number."""
    fit = np.asarray(Spline2(*data[:2], 3, knots))
    assert np.isnan(fit[-2]) and np.isnan(fit[-1])


# ---------------------------------------------------------------------------
# ``references/spline2.mcdx`` -- 13 points, small enough to reason about.
#
# It calls ``Spline2(x, y, 3)`` at the default ``level``, at 0.5 and at 0.001,
# and all three echo the **same** 15-element vector: knots ``[0, 6, 12]``. That
# is not a coincidence and it is the sheet's whole value -- see the two tests
# below, which pin the stopping rule and the starting knot set that the big
# sheet alone could not separate.

SMALL_SHEET = reference("spline2")
SMALL_X = np.arange(13.0)
SMALL_Y = np.array([3, 2.5, 2, 1.5, 1.5, 2, 4, 6, 10, 14, 18, 22, 26.0])
SMALL_B = "5"  # b := Spline2(x, y, 3); b2 and b3 are result-ids 6 and 7


def test_a_small_sheet_reproduces_its_whole_packed_vector():
    """Every element Mathcad computes, to 4e-15 -- an independent check of the
    fit on data with nothing in common with the 536-row sheet."""
    cached = np.array(cached_results(SMALL_SHEET)[SMALL_B])
    fit = np.asarray(Spline2(SMALL_X, SMALL_Y, 3, cached[2:5]))
    assert fit[:13] == pytest.approx(cached[:13], rel=1e-13, abs=1e-13)


def test_the_level_argument_changes_nothing_on_the_small_sheet():
    """``level`` 0.5, 0.001 and the default all give the identical vector.

    Mathcad grows the knot set until a Durbin-Watson test on the residuals
    passes at ``level``. Here the *first* candidate that passes does so at
    p = 0.79, far above every level tried, so all three stop at the same place.
    The three cached vectors being byte-identical is what pins that.
    """
    cache = cached_results(SMALL_SHEET)
    assert cache["6"] == cache[SMALL_B]
    assert cache["7"] == cache[SMALL_B]


def test_the_small_sheets_knots_are_uniform():
    """``[0, 6, 12]`` -- the midpoint exactly, on visibly asymmetric data.

    With one interval the fit is a single cubic, so ``|D³f|`` is constant and
    *any* curvature-based knot redistribution returns uniform knots. That is
    why this sheet cannot discriminate between the placement rules, and why it
    still settles the starting point: Mathcad begins at one interval spanning
    ``[min(x), max(x)]``.
    """
    cached = np.array(cached_results(SMALL_SHEET)[SMALL_B])
    assert cached[1] == 2  # two intervals
    assert cached[2:5] == pytest.approx([0.0, 6.0, 12.0], rel=0, abs=0)
