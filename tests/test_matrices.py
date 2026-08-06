"""Tests for the vector & matrix function family.

``matrices.mcdx`` is a catalogue sheet: it walks Mathcad's whole "Vector and
Matrix" category (shape, linear algebra, norms/conditions, eigen/singular
values, ordering, predicates) plus the four bar/row/cross *operators*, then
finishes with three worked examples (down-sampling, left/right eigenvectors, and
a principal-component analysis). The whole sheet runs end to end here and every
echoed region is matched against Mathcad's cached ``result.xml``.

Three things beyond "the name resolves" are exercised:

* **which ``·`` is a matrix product** -- Mathcad spells scalar, matrix and dot
  products identically, so `mcad2py.shapes` infers each name's shape across the
  sheet and rewrites only the array ones (``M·A`` -> ``matmul``, while
  ``2·identity(4)``, ``λ·R`` and ``M·kg`` stay ``*``);
* **the two-subscript forms** -- ``M[i, j]`` reads (``matelem``, which also
  copes with the 1-D arrays we store row/column vectors as) and ``X[i, j] :=``
  writes (``index_build_2d``, over the two ranges' outer product), plus the
  column-major ``[a b; c d] := M`` destructuring;
* **what LAPACK does and does not reproduce** -- eigen*values* match Mathcad
  exactly but not always in its order, and eigen*vector* signs are arbitrary, so
  those are checked as a set and by their defining equation rather than
  component by component.
"""

import math
import re

import numpy as np
import pint
import pytest

from conftest import flat, reference, run_sheet
from mcad2py.runtime import (
    arange,
    col,
    cross,
    csort,
    determinant,
    index_build,
    matelem,
    matrix,
    matrow,
    norm,
    rows,
    rsort,
    sort,
    stack,
    submatrix,
    tr,
    unpack,
)

REFERENCE = reference("matrices")

# Mathcad's cached results (result.xml), keyed by the index of the echo that
# produces them (regions are echoed in reading order). Matrices are listed
# **column-major**, the order both Mathcad's cache and ``<ml:matrix>`` use.
#
# Left out and covered by their own tests below: the 201-element down-sampling
# vectors, the 26x3 PCA matrices, and everything whose value depends on LAPACK's
# eigen ordering or eigenvector signs.
CACHED = {
    0: ("C := M·A", [10, 18, 22, 20]),
    1: ("B·C (row × column -> a scalar)", 112),
    2: ("diag(M)", [3, 3, 3, 3]),
    3: ("last(A)", 3),
    4: ("length(A)", 4),
    5: ("MM := M + 2·identity(4)", [5, 2, 1, 0, 2, 5, 2, 1, 1, 2, 5, 2, 0, 1, 2, 5]),
    6: ("AA := augment(A, A, A)", [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4]),
    7: ("cols(A)", 1),
    8: ("rows(A)", 4),
    9: ("col0 := M^<0>", [3, 2, 1, 0]),
    10: ("row1 := row(M, 1)", [2, 3, 2, 1]),
    11: ("M[1, 3]", 1),
    12: ("A[1]", 2),
    13: ("B[0, 2] (a 1×4 row)", 2),
    14: ("A[1, 0] (a 4×1 column)", 2),
    15: ("det(M)", 12),
    16: ("min(M)", 0),
    17: ("max(M)", 3),
    18: ("tr(MM)", 20),
    19: ("Σ diag(MM)", 20),
    20: ("M2 := matrix(3, 3, f), f(x, y) = x² − y", [0, 1, 4, -1, 0, 3, -2, -1, 2]),
    21: (
        "e := eigenvals(M)",
        [
            7.16227766016838,
            3.4142135623730954,
            0.83772233983162048,
            0.58578643762690452,
        ],
    ),
    22: (
        "eigenvec(M, e[0])",
        [
            0.41345260731526473,
            0.573634850322232,
            0.57363485032223194,
            0.41345260731526473,
        ],
    ),
    24: (
        "x := lsolve(M, A)",
        [
            0.33333333333333326,
            1.3322676295501878e-16,
            -1.3877787807814459e-16,
            1.3333333333333335,
        ],
    ),
    25: ("M·x (recovers A)", [0.99999999999999989, 2, 3, 4]),
    26: ("norm(x)", 1.3743685418725538),
    27: ("m := submatrix(MM, 2, 3, 2, 3)", [5, 2, 2, 5]),
    28: ("transpose(A)", [1, 2, 3, 4]),
    29: ("transpose(M)", [3, 2, 1, 0, 2, 3, 2, 1, 1, 2, 3, 2, 0, 1, 2, 3]),
    30: ("|A| on a vector -> its magnitude", 5.4772255750516612),
    31: ("|M| on a matrix -> its determinant", 12),
    32: (
        "vectorize(M + 10)",
        [13, 12, 11, 10, 12, 13, 12, 11, 11, 12, 13, 12, 10, 11, 12, 13],
    ),
    33: ("norm1(M)", 8),
    34: ("cond1(M)", 16.000000000000007),
    35: ("norm2(M)", 7.16227766016838),
    36: ("cond2(M)", 12.226772762414356),
    37: ("norme(M)", 8),
    38: ("conde(M)", 16.865480854231361),
    39: ("normi(M)", 8),
    40: ("condi(M)", 16.000000000000004),
    41: ("c := a × b", [-1, 1, -1]),
    42: (
        "Mi := geninv(M)",
        [
            0.66666666666666674, -0.5, 0.0, 0.16666666666666666,
            -0.49999999999999994, 1.0, -0.49999999999999967, -1.1102230246251565e-16,
            -5.5511151231257827e-17, -0.49999999999999978, 0.99999999999999978, -0.5,
            0.16666666666666657, -1.6653345369377348e-16, -0.49999999999999978,
            0.66666666666666674,
        ],
    ),
    43: (
        "Mi·A",
        [0.333333333333333, 0.0, 6.6613381477509392e-16, 1.3333333333333335],
    ),
    44: ("rank(M)", 4),
    45: ("rref(M)", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
    50: ("length(v)", 201),
    51: ("j := 0 .. (length(v) − 1)/28", [0, 1, 2, 3, 4, 5, 6, 7]),
    52: (
        "u[j] := v[n·j] (the down-sampled signal)",
        [
            0.0, -0.70710678118654768, -1.0, -0.70710678118654768,
            8.5722444767566408e-16, 0.70710678118654891, 1.0, 0.70710678118654458,
        ],
    ),
    54: ("range2[j] := j·n", [0, 28, 56, 84, 112, 140, 168, 196]),
    55: ("V := eigenvals(A)", [4, -3]),
    56: ("λ_0 := V[0]", 4),
    57: ("λ_1 := V[1]", -3),
    58: (
        "R := eigenvecs(A, \"R\")",
        [
            0.89442719099991586, 0.44721359549995793,
            -0.316227766016838, 0.94868329805051388,
        ],
    ),
    59: ("R_0 := R^<0>", [0.89442719099991586, 0.44721359549995793]),
    60: ("R_1 := R^<1>", [-0.316227766016838, 0.94868329805051388]),
    61: ("A·R_0", [3.5777087639996634, 1.7888543819998319]),
    62: ("λ_0·R_0 (same eigenpair)", [3.5777087639996634, 1.7888543819998317]),
    63: ("A·R_1", [0.94868329805051377, -2.846049894151542]),
    64: ("λ_1·R_1", [0.948683298050514, -2.8460498941515415]),
    65: (
        "L := eigenvecs(A, \"L\")",
        [
            0.94868329805051388, 0.316227766016838,
            -0.44721359549995793, 0.89442719099991586,
        ],
    ),
    66: ("L_0 := L^<0>", [0.94868329805051388, 0.316227766016838]),
    67: ("L_1 := L^<1>", [-0.44721359549995793, 0.89442719099991586]),
    68: ("L_0ᵀ·A", [3.7947331922020555, 1.2649110640673518]),
    69: ("λ_0·L_0ᵀ", [3.7947331922020555, 1.264911064067352]),
    70: ("L_1ᵀ·A", [1.3416407864998738, -2.6832815729997477]),
    71: ("λ_1·L_1ᵀ", [1.3416407864998738, -2.6832815729997477]),
    72: ("i := 0 .. rows(D) − 1", list(range(26))),
    73: ("j := 0 .. cols(D) − 1", [0, 1, 2]),
    75: (
        "S1 := Xᵀ·X / (rows(D) − 1) -- the sample covariance",
        [
            1.2938461538461539, 1.9484615384615387, 0.63769230769230767,
            1.9484615384615387, 2.9896153846153832, 0.99692307692307691,
            0.63769230769230767, 0.99692307692307691, 0.43538461538461531,
        ],
    ),
    76: (
        "V := reverse(sort(eigenvals(S1)))",
        [4.6027104710592646, 0.10124936041228062, 0.014886322374608265],
    ),
    83: (
        "S2 -- the transformed data's covariance, diagonal = the components",
        [
            4.602710471059261, 1.3322676295501878e-17, 3.7192471324942745e-16,
            2.2204460492503132e-17, 0.10124936041228055, -1.2878587085651815e-16,
            3.7192471324942745e-16, -1.2878587085651815e-16, 0.014886322374609013,
        ],
    ),
    84: ("IsScalar(S2)", 0),
    85: ("IsArray(S2)", 1),
    86: ("IsScalar(α)", 1),
    87: ("IsArray(α)", 0),
    92: ("norm1(M) -- the 3×3", 17),
    93: ("ACS_0 = |a_0| + |b_0| + |c_0| (column 0's absolute sum)", 13),
    94: ("ACS_1", 9),
    95: ("ACS_2", 17),
    96: ("N_L1 := max(ACS_0, ACS_1, ACS_2) == norm1(M)", 17),
    97: ("norm2(M)", 14.841898441682646),
    98: ("svds(M)", [14.841898441682643, 5.0979132482619631, 1.6520687515879497]),
    99: ("norme(M)", 15.7797338380595),
    100: ("N_e -- √Σ|M_ij|², the same by hand", 15.7797338380595),
    101: ("normi(M)", 22),
    102: ("ARS_0 = |a_0| + |a_1| + |a_2| (row 0's absolute sum)", 8),
    103: ("ARS_1", 22),
    104: ("ARS_2", 9),
    105: ("N_i := max(ARS_0, ARS_1, ARS_2) == normi(M)", 22),
    106: ("det(M)", 125),
    107: ("DET -- the same by cofactor expansion", 125),
    108: ("v := [a_0; b_0; c_0] (column 0 of M)", [1, 9, 3]),
    109: ("norm(v)", 9.5393920141694561),
    110: ("N -- √(a_0² + b_0² + c_0²), the same by hand", 9.5393920141694561),
}

# The sheet's two eigen-heavy echoes whose *order* is LAPACK's, not Mathcad's.
CACHED_EIGENVALS_M6 = [
    40.2738602172717,
    0.29793145505300023 + 0.1480217438362581j,
    0.29793145505300023 - 0.1480217438362581j,
    -0.15865723254089995,
    -0.34300443777379042,
    -1.8680614570630329,
]
CACHED_EIGENVALS_N6 = [
    39.126331221491895,
    0.752106543052555 + 1.7021799687892165j,
    0.752106543052555 - 1.7021799687892165j,
    -0.0028796808393989977,
    -2.0638323133724869 + 1.4098060094306633j,
    -2.0638323133724869 - 1.4098060094306633j,
]
CACHED_GENVALS = [
    285.56763307828948,
    1.1662423654732683,
    0.85948195692044149,
    0.029211868540474847,
    -0.0959196631536033,
    -0.23177781124980759,
]
# The three principal components of the PCA example (S2's diagonal).
CACHED_COMPONENTS = [4.6027104710592646, 0.10124936041228062, 0.014886322374608265]


@pytest.fixture(scope="module")
def sheet():
    return run_sheet(REFERENCE)


# ---------------------------------------------------------------------------
# Whole-sheet: every echoed region vs. Mathcad's cache
# ---------------------------------------------------------------------------


def test_sheet_runs_end_to_end(sheet):
    """No region is dropped or unsupported, and each one echoes exactly once."""
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == 111


def test_catalogue_matches_cached_results(sheet):
    """Every deterministic echo reproduces Mathcad's cached value."""
    _, _, echoed = sheet
    for index, (label, expected) in CACHED.items():
        got = flat(echoed[index])
        want = np.atleast_1d(np.asarray(expected, dtype=float))
        assert got.shape == want.shape, f"echo {index} ({label}): shape {got.shape}"
        assert np.allclose(got, want, rtol=1e-12, atol=1e-14), (
            f"echo {index} ({label}): {got} != {want}"
        )


def test_united_results_keep_their_units(sheet):
    """``[a1 b1 …] := M·kg`` and ``ti[i] := i/fs`` carry Mathcad's units."""
    _, _, echoed = sheet
    assert math.isclose(echoed[46].to("kg").magnitude, 3.0)   # b2 = M[1, 1]·kg
    assert math.isclose(echoed[47].to("kg").magnitude, 2.0)   # d3 = M[3, 2]·kg
    ti = echoed[48].to("s").magnitude                          # i / (16 Hz)
    assert len(ti) == 201
    assert math.isclose(ti[1], 0.0625) and math.isclose(ti[-1], 12.5)


def test_down_sampling_example(sheet):
    """The 201-point sine and the index ranges built over it."""
    _, ns, echoed = sheet
    v = flat(echoed[49])
    assert len(v) == 201
    assert math.isclose(v[1], 0.19509032201612825, rel_tol=1e-12)
    assert math.isclose(v[-1], 1.0, rel_tol=1e-12)
    assert list(flat(echoed[53])) == list(range(201))         # range1[i] := i
    # v[n·j] must be an *integer* index even though j's range stops at 7.14…
    assert np.issubdtype(np.asarray(ns["j"]).dtype, np.integer)


def test_centered_data_matrix_is_built_over_both_ranges(sheet):
    """``X[i, j] := D[i, j] − mean(D^<j>)`` builds the whole 26×3 matrix."""
    _, ns, echoed = sheet
    X = np.asarray(echoed[74], dtype=float)
    assert X.shape == (26, 3)
    assert math.isclose(X[0, 0], 1.5769230769230766, rel_tol=1e-12)
    assert math.isclose(X[25, 2], -0.34615384615384581, rel_tol=1e-12)
    # Centering means every column now has zero mean.
    assert np.allclose(X.mean(axis=0), 0.0, atol=1e-13)


# ---------------------------------------------------------------------------
# Eigen results: what LAPACK reproduces and what it cannot
# ---------------------------------------------------------------------------


def test_eigenvalues_match_the_cache_as_a_set(sheet):
    """Mathcad and LAPACK agree on the spectrum but not always on its order.

    For the symmetric matrices earlier in the sheet the order matches too (see
    ``CACHED[21]``/``CACHED[55]``); for these general 6×6s -- and for the
    generalized problem -- it does not, so only the multiset is asserted.

    The tolerance is looser than the rest of the sheet's for the same reason:
    these are *nonsymmetric* eigenproblems with clustered complex pairs, where
    the last few digits are the LAPACK build's, not the algorithm's (the
    ``N`` sheet's ``-2.0638 ± 1.4098i`` pair agrees to ~5e-9 absolute).
    """
    _, _, echoed = sheet

    def sorted_key(values):
        return sorted(
            np.asarray(values).reshape(-1),
            key=lambda z: (round(complex(z).real, 6), round(complex(z).imag, 6)),
        )

    for index, want in (
        (88, CACHED_EIGENVALS_M6),
        (89, CACHED_EIGENVALS_N6),
        (90, CACHED_GENVALS),
    ):
        assert np.allclose(
            sorted_key(echoed[index]), sorted_key(want), rtol=1e-8, atol=1e-8
        ), f"echo {index}"


def test_eigenvectors_satisfy_their_defining_equation(sheet):
    """Eigenvector *signs* are arbitrary, so check the property, not the digits.

    ``eigenvecs`` columns are unit-length right (``A·v = λ·v``) or left
    (``vᵀ·A = λ·vᵀ``) eigenvectors; ``eigenvec(M, λ)`` picks out one of them.
    """
    from mcad2py.runtime import eigenvals, eigenvec

    _, ns, _ = sheet
    # ``A`` is the sheet's 2×2 example; its eigenvalues are recomputed rather
    # than read from ``V``, which the PCA example further down rebinds.
    A, R, L = ns["A"], ns["R"], ns["L"]
    lambdas = eigenvals(A)
    for j in range(2):
        assert np.allclose(A @ R[:, j], lambdas[j] * R[:, j])
        assert np.allclose(L[:, j] @ A, lambdas[j] * L[:, j])
        assert math.isclose(float(np.linalg.norm(R[:, j])), 1.0)

    S1 = ns["S1"]  # the PCA covariance matrix, where the sheet uses eigenvec
    for lam in eigenvals(S1):
        vec = eigenvec(S1, lam)
        assert np.allclose(S1 @ vec, lam * vec, atol=1e-10)
        assert math.isclose(float(np.linalg.norm(vec)), 1.0)


def test_pca_recovers_the_cached_principal_components(sheet):
    """The transform matrix's column signs are arbitrary, but the components
    the analysis exists to produce -- ``S2``'s diagonal -- are not."""
    _, ns, _ = sheet
    diagonal = np.diag(np.asarray(ns["S2"], dtype=float))
    assert np.allclose(diagonal, CACHED_COMPONENTS, rtol=1e-9)


# ---------------------------------------------------------------------------
# The emitted source: which ``·`` became a matrix product, and the new forms
# ---------------------------------------------------------------------------


def test_array_products_become_matmul(sheet):
    """Mathcad's ``·`` is rewritten to ``matmul`` exactly when both operands
    are arrays -- which needs the sheet-wide shape inference, since ``M`` and
    ``A`` are plain names at the point of use."""
    src, _, _ = sheet
    assert "C = matmul(M, A)" in src                    # matrix × vector
    assert "print(matmul(B, C))" in src                 # row × column -> scalar
    assert "matmul(transpose(L_0), A)" in src           # vectorᵀ × matrix
    assert "S1 = matmul(transpose(X), X) / (rows(D) - 1)" in src


def test_scalar_products_stay_elementwise(sheet):
    """A scalar (or a unit) on either side keeps the ordinary ``*``."""
    src, _, _ = sheet
    assert "MM = M + 2 * identity(4)" in src            # scalar × matrix
    assert "print(lambda__0 * R_0)" in src              # eigenvalue × vector
    assert "tuple(unpack(M * ureg.kg))" in src          # matrix × unit
    assert "print(vectorize(M + 10))" in src            # under the arrow


def test_two_subscript_forms(sheet):
    """Reads go through ``matelem``; the ``X[i, j] :=`` write builds a matrix."""
    src, _, _ = sheet
    assert "elemM13 = matelem(M, 1, 3)" in src
    assert "elemB2 = matelem(B, 0, 2)" in src           # a 1×4 row, stored 1-D
    assert (
        "X = index_build_2d(i, j, lambda i, j: matelem(D, i, j) - mean(matcol(D, j)))"
        in src
    )


def test_bar_row_and_cross_operators(sheet):
    """Prime's ``|x|`` comes in two flavours, plus the row and cross operators."""
    src, _, _ = sheet
    assert "print(determinant(A))" in src               # bars on an array
    assert "ACS_0 = abs(a_0) + abs(b_0) + abs(c_0)" in src  # bars on scalars
    assert "row1 = matrow(M, 1)" in src
    assert "c = cross(a, b)" in src


def test_matrix_builtin_fills_from_a_function(sheet):
    """``matrix(m, n, f)`` shares its spelling with the literal builder."""
    src, _, _ = sheet
    assert "M2 = matrix(3, 3, f)" in src
    assert re.search(r"^f = lambda x, y: x\*\*2 - y$", src, re.M)


# ---------------------------------------------------------------------------
# Runtime helpers, directly
# ---------------------------------------------------------------------------


def test_unpack_flattens_column_major():
    """``[a b; c d] := M`` lists its targets column by column."""
    m = matrix(2, 2, 1, 2, 3, 4)  # columns [1, 2] and [3, 4]
    assert list(unpack(m)) == [1, 2, 3, 4]
    assert list(unpack(col(7, 8, 9))) == [7, 8, 9]  # a vector passes through


def test_matelem_handles_a_vector_stored_1d():
    """Row and column vectors are both 1-D here, so one subscript is always 0."""
    column, row = col(10, 20, 30), col(10, 20, 30)
    assert matelem(column, 1, 0) == 20   # 3×1: the row index selects
    assert matelem(row, 0, 2) == 30      # 1×3: the column index selects
    assert matelem(matrix(2, 2, 1, 2, 3, 4), 0, 1) == 3


def test_shape_helpers_treat_a_vector_as_a_column():
    assert rows(col(1, 2, 3)) == 3
    assert rows(matrix(2, 3, 1, 2, 3, 4, 5, 6)) == 2


def test_determinant_operator_dispatches_on_shape():
    """Mathcad's bars: determinant of a matrix, magnitude of a vector."""
    assert math.isclose(determinant(matrix(2, 2, 1, 2, 3, 4)), -2.0)
    assert math.isclose(determinant(col(3, 4)), 5.0)


def test_linear_algebra_helpers_keep_units_where_they_are_meaningful():
    ureg = pint.UnitRegistry()
    v = col(3 * ureg.m, 4 * ureg.m)
    assert math.isclose(norm(v).to("m").magnitude, 5.0)
    m = matrix(2, 2, 1 * ureg.m, 0 * ureg.m, 0 * ureg.m, 2 * ureg.m)
    assert math.isclose(tr(m).to("m").magnitude, 3.0)
    assert sort(col(3 * ureg.m, 1 * ureg.m)).to("m").magnitude.tolist() == [1.0, 3.0]
    assert submatrix(m, 0, 0, 0, 1).to("m").magnitude.tolist() == [[1.0, 0.0]]
    assert matrow(m, 1).to("m").magnitude.tolist() == [0.0, 2.0]


def test_cross_product_multiplies_the_units():
    ureg = pint.UnitRegistry()
    arm = col(3 * ureg.m, 0 * ureg.m, 0 * ureg.m)
    force = col(0 * ureg.N, 2 * ureg.N, 0 * ureg.N)
    moment = cross(arm, force)  # r × F, about the third axis
    assert moment.to("N*m").magnitude.tolist() == [0.0, 0.0, 6.0]


def test_stack_and_sorts():
    stacked = stack(col(1, 2), matrix(2, 2, 3, 4, 5, 6))
    assert np.asarray(stacked, dtype=float).tolist() == [[1, 0], [2, 0], [3, 5], [4, 6]]
    unsorted = matrix(2, 2, 2.0, 1.0, 30.0, 10.0)  # rows [2, 30] and [1, 10]
    assert csort(unsorted, 0).tolist() == [[1.0, 10.0], [2.0, 30.0]]
    assert rsort(unsorted, 0).tolist() == [[2.0, 30.0], [1.0, 10.0]]


def test_arange_stays_integral_when_only_the_endpoint_is_fractional():
    """``j := 0 .. 200/28`` runs 0…7 and is still usable as an index."""
    j = arange(0, 200 / 28, 1)
    assert np.issubdtype(j.dtype, np.integer)
    assert j.tolist() == [0, 1, 2, 3, 4, 5, 6, 7]


def test_index_build_accepts_vector_elements():
    """``x[j] := eigenvec(S, V[j])`` builds a vector *of* vectors."""
    built = index_build(np.arange(3), lambda k: col(k, k + 1))
    assert len(built) == 3
    assert list(built[2]) == [2, 3]
