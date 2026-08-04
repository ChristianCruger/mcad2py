"""Row vectors, labelled tables, and the table-search family
(``references/stack_augment_lookup.mcdx``).

Two things this sheet pins.

**A row vector is a matrix, a column vector is not.** We emitted every literal
with a dimension of 1 as ``col(...)``, a 1-D array -- so a ``1x3`` header
literal came back as a *column*, and ``stack(("A" "B" "C"), s)`` wrote the
labels down column 0 instead of across row 0. Mathcad states the distinction
itself in this sheet's cache: ``match`` on the ``3x1`` ``V`` returns the bare
index ``2``, while ``match`` on the ``1x3`` ``R`` returns the *pair* ``[0; 2]``
-- an index pair is what you get for a matrix. So ``cols == 1`` is the column
vector (1-D here), and ``1 x N`` is a genuine 2-D matrix.

``transpose`` is what moves between the two, which matters because Mathcad's
usual way of typing a column vector is a transposed row literal
(``(a b c)ᵀ``) -- it has to come back 1-D, and NumPy's transpose of a 1-D array
is itself.

**The table searches.** ``match``/``lookup``/``vlookup``/``hlookup``/
``vhlookup`` were the one gap left in the vector & matrix family. All five
return a *vector* even for a single hit (the cache holds ``1x1`` matrices, not
bare scalars), and a matrix is scanned **column-major** -- pinned by ``match(3,
s)``, whose two hits come back ``[1;1]`` before ``[0;2]``.

Note the cached result for region 0 (``i := 0 .. 2``) is a stale ``4x1``
``[0,1,2,3]`` left over from an earlier edit -- the region is a plain define
with nothing to echo, so Mathcad never refreshed it. Everything downstream
(``s`` is ``3x3``) confirms the live ``0 .. 2``. Same class of leftover as
``RC_interface.mcdx``'s ``ν_v``.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from mcad2py.convert import convert_file
from mcad2py.runtime import augment, col, lookup, match, matrix, stack, transpose

REFERENCE = Path(__file__).parent.parent / "references" / "stack_augment_lookup.mcdx"


def _cached() -> dict[int, object]:
    """``result.xml`` by result-id, as row-major nested lists.

    Mathcad stores a matrix **column-major**, and a cell may itself be a matrix
    (``match`` on a matrix caches nested index pairs), so this recurses.
    """
    root = ET.fromstring(zipfile.ZipFile(REFERENCE).read("mathcad/result.xml"))

    def local(tag):
        return tag.split("}")[-1]

    def value(elem):
        name = local(elem.tag)
        if name == "matrix":
            rows, cols = int(elem.get("rows")), int(elem.get("cols"))
            flat = [value(k) for k in elem]
            if cols == 1:  # a column vector -- flat, as this module stores it
                return flat
            # column-major -> row-major
            return [[flat[c * rows + r] for c in range(cols)] for r in range(rows)]
        if name == "str":
            return elem.text
        return float(elem.text)

    out = {}
    for data in root:
        results = [k for r in data for k in r]
        if results:
            out[int(data.get("result-id"))] = value(results[0])
    return out


def _run():
    src = convert_file(REFERENCE, fmt="py")
    echoed: list = []
    ns: dict = {"print": lambda *a: echoed.append(a[0] if len(a) == 1 else a)}
    exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return src, ns, echoed


@pytest.fixture(scope="module")
def sheet():
    return _run()


def _rows(value) -> list:
    """A value in the same canonical form as :func:`_cached`: a matrix is
    row-major nested lists, a column vector a flat list."""
    arr = np.asarray(getattr(value, "magnitude", value), dtype=object)
    if arr.ndim == 0:
        return [arr.item()]
    if arr.ndim == 1:
        return [_scalar(v) for v in arr]
    return [[_scalar(v) for v in row] for row in arr]


def _scalar(v):
    if isinstance(v, np.ndarray):
        return _rows(v)
    if isinstance(v, str):
        return v
    return float(getattr(v, "magnitude", v))


# --- the whole sheet vs the cache -------------------------------------------

# result-id -> the echo's index in reading order. Region 0's cached result is a
# stale leftover (see the module docstring) and has no echo, so it is absent.
_ECHOES = {4: 0, 5: 1, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6, 11: 7,
           12: 8, 13: 9, 14: 10, 15: 11, 16: 12, 17: 13, 18: 14}


def test_every_echo_matches_the_cache(sheet):
    _, _, echoed = sheet
    cached = _cached()
    assert len(echoed) == len(_ECHOES)
    for rid, position in _ECHOES.items():
        expected = cached[rid]
        assert _rows(echoed[position]) == expected, f"result-id {rid}"


# --- row vector vs column vector --------------------------------------------


def test_a_row_literal_is_a_matrix_and_a_column_literal_is_not(sheet):
    src, ns, _ = sheet
    assert "R = matrix(1, 3, 5, 6, 7)" in src
    assert "V = col(1, 2, 3)" in src
    assert np.asarray(ns["R"]).shape == (1, 3)
    assert np.asarray(ns["V"]).shape == (3,)


def test_match_proves_the_distinction_is_mathcads(sheet):
    """The evidence the rule rests on: the same call against a ``3x1`` and a
    ``1x3`` returns a scalar index in one case and an index *pair* in the
    other. Only a matrix has (row, col) positions."""
    _, ns, echoed = sheet
    assert _scalar(echoed[5][0]) == 2.0  # match(3, V) -- a column vector
    assert _scalar(ns["k"][0]) == [0.0, 2.0]  # match(7, R) -- a 1x3 matrix


def test_stack_puts_a_row_header_across_the_top(sheet):
    """The regression. ``S := stack(("A" "B" "C"), s)`` -- the labels are a
    header *row*; as a column they landed down column 0 and every later
    ``matelem`` read a label where a number belonged."""
    _, ns, _ = sheet
    assert _rows(ns["S"])[0] == ["A", "B", "C"]
    assert _rows(ns["S"])[1] == [1.0, 2.0, 3.0]


def test_augment_puts_a_column_header_down_the_side(sheet):
    """The other orientation, which has to keep working: a ``3x1`` label
    literal augmented onto a matrix is a header *column*."""
    _, ns, _ = sheet
    assert [row[0] for row in _rows(ns["W"])] == ["X", "Y", "Z"]
    assert _rows(ns["W"])[0] == ["X", 1.0, 2.0, 3.0]


def test_a_table_labelled_on_both_axes(sheet):
    """``M := augment(("Ø" "X" "Y" "Z")ᵀ, S)`` -- a column of labels onto an
    already row-labelled matrix, the shape ``vhlookup`` reads."""
    _, ns, _ = sheet
    rows = _rows(ns["M"])
    assert rows[0] == ["Ø", "A", "B", "C"]
    assert [r[0] for r in rows] == ["Ø", "X", "Y", "Z"]


# --- transpose moves between the two orientations ---------------------------


def test_transpose_turns_a_row_into_a_column_and_back():
    row = matrix(1, 3, 1.0, 2.0, 3.0)
    assert np.asarray(row).shape == (1, 3)

    column = transpose(row)
    assert np.asarray(column).shape == (3,)  # 1-D: this module's column vector
    assert np.asarray(column).tolist() == [1.0, 2.0, 3.0]

    assert np.asarray(transpose(column)).shape == (1, 3)


def test_transpose_of_a_row_literal_is_a_column_vector():
    """Mathcad's usual way of typing a column vector -- and the reason this
    can't lean on ``np.transpose``, whose 1-D transpose is the identity."""
    import pint

    ureg = pint.UnitRegistry()
    v = transpose(matrix(1, 3, 1.0, 2.0, 3.0) * ureg.mm)
    assert v.magnitude.ndim == 1
    assert v[2].to("mm").magnitude == 3.0


def test_a_genuine_matrix_transposes_normally():
    m = matrix(2, 3, 1, 2, 3, 4, 5, 6)  # column-major
    assert np.asarray(transpose(m)).tolist() == np.asarray(m).T.tolist()


# --- the table searches ------------------------------------------------------


def test_match_scans_a_matrix_column_major(sheet):
    """``s`` holds ``3`` twice, at ``(1,1)`` and ``(0,2)``. Mathcad caches them
    in that order -- which is the column-major scan, not the row-major one."""
    _, ns, _ = sheet
    assert [_scalar(p) for p in ns["ij"]] == [[1.0, 1.0], [0.0, 2.0]]


def test_lookup_reads_the_parallel_matrix(sheet):
    """``lookup(3, s, b)``: both positions of ``3`` in ``s``, read out of
    ``b = 50 + s`` -- so both are 53."""
    _, _, echoed = sheet
    assert _rows(echoed[11]) == [53.0, 53.0]


def test_the_row_and_column_lookups(sheet):
    _, _, echoed = sheet
    assert _rows(echoed[12]) == [1.0]  # vlookup("Y", W, 1)
    assert _rows(echoed[13]) == [5.0]  # hlookup("C", S, 2)
    assert _rows(echoed[14]) == [3.0]  # vhlookup("X", "C", M)


def test_a_search_returns_a_vector_even_for_one_hit(sheet):
    """Mathcad caches every one of these as a ``1x1`` *matrix*, not a scalar --
    a search can match more than once, so the result is always a vector."""
    _, _, echoed = sheet
    for position in (5, 12, 13, 14):
        assert np.asarray(echoed[position]).ndim == 1


def test_a_value_that_is_not_there_raises():
    """An error in Mathcad too -- returning an empty vector would let a typo'd
    label propagate silently."""
    table = matrix(2, 2, 1, 2, 3, 4)
    with pytest.raises(ValueError, match="not found"):
        match(99, table)
    with pytest.raises(ValueError, match="not found"):
        lookup(99, table, table)


def test_a_search_mixing_strings_and_numbers_does_not_raise():
    """A labelled table is heterogeneous by construction, so comparing a string
    cell to a numeric probe has to be plain 'not equal'."""
    labelled = augment(col("X", "Y"), col(1.0, 2.0))
    assert np.asarray(match("Y", labelled)[0]).tolist() == [1.0, 0.0]
    assert match(2.0, labelled)[0].tolist() == [1.0, 1.0]


# --- augment / stack take matrix blocks -------------------------------------


def test_augment_keeps_a_matrix_blocks_columns():
    """The supporting bug: ``augment`` flattened every argument to 1-D, so a
    matrix block collapsed into a single column of all its elements."""
    joined = augment(col("a", "b"), matrix(2, 2, 1, 2, 3, 4))
    assert np.asarray(joined).shape == (2, 3)
    assert _rows(joined) == [["a", 1.0, 3.0], ["b", 2.0, 4.0]]


def test_stack_keeps_a_matrix_blocks_rows():
    joined = stack(matrix(1, 2, "a", "b"), matrix(2, 2, 1, 2, 3, 4))
    assert np.asarray(joined).shape == (3, 2)
    assert _rows(joined) == [["a", "b"], [1.0, 3.0], [2.0, 4.0]]


def test_augment_of_a_single_column_is_a_column_vector():
    """Symmetric with ``stack``: a one-column result is a column vector, 1-D."""
    assert np.asarray(augment(col(1.0, 2.0))).shape == (2,)
