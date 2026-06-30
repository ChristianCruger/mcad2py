"""Leaf features surfaced by ``Beton_Vridning.mcdx`` (torsion in concrete).

This worksheet's backbone is *range-indexed vector assignment* (``T_Ed[i] := 400``
with ``i := 1 .. n``), which isn't supported yet, so the whole sheet can't run
end-to-end. These tests cover the three independent leaf features it also uses,
asserting the generated source (the execute-and-compare-to-``result.xml`` test
arrives with the vector backbone):

  * a *stepless* range ``i := 1 .. n`` (implicit step of 1);
  * the ``ceil`` builtin;
  * an inline ``if(cond, then, else)`` with Mathcad *string* literals.
"""

from mcad2py import ir
from mcad2py.convert import convert_file
from mcad2py.emit.codegen import expr_to_str

from pathlib import Path

REFERENCE = Path(__file__).parent.parent / "references" / "Beton_Vridning.mcdx"


def _src() -> str:
    return convert_file(REFERENCE, fmt="py")


def test_stepless_range_emits_inclusive_arange():
    # ``i := 1 .. n`` has no explicit ``next`` -> step defaults to 1.
    assert "i = arange(1, n, 1)" in _src()


def test_stepless_range_ir_has_no_step():
    # Directly: a <range> with two bare children (no <sequence>) -> step None.
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


def test_ceil_builtin_maps_to_math_ceil():
    assert "math.ceil(" in _src()
    assert expr_to_str(ir.Call(func="ceil", args=[ir.Number("2.1")])) == "math.ceil(2.1)"


def test_floor_and_round_builtins():
    assert expr_to_str(ir.Call(func="floor", args=[ir.Number("2.9")])) == "math.floor(2.9)"
    assert expr_to_str(ir.Call(func="round", args=[ir.Number("2.5")])) == "round(2.5)"


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
