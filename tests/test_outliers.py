"""Mathcad's outlier family: ``Grubbs`` / ``GrubbsClassic`` / ``ThreeSigma``
and the ``trim`` that drops what they flag.

``references/interpolation_prediction.mcdx`` reaches exactly one arm of this
family -- ``GrubbsClassic(y, 0.55)`` on a plain, unitless column, read for its
index alone. Everything else is pinned here against PTC's own worked examples
("Outlier Detection", "Grubbs' Method for Detecting Outliers" and "Outlier
Removal"), which publish the returned matrices in full for one 195-point
heatflow data set.

Those published matrices settle two things:

* the confidence convention -- PTC calls ``Grubbs(y, 1 - alpha)``, so ``a`` is
  a confidence and the significance level used inside is ``1 - a``;
* the **population** standard deviation. ``Grubbs(y, 0.85)`` returns three rows
  (3, 19, 188); the sample deviation puts row 188 just under the bound and
  returns two.

``references/grubbs.mcdx`` is the purpose-built fixture for the rest. It is a
20-value column with one outlier, and it caches the two cases no published page
shows: what happens when **nothing** clears the bound, and what a **matrix**
argument returns.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import echo_expr
from mcad2py.loader import load_mcdx
from mcad2py.runtime import Grubbs, GrubbsClassic, ThreeSigma, trim
from mcad2py.units import ureg

from conftest import cached_results, flat, reference, result_refs, run_sheet

SHEET = reference("grubbs")

# PTC's heatflow data set, the one every published example above uses.
HEATFLOW = np.array([
    9.206, 9.3, 9.278, 9.175, 9.275, 9.289, 9.287, 9.261,
    9.303, 9.276, 9.273, 9.288, 9.256, 9.252, 9.298, 9.267,
    9.257, 9.278, 9.248, 9.35, 9.276, 9.279, 9.267, 9.246,
    9.238, 9.269, 9.248, 9.257, 9.268, 9.288, 9.258, 9.286,
    9.251, 9.257, 9.268, 9.291, 9.219, 9.27, 9.219, 9.241,
    9.27, 9.227, 9.259, 9.286, 9.32, 9.328, 9.263, 9.248,
    9.239, 9.225, 9.221, 9.271, 9.252, 9.281, 9.271, 9.295,
    9.302, 9.279, 9.237, 9.234, 9.245, 9.222, 9.207, 9.259,
    9.276, 9.269, 9.257, 9.265, 9.296, 9.293, 9.264, 9.281,
    9.267, 9.301, 9.253, 9.261, 9.238, 9.225, 9.236, 9.24,
    9.264, 9.244, 9.278, 9.311, 9.262, 9.26, 9.253, 9.246,
    9.284, 9.251, 9.275, 9.255, 9.28, 9.275, 9.262, 9.275,
    9.252, 9.23, 9.255, 9.269, 9.29, 9.274, 9.256, 9.262,
    9.25, 9.262, 9.264, 9.265, 9.242, 9.24, 9.222, 9.242,
    9.215, 9.286, 9.272, 9.266, 9.285, 9.269, 9.268, 9.246,
    9.231, 9.241, 9.261, 9.274, 9.292, 9.271, 9.267, 9.309,
    9.264, 9.279, 9.255, 9.229, 9.253, 9.256, 9.263, 9.22,
    9.258, 9.268, 9.268, 9.249, 9.235, 9.243, 9.253, 9.263,
    9.243, 9.261, 9.26, 9.253, 9.241, 9.239, 9.264, 9.243,
    9.247, 9.252, 9.262, 9.247, 9.306, 9.238, 9.249, 9.257,
    9.266, 9.299, 9.245, 9.287, 9.301, 9.257, 9.271, 9.275,
    9.282, 9.253, 9.269, 9.282, 9.278, 9.285, 9.24, 9.268,
    9.248, 9.225, 9.231, 9.27, 9.265, 9.284, 9.281, 9.263,
    9.292, 9.252, 9.244, 9.283, 9.18, 9.231, 9.233, 9.235,
    9.217, 9.274, 9.274,
])


def test_grubbs_reproduces_the_published_matrix():
    """``Grubbs(y, 0.85)`` -- three rows, printed to three decimals in PTC's
    "Outlier Removal" example as ``3 3.526 -0.207 / 19 3.631 -0.312 /
    188 3.322 -0.003``."""
    got = Grubbs(HEATFLOW, 0.85)
    assert got.shape == (3, 3)
    assert got[:, 0].tolist() == [3.0, 19.0, 188.0]
    assert np.allclose(got[:, 1], [3.526, 3.631, 3.322], atol=5e-4)
    assert np.allclose(got[:, 2], [-0.207, -0.312, -0.003], atol=5e-4)


def test_a_tighter_confidence_returns_fewer_rows():
    """The same data at ``a = 0.9``: two rows, and the third column moves with
    the bound, not with the data (PTC's "Outlier Detection" example)."""
    got = Grubbs(HEATFLOW, 0.9)
    assert got[:, 0].tolist() == [3.0, 19.0]
    assert np.allclose(got[:, 2], [-0.102, -0.207], atol=5e-4)


def test_grubbs_falls_back_to_the_closest_point():
    """No published page shows this case, and it is not what the shape of the
    function suggests: with nothing past the bound ``Grubbs`` returns the one
    most extreme point, third column **positive**, exactly as ``GrubbsClassic``
    would. ``references/grubbs.mcdx`` region 8 is what pins it -- an empty table
    was the natural guess and it is wrong."""
    got = Grubbs(HEATFLOW, 0.99999999)
    assert got.shape == (1, 3)
    assert got[0, 0] == 19.0 and got[0, 2] > 0
    assert np.allclose(got, GrubbsClassic(HEATFLOW, 0.99999999))


def test_grubbs_classic_returns_the_extreme_point_outlier_or_not():
    """PTC's ``GrubbsClassic(y, 1 - 2*0.1)`` prints ``[19 3.631 -0.389]``. At a
    confidence where nothing clears the bound the same row comes back with a
    **positive** third column -- the documented "not an outlier, but the point
    most likely to be one"."""
    got = GrubbsClassic(HEATFLOW, 0.8)
    assert got.shape == (1, 3)
    assert got[0, 0] == 19.0
    assert math.isclose(got[0, 1], 3.631467844074731, rel_tol=1e-12)
    assert math.isclose(got[0, 2], -0.38928838671261223, rel_tol=1e-12)

    inside = GrubbsClassic(HEATFLOW, 0.98)
    assert inside[0, 0] == 19.0 and inside[0, 2] > 0


def test_three_sigma_returns_index_and_statistic_only():
    """Two columns, no bound to subtract: ``3 3.526 / 19 3.631 / 188 3.322``."""
    got = ThreeSigma(HEATFLOW)
    assert got.shape == (3, 2)
    assert got[:, 0].tolist() == [3.0, 19.0, 188.0]
    assert np.allclose(got[:, 1], [3.526, 3.631, 3.322], atol=5e-4)


def test_three_sigma_falls_back_to_the_closest_point():
    """Documented behaviour, and the one place the family invents a row: with
    no point past three deviations the nearest one is returned."""
    got = ThreeSigma(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert got.shape == (1, 2)
    assert got[0, 0] in (0.0, 4.0) and got[0, 1] < 3.0


def test_the_statistic_is_dimensionless_for_dimensioned_data():
    """``|x - mean| / stdev`` cancels the unit, so a column of metres gives the
    same matrix as the same numbers bare -- and indexing the result does not
    hand a sheet a stray unit."""
    bare = GrubbsClassic(HEATFLOW, 0.8)
    metres = GrubbsClassic(HEATFLOW * ureg.m, 0.8)
    assert not hasattr(metres, "units")
    assert np.allclose(metres, bare, rtol=1e-14)


def test_trim_drops_the_named_rows_of_a_matrix_and_keeps_the_unit():
    """PTC's "Outlier Removal" trims a two-column ``augment(x, y)``: 195 rows
    in, 192 out, columns untouched."""
    x = np.arange(len(HEATFLOW), dtype=float)
    data = np.column_stack([x, HEATFLOW]) * ureg.m
    got = trim(data, [3, 19, 188])
    assert got.shape == (192, 2)
    assert got.units == ureg.m
    assert got[:, 0].magnitude.tolist() == [
        v for v in x.tolist() if v not in (3.0, 19.0, 188.0)
    ]


def test_trim_takes_a_single_index():
    """The reference sheet passes ``matelem(GrubbsClassic(y, 0.55), 0, 0)`` --
    one scalar, not a vector -- and a vector keeps its 1-D shape."""
    v = np.array([10.0, 20.0, 30.0, 40.0])
    assert trim(v, 2).tolist() == [10.0, 20.0, 40.0]
    assert trim(v, 2.0).shape == (3,)


def test_trim_reduces_a_dimensionless_index():
    """An index a worksheet still carries as an unreduced Pint ratio must
    reduce before it is rounded: reading the raw magnitude of ``2000 mm / m``
    would drop row 2000 and silently trim nothing."""
    v = np.array([10.0, 20.0, 30.0, 40.0]) * ureg.s
    index = (2000 * ureg.mm) / (1 * ureg.m)
    assert trim(v, index).magnitude.tolist() == [10.0, 20.0, 40.0]


def test_a_matrix_is_one_flat_bag_with_nested_index_pairs():
    """A matrix argument is judged as a single sample of all its elements, and
    the position comes back as a nested 2x1 ``(row, col)`` column. Both halves
    are cached by ``references/grubbs.mcdx``; the sheet test below is the
    anchor, this one is the shape on its own.
    """
    grid = np.column_stack([np.arange(20.0), HEATFLOW[:20]])
    got = GrubbsClassic(grid, 0.9)
    assert got.shape == (1, 3) and got.dtype == object
    assert np.asarray(got[0, 0]).shape == (2, 1)
    # The whole 40 values set the mean, so the extreme is an ``x`` end, not a
    # heatflow reading -- which is the point of the flat-bag reading.
    assert np.asarray(got[0, 0]).reshape(-1).tolist() == [19.0, 0.0]


# ---------------------------------------------------------------------------
# references/grubbs.mcdx -- the purpose-built sheet
# ---------------------------------------------------------------------------

# ``result-id`` 17: ``Grubbs(M, 0.95)``, whose first column holds a *nested*
# matrix. ``cached_results`` reads only the direct ``<real>`` children of a
# matrix, so it returns that row's two scalar columns and nothing else -- which
# is exactly what can be compared. The nested pair itself is region 18, echoed
# as ``A[0, 0]`` for that reason.
NESTED = "17"


@pytest.fixture(scope="module")
def sheet():
    """Convert, execute, and return ``(source, namespace, echoed values)``."""
    return run_sheet(SHEET)


def test_the_sheet_converts_with_no_todo(sheet):
    """Every region of it is supported -- there is nothing left to suppress."""
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == 14


def test_every_echo_matches_the_cache(sheet):
    """The whole sheet against Mathcad's own numbers, to ~1e-11.

    This is what pins the critical value to full precision: PTC's published
    matrices print three decimals, and the cached ``-0.4049316586941907``
    confirms the ``qt(alpha/(2N), N-2)`` bound to fourteen digits rather than
    to four.
    """
    _, _, echoed = sheet
    cached, refs = cached_results(SHEET), result_refs(SHEET)
    regions = [r for r in convert_worksheet(load_mcdx(SHEET)).regions
               if echo_expr(r) is not None]
    assert len(regions) == len(echoed)

    for index, region in enumerate(regions):
        ref = refs[region.source.region_id]
        want = np.asarray(cached[ref], dtype=float)
        # The nested row cannot go through ``flat``; compare its scalar columns.
        got = (np.asarray(echoed[index][0, 1:], dtype=float) if ref == NESTED
               else flat(echoed[index]))
        assert got.shape == want.shape, f"echo {index}: {got.shape} vs {want.shape}"
        assert np.allclose(got, want, rtol=1e-11, atol=1e-12), (
            f"echo {index}: {got} != {want}"
        )


def test_the_sheet_pins_the_fallback_and_the_nested_pair(sheet):
    """The two readings no published page shows, named rather than left inside
    the sweep above: ``Grubbs`` at a confidence nothing clears returns the
    closest point (echo 3, third column positive), and a matrix argument
    returns a nested ``(row, col)`` column (echo 12)."""
    _, _, echoed = sheet
    assert echoed[3][0, 0] == 19.0 and echoed[3][0, 2] > 0
    assert np.allclose(np.asarray(echoed[3], dtype=float), echoed[5].astype(float))
    assert np.asarray(echoed[12]).reshape(-1).tolist() == [0.0, 0.0]


def test_a_unit_on_the_data_leaves_the_table_bare(sheet):
    """Prime accepts ``GrubbsClassic(v*m, 0.95)`` and caches it as plain reals,
    identical to the unitless call. The statistic divides the unit out, and the
    index never had one."""
    _, _, echoed = sheet
    assert not hasattr(echoed[13], "units")
    assert np.allclose(echoed[13].astype(float), echoed[4].astype(float))
