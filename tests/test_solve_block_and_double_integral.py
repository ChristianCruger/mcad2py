"""Tests for ``double_integral`` and ``solve_block``'s convergence checking.

Both were motivated by ``references/biaxial_bending.mcdx`` (a biaxial-bending
solve block built on a nested double integral of a piecewise stress-strain
law), but that sheet's solve block isn't executed here -- its guess sits deep
enough in a flat plateau that escaping it isn't reliable within a bounded
retry budget (see ``solve_block``'s docstring), which would make a full
execute-and-compare test slow and occasionally flaky. Instead:

* ``double_integral`` is checked directly against nested ``integral()`` calls
  (the two must agree -- ``double_integral`` is what a nested-``Integral`` IR
  pattern with outer-independent inner bounds now emits instead), and that
  codegen actually detects the pattern on the real sheet.
* ``solve_block``'s bug -- ``fsolve`` can report ``ier=1`` ("converged")
  while parked on a point whose residual is nowhere near zero (seen when the
  whole integration domain sits inside one flat branch of the piecewise
  model) -- is reproduced with a fast synthetic residual and a mocked
  ``fsolve`` first call, rather than the slow real double integral.
"""

import math
from pathlib import Path

import numpy as np
import pint

from mcad2py.convert import convert_file
from mcad2py.runtime import _coarse_presearch, double_integral, integral, solve_block

REFERENCE = Path(__file__).parent.parent / "references" / "biaxial_bending.mcdx"


# --- double_integral ---------------------------------------------------


def test_double_integral_matches_nested_integral():
    ureg = pint.UnitRegistry()
    sigma = lambda x, y: (2.0 * ureg.MPa) if x.magnitude >= 0 else (-1.0 * ureg.MPa)  # noqa: E731

    nested = integral(
        lambda y: integral(lambda x: sigma(x, y), -3.0 * ureg.mm, 5.0 * ureg.mm),
        -2.0 * ureg.mm,
        4.0 * ureg.mm,
    )
    dbl = double_integral(sigma, -3.0 * ureg.mm, 5.0 * ureg.mm, -2.0 * ureg.mm, 4.0 * ureg.mm)
    assert math.isclose(
        nested.to(ureg.MPa * ureg.mm**2).magnitude,
        dbl.to(ureg.MPa * ureg.mm**2).magnitude,
        rel_tol=1e-9,
    )


def test_double_integral_is_unit_aware():
    ureg = pint.UnitRegistry()
    # int_0^3 int_0^4 (2 MPa) dx dy = 2 MPa * 12 mm^2 = 24 MPa*mm^2.
    out = double_integral(
        lambda x, y: 2.0 * ureg.MPa, 0.0 * ureg.mm, 4.0 * ureg.mm, 0.0 * ureg.mm, 3.0 * ureg.mm
    )
    assert math.isclose(out.to(ureg.MPa * ureg.mm**2).magnitude, 24.0, rel_tol=1e-9)
    # A plain (unitless) integrand works the same way.
    out2 = double_integral(lambda x, y: x * y, 0.0, 2.0, 0.0, 3.0)
    assert math.isclose(out2, 9.0, rel_tol=1e-9)  # (int x dx)(int y dy) = 2 * 4.5


def test_biaxial_bending_nested_integral_detected_as_double_integral():
    """N/M_x/M_y are each ``integral(lambda y: integral(lambda x: …), …)`` in
    the sheet -- the inner bounds (-W/2..W/2) don't depend on y, so codegen
    must collapse the pair into one ``double_integral(...)`` call.
    """
    src = convert_file(REFERENCE, fmt="py")
    assert (
        "N = lambda epsilon, kappa_x, kappa_y: double_integral("
        "lambda x, y: sigma(epsilon + kappa_x * x + kappa_y * y), "
        "-W / 2, W / 2, -H / 2, H / 2)" in src
    )
    assert src.count("double_integral(") == 3  # N, M_x, M_y
    assert "integral(lambda y: integral(" not in src
    import_line = next(l for l in src.splitlines() if "from mcad2py.runtime import" in l)
    assert "double_integral" in import_line
    assert ", integral," not in import_line and not import_line.strip().endswith("integral")


# --- solve_block: verifying convergence, not just trusting fsolve ----------


def test_coarse_presearch_finds_a_better_seed_past_a_flat_plateau():
    """The escape mechanism in isolation: a residual that's constant (no
    gradient) on one side of the guess and has a real root on the other.
    ``_coarse_presearch`` picks whichever of its random samples has the
    lowest residual cost -- it doesn't compare against ``x0`` itself, so the
    guarantee to check is "found a lower-cost point than the flat plateau",
    not "landed near the exact root" (that's ``fsolve``'s job once seeded).
    """

    def wrapped(x):
        (v,) = x
        return [10.0] if v > 5 else [(v - 2.0) / 100.0]

    x0 = np.array([100.0])
    plateau_cost = sum(v * v for v in wrapped(x0))  # 10.0**2 = 100
    seed = _coarse_presearch(wrapped, x0, n_samples=15, seed=0)
    seed_cost = sum(v * v for v in wrapped(seed))
    assert seed_cost < plateau_cost


def test_solve_block_rejects_a_false_positive_convergence(monkeypatch):
    """Reproduces the actual bug: fsolve reports ier=1 ("converged") having
    left the guess untouched, with a residual nowhere near zero. solve_block
    must check the residual itself, not just trust ier, and retry.
    """
    import scipy.optimize

    real_fsolve = scipy.optimize.fsolve
    calls = {"n": 0}

    def fake_fsolve(func, x0, full_output=False, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # A bogus "success": unchanged guess, residual still huge.
            return (np.asarray(x0), {"fvec": func(x0)}, 1, "bogus success")
        return real_fsolve(func, x0, full_output=full_output, **kwargs)

    monkeypatch.setattr(scipy.optimize, "fsolve", fake_fsolve)

    def residual(vals):
        (x,) = vals
        return [x - 2.0]  # real root x=2, well-behaved everywhere -- no plateau

    out = solve_block(residual, [100.0])
    assert calls["n"] >= 2  # the bogus first "success" must not be the final answer
    assert math.isclose(out[0], 2.0, abs_tol=1e-4)


def test_solve_block_warns_and_returns_best_effort_when_truly_stuck(capsys):
    """A guess deep inside a huge flat plateau: solve_block can't confirm
    convergence and must say so (rather than silently returning the
    plateau's high-residual point as if it were a solution).

    With the pinned ``seed=0``, ``_coarse_presearch``'s 15 samples all land
    back on the plateau (it returns ~373.92, cost unchanged), so the retry
    can't escape and the honest "couldn't confirm" path is exercised
    deterministically.
    """

    def residual(vals):
        (x,) = vals
        return [10.0] if x > 5 else [x - 2.0]

    out = solve_block(residual, [100.0])
    printed = capsys.readouterr().out
    assert "didn't converge to an actual root" in printed
    assert "could not confirm convergence" in printed
    assert out[0] == 100.0  # best-effort: the original guess, not a fabricated answer
