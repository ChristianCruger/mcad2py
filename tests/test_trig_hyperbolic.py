"""Tests for the full trigonometric and hyperbolic function families.

``trig.mcdx`` and ``hyperbolic.mcdx`` are catalogue sheets: each applies every
member of one family to a single angle and echoes the result, so between them
they pin down the whole group.

Three things beyond "the name resolves" are exercised here:

* **argument handling** -- the forward trig functions read an angle (``34 deg``),
  while the hyperbolic and inverse functions take a *pure number*; since
  Mathcad's ``deg`` is a dimensionless ``π/180`` scale, ``sinh(103.2 deg)`` means
  ``sinh(1.80118)``;
* **the display override** -- inverse trig/hyperbolic results are bare radians,
  so ``atan(B) = … deg`` has to rescale (``disp``) rather than divide;
* **conventions that differ from Python/NumPy** -- ``atan2(x, y)`` takes its
  arguments in the opposite order to ``math.atan2(y, x)``, ``angle`` wraps to
  ``[0, 2π)``, ``acot`` uses the ``(0, π)`` branch, and ``sinc`` is the
  *unnormalised* ``sin(z)/z`` (not ``np.sinc``'s ``sin(πz)/(πz)``).

Both sheets run end-to-end and every echoed region is compared to Mathcad's
cached ``result.xml``.
"""

import io
import math
import re
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from mcad2py.convert import convert_file
from mcad2py.runtime import (
    acos,
    acosh,
    acot,
    acoth,
    acsc,
    acsch,
    angle,
    asec,
    asech,
    asin,
    asinh,
    atan,
    atan2,
    atanh,
    cos,
    cosh,
    cot,
    coth,
    csc,
    csch,
    disp,
    sec,
    sech,
    sin,
    sinc,
    sinh,
    tan,
    tanh,
)

REFERENCES = Path(__file__).parent.parent / "references"
TRIG = REFERENCES / "trig.mcdx"
HYPERBOLIC = REFERENCES / "hyperbolic.mcdx"

# Mathcad's cached results (result.xml), in region order -- as *displayed*.
#
# The one place the cache and the display differ is the ``θ :=`` region: with an
# empty (placeholder) override the cache stores the base-unit radian value
# (0.59341 / 1.80118) while Mathcad shows the same quantity as ``34 deg`` /
# ``103.2 deg``. Every other entry is the cached number verbatim.
TRIG_EXPECTED = [
    34,                     # θ := 34 deg          (cached 0.59341194567807209 rad)
    0.5591929034707469,     # A := sin(θ)
    0.37460659341591196,    # D := cos(2·θ)
    0.67450851684242674,    # B := tan(θ)
    1.48256096851274,       # C := cot(θ)
    34,                     # atan(B) = … deg
    0.59341194567807209,    # acot(C) =
    0.59341194567807221,    # asin(A) =
    68,                     # acos(D) = … deg
    1.2062179485039055,     # E := sec(θ)
    1.7882916499714003,     # F := csc(θ)
    0.59341194567807209,    # asec(E) =
    0.59341194567807221,    # acsc(F) =
    26.56505117707799,      # atan2(2, 1) = … deg
    18.43494882292201,      # angle(3, 1) = … deg
    0.94233509713353647,    # sinc(θ) =
    0.94233509713353647,    # sin(θ)/θ =   (the identity sinc(z) = sin(z)/z)
    2.677945044588987,      # acot(-2) =   (the (0, π) branch — see below)
    -1.4056476493802699,    # atan(-6) =
]

HYPERBOLIC_EXPECTED = [
    103.2,                  # θ := 103.2 deg       (cached 1.8011797880581482 rad)
    2.9458424962968333,     # A := sinh(θ)
    3.1109464818585932,     # B := cosh(θ)
    0.94692805339964548,    # C := tanh(θ)
    1.056046440286373,      # D := coth(θ)
    103.2,                  # asinh(A) = … deg
    1.8011797880581482,     # acosh(B) =
    1.8011797880581477,     # atanh(C) =
    1.8011797880581468,     # acoth(D) =
    0.054478170955597024,   # S := sech(2·θ)
    3.6023595761162963,     # asech(S) =
    0.97336648019200089,    # T := csch(θ/2)
    0.900589894029074,      # acsch(T) =
]

THETA_TRIG = math.radians(34)
THETA_HYP = math.radians(103.2)


def _run(path: Path) -> tuple[str, dict, list[float]]:
    """Convert, execute, and return (source, namespace, echoed numbers)."""
    src = convert_file(path, fmt="py")
    ns: dict = {}
    out = io.StringIO()
    with redirect_stdout(out):
        exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    # Each echo prints one line: a number, optionally followed by its unit.
    echoed = [
        float(re.match(r"-?[\d.eE+-]+", line).group())
        for line in out.getvalue().splitlines()
        if line.strip()
    ]
    return src, ns, echoed


# ---------------------------------------------------------------------------
# Whole-sheet: every echoed region vs. Mathcad's cache
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, expected",
    [(TRIG, TRIG_EXPECTED), (HYPERBOLIC, HYPERBOLIC_EXPECTED)],
    ids=["trig", "hyperbolic"],
)
def test_sheet_matches_cached_results(path, expected):
    """Every region of the sheet reproduces Mathcad's cached value."""
    _, _, echoed = _run(path)
    assert len(echoed) == len(expected)
    for i, (got, want) in enumerate(zip(echoed, expected)):
        assert math.isclose(got, want, rel_tol=1e-12), f"region {i}: {got} != {want}"


def test_forward_trig_reads_the_angle_unit():
    """``sin(34 deg)`` is 0.559, not ``sin(34)`` -- the arg carries a unit."""
    _, ns, _ = _run(TRIG)
    assert str(ns["theta"].units) == "degree"
    assert math.isclose(ns["A"], math.sin(THETA_TRIG))
    assert math.isclose(ns["E"], 1 / math.cos(THETA_TRIG))  # sec
    assert math.isclose(ns["F"], 1 / math.sin(THETA_TRIG))  # csc


def test_hyperbolic_reduces_the_angle_to_a_pure_number():
    """Mathcad's ``deg`` is a dimensionless π/180 scale, so ``sinh(103.2 deg)``
    is ``sinh(1.80118)`` -- not an error and not ``sinh(103.2)``."""
    _, ns, _ = _run(HYPERBOLIC)
    assert math.isclose(ns["A"], math.sinh(THETA_HYP))
    assert math.isclose(ns["S"], 1 / math.cosh(2 * THETA_HYP))  # sech(2θ)
    assert math.isclose(ns["T"], 1 / math.sinh(THETA_HYP / 2))  # csch(θ/2)


def test_generated_source_uses_runtime_helpers():
    """All of both families resolve to ``mcad2py.runtime`` names (no bare
    ``math.*``), so an angle argument and a Pint ratio both work."""
    trig_src, _, _ = _run(TRIG)
    hyp_src, _, _ = _run(HYPERBOLIC)
    assert "math." not in trig_src.split("import ureg")[1]  # body, not the header
    for name in ("sec", "csc", "sinc", "acot", "asec", "acsc", "atan2", "angle"):
        assert re.search(rf"\b{name}\(", trig_src), name
    for name in ("sinh", "cosh", "tanh", "coth", "sech", "csch",
                 "asinh", "acosh", "atanh", "acoth", "asech", "acsch"):
        assert re.search(rf"\b{name}\(", hyp_src), name


# ---------------------------------------------------------------------------
# Display override: a bare-radian result shown in degrees
# ---------------------------------------------------------------------------


def test_inverse_results_are_bare_radians():
    """The inverse functions return a plain float of radians, as Mathcad
    stores them -- the ``deg`` override is applied at display time."""
    assert not hasattr(atan(1.0), "units")
    assert math.isclose(atan(math.tan(THETA_TRIG)), THETA_TRIG)


def test_disp_rescales_a_bare_radian_into_degrees():
    """``atan(B) = … deg`` must rescale, not divide.

    A plain float has no ``.to()``, so without the angle-unit case ``disp``
    would fall through to ``value / ureg.deg`` and report ``0.593 1/degree``.
    """
    import pint

    ureg = pint.UnitRegistry()
    shown = disp(THETA_TRIG, ureg.deg)
    assert str(shown.units) == "degree"
    assert math.isclose(shown.magnitude, 34.0)
    # A genuinely incompatible override still falls back to division.
    assert str(disp(2.0, ureg.mm).units) == "1 / millimeter"


def test_disp_with_no_override_reduces_an_unreduced_ratio():
    """Mathcad's automatic display shows ``sin(θ)/θ`` as 0.942, where Pint
    leaves it as ``0.0164 1/degree``; likewise ``m/mm`` for a length ratio."""
    import pint

    ureg = pint.UnitRegistry()
    assert math.isclose(disp(sin(34 * ureg.deg) / (34 * ureg.deg)), 0.94233509713353647)
    assert math.isclose(disp((3 * ureg.m) / (300 * ureg.mm)), 10.0)
    # A dimensioned value passes through untouched.
    assert disp(5 * ureg.mm) == 5 * ureg.mm


def test_generated_echo_wraps_only_divisions():
    """``disp(...)`` is emitted for the automatic display of a *ratio* only, so
    ordinary echoes stay bare."""
    src, _, _ = _run(TRIG)
    assert "print(disp(sin(theta) / theta))" in src
    assert "print(A)" in src  # sin(θ): no division, echoed bare


# ---------------------------------------------------------------------------
# Conventions that differ from Python/NumPy
# ---------------------------------------------------------------------------


def test_atan2_argument_order_is_reversed_vs_python():
    """Mathcad ``atan2(x, y)`` is the angle of the point (x, y); Python's
    ``math.atan2`` takes (y, x)."""
    assert math.isclose(atan2(2, 1), math.atan2(1, 2))
    assert math.isclose(math.degrees(atan2(2, 1)), 26.56505117707799)


def test_angle_wraps_into_zero_to_two_pi():
    """``angle`` is ``atan2`` mapped onto [0, 2π), so a third-quadrant point
    comes back positive where ``atan2`` goes negative."""
    assert math.isclose(math.degrees(angle(3, 1)), 18.43494882292201)
    assert atan2(-1, -1) < 0 < angle(-1, -1)
    assert math.isclose(angle(-1, -1), math.pi + math.pi / 4)
    assert math.isclose(angle(-1, -1), atan2(-1, -1) + 2 * math.pi)


def test_sinc_is_unnormalised():
    """Mathcad ``sinc(z) = sin(z)/z``; ``np.sinc`` is ``sin(πz)/(πz)``."""
    import numpy as np

    assert math.isclose(sinc(THETA_TRIG), math.sin(THETA_TRIG) / THETA_TRIG)
    assert sinc(0) == 1.0
    assert not math.isclose(sinc(0.5), float(np.sinc(0.5)))
    assert math.isclose(sinc(0.5), float(np.sinc(0.5 / math.pi)))


def test_acot_uses_the_zero_to_pi_branch():
    """``acot`` is ``π/2 - atan(x)``, continuous across 0 -- the Maple/MuPAD
    convention, *not* Mathematica's ``atan(1/x)``.

    The sheet pins this down with a negative argument, where the two
    conventions disagree: Mathcad caches ``acot(-2) = 2.67794``, so the result
    stays in ``(0, π)`` rather than coming back as ``atan(-0.5) = -0.46365``.
    """
    assert math.isclose(acot(cot(34 * math.pi / 180)), THETA_TRIG)
    assert math.isclose(acot(0), math.pi / 2)
    assert math.isclose(acot(-2), 2.677945044588987, rel_tol=1e-12)  # cached
    assert not math.isclose(acot(-2), math.atan(-0.5))  # the other convention
    assert 0 < acot(-1) < math.pi  # the (0, π) branch, not a negative angle


def test_atan_keeps_pythons_signed_branch():
    """``atan`` is unambiguous -- ``(-π/2, π/2)``, signed like ``math.atan``;
    the sheet's cached ``atan(-6) = -1.40565`` confirms it isn't wrapped."""
    assert math.isclose(atan(-6), -1.4056476493802699, rel_tol=1e-12)  # cached
    assert -math.pi / 2 < atan(-6) < 0


# ---------------------------------------------------------------------------
# Round-trip identities across both families
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fwd, inv",
    [(sin, asin), (cos, acos), (tan, atan), (cot, acot), (sec, asec), (csc, acsc),
     (sinh, asinh), (cosh, acosh), (tanh, atanh), (coth, acoth),
     (sech, asech), (csch, acsch)],
    ids=lambda f: f.__name__,
)
def test_each_function_inverts_its_partner(fwd, inv):
    """Every forward/inverse pair round-trips a 0.6 rad angle, which lands in
    the principal branch of all twelve."""
    x = 0.6
    assert math.isclose(inv(fwd(x)), x, rel_tol=1e-12)


@pytest.mark.parametrize(
    "fn, reference",
    [(sec, lambda x: 1 / math.cos(x)), (csc, lambda x: 1 / math.sin(x)),
     (cot, lambda x: 1 / math.tan(x)), (coth, lambda x: 1 / math.tanh(x)),
     (sech, lambda x: 1 / math.cosh(x)), (csch, lambda x: 1 / math.sinh(x))],
    ids=lambda f: getattr(f, "__name__", "ref"),
)
def test_reciprocal_functions(fn, reference):
    """The six reciprocal functions Python's ``math`` doesn't provide."""
    assert math.isclose(fn(0.6), reference(0.6), rel_tol=1e-12)
