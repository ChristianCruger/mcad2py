"""Identifiers Mathcad left **auto-labelled** (``labels="*"``).

A ``<ml:id>`` normally says what it is -- ``labels="UNIT"``, ``"VARIABLE"``,
``"FUNCTION"``. A worksheet **converted from legacy .xmcd** is full of
``labels="*"`` instead: Mathcad 15's schema didn't carry the distinction, so
the Prime converter leaves the name uncommitted and resolves it from context.

That breaks any slot that is a unit by definition. ``MPa`` in a display
override arrived as a plain ``Name`` rather than a ``UnitRef``, so the echo
emitted ``x / (MPa)`` -- a ``NameError`` against a name nothing defines --
instead of ``disp(x, ureg.MPa)``.

The rule has to stay tied to the *slot*, not the name: the same converted sheet
auto-labels its loop index ``i``, which is emphatically not a unit.
"""

import pytest

from mcad2py import ir
from mcad2py.emit.codegen import echo_expr
from mcad2py.parser.regions import parse_worksheet

_WS = (
    '<worksheet xmlns="http://schemas.mathsoft.com/worksheet50" '
    'xmlns:ml="http://schemas.mathsoft.com/math50"><regions>{}</regions></worksheet>'
)


def _eval_region(unit_xml: str) -> ir.Evaluate:
    """A ``σ =`` echo whose unit override is ``unit_xml``."""
    ws = parse_worksheet(
        _WS.format(
            '<region top="10" left="0"><math><ml:eval>'
            '<ml:id labels="VARIABLE">sigma</ml:id>'
            f"<ml:unitOverride>{unit_xml}</ml:unitOverride>"
            "</ml:eval></math></region>"
        )
    )
    region = ws.regions[0]
    assert isinstance(region, ir.Evaluate)
    return region


def test_auto_labelled_unit_override_is_a_unit():
    """The bug: ``labels="*"`` on ``MPa`` emitted a bare, undefined name."""
    region = _eval_region('<ml:id labels="*" xml:space="preserve">MPa</ml:id>')
    assert isinstance(region.display_unit, ir.UnitRef)
    assert echo_expr(region) == "disp((sigma), ureg.MPa)"


def test_explicitly_labelled_unit_still_works():
    region = _eval_region('<ml:id labels="UNIT" xml:space="preserve">MPa</ml:id>')
    assert isinstance(region.display_unit, ir.UnitRef)
    assert echo_expr(region) == "disp((sigma), ureg.MPa)"


def test_auto_labels_are_reinterpreted_inside_a_compound_unit():
    """``kN·m`` reaches the IR as a ``<mult>`` of two ids, so the rewrite has
    to reach through the operator, not just handle a lone identifier."""
    region = _eval_region(
        "<ml:apply><ml:mult />"
        '<ml:id labels="*" xml:space="preserve">kN</ml:id>'
        '<ml:id labels="*" xml:space="preserve">m</ml:id>'
        "</ml:apply>"
    )
    assert echo_expr(region) == "disp((sigma), ureg.kN * ureg.m)"


def test_a_numeric_scale_override_is_untouched():
    """A pure numeric scale (Mathcad showing a dimensionless value as ×10⁻⁶)
    still divides -- ``.to`` only applies to a dimensioned quantity."""
    region = _eval_region("<ml:real>1000</ml:real>")
    assert region.display_unit is not None
    assert echo_expr(region) == "(sigma) / (1000)"


def test_an_explicit_variable_in_a_unit_slot_stays_a_variable():
    """A real variable used as a display scale is legal and already divides
    correctly; only the *uncommitted* ``*`` label is reinterpreted."""
    region = _eval_region('<ml:id labels="VARIABLE" xml:space="preserve">scale</ml:id>')
    assert isinstance(region.display_unit, ir.Name)
    assert echo_expr(region) == "(sigma) / (scale)"


def test_an_auto_labelled_name_outside_a_unit_slot_is_a_variable():
    """The counter-case that forbids a name-based rule: the same converted
    sheet auto-labels its loop index ``i``, which must stay a variable."""
    ws = parse_worksheet(
        _WS.format(
            '<region top="10" left="0"><math><ml:define>'
            '<ml:id labels="VARIABLE">y</ml:id>'
            '<ml:id labels="*" xml:space="preserve">i</ml:id>'
            "</ml:define></math></region>"
        )
    )
    define = ws.regions[0]
    assert isinstance(define, ir.Define)
    assert isinstance(define.value, ir.Name)
    assert define.value.py == "i"


@pytest.mark.parametrize("label", ["*", "UNIT"])
def test_plot_axis_unit_honours_the_label(label):
    """A plot axis's unit override is a unit slot too."""
    ws = parse_worksheet(
        _WS.format(
            '<region top="10" left="0"><plot><xyPlot><axes>'
            "<xAxis><plotEquations><plotEquation>"
            '<math><ml:id xml:space="preserve">x</ml:id></math>'
            "<math><ml:placeholder /></math>"
            "</plotEquation></plotEquations></xAxis>"
            "<yAxis><plotEquations><plotEquation>"
            '<math><ml:id xml:space="preserve">x</ml:id></math>'
            f'<math><ml:id labels="{label}" xml:space="preserve">MPa</ml:id></math>'
            "</plotEquation></plotEquations></yAxis>"
            "</axes></xyPlot></plot></region>"
        )
    )
    plot = ws.regions[0]
    assert isinstance(plot, ir.Plot)
    assert isinstance(plot.traces[0].y_unit, ir.UnitRef)
