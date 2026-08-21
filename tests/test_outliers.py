"""Mathcad's outlier family: ``Grubbs`` / ``GrubbsClassic`` / ``ThreeSigma``
and the ``trim`` that drops what they flag.

``references/interpolation_prediction.mcdx`` reaches exactly one arm of this
family -- ``GrubbsClassic(y, 0.55)`` on a plain, unitless column, read for its
index alone. Everything else is pinned here against PTC's own worked examples
("Outlier Detection", "Grubbs' Method for Detecting Outliers" and "Outlier
Removal"), which publish the returned matrices in full for one 195-point
heatflow data set.

Those published matrices settle two things the reference sheet cannot:

* the confidence convention -- PTC calls ``Grubbs(y, 1 - alpha)``, so ``a`` is
  a confidence and the significance level used inside is ``1 - a``;
* the **population** standard deviation. ``Grubbs(y, 0.85)`` returns three rows
  (3, 19, 188); the sample deviation puts row 188 just under the bound and
  returns two.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcad2py.runtime import Grubbs, GrubbsClassic, ThreeSigma, trim
from mcad2py.units import ureg

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


def test_grubbs_returns_nothing_when_no_point_clears_the_bound():
    """No example publishes this case, so an empty matrix comes back rather
    than an invented row. ``rows()`` of it is 0, which a sheet can act on."""
    got = Grubbs(HEATFLOW, 0.999)
    assert got.shape == (0, 3)


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


def test_a_matrix_argument_is_refused_rather_than_flattened():
    """Mathcad returns nested *pairs* of indices for a matrix. Flattening it
    would return a single index into a shape that has none."""
    grid = np.arange(12.0).reshape(4, 3)
    with pytest.raises(NotImplementedError, match="nested index pairs"):
        GrubbsClassic(grid, 0.9)
