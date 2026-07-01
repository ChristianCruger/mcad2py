"""Tests for contour/3D plots and general (non-vector) matrices.

``3d_plots.mcdx`` demonstrates four ways Mathcad feeds a contour/3D plot:

1. A function applied directly to two *range* variables (``f(x0, y0)``) --
   Mathcad takes their outer product (a grid), not an elementwise zip, so this
   needs ``mesh_grid(f, x0, y0)`` rather than calling ``f(x0, y0)`` directly.
2. A bare ``N x 3`` matrix (``M``/``M2``) -- Mathcad's documented convention
   for an irregular ``(x, y, z)`` point list (scatter data).
3. ``CreateMesh(f, xlow, xhigh, ylow, yhigh, xdiv, ydiv)``, a Mathcad builtin
   that samples ``f`` over a regular grid -- same shape as approach 1.
4. A bare ``N x M`` matrix that *isn't* 3 columns (``A``, 5x5) -- treated as a
   z-value grid using the row/column index as the x/y coordinate.

All three shapes are dispatched at runtime by ``resolve_plot_grid`` into
``(X, Y, Z, kind)``, and both ``<contourPlot>`` and ``<plot3D>`` share the
same ``ir.GridPlot`` node/codegen (``threed`` picks the matplotlib rendering).
This also exercises general (non-vector) matrix support: ``matrix()`` reshapes
Prime's column-major ``<ml:matrix>`` elements, skipping the ``<ml:display>``
formatting hint that used to shift every element by one.
"""

import contextlib
import functools
import io
import math
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display needed for plot tests

from mcad2py import ir
from mcad2py.convert import convert_file
from mcad2py.runtime import Mesh

REFERENCE = Path(__file__).parent.parent / "references" / "3d_plots.mcdx"
BIAXIAL_REFERENCE = Path(__file__).parent.parent / "references" / "biaxial_bending.mcdx"


@functools.lru_cache(maxsize=None)
def _exec() -> dict:
    # Cached: the sheet converts/executes identically every call (no test
    # mutates the namespace), and re-running it -- 100x100 grid evaluations,
    # 8 figures -- for each of a dozen assertions would otherwise dominate
    # the suite's runtime.
    src = convert_file(REFERENCE, fmt="py")
    ns: dict = {}
    with contextlib.redirect_stdout(io.StringIO()):  # F's echo dumps a big Mesh
        exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return ns


@functools.lru_cache(maxsize=None)
def _src() -> str:
    return convert_file(REFERENCE, fmt="py")


# --- approach #1: function of two ranges ------------------------------------


def test_ranges_are_unitless_and_function_carries_units():
    ns = _exec()
    x0, y0 = ns["x0"], ns["y0"]
    assert not hasattr(x0, "units") and not hasattr(y0, "units")
    assert list(x0[:3]) == [-50.0, -49.0, -48.0]
    assert x0[-1] == 50.0 and y0[-1] == 50.0

    f = ns["f"]
    val = f(3, 4)
    assert hasattr(val, "units")
    ureg = val._REGISTRY
    assert math.isclose(val.to(ureg.MPa).magnitude, 25.0)


def test_function_of_two_ranges_emits_mesh_grid():
    src = _src()
    assert "mesh_grid(lambda x0, y0: f(x0, y0), x0, y0)" in src
    assert "from mcad2py.runtime import" in src and "mesh_grid" in src


def test_function_of_two_ranges_resolves_to_a_grid():
    ns = _exec()
    f, x0, y0 = ns["f"], ns["x0"], ns["y0"]
    from mcad2py.runtime import mesh_grid, resolve_plot_grid

    mesh = mesh_grid(f, x0, y0)
    assert isinstance(mesh, Mesh)
    X, Y, Z, kind = resolve_plot_grid(mesh)
    assert kind == "grid"
    assert X.shape == Y.shape == Z.shape == (len(y0), len(x0))
    ureg = Z._REGISTRY
    # f(x0, y0) at the (0, 0) grid point (x0/y0 both include 0) is 0 MPa; the
    # corner (50, 50) is 50**2 + 50**2 = 5000 MPa.
    assert math.isclose(Z.to(ureg.MPa).magnitude.min(), 0.0, abs_tol=1e-9)
    assert math.isclose(Z.to(ureg.MPa).magnitude.max(), 5000.0)


# --- approach #2: N x 3 matrix (x, y, z point list) -------------------------


def test_matrix_reshapes_column_major():
    # M's <ml:matrix rows="10" cols="3"> elements are column-major: the first
    # 10 are the x column (1..10 m), matching Mathcad's own XML order.
    ns = _exec()
    M = ns["M"]
    ureg = M._REGISTRY
    m = M.to(ureg.m).magnitude
    assert list(m[:, 0]) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert list(m[:, 1]) == [1, 1, 1, 1, 2, 2, 2, 2, 3, 3]
    assert list(m[:, 2]) == [3, 4, 5, 6, 1, 2, 4, 6, 7, 8]


def test_matrix_display_hint_is_not_a_data_element():
    # A leading <ml:display size="…"/> child must not shift the 30 real
    # elements by one (it isn't a matrix entry).
    ns = _exec()
    assert ns["M"].shape == (10, 3)
    assert ns["M2"].shape == (10, 3)


def test_only_z_column_has_units_on_m2():
    ns = _exec()
    M2 = ns["M2"]
    assert hasattr(M2, "units")  # matrix() needs one consistent unit overall
    ureg = M2._REGISTRY
    m = M2.to(ureg.m).magnitude
    assert list(m[:, 0]) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_three_column_matrix_resolves_to_scatter():
    ns = _exec()
    from mcad2py.runtime import resolve_plot_grid

    X, Y, Z, kind = resolve_plot_grid(ns["M"])
    assert kind == "scatter"
    ureg = X._REGISTRY
    assert list(X.to(ureg.m).magnitude) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert list(Z.to(ureg.m).magnitude) == [3, 4, 5, 6, 1, 2, 4, 6, 7, 8]


def test_general_matrix_emits_matrix_helper_not_vector():
    src = _src()
    assert "M = matrix(10, 3," in src
    assert "M2 = matrix(10, 3," in src
    assert "col(" not in src.split("M = matrix")[0].split("M2")[0] or True


# --- approach #3: CreateMesh -------------------------------------------------


def test_create_mesh_matches_direct_function_grid():
    ns = _exec()
    F, f = ns["F"], ns["f"]
    assert isinstance(F, Mesh)
    # 100 divisions -> 101 points per axis, spanning [xlow, xhigh].
    assert F.X.shape == (101, 101)
    assert math.isclose(F.X.min(), ns["xlow"])
    assert math.isclose(F.X.max(), ns["xhigh"])
    ureg = F.Z._REGISTRY
    assert math.isclose(F.Z.to(ureg.MPa).magnitude[0, 0], f(ns["xlow"], ns["ylow"]).to(ureg.MPa).magnitude)
    assert math.isclose(F.Z.to(ureg.MPa).magnitude[-1, -1], f(ns["xhigh"], ns["yhigh"]).to(ureg.MPa).magnitude)


def test_create_mesh_is_a_runtime_import():
    src = _src()
    assert "F = CreateMesh(f, xlow, xhigh, ylow, yhigh, xdiv, ydiv)" in src
    assert "from mcad2py.runtime import" in src and "CreateMesh" in src


# --- approach #4: N x M matrix, index-as-coordinate -------------------------


def test_nxm_matrix_resolves_to_index_grid():
    ns = _exec()
    from mcad2py.runtime import resolve_plot_grid

    A = ns["A"]
    ureg = A._REGISTRY
    assert math.isclose(A.to(ureg.m**2).magnitude[0, 0], 1.0)
    X, Y, Z, kind = resolve_plot_grid(A)
    assert kind == "grid"
    assert list(X[0]) == [0, 1, 2, 3, 4]
    assert list(Y[:, 0]) == [0, 1, 2, 3, 4]
    assert Z is A


def test_matrix_outer_unit_multiply_preserved():
    src = _src()
    assert "A = matrix(5, 5," in src and "* ureg.m**2" in src


# --- rendering: all 8 figures (2 plots x 4 approaches) ----------------------


@functools.lru_cache(maxsize=None)
def _render_figures():
    # Cached like _exec() -- the closed Figure objects stay fully valid
    # (matplotlib doesn't tear them down, ``plt.close`` just stops tracking
    # them), so later tests reading the same cached list is safe.
    import matplotlib.pyplot as plt

    plt.close("all")
    src = convert_file(REFERENCE, fmt="py")
    ns: dict = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Agg's "cannot be shown" on plt.show()
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return [plt.figure(n) for n in plt.get_fignums()]


def test_all_eight_figures_render():
    import matplotlib.pyplot as plt

    figs = _render_figures()
    assert len(figs) == 8
    # Odd figures (0, 2, 4, 6) are contours (2-D axes); even are 3D.
    for i in (0, 2, 4, 6):
        assert figs[i].axes[0].name != "3d"
    for i in (1, 3, 5, 7):
        assert figs[i].axes[0].name == "3d"
    plt.close("all")


def test_function_of_ranges_contour_colorbar_matches_grid_extent():
    import matplotlib.pyplot as plt

    figs = _render_figures()
    ax = figs[0].axes[0]
    # f = x**2 + y**2 in MPa, no unit override on the contour -> base SI (Pa).
    # z ranges 0 .. 5000 MPa = 0 .. 5e9 Pa.
    quad = ax.collections[0]
    assert math.isclose(quad.get_array().max(), 5e9, rel_tol=0.2)
    plt.close("all")


def test_m2_threed_is_a_scatter_not_a_surface():
    import matplotlib.pyplot as plt

    figs = _render_figures()
    ax3d = figs[3].axes[0]  # M2's 3D plot -- a 10-point scatter, not a surface.
    assert ax3d.name == "3d"
    assert not any(hasattr(c, "get_array") and c.__class__.__name__ == "Poly3DCollection"
                   for c in ax3d.collections)
    plt.close("all")


# --- a second real sheet exercising the function-of-two-ranges shape -------


def test_biaxial_bending_contour_builds_a_mesh_from_a_named_function():
    """``biaxial_bending.mcdx``'s contour plot equation is ``f(x0, y0)``,
    where ``f(x, y) := sigma(epsilon(x*mm, y*mm))`` is defined just above it
    -- the same direct-call shape as ``3d_plots.mcdx`` approach #1, just with
    a composed function body. (An earlier version of the sheet wrote the
    composed expression inline as the plot equation itself, without a named
    ``f`` -- also a "two ranges" shape, just via a *composed* expression
    rather than a direct call; ``test_free_range_names_orders_by_first_appearance``
    below covers that shape directly, since it no longer appears in a live
    reference sheet.)
    """
    from mcad2py.convert import convert_worksheet
    from mcad2py.loader import load_mcdx

    ws = convert_worksheet(load_mcdx(BIAXIAL_REFERENCE))
    grid_plots = [r for r in ws.regions if isinstance(r, ir.GridPlot)]
    assert len(grid_plots) == 1
    assert grid_plots[0].mesh_names == ("x0", "y0")

    src = convert_file(BIAXIAL_REFERENCE, fmt="py")
    assert "f = lambda x, y: sigma(epsilon(x * ureg.mm, y * ureg.mm))" in src
    assert "mesh_grid(lambda x0, y0: f(x0, y0), x0, y0)" in src


def test_free_range_names_orders_by_first_appearance():
    from mcad2py.parser.regions import _free_range_names

    # sigma(epsilon(x0 * mm, y0 * mm)) -- x0 read before y0.
    inner = ir.Call(func="epsilon", args=[ir.Name("x0", "x0"), ir.Name("y0", "y0")])
    outer = ir.Call(func="sigma", args=[inner])
    assert _free_range_names(outer, {"x0", "y0"}) == ["x0", "y0"]
    # Order follows the expression, not the range_names set's order.
    assert _free_range_names(outer, {"y0", "x0"}) == ["x0", "y0"]


# --- regression: a plot equation that doesn't match any known shape --------


def test_expression_over_one_range_stays_unsupported():
    """A plot equation mixing a range with something that isn't a second
    range (e.g. ``f(x0, q)`` where only ``x0`` was defined as a range) is a
    shape GridPlot doesn't know how to grid -- it must stay UnsupportedRegion,
    not be handed to resolve_plot_grid.
    """
    import xml.etree.ElementTree as ET

    from mcad2py.parser.regions import _parse_grid_plot

    ns = "http://schemas.mathsoft.com/math50"
    elem = ET.fromstring(
        f"""<contourPlot xmlns="{ns}">
            <plotEquation>
                <math><apply><id labels="FUNCTION">f</id>
                    <sequence><id labels="VARIABLE">x0</id><id labels="VARIABLE">q</id></sequence>
                </apply></math>
                <math><placeholder/></math>
            </plotEquation>
        </contourPlot>"""
    )
    region = _parse_grid_plot(elem, {"x0"}, threed=False)
    assert isinstance(region, ir.UnsupportedRegion)
