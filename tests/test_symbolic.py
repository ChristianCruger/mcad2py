"""Tests for symbolic regions (equations + ``solve``) in ``NM_to_CT.mcdx``.

This worksheet mixes a symbolic part — three "show the steps" equations and a
``solve`` for ``C`` — with a numeric part that re-derives the same quantities
with Pint units. We check both: that the generated module executes and matches
Mathcad's cached numeric results (``result.xml``), and that the emitted
``solve`` agrees with Mathcad's cached *symbolic* answer (``symResult``).
"""

import contextlib
import io
import math
from pathlib import Path

import sympy

from mcad2py import ir
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.emit.codegen import (
    declaration_lines,
    expr_to_str,
    symbolic_eval_expr,
)
from mcad2py.loader import load_mcdx

REFERENCE = Path(__file__).parent.parent / "references" / "NM_to_CT.mcdx"
PLAIN = Path(__file__).parent.parent / "references" / "plain_concrete_cohesion.mcdx"

# Variable -> Mathcad's cached numeric result (in the worksheet's display unit).
EXPECTED = {
    "x_t": ("m", 0.52899999999999991),
    "x_c": ("mm", 349.99999999999994),
    "C": ("kN", 96707.78384527874),
    "T": ("kN", 19090.21615472126),
}


def _exec_generated() -> dict:
    src = convert_file(REFERENCE, fmt="py")
    namespace: dict = {}
    with contextlib.redirect_stdout(io.StringIO()):  # solve() prints to stdout
        exec(compile(src, "<generated>", "exec"), namespace)  # noqa: S102
    return namespace


def test_generated_numeric_values_match_mathcad():
    ns = _exec_generated()
    for name, (unit, expected) in EXPECTED.items():
        magnitude = ns[name].to(unit).magnitude
        assert math.isclose(magnitude, expected, rel_tol=1e-9), (
            f"{name}: got {magnitude}, expected {expected}"
        )


def _find(ws: ir.Worksheet, kind: type) -> ir.Region:
    return next(r for r in ws.regions if isinstance(r, kind))


def test_solve_matches_mathcad_symresult():
    """The emitted ``solve(...)`` equals Mathcad's cached symbolic answer."""
    ws = convert_worksheet(load_mcdx(REFERENCE))
    decls = _find(ws, ir.SymbolDeclarations)
    sym = _find(ws, ir.SymbolicEval)
    assert sym.command == "solve"
    assert sym.result is not None  # Mathcad cached the symbolic result

    env = {"Symbol": sympy.Symbol, "Eq": sympy.Eq, "solve": sympy.solve}
    for line in declaration_lines(decls):
        exec(line, env)  # noqa: S102 -- declares Symbol(...) names

    got = eval(symbolic_eval_expr(sym), env)[0]  # noqa: S307 -- solve(...)[0]
    expected = eval(expr_to_str(sym.result), env)  # noqa: S307
    assert sympy.simplify(got - expected) == 0


def test_symbols_declared_before_first_symbolic_use():
    ws = convert_worksheet(load_mcdx(REFERENCE))
    kinds = [type(r) for r in ws.regions]
    decl_at = kinds.index(ir.SymbolDeclarations)
    first_sym = next(
        i for i, k in enumerate(kinds)
        if k in (ir.SymbolicEquation, ir.SymbolicEval)
    )
    assert decl_at < first_sym
    decls = _find(ws, ir.SymbolDeclarations)
    # Every variable used in the solve is declared as a Symbol.
    assert {"C", "M", "N", "x_c", "x_t"} <= set(decls.names)


def test_step_equations_are_inert():
    """The three step equations become bare ``Eq(...)`` that assign nothing."""
    src = convert_file(REFERENCE, fmt="py")
    assert "Eq(M, C * x_c - T * x_t)" in src
    assert "Eq(N, C + T)" in src
    # ...and the only printed symbolic line is the solve.
    assert src.count("print(solve(") == 1


def test_compound_unit_override_in_echo():
    """A compound display unit (``kN*m``) survives as ``.to(ureg.kN * ureg.m)``.

    The final check region echoes ``C*x_c - T*x_t`` in ``kN*m``; Mathcad's
    cached value (result-id 13) is 23749 kN*m.
    """
    src = convert_file(REFERENCE, fmt="py")
    assert "disp((C * x_c - T * x_t), ureg.kN * ureg.m)" in src

    ns = _exec_generated()
    check = (ns["C"] * ns["x_c"] - ns["T"] * ns["x_t"]).to("kN*m")
    assert math.isclose(check.magnitude, 23749.0, rel_tol=1e-9)


def test_header_imports_sympy_only_when_needed():
    """Asserted on the converted artifact rather than on ``header_lines`` alone:
    the header is built *from* the rendered body (that's where the runtime
    imports are read off), so it isn't meaningful in isolation."""
    assert "from sympy import Eq, Symbol, solve" in convert_file(REFERENCE, fmt="py")
    assert "sympy" not in convert_file(PLAIN, fmt="py")
