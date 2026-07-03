"""``Beton_Vridning.mcdx`` -- torsion in a concrete cross-section (DS/EN 1992).

The sheet is built on *range-indexed vector assignment*: a range variable
``i := 1 .. n`` and a family of vectors defined element-wise over it
(``T_Ed[i] := 400``, ``A_sl[i] := …``, ``accept[i] := if(k[i] ≥ 0, "ok", …)``).
Each ``X[i] := expr`` emits ``X = index_build(i, lambda i: expr)``; the lambda's
``i`` is the *scalar* loop index, so the right-hand side (and ``X[i]`` reads
inside it) uses ordinary scalar codegen, while the outer ``i`` stays an integer
range array so the evaluation reads ``X[i]`` fancy-index into 1-element vectors
(matching Mathcad's cached ``1×1`` matrices).

We execute the generated module and compare to Mathcad's cached ``result.xml``,
plus assert the generated source for the supporting leaf features (stepless
range, ``ceil``, inline ``if`` with string literals).
"""

import math
from pathlib import Path

from mcad2py import ir
from mcad2py.convert import convert_file
from mcad2py.emit.codegen import expr_to_str

REFERENCE = Path(__file__).parent.parent / "references" / "Beton_Vridning.mcdx"

# Mathcad's cached results (result.xml).
U = 7770                          # id 3/22: u
A_T = 201.06192982974676          # id 17: A_t
T_EF = 285.32818532818533         # id 23: t_ef
A_K = 1830000                     # id 24/26: A_k
U_K = 6671                        # id 25/27: u_k
T_RDMAX = 3541.747378378378       # id 35: T_Rdmax
S_T_I = 971.25                    # id 32/36: s_t[i]
A_SL_I = 3353.7267759562842       # id 37: A_sl[i]
N_SL_I = 5                        # id 38: n_sl[i]
K_I = 0.11293860269140475         # id 33: k[i]
ONE_MINUS_K_I = 0.88706139730859523  # id 39: 1 - k[i]
ACCEPT_I = "ok"                   # id 40: accept[i]


def _exec() -> dict:
    src = convert_file(REFERENCE, fmt="py")
    ns: dict = {}
    exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return ns


def _src() -> str:
    return convert_file(REFERENCE, fmt="py")


# --- the range-indexed vector backbone -------------------------------------


def test_whole_sheet_runs_and_matches_cache():
    ns = _exec()
    i = ns["i"]
    assert math.isclose(ns["u"], U)
    assert math.isclose(ns["A_t"], A_T)
    assert math.isclose(ns["t_ef"], T_EF)
    assert math.isclose(ns["A_k"], A_K)
    assert math.isclose(ns["u_k"], U_K)
    assert math.isclose(ns["T_Rdmax"], T_RDMAX)
    # The indexed reads fancy-index into 1-element vectors.
    assert math.isclose(float(ns["s_t"][i][0]), S_T_I)
    assert math.isclose(float(ns["A_sl"][i][0]), A_SL_I)
    assert math.isclose(float(ns["n_sl"][i][0]), N_SL_I)
    assert math.isclose(float(ns["k"][i][0]), K_I)
    assert math.isclose(float((1 - ns["k"][i])[0]), ONE_MINUS_K_I)
    assert ns["accept"][i][0] == ACCEPT_I


def test_vector_is_zero_based_and_zero_filled():
    # ``T_Ed[i] := 400`` with ``i := 1 .. 1`` builds a 0-based vector whose
    # unwritten index 0 defaults to 0: ``[0, 400]``.
    ns = _exec()
    assert list(ns["T_Ed"]) == [0.0, 400.0]


def test_index_variable_is_integer_array():
    # ``i`` must be an integer array so it can index NumPy vectors directly.
    ns = _exec()
    i = ns["i"]
    assert i.dtype.kind == "i"
    assert list(i) == [1]


def test_indexed_assignment_emits_index_build():
    src = _src()
    assert "T_Ed = index_build(i, lambda i: 400)" in src
    assert "n_sl = index_build(i, lambda i: ceil(" in src
    assert "from mcad2py.runtime import" in src and "index_build" in src


def test_index_assign_ir_shape():
    # X[i] := expr  ->  ir.IndexAssign(target=X, index=i, value=expr).
    import xml.etree.ElementTree as ET

    from mcad2py.parser.regions import _parse_define

    ns = "http://schemas.mathsoft.com/math50"
    elem = ET.fromstring(
        f'<define xmlns="{ns}"><apply><indexer />'
        f'<id labels="VARIABLE">X</id><id labels="*">i</id></apply>'
        f"<real>400</real></define>"
    )
    region = _parse_define(elem)
    assert isinstance(region, ir.IndexAssign)
    assert region.target.py == "X"
    assert region.index.py == "i"
    assert expr_to_str(region.value) == "400"
    assert region.evaluate is False


# --- supporting leaf features (asserted on the generated source) -----------


def test_stepless_range_emits_inclusive_arange():
    # ``i := 1 .. n`` has no explicit ``next`` -> step defaults to 1.
    assert "i = arange(1, n, 1)" in _src()


def test_stepless_range_ir_has_no_step():
    import xml.etree.ElementTree as ET

    from mcad2py.parser.expressions import parse_expr

    ns = "http://schemas.mathsoft.com/math50"
    elem = ET.fromstring(
        f'<range xmlns="{ns}"><real>1</real>'
        f'<id labels="VARIABLE">n</id></range>'
    )
    rng = parse_expr(elem)
    assert isinstance(rng, ir.Range)
    assert rng.step is None
    assert expr_to_str(rng.start) == "1"
    assert expr_to_str(rng.stop) == "n"


def test_ceil_maps_to_dimensionless_aware_helper():
    # ceil/floor/round are runtime helpers that reduce a dimensionless-but-
    # unreduced Pint quantity (e.g. l/s = m/mm) before rounding.
    assert "ceil(" in _src()
    assert expr_to_str(ir.Call(func="ceil", args=[ir.Number("2.1")])) == "ceil(2.1)"


def test_floor_and_round_builtins():
    assert expr_to_str(ir.Call(func="floor", args=[ir.Number("2.9")])) == "floor(2.9)"
    assert expr_to_str(ir.Call(func="round", args=[ir.Number("2.5")])) == "mround(2.5)"


def test_inline_if_with_string_literals():
    # accept[i] := if(k[i] >= 0, "ok", "tværsnit overudnyttet")
    # -> a conditional *expression* (ternary), not a call or a def.
    src = _src()
    assert "'ok' if k[i] >= 0 else 'tværsnit overudnyttet'" in src
    # The inline if must not become a function definition.
    assert "def accept" not in src


def test_inline_if_ir_is_program_ternary():
    cond = ir.BinOp(op="ge", left=ir.Name("x", "x"), right=ir.Number("0"))
    prog = ir.Program(branches=[(cond, ir.Str("ok")), (None, ir.Str("no"))])
    assert expr_to_str(prog) == "'ok' if x >= 0 else 'no'"


def test_string_literal_repr():
    assert expr_to_str(ir.Str("ok")) == "'ok'"
    assert expr_to_str(ir.Str("tværsnit overudnyttet")) == "'tværsnit overudnyttet'"
