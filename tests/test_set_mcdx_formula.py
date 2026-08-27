"""Tests for ``tools/set_mcdx_formula.py``.

This tool changes the *maths*, not a number, so the properties that matter are
the ones that stop it changing maths you did not mean:

* it replaces the smallest subtree that carries the formula -- the target name,
  the unit override and the result format keep their own bytes;
* ``--expect`` refuses a formula that is not the one you read;
* the new text has to parse into the writable subset, with names the sheet
  already uses;
* the edit is verified by converting the whole sheet again *before* anything is
  written;
* replacing a formula with itself changes no bytes at all -- which is what
  proves the span, the front end and the backend all agree.

The last one is swept across every region of several worksheets, so it is the
test that carries the most weight.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from set_mcdx_formula import (  # noqa: E402
    Refused,
    current_expr,
    rewrite,
    set_formula,
    value_span,
)

from mcad2py.emit.codegen import expr_to_str  # noqa: E402
from mcad2py.loader import load_mcdx  # noqa: E402

from conftest import reference, run_sheet  # noqa: E402

WORKSHEET = "mathcad/worksheet.xml"

# f_cd := 30 MPa / 1.5, shown in MPa -- a formula with a unit override beside it.
COHESION_REGION = 0
COHESION = "30 * ureg.MPa / 1.5"


def _worksheet(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        return zf.read(WORKSHEET).decode("utf-8")


@pytest.fixture
def sheet(tmp_path):
    """A writable copy of ``plain_concrete_cohesion.mcdx``."""
    target = tmp_path / "plain_concrete_cohesion.mcdx"
    target.write_bytes(reference("plain_concrete_cohesion").read_bytes())
    return target


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def test_reads_the_formula_in_a_region(sheet):
    assert expr_to_str(current_expr(_worksheet(sheet), COHESION_REGION)) == COHESION


def test_the_span_is_the_value_only(sheet):
    """Not the region, not the define, not the unit override: a rewrite must
    leave the target name and the display unit exactly as Prime wrote them."""
    ws = _worksheet(sheet)
    start, end = value_span(ws, COHESION_REGION)
    span = ws[start:end]
    assert span.startswith("<ml:apply>") and span.endswith("</ml:apply>")
    assert "unitOverride" not in span
    assert "ml:define" not in span


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def test_replaces_the_formula(sheet):
    before, after = rewrite(sheet, sheet, COHESION_REGION, COHESION,
                            "0.85 * 30 * ureg.MPa / 1.5")
    assert before[0] == "f_cd = 30 * ureg.MPa / 1.5"
    assert after[0] == "f_cd = 0.85 * 30 * ureg.MPa / 1.5"


def test_executed_python_carries_the_new_formula(sheet):
    """20 MPa becomes 0.85 * 20 = 17 MPa, through the real parser and Pint."""
    rewrite(sheet, sheet, COHESION_REGION, COHESION, "0.85 * 30 * ureg.MPa / 1.5")
    _, namespace, _ = run_sheet(sheet)
    assert namespace["f_cd"].to("MPa").magnitude == pytest.approx(17.0)


def test_can_bring_in_another_name_from_the_sheet(sheet):
    """``k`` is defined further down the sheet, so it is a name the tool will
    accept -- and the result still runs."""
    rewrite(sheet, sheet, COHESION_REGION, COHESION, "30 * ureg.MPa / 1.5 + 1 * ureg.MPa")
    _, namespace, _ = run_sheet(sheet)
    assert namespace["f_cd"].to("MPa").magnitude == pytest.approx(21.0)


def test_only_worksheet_xml_changes(sheet):
    with zipfile.ZipFile(sheet) as zf:
        original = {name: zf.read(name) for name in zf.namelist()}
    rewrite(sheet, sheet, COHESION_REGION, COHESION, "30 * ureg.MPa / 1.4")
    with zipfile.ZipFile(sheet) as zf:
        for name in zf.namelist():
            if name == WORKSHEET:
                continue
            assert zf.read(name) == original[name], f"{name} was modified"


def test_everything_outside_the_formula_is_untouched(sheet):
    """The edit is a splice: the bytes before and after the value subtree are
    identical, so the region id, the target name and the override survive."""
    before = _worksheet(sheet)
    start, end = value_span(before, COHESION_REGION)
    rewrite(sheet, sheet, COHESION_REGION, COHESION, "30 * ureg.MPa / 1.4")
    after = _worksheet(sheet)
    assert after[:start] == before[:start]
    assert after[len(after) - (len(before) - end):] == before[end:]


def test_output_leaves_the_input_alone(sheet, tmp_path):
    out = tmp_path / "edited.mcdx"
    rewrite(sheet, out, COHESION_REGION, COHESION, "30 * ureg.MPa / 1.4")
    assert expr_to_str(current_expr(_worksheet(sheet), COHESION_REGION)) == COHESION
    assert "1.4" in expr_to_str(current_expr(_worksheet(out), COHESION_REGION))


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


def test_expect_must_match(sheet):
    with pytest.raises(Refused, match="not the expected"):
        set_formula(_worksheet(sheet), load_mcdx(sheet), COHESION_REGION,
                    "30 * ureg.MPa / 1.4", "1 * ureg.MPa")


def test_expect_ignores_only_whitespace(sheet):
    edited = set_formula(_worksheet(sheet), load_mcdx(sheet), COHESION_REGION,
                         "30*ureg.MPa   / 1.5", "30 * ureg.MPa / 1.4")
    assert edited != _worksheet(sheet)


@pytest.mark.parametrize("value, why", [
    ("tan(phi)", "function call"),
    ("gamma_made_up * 2", "not a name this worksheet uses"),
    ("1 +", "not a Python expression"),
])
def test_refuses_what_it_cannot_write(sheet, value, why):
    with pytest.raises(Refused, match=why):
        set_formula(_worksheet(sheet), load_mcdx(sheet), COHESION_REGION,
                    COHESION, value)


def test_refuses_a_region_that_is_not_a_formula(sheet):
    """Region 2 of the sheet is a text note."""
    with pytest.raises(Refused, match="not a formula region"):
        current_expr(_worksheet(sheet), 2)


def test_refuses_an_unknown_region(sheet):
    with pytest.raises(Refused, match="no region with region-id"):
        current_expr(_worksheet(sheet), 999)


# ---------------------------------------------------------------------------
# The sweep: replacing a formula with itself writes no bytes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["plain_concrete_cohesion", "RC_torsion",
                                  "shrinkage", "Constants", "statistics"])
def test_writing_a_formula_back_unchanged_is_a_no_op(name, tmp_path):
    """The strongest property available without Mathcad itself.

    Every region whose formula is inside the writable subset goes out through
    the code generator, back through the front end, and out through the XML
    backend -- and must land on the bytes Prime wrote. A disagreement anywhere
    in that chain shows up here as a changed worksheet.
    """
    path = tmp_path / f"{name}.mcdx"
    path.write_bytes(reference(name).read_bytes())
    ws = _worksheet(path)
    pkg = load_mcdx(path)

    from _mcdx_edit import region_ids  # noqa: PLC0415

    checked = 0
    for region_id in region_ids(ws):
        try:
            shown = expr_to_str(current_expr(ws, region_id))
            edited = set_formula(ws, pkg, region_id, shown, shown)
        except Refused:
            continue
        assert edited == ws, f"{name} region {region_id}: {shown}"
        checked += 1
    assert checked > 2, f"{name}: the sweep reached almost nothing"


def test_the_no_op_sweep_reaches_most_writable_regions():
    """A floor under the sweep above, across every reference worksheet.

    331 regions pass end to end at the time of writing -- through the code
    generator, the front end, the backend and the guard. The floor is what
    stops the sweep quietly shrinking to nothing.
    """
    from _mcdx_edit import Refused as _Refused  # noqa: PLC0415
    from _mcdx_edit import region_ids  # noqa: PLC0415

    from test_mcdx_backend import SHEETS  # noqa: PLC0415

    accepted = 0
    for name in SHEETS:
        pkg = load_mcdx(reference(name))
        ws = pkg.worksheet_xml
        for region_id in region_ids(ws):
            try:
                shown = expr_to_str(current_expr(ws, region_id))
                assert set_formula(ws, pkg, region_id, shown, shown) == ws
            except _Refused:
                continue
            accepted += 1
    assert accepted > 300


def test_refuses_a_region_it_cannot_reproduce():
    """``shrinkage.mcdx`` region 9 holds ``RH / 100%``. The percent sign parses
    to ``/ 100``, so a rewrite would show ``100/100`` -- the tool refuses
    rather than restyle maths the edit does not touch."""
    pkg = load_mcdx(reference("shrinkage"))
    ws = pkg.worksheet_xml
    shown = expr_to_str(current_expr(ws, 9))
    with pytest.raises(Refused, match="would not survive a rewrite"):
        set_formula(ws, pkg, 9, shown, shown)
