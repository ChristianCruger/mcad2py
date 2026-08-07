"""Tests for equation breaks, number sets and logic
(``references/breaks-sets-logic.mcdx``).

A small catalogue sheet covering four unrelated corners that all happen to be
about *notation* rather than numerics:

* **`≡` (`<ml:globalDefine>`)** -- a global definition, in scope over the whole
  sheet rather than from its position down. The parser hoists it to the top,
  which is the only way a linear Python module can honour that.
* **Equation breaks** -- `split="true"` on an operator is Mathcad wrapping a long
  formula across lines in its *display*. It changes nothing about the tree, so
  the emitted expression is the same as an unbroken one; the sheet is here to
  prove the attribute is safely ignored.
* **Number sets** -- `3 ∈ ℤ`. The set is a bare `<ml:id>` with no `labels`
  attribute at all, so it travels to the runtime as a *string*.
* **Logic** -- `⊕`, `¬`, `≠` alongside the comparisons and connectives already
  supported. Mathcad answers every one of them with a numeric 1 or 0.

`π ∈ ℚ` is the interesting one: Mathcad refuses to answer it numerically (the
sheet's own text says "Rational numbers has to be evaluated symbolically"), so
it carries the symbolic `→` with an *empty* command -- a plain symbolic
evaluation, which maps to SymPy's `simplify`.
"""

import numpy as np
import pytest

from conftest import cached_results, reference, result_refs, run_sheet
from mcad2py import ir
from mcad2py.convert import convert_worksheet
from mcad2py.emit.codegen import echo_expr
from mcad2py.loader import load_mcdx

REFERENCE = reference("breaks-sets-logic")

# ``π ∈ ℚ`` is a symbolic evaluation: its answer lives in the worksheet's own
# ``<ml:symResult>``, so ``result.xml`` caches nothing for it.
SYMBOLIC = 9


@pytest.fixture(scope="module")
def sheet():
    """Convert, execute, and return ``(source, namespace, echoed values)``."""
    return run_sheet(REFERENCE)


def test_sheet_runs_end_to_end(sheet):
    """Nothing unsupported is left, and every evaluated region echoes."""
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == 24


def test_matches_cached_results(sheet):
    """Every numeric echo reproduces Mathcad's cached value.

    Mathcad answers a comparison or a connective with the *number* 1 or 0 where
    Python gives ``True``/``False``. Those are the same value (``bool`` is an
    ``int``), which is why the comparison is numeric rather than by identity.
    """
    _, _, echoed = sheet
    cached, refs = cached_results(REFERENCE), result_refs(REFERENCE)
    # A SymbolicEval prints too, but through ``symbolic_eval_expr`` rather than
    # ``echo_expr`` -- so it has to be counted in to keep the echoes aligned.
    regions = [r for r in convert_worksheet(load_mcdx(REFERENCE)).regions
               if echo_expr(r) is not None or isinstance(r, ir.SymbolicEval)]
    assert len(regions) == len(echoed)

    checked = 0
    for index, region in enumerate(regions):
        if index == SYMBOLIC:
            continue
        value = echoed[index]
        got = float(getattr(value, "magnitude", value))
        want = cached[refs[region.source.region_id]][0]
        assert np.isclose(got, want, rtol=1e-12), (
            f"echo {index} ({echo_expr(region)}): {got} != {want}"
        )
        checked += 1
    assert checked == 23


def test_global_define_is_hoisted_above_the_sheet(sheet):
    """``G ≡ 10`` binds everywhere, including the regions *above* it, so it is
    emitted first -- ahead of even the text region that introduces it."""
    src, ns, _ = sheet
    ws = convert_worksheet(load_mcdx(REFERENCE))
    assert isinstance(ws.regions[0], ir.Define)
    assert ws.regions[0].global_scope and ws.regions[0].target.py == "G"
    assert ns["G"] == 10
    body = src.split("from mcad2py.units import ureg")[1]
    assert body.index("G = 10") < body.index("# constant def")


def test_equation_breaks_are_display_only(sheet):
    """``split="true"`` wraps a formula across lines in Mathcad's display and
    says nothing about the tree -- ``A² + B²`` emits exactly as it would
    unbroken."""
    src, _, _ = sheet
    assert "print(A**2 + B**2)" in src
    assert "print(B - A)" in src


def test_number_sets_travel_as_strings(sheet):
    """The set symbol is an ``<ml:id>`` carrying *no* ``labels`` attribute --
    unique in the schema. Left as a name it would emit an undefined ``ℤ``."""
    src, _, echoed = sheet
    assert "element_of(3, 'ℤ')" in src
    assert (echoed[5], echoed[6], echoed[7], echoed[8]) == (1, 0, 1, 1)


def test_rational_membership_needs_the_symbolic_arrow(sheet):
    """``π ∈ ℚ`` is 0, and no float can say so on its own -- every float is a
    rational. The region carries Mathcad's ``→`` with an empty command, and the
    answer is recovered from the closed form ``nsimplify`` puts back."""
    from mcad2py.runtime import element_of

    _, _, echoed = sheet
    assert echoed[SYMBOLIC] == 0
    ws = convert_worksheet(load_mcdx(REFERENCE))
    symbolic = next(r for r in ws.regions if isinstance(r, ir.SymbolicEval))
    assert symbolic.command == "simplify"
    assert symbolic.result == ir.Number("0")  # Mathcad's own cached <symResult>
    # 3.1 is rational, and stays so however it is written.
    assert element_of(3.1, "ℚ") == 1


def test_logical_xor_is_not_bitwise():
    """Mathcad's ``⊕`` reads any non-zero operand as true, so ``3 ⊕ 2`` is 0 --
    Python's ``^`` would do bitwise arithmetic and answer 1."""
    from mcad2py.runtime import xor

    assert (xor(1, 1), xor(0, 1), xor(0, 0), xor(1, 0)) == (0, 1, 0, 1)
    assert xor(3, 2) == 0 != 3 ^ 2


def test_element_of_rejects_an_unknown_set():
    """A set symbol we don't know is a bug, not something to answer 0 to."""
    from mcad2py.runtime import element_of

    with pytest.raises(ValueError):
        element_of(1, "ℤ+")
