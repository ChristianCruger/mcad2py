"""Tests for ``tools/set_mcdx_literal.py``.

The tool changes a number *inside* a formula, so the properties worth pinning
are the guards that stop it changing the wrong one:

* every number in a region is found, in the order an agent will index them,
  and each is classified by the role it plays in the expression tree;
* ``--expect`` refuses a mismatch, which is what makes a stale index safe;
* an exponent, a subscript and a display scale are gated, because editing one
  changes what the formula *means*;
* the edit is one character run in ``mathcad/worksheet.xml`` and nothing else;
* the edited worksheet still converts, and the executed Python carries the new
  number through to the result.

The last one is the real end-to-end check: it goes back through the parser the
rest of the suite trusts, rather than asserting on XML the parser might read
differently.
"""

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from set_mcdx_literal import (  # noqa: E402
    Refused,
    literals,
    rewrite,
    set_literal,
)

from conftest import reference, run_sheet  # noqa: E402

WORKSHEET = "mathcad/worksheet.xml"

# f_cd := 30 MPa / 1.5 -- the smallest formula with two numbers of two kinds.
COHESION_REGION = 0


def _worksheet(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        return zf.read(WORKSHEET).decode("utf-8")


@pytest.fixture
def sheet(tmp_path):
    """A writable copy of ``plain_concrete_cohesion.mcdx``."""
    target = tmp_path / "plain_concrete_cohesion.mcdx"
    target.write_bytes(reference("plain_concrete_cohesion").read_bytes())
    return target


def test_lists_every_number_with_its_role(sheet):
    found = literals(_worksheet(sheet), COHESION_REGION)
    assert [(lit.index, lit.value, lit.unit, lit.kind) for lit in found] == [
        (0, "30", "MPa", "value"),
        (1, "1.5", "", "factor"),
    ]
    assert all(lit.editable for lit in found)


def test_sets_the_number_inside_the_formula(sheet):
    before, after = rewrite(sheet, sheet, region_id=COHESION_REGION, index=1,
                            expect="1.5", value="1.4")
    assert before[0] == "f_cd = 30 * ureg.MPa / 1.5"
    assert after[0] == "f_cd = 30 * ureg.MPa / 1.4"


def test_only_worksheet_xml_changes(sheet):
    with zipfile.ZipFile(sheet) as zf:
        original = {name: zf.read(name) for name in zf.namelist()}
    rewrite(sheet, sheet, region_id=COHESION_REGION, index=1,
            expect="1.5", value="1.4")
    with zipfile.ZipFile(sheet) as zf:
        for name in zf.namelist():
            if name == WORKSHEET:
                continue
            assert zf.read(name) == original[name], f"{name} was modified"


def test_edit_is_minimal(sheet):
    """Exactly one character differs -- the rest of the part is untouched."""
    before = _worksheet(sheet)
    rewrite(sheet, sheet, region_id=COHESION_REGION, index=1,
            expect="1.5", value="1.4")
    after = _worksheet(sheet)
    assert len(before) == len(after)
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert len(differing) == 1  # "1.5" -> "1.4"


def test_executed_python_carries_the_new_number(sheet):
    """f_cd = 30 MPa / 1.5 = 20 MPa becomes 30 MPa / 1.5 -> /1.25 = 24 MPa."""
    rewrite(sheet, sheet, region_id=COHESION_REGION, index=1,
            expect="1.5", value="1.25")
    _, namespace, _ = run_sheet(sheet)
    assert namespace["f_cd"].to("MPa").magnitude == pytest.approx(24.0)


def test_expect_must_match(sheet):
    with pytest.raises(Refused, match="not the expected"):
        set_literal(_worksheet(sheet), COHESION_REGION, index=1,
                    expect="30", value="1.4")


def test_expect_must_be_a_number(sheet):
    with pytest.raises(Refused, match="is not a number"):
        set_literal(_worksheet(sheet), COHESION_REGION, index=1,
                    expect="one-and-a-half", value="1.4")


def test_index_out_of_range(sheet):
    with pytest.raises(Refused, match="out of range"):
        set_literal(_worksheet(sheet), COHESION_REGION, index=7,
                    expect="1.5", value="1.4")


def test_accepts_a_negative_value(sheet):
    """Prime stores a negative straight in <ml:real>; no <ml:neg/> is needed."""
    edited = set_literal(_worksheet(sheet), COHESION_REGION, index=1,
                         expect="1.5", value="-1.4")
    assert "<ml:real>-1.4</ml:real>" in edited


def test_renames_the_unit_of_a_scaled_number(sheet):
    before, after = rewrite(sheet, sheet, region_id=COHESION_REGION, index=0,
                            expect="30", value="35", unit="kPa")
    assert before[0] == "f_cd = 30 * ureg.MPa / 1.5"
    assert after[0] == "f_cd = 35 * ureg.kPa / 1.5"


def test_unit_needs_a_scaled_number(sheet):
    with pytest.raises(Refused, match="no unit of its own"):
        set_literal(_worksheet(sheet), COHESION_REGION, index=1,
                    expect="1.5", value="1.4", unit="kPa")


def test_output_leaves_the_input_alone(sheet, tmp_path):
    out = tmp_path / "edited.mcdx"
    rewrite(sheet, out, region_id=COHESION_REGION, index=1,
            expect="1.5", value="1.4")
    assert "<ml:real>1.5</ml:real>" in _worksheet(sheet)
    assert "<ml:real>1.4</ml:real>" in _worksheet(out)


@pytest.mark.parametrize(
    "name, region_id, index, value, kind",
    [
        ("RC_torsion", 26, 1, "2", "exponent"),       # the 2 in cm**2
        ("RC_torsion", 26, 7, "2", "display-scale"),  # inside <ml:unitOverride>
        ("matrices", 17, 0, "1", "index"),            # a subscript
        ("shrinkage", 9, 3, "3", "exponent"),         # a power
    ],
)
def test_classifies_and_gates_the_risky_kinds(name, region_id, index, value, kind):
    """These change what the formula means, so they need --allow-kind."""
    worksheet = _worksheet(reference(name))
    target = literals(worksheet, region_id)[index]
    assert (target.value, target.kind) == (value, kind)
    assert not target.editable

    with pytest.raises(Refused, match=kind):
        set_literal(worksheet, region_id, index, expect=value, value="4")
    edited = set_literal(worksheet, region_id, index, expect=value, value="4",
                         allow_kinds=(kind,))
    assert edited != worksheet


def test_matrix_cells_are_editable():
    """A literal matrix's cells are ordinary values, not gated."""
    worksheet = _worksheet(reference("statistics"))
    cells = [lit for lit in literals(worksheet, 54) if lit.kind == "matrix-element"]
    assert len(cells) == 50 and all(lit.editable for lit in cells)
    assert any(lit.value.startswith("-") for lit in cells)


@pytest.mark.parametrize("name", ["RC_col", "matrices", "statistics"])
def test_every_listed_number_reads_back(name):
    """Each index addresses a number that is really there, sheet-wide."""
    worksheet = _worksheet(reference(name))
    from _mcdx_edit import region_ids  # noqa: PLC0415

    seen = 0
    for region_id in region_ids(worksheet):
        # Three per region is enough breadth; a 50-cell matrix would only make
        # the same point fifty times, slowly.
        for lit in literals(worksheet, region_id)[:3]:
            float(lit.value)  # every listed value parses as a real
            # Setting it to itself is a no-op, which proves the span is right.
            assert set_literal(worksheet, region_id, lit.index, expect=lit.value,
                               value=lit.value,
                               allow_kinds=("exponent", "index",
                                            "display-scale")) == worksheet
            seen += 1
    assert seen > 10
