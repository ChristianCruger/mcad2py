"""Tests for the statistics family (``references/statistics.mcdx``).

PTC's own statistics tutorial, and the widest single catalogue sheet in the
suite -- 82 evaluated regions covering descriptive statistics, regression,
hypothesis tests, the normal/Student-t/Weibull distributions, and the
Numerical-Recipes correlation set. Points worth knowing:

* **Capitalisation is the estimator.** ``var``/``stdev`` divide by n (the
  population forms), ``Var``/``Stdev`` by n-1 (the sample forms). The sheet
  computes each one twice -- once via the builtin and once from a hand-written
  Σ formula -- so the pair pins which is which.
* ``percentile(A, p)`` interpolates at position ``p·(n+1)`` of the 1-based
  sorted sample, not NumPy's default: the 90th percentile of ``0 … 10`` is 9.8.
  It also accepts ``50%``, since Mathcad's ``%`` is a dimensionless *unit*.
* ``mode`` **errors** rather than guessing -- once for data with no repeat, once
  for multimodal data. Mathcad caches both as ``<engineError>``, so those two
  regions are emitted guarded and the sheet still runs to the end (this is the
  behaviour ``ir.Region.cached_error`` exists for).
* ``data[2] := 1.2·data[2]`` rewrites one element of an existing vector -- a
  constant-index :class:`ir.Recurrence`, which is why every mean below it moves
  from 75.4 to 77.24.
* ``Spear``/``kendltau``/``kendltau2``/``contingtbl``/``Ftest`` return the whole
  vector of statistics the Numerical Recipes routine computes (coefficient, test
  statistic, p-value, …), which is what Mathcad's cache holds.

**Two documented divergences** (see docs/test-coverage.md):

* Everything downstream of ``rnorm``/``rweibull``/``rt`` is a fresh random draw
  and cannot reproduce a cached number -- 16 of the 82 echoes, listed in
  ``RANDOM`` below. They are still executed, so the code path is covered.
* The four p-values from the correlation set agree only to ~1e-7, not the ~1e-14
  the rest of the sheet hits: Mathcad evaluates them with Numerical Recipes'
  Chebyshev ``erfcc``/``betai`` approximations, and we use SciPy's exact
  ``erfc``/``betainc``, which is the more accurate of the two.
"""

import math

import numpy as np
import pytest

from conftest import cached_results, flat, reference, result_refs, run_sheet
from mcad2py import ir
from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import echo_expr
from mcad2py.loader import load_mcdx

REFERENCE = reference("statistics")

# Echoes fed by a random draw (``rt``/``rnorm``/``rweibull``): a different
# sample every run, so there is no cached number to match. The comment names
# what each group shows.
RANDOM = frozenset(
    {25}                       # rt(7, ν): seven Student-t draws
    | set(range(39, 49))       # mean/Var/Stdev/var/stdev of the random samples
    | set(range(61, 66))       # kurt/skew of the random samples
)

# Regions Mathcad itself reports an error for, so its cache holds no value.
ENGINE_ERRORS = frozenset({5, 11})

# Echo index -> relative tolerance, for the Numerical Recipes p-values (see the
# module docstring). Everything else is held to 1e-12.
APPROXIMATE = {
    67: 1e-9,   # Ftest    -- betai continued fraction vs scipy.special.betainc
    78: 1e-6,   # Spear    -- erfcc Chebyshev approximation vs scipy erfc
    79: 1e-7,   # kendltau
    80: 1e-6,   # kendltau2
}


@pytest.fixture(scope="module")
def sheet():
    """Convert, execute, and return ``(source, namespace, echoed values)``."""
    np.random.seed(0)  # the random draws still have to be *reproducible* here
    return run_sheet(REFERENCE)


def test_sheet_runs_end_to_end(sheet):
    """Nothing is dropped or unsupported, and every evaluated region echoes."""
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == 82


def test_sheet_matches_cached_results(sheet):
    """Every deterministic echo reproduces Mathcad's cached value."""
    _, _, echoed = sheet
    cached, refs = cached_results(REFERENCE), result_refs(REFERENCE)
    regions = [r for r in convert_worksheet(load_mcdx(REFERENCE)).regions
               if echo_expr(r) is not None]
    assert len(regions) == len(echoed)

    checked = 0
    for index, region in enumerate(regions):
        if index in RANDOM or index in ENGINE_ERRORS:
            continue
        want = np.asarray(cached[refs[region.source.region_id]], dtype=float)
        got = flat(echoed[index])
        assert got.shape == want.shape, f"echo {index}: {got.shape} vs {want.shape}"
        rtol = APPROXIMATE.get(index, 1e-12)
        assert np.allclose(got, want, rtol=rtol, atol=1e-12), (
            f"echo {index} ({echo_expr(region)}): {got} != {want}"
        )
        checked += 1
    assert checked == 64  # the whole sheet bar the random draws and the errors


def test_population_and_sample_estimators_are_distinct(sheet):
    """Mathcad's lower-case ``var``/``stdev`` divide by n and its capitalised
    ``Var``/``Stdev`` by n-1. The sheet's own Σ formulas (``variance`` and
    ``Variance``) sit next to them and must land on the same pair."""
    _, ns, _ = sheet
    sample = ns["D"]
    n = len(flat(sample))
    assert math.isclose(ns["Var"](sample) / ns["var"](sample), n / (n - 1), rel_tol=1e-14)
    assert math.isclose(ns["Stdev"](sample) ** 2, ns["Var"](sample), rel_tol=1e-14)
    assert math.isclose(ns["stdev"](sample) ** 2, ns["var"](sample), rel_tol=1e-14)
    # And the sheet's hand-written versions agree with the builtins.
    assert math.isclose(ns["Variance"](sample), ns["Var"](sample), rel_tol=1e-12)
    assert math.isclose(ns["variance"](sample), ns["var"](sample), rel_tol=1e-12)


def test_percentile_interpolates_at_mathcads_position(sheet):
    """``percentile(A, p)`` sits at position ``p·(n+1)`` of the 1-based sorted
    sample -- so the 90th percentile of ``0 … 10`` is 9.8, where NumPy's default
    (and every "nearest rank" definition) would say 9."""
    from mcad2py.runtime import percentile

    x = np.arange(11.0)
    assert math.isclose(percentile(x, 0.90), 9.8, rel_tol=1e-14)
    assert math.isclose(percentile(x, 0.50), 5.0, rel_tol=1e-14)
    assert not math.isclose(percentile(x, 0.90), np.percentile(x, 90))


def test_percent_is_a_dimensionless_unit(sheet):
    """``percentile(X, 50%)`` -- Mathcad's ``%`` is a *unit* worth 0.01, spelled
    in the XML as a scale apply just like ``50 mm``, but labelled FUNCTION."""
    src, _, echoed = sheet
    assert "percentile(X, 50 * ureg.percent)" in src
    assert math.isclose(float(flat(echoed[14])[0]), 5.0, rel_tol=1e-14)


def test_mode_refuses_to_guess(sheet):
    """No repeated value, or a tie for most frequent, is an *error* in Mathcad
    (both cached as ``<engineError>``); the sheet demonstrates each in turn and
    only its third ``mode`` call has an answer."""
    from mcad2py.runtime import mode

    _, _, echoed = sheet
    for index in sorted(ENGINE_ERRORS):
        label, error = echoed[index]
        assert label == "error:" and isinstance(error, ValueError)
    assert math.isclose(float(flat(echoed[12])[0]), 4.0)  # [1 2 3 4 4 5 6]

    with pytest.raises(ValueError, match="No value occurs more frequently"):
        mode(np.array([1.0, 2.0, 3.0]))
    with pytest.raises(ValueError, match="multimodal"):
        mode(np.array([1.0, 1.0, 2.0, 2.0]))


def test_in_place_element_update_is_a_recurrence(sheet):
    """``data[2] := 1.2·data[2]`` writes one slot of a vector that already
    exists -- a constant-index :class:`ir.Recurrence`, not a new definition --
    so every statistic below it sees 55.2 in place of 46."""
    src, _, echoed = sheet
    assert "data = vec_set(data, 2, 1.2 * data[2])" in src
    ws = convert_worksheet(load_mcdx(REFERENCE))
    update = next(
        r for r in ws.regions
        if isinstance(r, ir.Recurrence) and r.targets[0].base.py == "data"
    )
    assert update.index is None and update.create == []  # updates, never creates
    assert math.isclose(float(flat(echoed[0])[0]), 75.4)   # mean before
    assert math.isclose(float(flat(echoed[2])[0]), 77.24)  # mean after


def test_regression_and_correlation_agree_with_the_sheets_own_formulas(sheet):
    """``slope`` is ``cvar/var`` and ``corr`` is the standardised Σ the sheet
    spells out beside it -- both checked here against Mathcad's cache too."""
    _, ns, echoed = sheet
    v1, v2 = ns["V_1"], ns["V_2"]
    assert math.isclose(ns["slope"](v1, v2), ns["cvar"](v1, v2) / ns["var"](v1),
                        rel_tol=1e-14)
    assert math.isclose(ns["corr"](v1, v2), -0.98084821135069744, rel_tol=1e-14)
    assert math.isclose(float(flat(echoed[73])[0]), ns["corr"](v1, v2) ** 2,
                        rel_tol=1e-14)


def test_rank_is_one_based_ascending(sheet):
    """``Rank`` gives each element its 1-based position in ascending order --
    the Spearman rank correlation is then ``corr`` of the two rank vectors."""
    from mcad2py.runtime import Rank

    _, ns, _ = sheet
    assert list(Rank(np.array([0.1, -0.86, -3.7]))) == [3.0, 2.0, 1.0]
    assert list(flat(ns["Rank2"])) == list(range(1, 11))  # V_2 is monotonic
    assert math.isclose(ns["corr"](ns["Rank1"], ns["Rank2"]), -0.98787878787878791,
                        rel_tol=1e-14)


def test_contingency_table_statistics(sheet):
    """``contingtbl`` returns ``(χ², df, p, Cramér's V, C)``. The two association
    measures are just χ² rescaled, which is worth pinning independently of the
    cached numbers."""
    _, ns, _ = sheet
    chisq, df, _prob, cramrv, ccc = flat(ns["c"])
    total = float(np.sum(flat(ns["Table"])))
    assert df == 6.0  # (3 rows - 1) x (4 columns - 1)
    assert math.isclose(cramrv, math.sqrt(chisq / (total * 2)), rel_tol=1e-14)
    assert math.isclose(ccc, math.sqrt(chisq / (chisq + total)), rel_tol=1e-14)


def test_distributions_are_mutually_consistent():
    """``q`` inverts ``p``, and ``d`` is the derivative of ``p`` -- enough to
    show the ``d``/``p``/``q`` naming is wired to the right SciPy end."""
    from mcad2py.runtime import dnorm, pnorm, pt, qnorm, qt

    assert math.isclose(pnorm(qnorm(0.975, 0, 1), 0, 1), 0.975, rel_tol=1e-12)
    assert math.isclose(pt(qt(0.95, 39), 39), 0.95, rel_tol=1e-12)
    assert math.isclose(pnorm(0, 0, 1), 0.5, rel_tol=1e-14)
    assert math.isclose(dnorm(0, 0, 1), 1 / math.sqrt(2 * math.pi), rel_tol=1e-14)


def test_random_draws_have_the_right_shape_even_though_they_cannot_match(sheet):
    """The random-sample regions can't reproduce a cached value, but they do run
    -- and the distributions they build are the size the sheet asked for."""
    _, ns, echoed = sheet
    assert len(flat(echoed[25])) == 7          # rt(7, ν)
    assert len(flat(ns["WeibDist"])) == 2000
    assert len(flat(ns["NormDist"])) == 2000
    # ``histogram(15, A)`` is a 15 x 2 matrix of bin midpoints and counts; the
    # midpoints keep the sample's unit, so the two columns stay a mixed-unit
    # (object) matrix -- which is exactly what the plot below reads with
    # ``plot_axis(matcol(WeibHist, 0), ureg.kg)``.
    hist = ns["WeibHist"]
    assert hist.shape == (15, 2)
    assert str(hist[0, 0].units) == "kilogram"
    assert float(np.sum(hist[:, 1].astype(float))) == 2000.0
