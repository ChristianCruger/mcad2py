"""Tests for the ordering family (``references/sort.mcdx``).

A small catalogue sheet: it builds a 5x5 matrix ``M`` from a range-indexed
formula, then applies ``sort``/``csort``/``reverse``/``rsort`` to it and a
plain vector ``A``. Every one of these already has runtime support (added for
``matrices.mcdx``), so this file mainly pins that the *sheet* -- not just the
functions in isolation -- converts and runs end to end and matches Mathcad's
cached ``result.xml``.

One thing worth noting: ``M``'s columns are each monotonic (built from a
quadratic in ``i`` and ``j``), so ``csort(M, 4)``, ``reverse(M)`` and
``rsort(M, 2)`` all happen to produce the *same* matrix here -- that's a
property of this particular ``M``, not a bug (each is checked against its own
cached value below, they just happen to be equal).
"""

import math

import numpy as np
import pytest

from conftest import flat, reference, run_sheet

REFERENCE = reference("sort")

# Mathcad's cached results (result.xml), in region/echo order. Matrices are
# listed **column-major**, matching both the cache's own ``<ml:matrix>`` order
# and ``flat``'s column-major reshape of the computed array below.
CACHED = {
    0: (
        "M := index_build_2d(...)",
        [
            19, 14, 7, -2, -13,
            11, 7, 1, -7, -17,
            -1, -4, -9, -16, -25,
            -17, -19, -23, -29, -37,
            -37, -38, -41, -46, -53,
        ],
    ),
    1: ("sort(A)", [1, 3, 3, 4, 5, 6, 7, 9]),
    2: (
        "csort(M, 4)",
        [
            -13, -2, 7, 14, 19,
            -17, -7, 1, 7, 11,
            -25, -16, -9, -4, -1,
            -37, -29, -23, -19, -17,
            -53, -46, -41, -38, -37,
        ],
    ),
    3: (
        "reverse(M)",
        [
            -13, -2, 7, 14, 19,
            -17, -7, 1, 7, 11,
            -25, -16, -9, -4, -1,
            -37, -29, -23, -19, -17,
            -53, -46, -41, -38, -37,
        ],
    ),
    4: (
        "rsort(M, 2)",
        [
            -37, -38, -41, -46, -53,
            -17, -19, -23, -29, -37,
            -1, -4, -9, -16, -25,
            11, 7, 1, -7, -17,
            19, 14, 7, -2, -13,
        ],
    ),
}


@pytest.fixture(scope="module")
def sheet():
    return run_sheet(REFERENCE)


def test_sheet_runs_end_to_end(sheet):
    """No region is dropped or unsupported, and each one echoes exactly once."""
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == 5


def test_sheet_matches_cached_results(sheet):
    """Every echo reproduces Mathcad's cached value."""
    _, _, echoed = sheet
    for index, (label, expected) in CACHED.items():
        got = flat(echoed[index])
        want = np.atleast_1d(np.asarray(expected, dtype=float))
        assert got.shape == want.shape, f"echo {index} ({label}): shape {got.shape}"
        assert np.allclose(got, want, rtol=1e-12, atol=1e-9), (
            f"echo {index} ({label}): {got} != {want}"
        )


def test_generated_source_uses_runtime_helpers(sheet):
    src, _, _ = sheet
    for name in ("sort", "csort", "reverse", "rsort"):
        assert f"{name}(" in src, name


def test_sort_returns_ascending_vector(sheet):
    """``sort(A)`` on the unsorted ``A := (4 3 7 1 9 6 3 5)`` -- a plain
    element-wise ascending sort, independent of the matrix machinery above."""
    _, ns, _ = sheet
    got = flat(ns["sort"](ns["A"]))
    assert math.isclose(got[0], 1) and math.isclose(got[-1], 9)
    assert list(got) == sorted(got)
