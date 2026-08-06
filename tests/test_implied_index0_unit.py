"""A program vector whose **index 0 is never written**
(``references/implied_index0_unit.mcdx``).

The sheet's loop runs ``i = 1 .. 10`` and assigns ``z[i] := h/2 − (2i−1)·h/20``,
so Mathcad auto-grows ``z`` and zero-fills the untouched index 0. Its cache
shows what that means: an ``11x1`` matrix carrying **one** unit (metre), the gap
included -- ``0`` is ``0`` in any unit, so it doesn't make the vector
heterogeneous.

We kept the gap as a bare ``0``, which left ``z`` an ``dtype=object`` array of
mixed plain/Pint entries. That is wrong in two compounding ways:

* the array never fused, so a later ``z / m`` divided a *dimensionless* object
  array by a length and read as ``1/meter`` -- the real sheet this came from
  died on ``DimensionalityError: Cannot convert from '1 / meter' to
  'dimensionless'``, several regions downstream of the actual mistake;
* ``stack`` returned an ``n x 1`` matrix rather than the 1-D form this module
  represents column vectors with, so the single-subscript echo ``z[0] =`` read a
  one-row *slice* and printed ``[0.0] / millimeter`` where Mathcad caches ``0``.

Both are runtime-side; the emitted source was already correct.
"""

from pathlib import Path

import numpy as np
import pint
import pytest

from mcad2py.convert import convert_file
from mcad2py.runtime import _consolidate, col, matrix, stack, vec_set

REFERENCE = Path(__file__).parent.parent / "references" / "implied_index0_unit.mcdx"

# result.xml, in metres: the zero-fill at index 0 then the ten loop values.
CACHED_Z = [
    0,
    0.225,
    0.175,
    0.125,
    0.074999999999999983,
    0.024999999999999994,
    -0.025000000000000022,
    -0.075000000000000011,
    -0.125,
    -0.17500000000000004,
    -0.22500000000000003,
]
CACHED_Z0 = 0.0  # ``z[0] =`` displayed in mm


def _run():
    """Convert, execute, and return ``(source, namespace, echoed values)``.

    Echoes are captured as objects rather than text -- the point of this sheet
    is the *type* of what gets printed, which a line-based parse would flatten
    away.
    """
    src = convert_file(REFERENCE, fmt="py")
    echoed: list = []
    ns: dict = {"print": lambda *a: echoed.append(a[0] if len(a) == 1 else a)}
    exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return src, ns, echoed


@pytest.fixture(scope="module")
def sheet():
    return _run()


# --- the sheet ---------------------------------------------------------------


def test_whole_sheet_matches_the_cache(sheet):
    _, _, echoed = sheet
    z, z0 = echoed
    assert np.allclose(z.to("m").magnitude, CACHED_Z, rtol=0, atol=1e-15)
    assert z0.to("mm").magnitude == pytest.approx(CACHED_Z0, abs=1e-15)


def test_the_zero_filled_vector_is_one_fused_dimensioned_array(sheet):
    """The crux. Not an object array of ``0`` plus ten millimetre scalars."""
    _, ns, _ = sheet
    z = ns["z"]
    assert z.check("[length]")
    assert z.magnitude.dtype != object
    assert z.magnitude.shape == (11,)


def test_dividing_the_vector_by_a_length_is_dimensionless(sheet):
    """The downstream symptom: an unfused ``z`` made ``z / m`` read ``1/meter``,
    and the failure surfaced regions later as a ``DimensionalityError``."""
    _, ns, _ = sheet
    ureg = ns["ureg"]
    assert (ns["z"] / ureg.m).check("[]")


def test_a_single_subscript_reads_an_element_not_a_row(sheet):
    """``z[0]`` is the scalar gap, not a length-1 slice of it."""
    _, ns, _ = sheet
    z0 = ns["z"][0]
    assert not isinstance(z0.magnitude, np.ndarray)
    assert z0.check("[length]")


def test_the_fixture_still_leaves_index_zero_unwritten(sheet):
    """Guard the fixture: if the loop were ever re-authored from ``i = 0`` there
    would be no gap, and every test above would pass while testing nothing."""
    src, _, _ = sheet
    assert "for i in arange(1, 10, 1)" in src
    assert "vec_set(z, i," in src
    assert "stack(z)" in src


# --- _consolidate: which arrays fuse ----------------------------------------


def _obj(*elements):
    out = np.empty(len(elements), dtype=object)
    for i, e in enumerate(elements):
        out[i] = e
    return out


def test_a_zero_gap_is_absorbed_into_the_prevailing_unit():
    ureg = pint.UnitRegistry()
    fused = _consolidate(_obj(0, 2 * ureg.mm, 3 * ureg.mm))
    assert fused.check("[length]")
    assert fused.magnitude.tolist() == [0.0, 2.0, 3.0]


def test_a_nonzero_plain_entry_still_blocks_fusing():
    """The counter-case that keeps the rule honest: a genuinely dimensionless
    entry (RC_col's ``[1; −l/2; −w/2]`` constant column) is *not* a gap, and
    absorbing it would invent a unit it never had."""
    ureg = pint.UnitRegistry()
    mixed = _consolidate(_obj(1, 2 * ureg.mm, 3 * ureg.mm))
    assert mixed.dtype == object
    assert mixed[0] == 1


def test_incompatible_units_still_block_fusing():
    ureg = pint.UnitRegistry()
    mixed = _consolidate(_obj(0, 2 * ureg.mm, 3 * ureg.kg))
    assert mixed.dtype == object


def test_an_all_plain_array_is_unaffected():
    plain = _consolidate(_obj(0, 1, 2))
    assert plain.dtype != object
    assert plain.tolist() == [0.0, 1.0, 2.0]


# --- vec_set: the gap, 1-D and 2-D ------------------------------------------


def test_vec_set_zero_fill_adopts_the_vectors_unit():
    ureg = pint.UnitRegistry()
    z = None
    for i in range(1, 4):
        z = vec_set(z, i, i * ureg.mm)
    assert z.check("[length]")
    assert z.magnitude.tolist() == [0.0, 1.0, 2.0, 3.0]


def test_vec_set_zero_fill_adopts_the_unit_in_2d():
    """The same gap in the 2-D form (``Ans[j, 0] :=``, the RC_col shape)."""
    ureg = pint.UnitRegistry()
    a = None
    for j in range(1, 3):
        a = vec_set(a, (j, 0), j * ureg.kN)
    assert a.check("[force]")
    assert a.magnitude.shape == (3, 1)
    assert a.magnitude.reshape(-1).tolist() == [0.0, 1.0, 2.0]


# --- stack: column vector vs. matrix ----------------------------------------


def test_stack_of_column_vectors_stays_a_column_vector():
    """1-D, the shape ``col()`` produces -- so a single subscript indexes it."""
    ureg = pint.UnitRegistry()
    v = stack(col(1.0, 2.0) * ureg.mm)
    assert v.magnitude.ndim == 1
    assert v[1].to("mm").magnitude == 2.0


def test_stack_accepts_a_scalar_block():
    """``stack("α", v)`` -- Mathcad's idiom for captioning a data column with a
    string header. A 0-d block has no ``shape[1]``, so this used to raise
    ``IndexError: tuple index out of range`` before any of the units mattered."""
    ureg = pint.UnitRegistry()

    labelled = stack("alpha", col(1.0, 2.0) * ureg.mm)
    assert labelled.dtype == object  # a string beside lengths stays per-element
    assert labelled[0] == "alpha"
    assert labelled[2].to("mm").magnitude == 2.0

    numeric = stack(5.0, col(1.0, 2.0))
    assert numeric.tolist() == [5.0, 1.0, 2.0]


def test_stack_with_a_wider_block_is_still_a_matrix():
    """Only a single-column result collapses; stacking against a 2x2 keeps the
    2-D shape (and its zero fill)."""
    stacked = stack(col(1, 2), matrix([3, 5], [4, 6]))
    assert np.asarray(stacked, dtype=float).tolist() == [[1, 0], [2, 0], [3, 5], [4, 6]]
