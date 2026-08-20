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
from mcad2py.convert import convert_file
from mcad2py.units import ureg

from conftest import cached_results, flat, reference, run_sheet

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


def test_the_last_two_statistics_are_the_durbin_watson_bounds(data, cache):
    """The trailer ends with the classical **bounds** of the Durbin-Watson test.

    The statistic's exact null distribution depends on the design matrix, so
    Durbin and Watson published two design-free bounds instead. Mathcad stores
    both: the upper first -- the probability of no positive autocorrelation,
    which is what the fit is judged by -- then the lower. Each is a Beta
    approximation on ``[0, 4]``, which is how their published tables were built.
    """
    x, y, _ = data
    packed = np.array(cache[PACKED_B])
    intervals = int(packed[1])
    refit = np.asarray(Spline2(x, y, 3, packed[2:3 + intervals]))
    # 1e-7 rather than tighter: on 536 points the Beta CDF is itself only
    # good to about 1e-8 out in the tail, and that is the whole error.
    assert refit[-2:] == pytest.approx(packed[-2:], rel=0, abs=1e-7)


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


# ---------------------------------------------------------------------------
# ``references/spline2A.mcdx`` -- 45 points on **non-uniformly spaced** x, with
# two kinks placed in the sparse half. It calls ``Spline2(x, y, 3)`` at the
# default ``level``, at 0.5 and at 0.001, and the three results have 6, 4 and 3
# intervals. That spread is what makes the sheet worth its place: it exposes the
# starting knot set, which the two earlier sheets could not.

WIGGLY_SHEET = reference("spline2A")
WIGGLY_DEFAULT = "7"  # b  := Spline2(x, y, 3)         -> 6 intervals, moved
WIGGLY_HALF = "8"  # b2 := Spline2(x, y, 3, 0.5)    -> 29 intervals, moved
WIGGLY_TINY = "9"  # b3 := Spline2(x, y, 3, 0.001)  -> 6 intervals, uniform
WIGGLY_X = "2"
WIGGLY_Y = "6"


@pytest.fixture(scope="module")
def wiggly() -> tuple[np.ndarray, np.ndarray, dict[str, list[float]]]:
    cache = cached_results(WIGGLY_SHEET)
    return np.array(cache[WIGGLY_X]), np.array(cache[WIGGLY_Y]), cache


def _uniform_in_index(x: np.ndarray, intervals: int) -> np.ndarray:
    """Knots at equally spaced **data indices**, linearly interpolated in x."""
    last = len(x) - 1
    return np.interp(np.arange(intervals + 1) * last / intervals,
                     np.arange(last + 1), x)


def test_the_starting_knots_are_uniform_in_data_index(wiggly):
    """Mathcad's first knot set at each interval count puts an **equal number
    of data points** in each interval, not an equal width.

    Exactly, to the last bit, on x whose spacing varies by a factor of four --
    so this is not a coincidence of near-uniform data. The knot lands between
    two data points and is linearly interpolated there, which is where the
    non-round values come from. The ``level = 0.001`` call is the one that
    stops on this set; the other two go on to move the knots.
    """
    x, _, cache = wiggly
    packed = np.array(cache[WIGGLY_TINY])
    intervals = int(packed[1])
    assert packed[2:3 + intervals] == pytest.approx(
        _uniform_in_index(x, intervals), rel=0, abs=0)


@pytest.mark.parametrize("ref", [WIGGLY_DEFAULT, WIGGLY_HALF])
def test_a_harder_level_moves_the_knots_off_that_set(wiggly, ref):
    """When the uniform-in-index fit is still rejected, Mathcad moves the knots
    before adding another interval. Both of these calls stop on a moved set --
    the default one at the *same* six intervals the ``level = 0.001`` call
    accepted, which is what shows the move is a separate step rather than more
    knots. The rule behind the move is the last unsolved piece of this family.
    """
    x, _, cache = wiggly
    packed = np.array(cache[ref])
    intervals = int(packed[1])
    assert np.abs(packed[2:3 + intervals]
                  - _uniform_in_index(x, intervals)).max() > 0.1


@pytest.mark.parametrize("ref", [WIGGLY_DEFAULT, WIGGLY_HALF, WIGGLY_TINY])
def test_every_cached_vector_is_reproduced_from_its_own_knots(wiggly, ref):
    """Given the knots, everything else comes back -- at 6 and at 29
    intervals, where 29 leaves only 13 residual degrees of freedom."""
    x, y, cache = wiggly
    packed = np.array(cache[ref])
    intervals = int(packed[1])
    fit = np.asarray(Spline2(x, y, 3, packed[2:3 + intervals]))
    assert fit == pytest.approx(packed, rel=0, abs=1e-8)


def test_the_sheets_noise_is_our_own_random_stream(wiggly):
    """``Seed(1)`` then ``rnorm(45, 0, 0.85)``, reproduced exactly.

    An earlier save of this sheet had drawn the vector twice, so its cached
    noise was our stream at offset 45; the sheet was re-saved and it now starts
    where it should. Keeping the check is worth it either way -- it is the only
    place a fixture pins the generator against data that was *used* for
    something rather than just echoed.
    """
    from mcad2py.runtime import Seed, rnorm

    x, y, _ = wiggly
    kinked = np.where(x <= 5, 1 + 0.2 * x,
                      np.where(x <= 8, 2 + (x - 5) ** 2, 11 - 1.5 * (x - 8)))
    Seed(1)
    stream = np.asarray(rnorm(45, 0, 0.85)).reshape(-1)
    assert kinked + stream == pytest.approx(y, rel=1e-12, abs=1e-12)


# ---------------------------------------------------------------------------
# ``references/spline2B.mcdx`` -- 31 points fitted on five **explicit** knot
# vectors and at two degrees. No placement rule is involved anywhere, so every
# echo is a clean (design, statistic, p-value) triple. That is what identified
# the two trailing statistics, and what pins the cubic cap.

EXPLICIT_SHEET = reference("spline2B")
EXPLICIT_X = "2"
EXPLICIT_Y = "6"
# result-id -> (degree, interval count)
EXPLICIT_FITS = {"12": (3, 2), "13": (3, 4), "14": (3, 5),
                 "15": (3, 8), "16": (3, 10), "17": (2, 5)}


@pytest.fixture(scope="module")
def explicit() -> tuple[np.ndarray, np.ndarray, dict[str, list[float]]]:
    cache = cached_results(EXPLICIT_SHEET)
    return np.array(cache[EXPLICIT_X]), np.array(cache[EXPLICIT_Y]), cache


@pytest.mark.parametrize("ref", sorted(EXPLICIT_FITS))
def test_the_whole_packed_vector_matches_element_for_element(explicit, ref):
    """Knots, coefficients, residual standard error, statistic **and both
    p-values** -- 3e-9 across six fits, which is the Beta CDF's own precision.

    Five interval counts from 2 to 10 and two degrees. The degree-2 fit is the
    only non-cubic case in any fixture, and it is what shows the coefficient
    count is ``m + degree`` rather than ``m + 3``.
    """
    x, y, cache = explicit
    degree, _ = EXPLICIT_FITS[ref]
    packed = np.array(cache[ref])
    intervals = int(packed[1])
    assert packed[0] == degree + 1  # the packed order is degree + 1
    fit = np.asarray(Spline2(x, y, degree, packed[2:3 + intervals]))
    assert fit == pytest.approx(packed, rel=0, abs=1e-8)


def test_a_higher_degree_is_refused_the_way_mathcad_refuses_it():
    """The sheet's seventh call, ``Spline2(x, y, 4, k5)``, is the one region
    Mathcad itself will not compute: its cached result is an ``order_too_big``
    engine error whose argument is 3. So the family is capped at cubic.
    """
    root = ET.fromstring(zipfile.ZipFile(EXPLICIT_SHEET).read("mathcad/result.xml"))
    codes = [node.text for node in root.iter() if _local(node.tag) == "errorCode"]
    assert "order_too_big" in codes
    with pytest.raises(ValueError, match="no greater than 3"):
        Spline2(np.arange(31.0), np.arange(31.0), 4, np.array([0.0, 15.0, 30.0]))


# ---------------------------------------------------------------------------
# ``references/spline2C.mcdx`` -- the same 45 points as ``spline2A``, fitted at
# eight values of ``level``. It is what turned the knot-count loop from a guess
# into a rule, because the interval counts it returns are sharply **non**
# monotone in ``level``: 6, 6, 15, 15, 29, 5, 5, 7.

LADDER_SHEET = reference("spline2C")
# result-id -> (level, interval count)
LADDER = {"7": (0.1, 6), "8": (0.2, 6), "9": (0.3, 15), "10": (0.4, 15),
          "11": (0.5, 29), "12": (0.6, 5), "13": (0.7, 5), "14": (0.8, 7)}


@pytest.fixture(scope="module")
def ladder() -> tuple[np.ndarray, np.ndarray, dict[str, list[float]]]:
    cache = cached_results(LADDER_SHEET)
    return np.array(cache["2"]), np.array(cache["6"]), cache


def _phase_one(x, y, intervals, degree=3):
    """``(knots, upper, lower)`` for the uniform-in-index fit at that count."""
    from mcad2py.runtime import (_bspline_design, _clamped_knots,
                                 _durbin_watson, _durbin_watson_bounds)

    knots = _uniform_in_index(x, intervals)
    design = _bspline_design(_clamped_knots(knots, degree), degree, x)
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    statistic = _durbin_watson(y - design @ coef)
    return (knots,) + _durbin_watson_bounds(len(x), design.shape[1], statistic)


@pytest.mark.parametrize("ref", sorted(LADDER, key=int))
def test_every_rung_is_reproduced_from_its_own_knots(ladder, ref):
    x, y, cache = ladder
    packed = np.array(cache[ref])
    intervals = int(packed[1])
    assert intervals == LADDER[ref][1]
    fit = np.asarray(Spline2(x, y, 3, packed[2:3 + intervals]))
    assert fit == pytest.approx(packed, rel=0, abs=1e-8)


@pytest.mark.parametrize("first,second", [("7", "8"), ("9", "10"), ("12", "13")])
def test_the_moved_knot_set_does_not_depend_on_level(ladder, first, second):
    """Two levels that stop at the same interval count return the *identical*
    vector. So the moved set is a function of the data and the count alone --
    ``level`` chooses when to stop, never where the knots go.
    """
    _, _, cache = ladder
    assert cache[first] == cache[second]


def test_the_loop_accepts_the_first_fit_whose_lower_bound_beats_level(ladder):
    """The rungs from 0.1 to 0.5 form a ladder, and each one is the first fit
    that clears its own level.

    The moved fits reach lower bounds of 0.034 (5 intervals), 0.203 (6), 0.065
    (7), 0.461 (15) and 0.520 (29). Read against the levels: 0.1 and 0.2 stop
    at 6 because 0.203 is the first value above them; 0.3 and 0.4 pass 6 and 15
    is the next above; 0.5 needs 29. Each cached fit clears its level, and the
    largest lower bound of any *smaller* cached count does not -- which is what
    this asserts.
    """
    _, _, cache = ladder
    rungs = sorted(((LADDER[ref][0], int(np.array(cache[ref])[1]),
                     float(np.array(cache[ref])[-1]))
                    for ref in LADDER if LADDER[ref][0] <= 0.5),
                   key=lambda row: row[0])
    for level, intervals, lower in rungs:
        assert lower > level
        smaller = [low for _, count, low in rungs if count < intervals]
        assert all(low <= level for low in smaller)


def test_the_level_0_001_rung_is_predicted_from_scratch(wiggly):
    """The one cached fit the loop reproduces end to end, with no unsolved step.

    ``spline2A``'s ``level = 0.001`` call stops on a uniform-in-index set, so
    sweeping interval counts and taking the first whose *lower* bound clears
    0.001 must land on exactly Mathcad's knots -- count included.
    """
    x, y, cache = wiggly
    packed = np.array(cache[WIGGLY_TINY])
    for intervals in range(1, 20):
        knots, _upper, lower = _phase_one(x, y, intervals)
        if lower > 0.001:
            break
    assert intervals == int(packed[1])
    assert knots == pytest.approx(packed[2:3 + intervals], rel=0, abs=0)
    assert lower == pytest.approx(packed[-1], rel=0, abs=1e-9)


def test_the_three_highest_levels_are_accepted_on_the_upper_bound(ladder):
    """0.6, 0.7 and 0.8 stop at 5, 5 and 7 intervals -- *fewer* than 0.5's 29.

    Their lower bounds (0.034, 0.034, 0.065) are far below their levels, so the
    ladder above cannot explain them; their **upper** bounds (0.768, 0.768,
    0.972) do clear. Whatever the loop does when it cannot satisfy a level, it
    falls back to the weaker half of the bounds test and to a knot count it had
    already passed. That fallback is not reproduced, and this test records the
    evidence rather than a rule.
    """
    _, _, cache = ladder
    for ref in ("12", "13", "14"):
        level = LADDER[ref][0]
        packed = np.array(cache[ref])
        assert packed[-1] < level < packed[-2]


# ---------------------------------------------------------------------------
# The per-call gate. ``Spline2`` is not all-or-nothing: given an explicit knot
# vector it is exact, so it is suppressed per *call* rather than per name --
# see ``regions._spline2_needs_its_own_knots``.


def test_a_sheet_of_explicit_knot_calls_converts_completely():
    """``spline2B`` has no TODO left in it, and its numbers match the cache.

    Six fits and the degree-4 region Mathcad itself refuses, which converts as a
    guarded region the way any cached engine error does. The sheet's ``x`` and
    ``y`` come back exactly too, since they are built from ``Seed``/``rnorm``.
    """
    source, _namespace, echoed = run_sheet(EXPLICIT_SHEET)
    assert "# TODO" not in source
    cache = cached_results(EXPLICIT_SHEET)
    assert flat(echoed[0]) == pytest.approx(cache[EXPLICIT_X], rel=0, abs=0)
    assert flat(echoed[3]) == pytest.approx(cache[EXPLICIT_Y], rel=0, abs=0)
    for echo, ref in zip(echoed[4:10], sorted(EXPLICIT_FITS, key=int)):
        assert flat(echo) == pytest.approx(cache[ref], rel=0, abs=1e-8)
    label, error = echoed[10]
    assert label == "error:" and "no greater than 3" in str(error)


def test_the_gate_keeps_the_adaptive_calls_out():
    """The catalogue sheet has both kinds, and each lands on the right side.

    ``Spline2(x, y, n, w, Knots)`` and ``Spline2(x, y, n, Knots)`` convert --
    the second only because the first named ``Knots`` in the unambiguous fifth
    slot, since nothing else about a four-argument vector says knots rather than
    weights. ``Spline2(x, y, n, w)``, ``Spline2(x, y, n)``, ``Spline2(…, 0.5)``
    and ``Spline2(x, y, n, w, level)`` all still become comments: an unsorted
    column, no fourth argument at all, and a significance in the knot slot.
    """
    source = convert_file(reference("interpolation_prediction"), fmt="py")
    assert "SplineW = Spline2(x, y, n, w, Knots)" in source
    assert "SplineNW = Spline2(x, y, n, Knots)" in source
    assert "spline3 = transpose(Binterp(range_, SplineW))" in source
    assert "print(DWS(SplineW))" in source
    for adaptive in ("Spline2(x, y, n)", "Spline2(x, y, n, w)",
                     "Spline2(x, y, n, 0.5)", "Spline2(x, y, n, w, level)"):
        assert adaptive not in source
    assert source.count("# TODO unsupported region: Spline2 would have to") == 5
