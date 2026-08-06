"""Tests for ``linterp``, transpose, percent, and a scriptable ListBox control.

``shrinkage.mcdx`` (EN 1992 concrete shrinkage) exercises four constructs:

* ``linterp(vx, vy, x)`` -- Mathcad's linear interpolation builtin (a runtime
  helper: it reorders args vs ``np.interp`` and is unit-aware/extrapolating);
* vector ``transpose`` (``<ml:transpose>``);
* ``percent`` (``80%`` -> ``80 / 100``);
* a ``ListBoxScriptableControl`` -- its embedded JScript is *not* transpiled;
  we recover the control's cached output value (``[3, 0.13]`` for "Class S").

The whole sheet runs end-to-end and is compared to Mathcad's cached
``result.xml``. One value (``epsilon_cd``) carries a ~1e-5 relative difference
because Pint's Julian year (365.25 d) differs from Mathcad's mean year.
"""

import math
from pathlib import Path

from mcad2py.convert import convert_file

REFERENCE = Path(__file__).parent.parent / "references" / "shrinkage.mcdx"

# Mathcad's cached results (result.xml). Strain values are dimensionless; the
# epsilon_cd0 display is in units of 1e-6, so the variable itself is *1e-6.
EPSILON_CD0 = 202.19132579484841e-6     # result-id 9
EPSILON_CA = 6.2499999999885713e-5      # result-id 16
EPSILON_CORE = 0.00020108000000000002   # result-id 19
EPSILON_CD = 0.0001297208757038731      # result-id 15 (year-length sensitive)
EPSILON_CS = 0.0001922208757037588      # result-id 18 (year-length sensitive)
T_U = 35.179999999999993                # result-id 21, kelvin
T_CORE = 20.108                         # result-id 22, kelvin
T_AVE = 22.62                           # result-id 23, kelvin


def _exec() -> dict:
    """Execute the full generated module and return its namespace."""
    src = convert_file(REFERENCE, fmt="py")
    ns: dict = {}
    exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return ns


def _exec_head() -> dict:
    """Execute up to (not including) the thermal-expansion redefinition of α.

    ``α`` is first the ListBox vector ``[3, 0.13]`` then later reassigned to the
    thermal-expansion coefficient ``1e-5/K``; slicing keeps the vector visible.
    """
    src = convert_file(REFERENCE, fmt="py")
    head = src[: src.index("\nalpha = 1 ")]
    ns: dict = {}
    exec(compile(head, "<generated>", "exec"), ns)  # noqa: S102
    return ns


# ---------------------------------------------------------------------------
# ListBox scriptable control
# ---------------------------------------------------------------------------


def test_listbox_recovers_cached_value():
    """The control's JScript isn't run; its cached [3, 0.13] output is used."""
    ns = _exec_head()
    alpha = ns["alpha"]  # first definition (later reused for thermal expansion)
    # alpha[0] and alpha[1] feed epsilon_cd0; the cached selection is "Class S".
    assert math.isclose(float(alpha[0]), 3.0)
    assert math.isclose(float(alpha[1]), 0.13)


def test_listbox_documents_selection_without_transpiling_script():
    src = convert_file(REFERENCE, fmt="py")
    assert "alpha = col(3, 0.13)" in src
    # The selection and options are documented; the JScript is not converted.
    assert 'selected "Class S"' in src
    assert "Class S, Class N, Class R" in src
    assert "not transpiled" in src
    assert "function ListBoxEvent_Exec" not in src  # script body never emitted


# ---------------------------------------------------------------------------
# percent
# ---------------------------------------------------------------------------


def test_percent_is_divide_by_100():
    ns = _exec()
    assert math.isclose(ns["RH"], 0.8)  # RH := 80%
    # beta_RH uses RH / (100%) == RH / 1; check a known point.
    assert math.isclose(ns["beta_RH"](0.8), 1.55 * (1 - 0.8**3))


def test_percent_emitted_source():
    src = convert_file(REFERENCE, fmt="py")
    assert "RH = 80 / 100" in src


# ---------------------------------------------------------------------------
# linterp + transpose
# ---------------------------------------------------------------------------


def test_linterp_and_transpose_emitted():
    """The data rows are ``1x6`` *row* literals transposed into columns --
    Mathcad's usual way of typing a column vector. A row vector is a genuine
    ``1 x N`` matrix (not a 1-D array), so ``transpose`` is what brings it back
    to the 1-D column form ``linterp`` reads."""
    src = convert_file(REFERENCE, fmt="py")
    assert "transpose(matrix([1.0, 1.0, 0.85, 0.75, 0.70, 0.70]))" in src
    assert "linterp(transpose(" in src


def test_linterp_interpolates_and_extrapolates():
    ns = _exec()
    ureg = ns["ureg"]
    k_h = ns["k_h"]
    # At a knot.
    assert math.isclose(float(k_h(0 * ureg.mm)), 1.0)
    # Interior: halfway between 100 mm (1.0) and 200 mm (0.85) -> 0.925.
    assert math.isclose(float(k_h(150 * ureg.mm)), 0.925)
    # Beyond the last knot (1 m): the final segment is flat (0.70, 0.70), so the
    # linear extrapolation stays 0.70 -- matching Mathcad's cached k_h = 0.7.
    assert math.isclose(float(k_h(1200 * ureg.mm)), 0.7)


# ---------------------------------------------------------------------------
# Whole-sheet values vs cached result.xml
# ---------------------------------------------------------------------------


def test_sheet_values_match_cache():
    ns = _exec()
    ureg = ns["ureg"]
    assert math.isclose(float(ns["h_0"].to(ureg.m).magnitude), 1.2, rel_tol=1e-12)
    assert math.isclose(float(ns["epsilon_cd0"]), EPSILON_CD0, rel_tol=1e-12)
    assert math.isclose(float(ns["epsilon_ca"].magnitude), EPSILON_CA, rel_tol=1e-9)
    assert math.isclose(float(ns["epsilon_core"].magnitude), EPSILON_CORE, rel_tol=1e-12)
    # Year-length sensitive (Pint Julian year vs Mathcad mean year).
    assert math.isclose(float(ns["epsilon_cd"].magnitude), EPSILON_CD, rel_tol=1e-4)
    assert math.isclose(float(ns["epsilon_cs"].magnitude), EPSILON_CS, rel_tol=1e-4)


def test_temperature_equivalents_match_cache():
    ns = _exec()
    ureg = ns["ureg"]
    assert math.isclose(float(ns["T_u"].to(ureg.K).magnitude), T_U, rel_tol=1e-12)
    assert math.isclose(float(ns["T_core"].to(ureg.K).magnitude), T_CORE, rel_tol=1e-12)
    assert math.isclose(float(ns["T_ave"].to(ureg.K).magnitude), T_AVE, rel_tol=1e-12)
