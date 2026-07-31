"""``RC_interface.mcdx`` -- shear capacity of a concrete joint.

The new construct here is the native ``<ml:ComboBoxControl>`` row-selector: the
user picks a row (``SelectedRow``, 0-based) from a named table and its column
value(s) are assigned to the left-hand-side target(s) -- a single id or a
``<ml:matrix>`` of ids. A control with no value table yields the selected row
*name* (a string). The sheet also exercises a few supporting constructs:

  * a ``<ml:program>`` used directly as a scalar value (with ``alsoif`` = elif)
    -> an inline conditional-expression chain;
  * the ``and`` connective and a *boolean* ``=`` (``crack = "Yes"``), which must
    emit ``and`` / ``==`` -- not a SymPy ``Eq`` (the sheet imports no SymPy).

We execute the generated module and compare to Mathcad's cached ``result.xml``.

Note on the cache: ``result.xml`` is internally *inconsistent* -- ``ν_v``'s
cached ``0.525`` implies ``f_ck = 35`` (C35), but the cached ``τ_Rd = 0.70704…``
requires ``f_ctk = 2.5`` (C40), and the live control is ``SelectedRow=6`` = C40.
The worksheet was evidently re-selected to C40 and ``τ_Rd`` recalculated while
``ν_v``'s display stayed stale. We assert the mutually-consistent C40 values
(``f_yd``/``τ_Rd``/``τ_Sd``/``Accept``) and that ``ν_v`` computes ``0.5`` for the
live ``f_ck = 40`` (the stale ``0.525`` is not asserted).
"""

import math
from pathlib import Path

from mcad2py import ir
from mcad2py.convert import convert_file

REFERENCE = Path(__file__).parent.parent / "references" / "RC_interface.mcdx"

# Mathcad's cached results (result.xml), C40 selection.
F_YD = 416.66666666666663      # id 18: f_yd = f_yk / gamma_s
TAU_RD = 0.8995070989304812    # id 27: tau_Rd
TAU_SD = 0.0634                # id 28: tau_Sd
ACCEPT = "ok"                  # id 29: Accept_tau


def _exec() -> dict:
    src = convert_file(REFERENCE, fmt="py")
    ns: dict = {}
    exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return ns


def _src() -> str:
    return convert_file(REFERENCE, fmt="py")


def _mag(x):
    return getattr(x, "magnitude", x)


def test_whole_sheet_runs_and_matches_cache():
    ns = _exec()
    assert math.isclose(_mag(ns["f_yd"]), F_YD)
    assert math.isclose(_mag(ns["tau_Rd"]), TAU_RD)
    assert math.isclose(_mag(ns["tau_Sd"]), TAU_SD)
    assert ns["Accept_tau"] == ACCEPT
    # nu_v for the live f_ck = 40 (cache's 0.525 is a stale pre-C40 leftover).
    assert math.isclose(_mag(ns["nu_v"]), 0.5)


def test_combobox_selects_row_values():
    ns = _exec()
    # Multi-column control -> the selected row maps onto a matrix of targets.
    assert _mag(ns["f_ck"]) == 40 and _mag(ns["f_ctk"]) == 2.5   # C40 (row 6)
    assert _mag(ns["c"]) == 0.5 and _mag(ns["mu"]) == 0.9        # "Fortandet" (row 0)
    # Single-column controls.
    assert _mag(ns["f_yk"]) == 550   # B550 (row 2)
    assert _mag(ns["k"]) == 0.5      # "Dynamic" (row 1)


def test_combobox_empty_values_yields_row_name():
    # A control with no <ml:ComboBoxValues> assigns the selected row *name*.
    assert _exec()["crack"] == "No"


def test_combobox_emits_comment_and_assignments():
    src = _src()
    assert '# Mathcad ComboBoxControl: selected "C40"' in src
    assert "f_ck = 40" in src and "f_ctk = 2.5" in src
    assert "crack = 'No'" in src


def test_program_value_becomes_inline_conditional():
    # sigma_nd := <program with if> (a scalar, no params) -> a ternary, and the
    # `c` program's `alsoif` becomes a chained ternary.
    src = _src()
    assert "sigma_nd = sigma_nd if sigma_nd < 0.6 * f_cd else 0.6 * f_cd" in src
    assert " else 0 if " in src  # the alsoif (elif) branch in `c`


def test_boolean_equal_is_comparison_not_sympy_eq():
    src = _src()
    assert "crack == 'Yes'" in src
    assert "and crack ==" in src   # the `and` connective
    assert "Eq(" not in src        # boolean `=` must not become a SymPy Eq
    assert "from sympy" not in src


def test_combobox_ir_shape():
    import xml.etree.ElementTree as ET

    from mcad2py.parser.regions import _parse_define

    ns = "http://schemas.mathsoft.com/math50"
    elem = ET.fromstring(
        f'<define xmlns="{ns}">'
        f'<matrix rows="2" cols="1"><id labels="VARIABLE">a</id>'
        f'<id labels="VARIABLE">b</id></matrix>'
        f'<ComboBoxControl rows="2" cols="2" SelectedRow="1">'
        f"<ComboBoxRowNames><rowName>lo</rowName><rowName>hi</rowName></ComboBoxRowNames>"
        f"<ComboBoxValues><real>1</real><real>2</real><real>3</real><real>4</real>"
        f"</ComboBoxValues></ComboBoxControl></define>"
    )
    region = _parse_define(elem)
    assert isinstance(region, ir.ComboBoxAssign)
    assert [t.py for t in region.targets] == ["a", "b"]
    assert [v.value for v in region.values] == ["3", "4"]  # row 1 (0-based)
    assert 'selected "hi"' in region.comment
