"""A solve block with one unknown and a bare-name target: ``s := find(x)``.

The fixture sheets only use the matrix target ``[a; b] := find(a, b)`` or a
function target. A bare ``<ml:id>`` target used to leave the target list empty,
which turned the whole block into ``# TODO unsupported region: solve block (no
solver region)``. The constraint also carries a ``0.4 mm`` whose ``mm`` Prime
wrote with no ``labels`` at all -- read as a variable it emitted a bare ``mm``.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from mcad2py import ir
from mcad2py.emit.codegen import solve_block_lines
from mcad2py.parser.expressions import parse_expr
from mcad2py.parser.regions import _parse_solveblock

_ML = 'xmlns:ml="http://schemas.mathsoft.com/math50"'

# Shape copied from a real Prime sheet: guess x := 2 m, constraint
# x * 2 = 0.4 mm (``mm`` unlabelled), solver s := find(x) with an MPa-style
# display override.
_BLOCK = f"""
<solveblock xmlns="http://schemas.mathsoft.com/worksheet50" {_ML}><regions>
  <region solve-block-category="guess-value"><math><ml:define>
    <ml:id labels="VARIABLE">x</ml:id>
    <ml:apply><ml:scale /><ml:real>2</ml:real><ml:id labels="UNIT">m</ml:id></ml:apply>
  </ml:define></math></region>
  <region solve-block-category="constraint"><math><ml:apply><ml:equal />
    <ml:apply><ml:mult /><ml:id labels="VARIABLE">x</ml:id><ml:real>2</ml:real></ml:apply>
    <ml:apply><ml:scale /><ml:real>0.4</ml:real><ml:id>mm</ml:id></ml:apply>
  </ml:apply></math></region>
  <region solve-block-category="solver"><math><ml:define>
    <ml:id labels="VARIABLE">s</ml:id>
    <ml:eval>
      <ml:apply><ml:id labels="KEYWORD">find</ml:id><ml:id labels="VARIABLE">x</ml:id></ml:apply>
      <ml:unitOverride><ml:id labels="UNIT">mm</ml:id></ml:unitOverride>
    </ml:eval>
  </ml:define></math></region>
</regions></solveblock>
"""


def _block() -> ir.SolveBlock:
    region = _parse_solveblock(ET.fromstring(_BLOCK))
    assert isinstance(region, ir.SolveBlock), region
    return region


def test_bare_name_target_is_a_solve_block():
    block = _block()
    assert [t.py for t in block.targets] == ["s"]
    assert [u.py for u in block.unknowns] == ["x"]


def test_unlabelled_unit_in_a_constraint_is_a_unit():
    (eq,) = _block().constraints
    assert eq.rhs == ir.Quantity(value=ir.Number("0.4"), unit=ir.UnitRef("mm"))


def test_emitted_block_solves():
    from mcad2py.runtime import solve_block
    from mcad2py.units import ureg

    source = "\n".join(solve_block_lines(_block()))
    namespace = {"solve_block": solve_block, "ureg": ureg}
    exec(source, namespace)
    assert abs(namespace["s"].to(ureg.mm).magnitude - 0.2) < 1e-9


def test_solver_eval_is_echoed_in_its_display_unit():
    """``s := find(x) = … mm``: the sheet shows the result, so the script does."""
    from mcad2py.emit.codegen import echo_expr

    block = _block()
    assert block.evaluate
    assert echo_expr(block) == "disp(s, ureg.mm)"


def test_unlabelled_unit_outside_a_solve_block_is_unchanged():
    """A symbolic equation (``shrinkage.mcdx``) keeps the name: it emits SymPy."""
    elem = ET.fromstring(
        f'<ml:apply {_ML}><ml:scale /><ml:real>100</ml:real><ml:id>mm</ml:id></ml:apply>'
    )
    node = parse_expr(elem)
    assert isinstance(node, ir.Quantity)
    assert isinstance(node.unit, ir.Name)
