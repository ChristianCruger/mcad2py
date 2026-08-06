"""``RC_col.mcdx`` -- a large reinforced-concrete column check.

This sheet introduces several constructs at once. Stage 1 covers the *leaf*
features (the multi-line imperative programs are Stage 2); this test asserts
them on the generated source and unit-tests the new runtime helpers directly:

  * a **data table** (``<ml:spec-table>``) whose columns become vectors named by
    their headers -- string columns (``LS``) and unit-bearing columns
    (``Fz``/``Fy``/``Fx`` in ``kN``);
  * the ``augment`` builtin (stack column vectors into a matrix);
  * a **bare ``Σ``** over a whole vector (no index bounds) -> ``total``;
  * **column extraction** ``A^<i>`` (``<ml:matcol>``) -> ``matcol``;
  * **matrix multiplication** (Mathcad's ``*`` on matrix operands) -> ``matmul``,
    detected by codegen when both operands are statically matrix-shaped;
  * **multi-target destructuring** ``[a; b; c] := <expr>`` -> tuple unpack;
  * **TextBoxScriptableControl** status widgets: the JScript isn't transpiled,
    but the real boolean expression from the control's ``PiggybackNode`` is
    emitted (with the cached message as a comment);
  * **parametric plots** -- the section outline / rebar scatter / neutral-axis
    lines whose *both* axes are data vectors (plotted point-by-point, no
    ``y = f(domain)`` sampling), with the ``m -> mm`` axis override reduced.

Numeric execute-and-compare against ``result.xml`` for the whole sheet arrives
in Stage 2, once the imperative programs run.
"""

import math
from pathlib import Path

import numpy as np
import pint

from mcad2py.convert import convert_file
from mcad2py.runtime import augment, col, matcol, matmul, matrix, total

REFERENCE = Path(__file__).parent.parent / "references" / "RC_col.mcdx"


def _src() -> str:
    return convert_file(REFERENCE, fmt="py")


# ---------------------------------------------------------------------------
# Runtime helpers (numeric)
# ---------------------------------------------------------------------------


def test_matmul_homogeneous_units():
    u = pint.UnitRegistry()
    # identity @ length-vector -> the vector, unit preserved.
    res = matmul(matrix(2, 2, 1.0, 0.0, 0.0, 1.0), col(3.0 * u.m, 4.0 * u.m))
    assert [float(x) for x in res.to("m").magnitude] == [3.0, 4.0]
    # dimensionless matrix @ length matrix -> length matrix.
    prod = matmul(matrix(2, 2, 1.0, 0.0, 0.0, 2.0), matrix(2, 2, 1.0 * u.m, 0.0 * u.m, 0.0 * u.m, 5.0 * u.m))
    assert prod.units == u.m
    assert prod.magnitude.tolist() == [[1.0, 0.0], [0.0, 10.0]]


def test_matmul_mixed_column_units():
    # augment(ones, Xs_mm) @ [strain; curvature] -> dimensionless strain per row.
    u = pint.UnitRegistry()
    dl = u.dimensionless
    M = augment(col(1.0 * dl, 1.0 * dl, 1.0 * dl), col(10.0 * u.mm, 20.0 * u.mm, 30.0 * u.mm))
    strain = matmul(M, col(0.001 * dl, 0.0001 / u.mm))
    got = [float(x.to("dimensionless").magnitude) for x in strain]
    assert got == [0.002, 0.003, 0.004]


def test_total_sums_vector_elements():
    u = pint.UnitRegistry()
    assert math.isclose(total(col(1.0 * u.kN, 2.0 * u.kN, 3.0 * u.kN)).to("kN").magnitude, 6.0)
    # mixed-but-compatible units add correctly.
    assert math.isclose(total(col(1.0 * u.m, 200.0 * u.cm)).to("m").magnitude, 3.0)
    assert total(col(2.0, 5.0, 8.0)) == 15.0


def test_matcol_extracts_column():
    u = pint.UnitRegistry()
    m = matrix(2, 2, 1.0 * u.m, 0.0 * u.m, 3.0 * u.m, 4.0 * u.m)  # column-major
    assert matcol(m, 0).to("m").magnitude.tolist() == [1.0, 0.0]
    assert matcol(m, 1).to("m").magnitude.tolist() == [3.0, 4.0]


def test_augment_builds_matrix_usable_by_matmul():
    u = pint.UnitRegistry()
    M = augment(col(1.0, 2.0), col(3.0, 4.0))  # 2x2, columns [1,2] and [3,4]
    assert M.shape == (2, 2)
    res = matmul(M, col(1.0, 0.0))  # first column
    assert [float(x) for x in np.atleast_1d(res)] == [1.0, 2.0]


# ---------------------------------------------------------------------------
# Generated source (leaf features)
# ---------------------------------------------------------------------------


def test_data_table_columns_named_by_header():
    src = _src()
    # String column -> a clean col() of strings (no `* None` placeholder-unit).
    assert "LS = col('ULS', 'ULS', 'ULS', 'ULS', 'ALS'" in src
    assert "* None  # placeholder" not in src
    # Unit-bearing columns keep their unit (kN).
    assert "Fz = col(1819, 1853, 1850, 1822, 2669, 3036, 8041" in src
    assert "* ureg.kN" in src
    assert "Fx = col(0, 0, 0, 0, 0, 0, 776, 805, 0, 0, 0, 0) * ureg.kN" in src


def test_augment_matmul_matcol_total_emitted():
    src = _src()
    assert "augment(ones(n), X_s, Y_s)" in src
    # A genuine matrix product (both operands matrix literals) -> matmul.
    assert "matmul(matrix(5, 2," in src
    assert "matmul(augment(ones(n), X_s, Y_s), col(e, kx, ky))" in src
    # Column extraction A^<i>.
    assert "matcol(Contour, 0)" in src
    # Bare Sigma over a vector -> total().
    assert "total(F_ci(e, kx, ky))" in src


def test_elementwise_product_stays_star_not_matmul():
    # A product of two function-call vectors under vectorize is element-wise,
    # not a matrix product (only statically matrix-shaped operands -> matmul).
    src = _src()
    assert "vectorize(F_ci(e, kx, ky) * Y_c)" in src


def test_multi_target_destructuring():
    src = _src()
    assert "e, kx, ky = tuple(" in src


def test_textbox_status_control_prints_expr_value_and_message():
    src = _src()
    # Each status widget prints the expression source, its live value, and the
    # cached message (the JScript that maps value -> message isn't transpiled).
    assert (
        "print('mc_max(UR_c_max, UR_s_max) < 1', "
        "mc_max(UR_c_max, UR_s_max) < 1, 'All loadcases pass!')" in src
    )
    assert "print('ERR == 0', ERR == 0, 'Solved without errors')" in src


def test_no_unsupported_regions():
    # With the Stage 2 imperative-program engine, the whole sheet converts with
    # no ``# TODO unsupported`` markers left.
    assert "TODO unsupported" not in _src()


# ---------------------------------------------------------------------------
# Stage 2: imperative programs (generated source)
# ---------------------------------------------------------------------------


def test_imperative_program_constructs_emitted():
    src = _src()
    # The coordinate builder: a nullary helper with for-loops and growable
    # ``vec_set`` writes, destructured into [Xs; Ys; n].
    assert "def _X_s_Y_s_n():" in src
    assert "X_s, Y_s, n = tuple(_X_s_Y_s_n())" in src
    assert "for i in arange(0, n_s[0], 1):" in src
    assert "X = vec_set(X, j, " in src
    # A function-bodied program keeps its parameters.
    assert "def Neutral(e, kx, ky):" in src
    # The loadcase loop's tryCatch -> try/except with an early return.
    assert "try:" in src and "except Exception:" in src
    # 2-D element assignment inside Neutral (Ans[j, 0]).
    assert "vec_set(Ans, (j, 0)" in src or "vec_set(Ans, (j, " in src


def test_solve_block_defines_function():
    # solve_strain(N, Mx, My) := find(e, kx, ky) -> a def wrapping solve_block.
    assert "def solve_strain(N, Mx, My):" in _src()


# ---------------------------------------------------------------------------
# Stage 2: whole sheet executes and matches result.xml
# ---------------------------------------------------------------------------


def _dimensionless(x):
    """Reduce an (unreduced) dimensionless Pint quantity to a plain float."""
    return float(x.to("dimensionless").magnitude)


def _exec_full():
    # Execute the sheet's computation only. The plots render fine now (see
    # ``test_parametric_plots_render``), but the numeric tests strip them so they
    # stay fast and don't depend on a matplotlib backend.
    out, skip = [], False
    for line in _src().splitlines():
        s = line.strip()
        if s.startswith("_fig") or s.startswith("_X, _Y, _Z"):
            skip = True
        if skip:
            if s == "plt.show()":
                skip = False
            continue
        out.append(line)
    ns: dict = {}
    exec(compile("\n".join(out), "<rc-col>", "exec"), ns)  # noqa: S102
    return ns


def test_whole_sheet_runs_and_matches_cache():
    ns = _exec_full()
    # Coordinate builder: 12 rebars around the section perimeter.
    assert ns["n"] == 12
    assert len(ns["X_s"]) == 12
    # The 12-loadcase solve loop (tryCatch/for/if/return) recovers Mathcad's
    # cached governing utilisations and indices (result.xml: [0.18899, 7,
    # 0.012134, 0], ERR = 0).
    assert int(ns["ERR"]) == 0
    assert int(ns["i_c"]) == 7 and int(ns["i_s"]) == 0
    assert math.isclose(_dimensionless(ns["UR_c_max"]), 0.1889903785884624, rel_tol=1e-6)
    assert math.isclose(_dimensionless(ns["UR_s_max"]), 0.012134498087164845, rel_tol=1e-6)


def test_solve_strain_converges_to_cached_strain():
    ns = _exec_full()
    # solve_strain for loadcase 0 -> cached [e, kx, ky] (result.xml).
    e = ns["solve_strain"](ns["N"][0], ns["M_x"][0], ns["M_y"][0])
    assert math.isclose(_dimensionless(e[0]), 0.00034938711653112296, rel_tol=1e-5)
    assert math.isclose(e[1].to("1/m").magnitude, -7.3703711589287436e-05, rel_tol=1e-5)
    assert math.isclose(e[2].to("1/m").magnitude, -0.0012002546268561896, rel_tol=1e-5)


def test_min_reinforcement_is_scalar_not_vector():
    # A_smin = max(vectorize(0.1·(-N))/f_yd, 0.002·A_c): Mathcad's max flattens
    # the vector argument and reduces to a scalar (not an element-wise vector).
    ns = _exec_full()
    assert getattr(ns["A_smin"], "shape", ()) == ()


# ---------------------------------------------------------------------------
# Parametric plots (section outline / rebar scatter / neutral axis)
# ---------------------------------------------------------------------------


def test_parametric_plots_emit_direct_axes():
    # A parametric plot's axes are data vectors plotted point-by-point -- no
    # ``sample(lambda ...)`` domain wrapping (that's only for ``y = f(range)``).
    src = _src()
    assert (
        "plot_trace(plot_axis(matcol(Contour, 0), ureg.mm), "
        "plot_axis(matcol(Contour, 1), ureg.mm)" in src
    )
    assert "plot_trace(plot_axis(X_s, ureg.mm), plot_axis(Y_s, ureg.mm)" in src
    # The rebar/outline vectors are *not* re-sampled over a bogus domain.
    assert "sample(lambda X_s:" not in src


def test_parametric_plots_render_with_section_geometry():
    import matplotlib.pyplot as plt

    plt.close("all")
    exec(compile(_src(), "<rc-col-plots>", "exec"), {})  # noqa: S102

    # Collect every real data trace (skip the axhline/axvline guides).
    traces = {
        ln.get_label(): ln
        for fn in plt.get_fignums()
        for ax in plt.figure(fn).axes
        for ln in ax.get_lines()
        if len(ln.get_xdata()) > 2
    }
    assert plt.get_fignums()  # figures were created

    # The concrete section outline: a closed rectangle at +/-650 mm.
    outline = traces["matcol(Contour, 0)"]
    assert len(outline.get_xdata()) == 5  # 4 corners + closing point
    assert math.isclose(float(np.max(np.abs(outline.get_xdata()))), 650.0, rel_tol=1e-6)
    assert math.isclose(float(np.max(np.abs(outline.get_ydata()))), 650.0, rel_tol=1e-6)

    # The 12 rebars sit at +/-583 mm (not normalized to +/-1: the m->mm axis
    # override must reduce, else the outline would read +/-0.65).
    rebars = traces["X_s"]
    assert len(rebars.get_xdata()) == 12
    assert math.isclose(float(np.max(np.abs(rebars.get_xdata()))), 583.0, rel_tol=1e-3)
    plt.close("all")
