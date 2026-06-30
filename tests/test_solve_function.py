"""Test a solve block used to *define a function*.

``Solve_as_function.mcdx`` has a Given/Find block whose solver region is a
function definition::

    Given
        x := 3                  (guess)
        a*x^2 - b = cos(x)      (constraint -- depends on the function params)
    f(a, b) := find(x)          (solver -> defines a function)

So the constraint closes over the function's parameters ``a``/``b``; the whole
solve must be emitted *inside* ``def f(a, b):`` and return the solved unknown.
We execute the generated module and compare to Mathcad's cached ``result.xml``.
"""

import math
from pathlib import Path

from mcad2py.convert import convert_file

REFERENCE = Path(__file__).parent.parent / "references" / "solve_as_function.mcdx"

# Mathcad's cached results (result.xml).
G = 1.6957050990830669          # result-id 3: G := f(1, 3)
COS_G = -0.12458421694368665    # result-id 6: cos(G)
CHECK = -0.12458421694368615    # result-id 7: a*G^2 - b  (== cos(G) at the root)


def _exec() -> dict:
    src = convert_file(REFERENCE, fmt="py")
    ns: dict = {}
    exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return ns


def test_solver_emits_function_def():
    src = convert_file(REFERENCE, fmt="py")
    # The solver region becomes a real function whose body runs the solve and
    # returns the solved unknown (closing over the parameters a, b).
    assert "def f(a, b):" in src
    assert "def _residuals_x(_x):" in src
    assert "return solve_block(_residuals_x, [x])[0]" in src


def test_function_solves_and_matches_cache():
    ns = _exec()
    f = ns["f"]
    assert math.isclose(f(1, 3), G, rel_tol=1e-9)
    # The whole sheet evaluates G := f(1, 3) and two checks at the root.
    assert math.isclose(ns["G"], G, rel_tol=1e-9)
    assert math.isclose(ns["cos"](ns["G"]), COS_G, rel_tol=1e-9)


def test_function_is_reusable_with_other_args():
    """A solve-as-function is callable with new params, not a one-shot value."""
    ns = _exec()
    f = ns["f"]
    root = f(1, 3)
    # f(a, b) solves a*x^2 - b = cos(x); verify the returned root satisfies it.
    assert math.isclose(1 * root**2 - 3, math.cos(root), abs_tol=1e-9)
    # Different parameters give a different root.
    assert not math.isclose(f(2, 5), root, rel_tol=1e-6)
