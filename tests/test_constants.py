"""Tests for Mathcad's built-in constants (``references/Constants.mcdx``).

The sheet evaluates Prime's whole *Constants* label -- the maths trio
(``e``/``π``/``∞``), the Euler-Mascheroni ``γ``, and the physics set (``c``,
``g``, ``e_c``, ``h``, ``ℏ``, ``k``, ``m_u``, ``N_A``, ``R``, ``R_∞``, ``α``,
``ε_0``, ``μ_0``, ``σ``, ``Φ_0``) -- with nothing defined anywhere on it.

What makes these work at all is the **label**: Prime writes
``<ml:id labels="CONSTANT">c</ml:id>``, so the lookup in ``mapping.CONSTANTS``
is label-gated and a worksheet's own ``c``, ``g``, ``k`` or ``R`` (labelled
VARIABLE, as every other fixture here has them) is untouched. The sheet's own
opening text says as much: "if symbols have not been defined as something else".

**One documented divergence** (see docs/test-coverage.md): Mathcad's ``∞`` is
really 10³⁰⁷, and that is the number ``result.xml`` caches. We emit ``math.inf``
-- the faithful reading of what the symbol means, and the only one that behaves
as an integration limit or a comparison bound -- so that echo is checked for
being an infinity rather than against the cache.
"""

import math

import numpy as np
import pytest

from conftest import cached_results, flat, reference, result_refs, run_sheet
from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import echo_expr
from mcad2py.loader import load_mcdx
from mcad2py.mapping import CONSTANTS

REFERENCE = reference("Constants")

# Echo index of ``∞`` -- see the module docstring.
INFINITY = 2


@pytest.fixture(scope="module")
def sheet():
    """Convert, execute, and return ``(source, namespace, echoed values)``."""
    return run_sheet(REFERENCE)


def test_every_constant_resolves(sheet):
    """No region is dropped, and nothing falls through to a bare identifier --
    an unmapped constant would emit its sanitized *name* (``N_A``), which the
    generated module never defines, so execution would raise ``NameError``."""
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == 19


def test_matches_cached_results(sheet):
    """Every constant reproduces the number Prime itself cached.

    Prime caches a constant shown with Mathcad's *automatic* display in base SI
    units, and the table stores it the same way, so ``to_base_units()`` is the
    common ground there. With a display override the cache holds the number as
    shown instead -- ``e_c`` in ``pC``, ``h`` divided by ``10⁻³⁴ kg·m²/s`` -- and
    ``disp`` has already produced exactly that, so the magnitude is taken as-is.
    """
    _, _, echoed = sheet
    cached, refs = cached_results(REFERENCE), result_refs(REFERENCE)
    regions = [r for r in convert_worksheet(load_mcdx(REFERENCE)).regions
               if echo_expr(r) is not None]
    assert len(regions) == len(echoed)

    checked = 0
    for index, region in enumerate(regions):
        if index == INFINITY:
            continue
        value = echoed[index]
        if region.display_unit is None and hasattr(value, "to_base_units"):
            value = value.to_base_units()
        got = flat(value)
        want = np.asarray(cached[refs[region.source.region_id]], dtype=float)
        assert np.allclose(got, want, rtol=1e-12), (
            f"echo {index} ({echo_expr(region)}): {got} != {want}"
        )
        checked += 1
    assert checked == 18


def test_infinity_is_a_real_infinity(sheet):
    """Mathcad's stand-in for ``∞`` is 10³⁰⁷; ours is an actual infinity."""
    _, _, echoed = sheet
    assert math.isinf(echoed[INFINITY])
    assert float(cached_results(REFERENCE)["2"][0]) == 1e307


def test_dimensioned_constants_carry_their_units(sheet):
    """``c`` is a speed, not a bare 299792458 -- the physics constants come out
    of the table as Pint quantities, so they compose with the rest of a sheet."""
    _, _, echoed = sheet
    speed_of_light, gravity = echoed[3], echoed[4]
    assert str(speed_of_light.units) == "meter / second"
    assert str(gravity.to_base_units().units) == "meter / second ** 2"


def test_lookup_is_label_gated():
    """The table is keyed by *display* name and consulted only for an id Prime
    labelled CONSTANT. Names that would collide with everyday worksheet
    variables (``c``, ``g``, ``k``, ``R``, ``e``, ``σ``, ``α``, ``γ``) are in it
    precisely because the label -- not the spelling -- decides."""
    from mcad2py import ir
    from mcad2py.emit.codegen import expr_to_str

    assert {"c", "g", "k", "R", "e", "σ", "α", "γ"} <= set(CONSTANTS)
    as_variable = ir.Name(py="c", original="c", role="VARIABLE")
    as_constant = ir.Name(py="c", original="c", role="CONSTANT")
    assert expr_to_str(as_variable) == "c"
    assert expr_to_str(as_constant) == CONSTANTS["c"]
