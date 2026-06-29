"""Tests for vectors, indexing, programs (if/else), and the vectorize 'arrow'.

``Xsection_solver.mcdx`` defines NumPy/Pint vectors (``Ø``, ``z_s``, ``s``,
``A_s``), a piecewise stress function ``σ_c`` (a Mathcad program -> a Python
``def``), element-wise ``min``/``max`` clamps (``σ_s``), and uses the
element-wise 'arrow' (vectorize) on ``A_s`` and ``F_s``.

We execute the generated module up to ``F_s`` (later regions use not-yet-
supported integrals) and compare to Mathcad's cached ``result.xml``.
"""

import math
from pathlib import Path

import numpy as np

from mcad2py import ir
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.loader import load_mcdx

REFERENCE = Path(__file__).parent.parent / "references" / "Xsection_solver.mcdx"

# Mathcad's cached results (result.xml), in SI base units.
Z_S_M = [0.175, -0.16249999999999998]            # z_s, metres
A_S_MM2 = [0.0, 3272.4923474893685]              # A_s, mm**2

# The solve block's cached find(e, k) output, and the N_int/M_int checks it
# feeds. The solve block itself isn't supported yet, so we inject e_1/k_1.
E_1 = 0.00078313833636410655                     # strain, dimensionless
K_1 = -0.0059352913987688214                     # curvature, 1/m
N_INT_KN = -499.99999999999955                   # N_int(e_1, k_1)
M_INT_KNM = -530.00000000000011                  # M_int(e_1, k_1)


def _exec_head() -> dict:
    """Execute the generated .py up to the first unsupported region."""
    src = convert_file(REFERENCE, fmt="py")
    head = src[: src.index("# Internal forces:")]
    ns: dict = {}
    exec(compile(head, "<generated>", "exec"), ns)  # noqa: S102
    return ns


def test_vectors_match_mathcad():
    ns = _exec_head()
    ureg = ns["ureg"]
    z_s = ns["z_s"].to("m").magnitude
    a_s = ns["A_s"].to(ureg.mm**2).magnitude
    for got, expected in zip(z_s, Z_S_M):
        assert math.isclose(got, expected, rel_tol=1e-12)
    for got, expected in zip(a_s, A_S_MM2):
        assert math.isclose(got, expected, rel_tol=1e-12, abs_tol=1e-15)


def test_vector_len_and_indexing():
    ns = _exec_head()
    assert ns["n"] == 2  # n = length(Ø) -> len(Ø)
    # z_s uses Ø[0]/Ø[1] indexing; first layer (Ø[0]=0) -> 175 mm.
    assert math.isclose(ns["z_s"].to("mm").magnitude[0], 175.0, rel_tol=1e-12)


def test_program_emits_def_and_branches():
    src = convert_file(REFERENCE, fmt="py")
    # A Mathcad program becomes a real def (preserving if/elif/else), not a lambda.
    assert "def sigma_c(e):" in src
    ns = _exec_head()
    sigma_c, ureg = ns["sigma_c"], ns["ureg"]
    assert math.isclose(sigma_c(-0.0025).to("MPa").magnitude, -45.0)   # e < epsilon_c2
    assert math.isclose(sigma_c(-0.001).to("MPa").magnitude, -33.75)   # elif e < 0
    assert sigma_c(0.001).to("MPa").magnitude == 0.0                   # else


def test_minmax_clamp_is_elementwise():
    ns = _exec_head()
    ureg = ns["ureg"]
    sigma_s = ns["sigma_s"]
    strain = ureg.Quantity(np.array([-0.01, 0.001, 0.0]), "")
    out = sigma_s(strain).to("MPa").magnitude  # f_yd = 500 MPa
    assert list(out) == [-500.0, 200.0, 0.0]


def test_vectorized_function_of_array():
    """F_s applies a scalar clamp over the layer vector, element-wise."""
    ns = _exec_head()
    ureg = ns["ureg"]
    forces = ns["F_s"](-0.001, 0.0 * ureg("1/mm")).to("kN").magnitude
    # layer 0 has Ø=0 -> A_s=0 -> 0 force; layer 1: A_s * (E_s*-0.001).
    assert math.isclose(forces[0], 0.0, abs_tol=1e-12)
    assert math.isclose(forces[1], -654.4984694978736, rel_tol=1e-9)


def test_vectorize_wrapper_emitted():
    src = convert_file(REFERENCE, fmt="py")
    assert "from mcad2py.runtime import col, vectorize" in src
    assert "A_s = vectorize(" in src
    assert "import numpy as np" in src


def test_range_emits_arange():
    ns = _exec_head()
    e_plot = np.asarray(ns["e_plot"])
    # start, next .. stop  =>  -0.0035, step 5e-5, inclusive of 0.001.
    assert math.isclose(e_plot[0], -0.0035, rel_tol=1e-12)
    assert math.isclose(e_plot[1] - e_plot[0], 5e-5, rel_tol=1e-9)
    assert e_plot[-1] >= 0.001 - 1e-9


def _exec_through_forces() -> dict:
    """Execute the module up to (but not into) the unsupported solve block.

    Regions after the solve reference its outputs e_1/k_1, so we stop at the
    first line that mentions them and inject the cached values ourselves.
    """
    src = convert_file(REFERENCE, fmt="py")
    keep: list[str] = []
    for line in src.splitlines():
        if "e_1" in line or "k_1" in line:
            break
        keep.append(line)
    ns: dict = {}
    exec(compile("\n".join(keep), "<generated>", "exec"), ns)  # noqa: S102
    return ns


def test_integral_and_summation_match_mathcad_checks():
    """N_int/M_int (concrete integral + steel summation) at the cached solve
    point reproduce Mathcad's cached force/moment checks."""
    ns = _exec_through_forces()
    ureg = ns["ureg"]
    k_1 = K_1 * ureg("1/m")
    n_int = ns["N_int"](E_1, k_1).to("kN").magnitude
    m_int = ns["M_int"](E_1, k_1).to(ureg.kN * ureg.m).magnitude
    # Loosened from full precision: quad on the piecewise integrand vs Mathcad's
    # own quadrature at its TOL=1e-3 solution differ by ~1e-5.
    assert math.isclose(n_int, N_INT_KN, rel_tol=1e-4)
    assert math.isclose(m_int, M_INT_KNM, rel_tol=1e-4)


def test_integral_emits_scipy_helpers():
    src = convert_file(REFERENCE, fmt="py")
    assert "integral, summation" in src or "summation, integral" in src
    assert "N_int = lambda e, k: w * integral(lambda z: sigma(z, e, k)" in src
    assert "summation(lambda i: F_s(e, k)[i], 0, n - 1)" in src


def test_integral_helper_is_unit_aware():
    """integral(f, a, b) integrates magnitudes and reattaches f_unit * z_unit."""
    import pint

    from mcad2py.runtime import integral

    ureg = pint.UnitRegistry()
    # ∫ (2 MPa) dz from 0 to 3 mm = 6 MPa·mm.
    out = integral(lambda z: 2.0 * ureg.MPa, 0.0 * ureg.mm, 3.0 * ureg.mm)
    assert math.isclose(out.to(ureg.MPa * ureg.mm).magnitude, 6.0, rel_tol=1e-9)
    # ∫ z dz from 0 to 4 m = 8 m**2.
    out2 = integral(lambda z: z, 0.0 * ureg.m, 4.0 * ureg.m)
    assert math.isclose(out2.to(ureg.m**2).magnitude, 8.0, rel_tol=1e-9)


def test_summation_helper_is_inclusive():
    from mcad2py.runtime import summation

    # Σ_{i=0}^{4} i = 10, inclusive of both ends.
    assert summation(lambda i: i, 0, 4) == 10
    assert summation(lambda i: i, 2, 2) == 2  # single term
    assert summation(lambda i: i, 3, 1) == 0  # empty range


def test_matrix_region_parsed_as_vector():
    ws = convert_worksheet(load_mcdx(REFERENCE))
    defines = {d.target.py: d for d in ws.regions if isinstance(d, ir.Define)}
    # Ø := [0; 25] mm  -> a 2x1 matrix literal scaled by a unit.
    phi_def = defines["Ø"]
    assert isinstance(phi_def.value, ir.Quantity)
    assert isinstance(phi_def.value.value, ir.MatrixLiteral)
    assert phi_def.value.value.rows == 2
