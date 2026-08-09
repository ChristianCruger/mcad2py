"""Tests for the probability distribution family (``references/probability.mcdx``).

PTC's own probability tutorial: the normal/Student-t/Weibull families were
already covered by ``statistics.mcdx`` (``test_statistics.py``); this sheet is
what pins the *rest* -- uniform, exponential, gamma, logistic, Cauchy,
geometric, hypergeometric, binomial, negative binomial, beta, chi-squared, F,
and log-normal, each with its full ``d``/``p``/``q``/``r`` set, plus the
Mathcad-15 ``cnorm`` alias and a Monte Carlo simulation exercising ``Re``.

* Every ``r*`` draw, and anything computed *from* one downstream (a histogram's
  ``lower``/``upper`` bin edges, a Monte Carlo ``Prob`` estimate and the
  ``qlogis`` built from it), is a fresh random sample each run and cannot
  reproduce Mathcad's cached number -- listed in ``RANDOM`` below, same
  divergence documented for ``rnorm``/``rweibull``/``rt`` in
  ``statistics.mcdx``. They still execute, so the code path is covered.
* ``histogram`` has two call shapes here: ``histogram(n, A)`` (an ``n x 2``
  midpoint/count matrix, the form ``statistics.mcdx`` uses) and
  ``histogram(intvls, A)`` (an explicit boundary vector, returning just the
  counts) -- this sheet is what exercises the second one.
* A "Uniformly Distributed" plot draws ``range`` (a 21-point ``0..n_bins``
  Mathcad range) against ``histogram``'s 20-row output; Mathcad pads the
  shorter trace with blanks rather than rejecting the mismatch, which is why
  :func:`mcad2py.runtime.plot_trace` pads along axis 0 instead of assuming 1-D.
"""

import math

import numpy as np
import pint
import pytest

from conftest import cached_results, flat, reference, result_refs, run_sheet
from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import echo_expr
from mcad2py.loader import load_mcdx
from mcad2py.units import ureg

REFERENCE = reference("probability")

# Echoes fed by a random draw, or computed from one downstream: a different
# sample every run, so there is no cached number to match.
RANDOM = frozenset(
    {9, 13, 19, 28}            # rbinom / rbeta / rF / rchisq
    | {55, 56, 57, 58}         # lower/upper bin edges of a random histogram
    | {59, 62}                 # Monte Carlo Prob, and qlogis(Prob, ...)
    | {67, 71, 75, 79, 83, 89} # rgamma / rgeom / rhypergeom / rbinom / rnbinom / rlnorm
)


@pytest.fixture(scope="module")
def sheet():
    """Convert, execute, and return ``(source, namespace, echoed values)``."""
    np.random.seed(0)  # the random draws still have to be *reproducible* here
    return run_sheet(REFERENCE)


def test_sheet_runs_end_to_end(sheet):
    """Nothing is dropped or unsupported, and every evaluated region echoes."""
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == 90


def test_sheet_matches_cached_results(sheet):
    """Every deterministic echo reproduces Mathcad's cached value."""
    _, _, echoed = sheet
    cached, refs = cached_results(REFERENCE), result_refs(REFERENCE)
    regions = [r for r in convert_worksheet(load_mcdx(REFERENCE)).regions
               if echo_expr(r) is not None]
    assert len(regions) == len(echoed)

    checked = 0
    for index, region in enumerate(regions):
        if index in RANDOM:
            continue
        want = np.asarray(cached[refs[region.source.region_id]], dtype=float)
        got = flat(echoed[index])
        assert got.shape == want.shape, f"echo {index}: {got.shape} vs {want.shape}"
        assert np.allclose(got, want, rtol=1e-9, atol=1e-12), (
            f"echo {index} ({echo_expr(region)}): {got} != {want}"
        )
        checked += 1
    assert checked == 90 - len(RANDOM)


def test_distributions_are_mutually_consistent():
    """``q`` inverts ``p`` across the new families -- enough to show the
    ``d``/``p``/``q`` naming is wired to the right SciPy end for each."""
    from mcad2py.runtime import (
        pbeta, pbinom, pchisq, pF, pgamma, phypergeom, plnorm, pnbinom,
        punif, qbeta, qbinom, qchisq, qF, qgamma, qhypergeom, qlnorm,
        qnbinom, qunif,
    )

    assert math.isclose(punif(qunif(0.4, 1, 5), 1, 5), 0.4, rel_tol=1e-12)
    assert math.isclose(pgamma(qgamma(0.3, 3), 3), 0.3, rel_tol=1e-9)
    assert math.isclose(pbeta(qbeta(0.6, 2, 5), 2, 5), 0.6, rel_tol=1e-9)
    assert math.isclose(pchisq(qchisq(0.9, 7), 7), 0.9, rel_tol=1e-9)
    assert math.isclose(pF(qF(0.7, 4, 6), 4, 6), 0.7, rel_tol=1e-9)
    assert math.isclose(plnorm(qlnorm(0.8, 2, 1), 2, 1), 0.8, rel_tol=1e-9)
    # Discrete: q gives the smallest k whose cdf clears p, so cdf(q(p)) >= p.
    assert pbinom(qbinom(0.5, 15, 0.6), 15, 0.6) >= 0.5
    assert phypergeom(qhypergeom(0.5, 5, 4, 6), 5, 4, 6) >= 0.5
    assert pnbinom(qnbinom(0.5, 5, 0.75), 5, 0.75) >= 0.5


def test_dgeom_and_dbinom_are_zero_indexed_and_sum_to_one():
    """Mathcad's ``k`` starts at 0 (failures/successes before the event), so
    the pmf over ``k = 0 .. n`` must still sum to 1."""
    from mcad2py.runtime import dbinom, dgeom

    n, q = 5, 0.75
    total = sum(dbinom(k, n, q) for k in range(n + 1))
    assert math.isclose(total, 1.0, rel_tol=1e-12)
    # Geometric has infinite support; a large-enough prefix should still be
    # within a hair of 1.
    total_geom = sum(dgeom(k, q) for k in range(50))
    assert math.isclose(total_geom, 1.0, rel_tol=1e-9)


def test_cnorm_is_the_standard_normal_cdf():
    """``cnorm`` is Mathcad-15's alias for ``pnorm(x, 0, 1)``."""
    from mcad2py.runtime import cnorm, pnorm

    assert math.isclose(cnorm(1.5), pnorm(1.5, 0, 1), rel_tol=1e-14)
    assert math.isclose(cnorm(0), 0.5, rel_tol=1e-14)


def test_histogram_supports_both_call_shapes():
    """``histogram(n, A)`` -- the ``statistics.mcdx`` form -- returns an
    ``n x 2`` midpoint/count matrix; ``histogram(intvls, A)`` -- an explicit
    boundary vector -- returns just the ``len(intvls) - 1`` counts."""
    from mcad2py.runtime import histogram

    data = np.array([0.5, 1.5, 1.6, 2.5, 2.6, 2.7])
    by_count = histogram(3, data)
    assert by_count.shape == (3, 2)
    assert float(np.sum(by_count[:, 1].astype(float))) == len(data)

    edges = np.array([0.0, 1.0, 2.0, 3.0])
    by_edges = histogram(edges, data)
    assert by_edges.shape == (3,)
    assert list(by_edges) == [1.0, 2.0, 3.0]


def test_histogram_converts_boundaries_into_the_data_unit():
    """Boundaries in a *different* (but compatible) unit than the data must be
    converted, not compared as raw magnitudes -- millimetre edges against metre
    data would otherwise pile every value into the first bin."""
    from mcad2py.runtime import histogram

    data = np.array([0.5, 1.5, 2.5]) * ureg.meter
    in_mm = np.array([0.0, 1000.0, 2000.0, 3000.0]) * ureg.millimeter
    in_m = np.array([0.0, 1.0, 2.0, 3.0]) * ureg.meter
    assert list(histogram(in_mm, data)) == list(histogram(in_m, data)) == [1.0, 1.0, 1.0]

    with pytest.raises(pint.DimensionalityError):
        histogram(np.array([0.0, 1.0, 2.0]) * ureg.second, data)


def test_Re_keeps_a_unit_and_takes_the_real_part():
    """Mathcad's ``Re`` applies to a *dimensioned* complex value (a complex
    impedance, a complex modulus), which ``np.real`` alone cannot handle -- it
    has no implementation for a Pint quantity and raises."""
    from mcad2py.runtime import Re

    assert Re(3.0) == 3.0
    assert Re(2.0 + 5.0j) == 2.0

    z = (2.0 + 5.0j) * ureg.ohm
    assert Re(z).magnitude == 2.0
    assert Re(z).units == ureg.ohm

    vec = np.array([1.0 + 1.0j, 3.0 - 2.0j]) * ureg.ohm
    assert list(Re(vec).magnitude) == [1.0, 3.0]


def test_distribution_parameters_accept_an_unreduced_ratio():
    """A worksheet feeds these a ratio Pint still carries as e.g. ``m/mm``; the
    wrappers reduce it rather than reading the raw magnitude."""
    from mcad2py.runtime import pbinom, rbinom, runif

    ratio = (600 * ureg.mm) / (1000 * ureg.mm)  # dimensionless 0.6, unit mm/mm
    assert math.isclose(pbinom(10, 15, ratio), pbinom(10, 15, 0.6), rel_tol=1e-14)
    assert len(rbinom(5 * ureg.dimensionless, 7, ratio)) == 5
    assert len(runif(4, 0 * ureg.dimensionless, ratio)) == 4


def test_random_draws_have_the_right_shape_even_though_they_cannot_match(sheet):
    """The random-sample regions can't reproduce a cached value, but they do
    run -- and the distributions they build are the size the sheet asked for."""
    _, _, echoed = sheet
    assert len(flat(echoed[9])) == 5    # rbinom(5, 7, 0.65)
    assert len(flat(echoed[13])) == 5   # rbeta(5, 6, 0.75)
    assert len(flat(echoed[19])) == 7   # rF(7, 2, 3)
    assert len(flat(echoed[28])) == 9   # rchisq(9, 3)
    assert len(flat(echoed[89])) == 8   # rlnorm(8, mu, sigma)
