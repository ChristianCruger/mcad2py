"""Tests for the interpolation & prediction family
(``references/interpolation_prediction.mcdx``).

PTC's own "Interpolation and Prediction" tutorial: the three cubic splines and
``interp``, the polynomial set (``polyint``/``polyiter``/``polycoeff``), the
rational and Thiele continued-fraction interpolants, and ``predict``. Points
worth knowing:

* **``polyint`` and its relatives return vectors, not numbers.** ``polyint`` and
  ``rationalint`` give ``[value, error estimate]`` and ``polyiter``
  ``[converged, order, value]`` -- and Mathcad tags the *whole* vector with the
  ordinates' unit, flag and order included, which is what the cache holds.
* **``polyiter`` stops on the change, not on the error estimate.** It takes one
  more data point per step *in the order given* and stops when two successive
  interpolations differ by less than ``ε``. The sheet pins this three ways: the
  same data and query converge at order 3 when allowed 5, and report failure at
  order 2 when capped there -- which no "|error estimate| < ε" reading produces.
* **``Thielecoeff`` divides by 1e-65, not by zero.** Two equal ordinates make a
  reciprocal difference infinite; Mathcad substitutes a tiny denominator and
  carries on, so its second example's coefficients are ``1e65``/``-1e-65`` and
  its last one (-4.27e-50) is a pure floating-point artefact of that
  substitution. Reproducing the substitution reproduces the artefact exactly.
* ``predict`` is Burg's maximum-entropy method. The sheet writes the recurrence
  out by hand next to it (``Xpred``), and the two agree to the last bit.
* ``predict(v, m, n)`` with ``m >= rows(v)`` is an *error* in Mathcad ("This
  value must be less than the number of data points"), cached as an
  ``<engineError>`` -- the one region here emitted guarded.

**Three documented divergences** (see docs/test-coverage.md):

* The sheet's **least-squares spline** section (``Spline2``/``Binterp``/``DWS``,
  and the ``GrubbsClassic``/``trim`` outlier pair) is not implemented: Mathcad's
  adaptive knot placement is undocumented and guessing it would return plausible
  wrong numbers. Those regions convert to visible ``# TODO unsupported region``
  comments and the rest of the sheet still runs -- which is what
  ``test_unimplemented_builtins_do_not_break_the_module`` pins.
* The **second derivative at an interior knot** (``sd_p(vx[1])`` and
  ``sd_p(vx[last-1])``) agrees only to ~1e-3 and ~1e-5. A spline's third
  derivative jumps at a knot, so *any* finite difference straddling one is
  wrong in the last digits; Mathcad's own two values for what is provably the
  same number disagree at the 7th. The values at the *ends* -- where the end
  piece continues smoothly -- match to 1e-13, which is the real check on the
  spline coefficients.
* ``polycoeff`` agrees to 1e-11 rather than 1e-14: a 5th-degree fit over
  x ≈ 300…333 has a leading coefficient of 1.8e4 and a trailing one of 2.4e-6,
  and the cancellation between them is the whole computation.
"""

import math

import numpy as np
import pytest

from conftest import cached_results, flat, reference, result_refs, run_sheet
from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import echo_expr
from mcad2py.loader import load_mcdx
from mcad2py.units import ureg

REFERENCE = reference("interpolation_prediction")

# The region Mathcad itself reports an error for, so its cache holds no value.
ENGINE_ERRORS = frozenset({13})

# Echo index -> relative tolerance, for the two numeric-derivative and one
# ill-conditioned echo described in the module docstring. Everything else is
# held to 1e-12.
APPROXIMATE = {
    8: 2e-3,    # sd_p(vx[1])          -- across a knot, third derivative jumps
    9: 1e-4,    # sd_p(vx[last-1])     -- likewise
    18: 1e-10,  # polycoeff            -- cancellation over four decades
}


@pytest.fixture(scope="module")
def sheet():
    """Convert, execute, and return ``(source, namespace, echoed values)``."""
    return run_sheet(REFERENCE)


def test_sheet_runs_end_to_end(sheet):
    """Every region the converter supports echoes, and nothing else is left
    unsupported: the only TODOs are the least-squares spline section.

    Three of that section's echoes convert: the ``DWS`` of the two fits built
    on an **explicit** knot vector, and the ``GrubbsClassic`` outlier index.
    """
    src, _, echoed = sheet
    assert len(echoed) == 31
    assert "TODO unsupported:" not in src  # no *expression* was dropped
    notes = [line for line in src.splitlines()
             if line.startswith("# TODO unsupported region:")]
    assert notes, "the Spline2 section should be suppressed, not silently dropped"


def test_sheet_matches_cached_results(sheet):
    """Every echo reproduces Mathcad's cached value."""
    _, _, echoed = sheet
    cached, refs = cached_results(REFERENCE), result_refs(REFERENCE)
    regions = [r for r in convert_worksheet(load_mcdx(REFERENCE)).regions
               if echo_expr(r) is not None]
    assert len(regions) == len(echoed)

    checked = 0
    for index, region in enumerate(regions):
        if index in ENGINE_ERRORS:
            continue
        want = np.asarray(cached[refs[region.source.region_id]], dtype=float)
        got = flat(echoed[index])
        assert got.shape == want.shape, f"echo {index}: {got.shape} vs {want.shape}"
        rtol = APPROXIMATE.get(index, 1e-12)
        assert np.allclose(got, want, rtol=rtol, atol=1e-12), (
            f"echo {index} ({echo_expr(region)}): {got} != {want}"
        )
        checked += 1
    assert checked == 30  # the whole sheet bar the one Mathcad errors on


def test_predict_refuses_to_use_every_data_point(sheet):
    """``predict(v, m, n)`` needs ``m < rows(v)``: the predicted values cannot
    be a linear function of *all* the data. Mathcad caches this as an
    ``<engineError>``, so the region is emitted guarded and the sheet runs on."""
    from mcad2py.runtime import predict

    _, _, echoed = sheet
    label, error = echoed[13]
    assert label == "error:" and isinstance(error, ValueError)
    assert "less than the number of data points" in str(error)

    # And the very next region, one point short, has an answer.
    assert flat(echoed[14]).shape == (3,)

    with pytest.raises(ValueError, match="less than the number of data points"):
        predict(np.array([1.0, 2.0, 3.0]), 3, 2)


def test_predict_matches_the_sheets_hand_written_recurrence(sheet):
    """The tutorial writes the linear predictor out term by term (``Xpred``)
    next to the builtin call. Burg's coefficients are what make the two the
    same number rather than merely a close one."""
    _, _, echoed = sheet
    assert np.allclose(flat(echoed[11]), flat(echoed[12]), rtol=1e-14, atol=0)


def test_polyiter_stops_on_the_change_not_the_error_estimate(sheet):
    """Same data, same query, two order caps: allowed 5 it converges at order 3,
    capped at 2 it reports failure. ``polyint``'s error estimate at order 2 is
    exactly zero here (the query is one of the data points), so an
    "|error| < ε" rule would have converged immediately in both."""
    _, ns, _ = sheet
    from mcad2py.runtime import polyint, polyiter

    x, y, u, s = ns["X"], ns["Y"], ns["U"], ns["s"]
    assert flat(polyiter(x, y, u, 5, 0.1 * s))[:2].tolist() == [1.0, 3.0]
    assert flat(polyiter(x, y, u, 2, 0.1 * s))[:2].tolist() == [0.0, 2.0]
    assert flat(polyint(x, y, u))[1] == 0.0


def test_polyint_family_carries_the_ordinates_unit(sheet):
    """Mathcad tags the whole returned vector with ``vy``'s unit -- the error
    estimate, and even ``polyiter``'s flag and order. Reading the value out of
    ``polyint(X, Y, U)[0]`` must therefore give a time, not a bare number."""
    _, ns, _ = sheet
    from mcad2py.runtime import polyint, polyiter

    value = polyint(ns["X"], ns["Y"], ns["U"])
    assert value.units == ureg.s
    assert math.isclose(value[0].to("s").magnitude, 4 / 3, rel_tol=1e-14)
    assert polyiter(ns["X"], ns["Y"], ns["U"], 5, 0.1 * ns["s"]).units == ureg.s


def test_query_point_is_converted_into_the_abscissae_unit():
    """A query in mm against knots in m is the failure this seam exists for: it
    would otherwise interpolate a thousand times too near the origin and return
    a plausible wrong number rather than raise."""
    from mcad2py.runtime import cspline, interp, linterp, polyint, polyiter

    vx = np.array([1.0, 2.0, 3.0, 4.0]) * ureg.m
    vy = np.array([10.0, 20.0, 30.0, 40.0]) * ureg.s

    for value in (linterp(vx, vy, 2500 * ureg.mm),
                  interp(cspline(vx, vy), vx, vy, 2500 * ureg.mm),
                  polyint(vx, vy, 2500 * ureg.mm)[0]):
        assert math.isclose(value.to("s").magnitude, 25.0, rel_tol=1e-12)

    # The tolerance is converted the same way -- 100 ms is 0.1 s, not 100.
    order = flat(polyiter(vx, vy, 2500 * ureg.mm, 3, 100 * ureg.ms))[1]
    assert order == flat(polyiter(vx, vy, 2500 * ureg.mm, 3, 0.1 * ureg.s))[1]


def test_interp_applies_element_wise_to_a_vector_of_queries():
    """Mathcad interpolates a whole column with no vectorize arrow, which is how
    the sheet plots ``fitc(x)`` over a range. A ``float()`` on the way out would
    raise on exactly that call."""
    from mcad2py.runtime import cspline, interp

    vx = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    vy = vx ** 2
    query = np.array([0.5, 1.5, 2.5])
    got = interp(cspline(vx, vy), vx, vy, query)
    assert got.shape == query.shape
    # x² is a cubic spline's exact fit, so the not-a-knot spline reproduces it.
    assert np.allclose(got, query ** 2, rtol=1e-12)


def test_the_three_splines_differ_only_at_the_ends():
    """``lspline`` ends straight (zero second derivative), ``pspline``
    parabolic (constant second derivative over the end piece) and ``cspline``
    cubic. Those end conditions are the whole difference between them."""
    from mcad2py.runtime import cspline, lspline, pspline

    vx = np.array([0.0, 1.0, 2.5, 4.0, 6.0, 9.0])
    vy = np.array([0.0, 0.8, 1.9, 2.1, 3.6, 3.9])

    assert lspline(vx, vy).y2[0] == 0.0
    assert lspline(vx, vy).y2[-1] == 0.0
    parabolic = pspline(vx, vy).y2
    assert math.isclose(parabolic[0], parabolic[1], rel_tol=1e-14)
    assert math.isclose(parabolic[-1], parabolic[-2], rel_tol=1e-14)
    # All three still pass through every knot.
    for spline in (lspline, pspline, cspline):
        fit = spline(vx, vy)
        assert np.allclose([_evaluate(fit, x) for x in vx], vy, rtol=1e-12)


def _evaluate(fit, x):
    from mcad2py.runtime import interp
    return interp(fit, fit.xs, fit.ys, x)


def test_rationalint_beats_polyint_on_a_pole():
    """Rational interpolation is the tool for data with a pole nearby: the
    sheet's own comparison plots ``rationalint`` against a Thiele fit of
    1/(1 + 500(x - ½)²), which a polynomial of the same order cannot follow."""
    from mcad2py.runtime import polyint, rationalint

    vx = np.linspace(-2.0, 2.0, 9)
    vy = 1.0 / (1.0 + 25.0 * vx ** 2)
    at = 0.15
    exact = 1.0 / (1.0 + 25.0 * at ** 2)
    rational = abs(flat(rationalint(vx, vy, at))[0] - exact)
    polynomial = abs(flat(polyint(vx, vy, at))[0] - exact)
    assert rational < polynomial
    # An exact hit on a data point is returned as-is, with no error.
    assert flat(rationalint(vx, vy, vx[3])).tolist() == [vy[3], 0.0]


def test_thiele_coefficients_reproduce_their_own_interpolant(sheet):
    """``Thielecoeff`` then ``Thiele`` is a round trip: the continued fraction
    passes through every data point it was built from. The sheet checks this
    the long way round, by writing the fraction out as ``Q(a)``."""
    from mcad2py.runtime import Thiele, Thielecoeff

    vx = np.array([0.0, 0.4, 0.9, 1.6, 2.2])
    vy = 1.0 / (1.0 + vx ** 2)
    coeff = Thielecoeff(vx, vy)
    assert np.allclose(Thiele(vx, coeff, vx), vy, rtol=1e-10)


def test_thielecoeff_substitutes_a_tiny_denominator_for_zero(sheet):
    """Two equal ordinates make a reciprocal difference infinite. Mathcad
    divides by 1e-65 instead of raising, which is why its cached coefficients
    for the sheet's second example read 1e65 and -1e-65 -- and why the last one
    is a rounding artefact rather than a number with meaning."""
    _, _, echoed = sheet
    degenerate = flat(echoed[21])
    assert math.isclose(degenerate[1], 1e65, rel_tol=1e-15)
    assert math.isclose(degenerate[2], -1e-65, rel_tol=1e-15)
    assert abs(degenerate[4]) < 1e-49  # the artefact, reproduced exactly


def test_derivative_is_unit_aware():
    """The operator divides ``f``'s unit by ``x``'s to the order taken, so a
    displacement differentiated twice against time is an acceleration."""
    from mcad2py.runtime import derivative

    def position(t):
        return 3.0 * ureg("m/s**2") * t ** 2

    got = derivative(position, 2.0 * ureg.s, 2)
    assert got.check("[length] / [time] ** 2")
    assert math.isclose(got.to("m/s**2").magnitude, 6.0, rel_tol=1e-8)


def test_range_sum_reads_its_limits_off_the_range(sheet):
    """Mathcad's ``Σ`` over a range variable writes no bounds: it runs over
    exactly the values the range holds, step and direction included."""
    from mcad2py.runtime import arange, range_sum

    assert range_sum(arange(0, 4, 1), lambda i: i ** 2) == 30
    assert range_sum(arange(0, 10, 2), lambda i: i) == 30
    # And it keeps a unit rather than starting the accumulation from a bare 0.
    total = range_sum(arange(1, 3, 1), lambda i: i * ureg.m)
    assert total.to("m").magnitude == 6.0

    # The sheet builds a polynomial that way, over the range ``i`` that its
    # polycoeff vector was indexed by -- with no bounds written anywhere.
    src, _, _ = sheet
    assert "f = lambda z: range_sum(i, lambda i: c[i] * power(z, i))" in src


def test_unimplemented_builtins_do_not_break_the_module(sheet):
    """A ``Spline2`` that would place its own knots becomes a visible comment,
    and so does every region that read what it defined. The point is that the
    module still imports and the other echoes still run; a bare name would have
    raised ``NameError`` on the first of them.

    ``Spline2`` is gated per *call*, not per name -- the two calls on this sheet
    that pass an explicit knot vector convert and run, and ``Binterp`` and
    ``DWS`` with them. Nothing is blocked by name any more: ``GrubbsClassic``
    and ``trim`` run, and only the calls whose knots Mathcad would place itself
    are left as comments.
    """
    src, ns, _ = sheet
    assert "# TODO unsupported region: Spline2 would have to place its own" in src
    for name in ("Spline2", "Binterp", "DWS", "GrubbsClassic", "trim"):
        assert name in ns
    # The taint stops at the next region that rebinds the name: ``i`` is a
    # suppressed range at first and a live one a few lines later.
    assert "needs b, left undefined above" in src
    assert "i" in ns


def test_a_displayed_equation_is_not_evaluated(sheet):
    """The tutorial writes the linear-prediction recurrence out beside the data
    it applies to. Mathcad computes nothing for such a region; evaluating it
    would index a real array with a real range variable and raise."""
    src, _, _ = sheet
    assert "# shown, not computed: Eq(X[k], c[0] * X[k - 3]" in src


def test_a_suppressed_region_shows_the_python_it_would_have_been(sheet):
    """Each TODO carries the commented-out code above it.

    Without that, "needs b, left undefined above" tells a reader that something
    is missing but not *what* -- and the whole point of a visible TODO is that
    someone can act on it. With it, the chain reads top to bottom: ``b`` was a
    ``Spline2`` call that needs a knot vector, and everything below it is
    downstream of that one line.
    """
    src, _, _ = sheet
    lines = src.splitlines()
    notes = [i for i, line in enumerate(lines)
             if line.startswith("# TODO unsupported region:")]
    assert notes
    for index in notes:
        above = lines[index - 1]
        assert above.startswith("# ") and not above.startswith("# TODO"), (
            f"line {index + 1} has no would-be code above it"
        )
    assert "# b = Spline2(x, y, n, w)" in src
    # A multi-line region is commented whole -- this plot names the three
    # variables its own note lists as missing.
    assert "# _fig, _ax = plt.subplots()" in src
