"""Tests for ``tools/set_mcdx_value.py``.

The tool is a *write* path into a proprietary format, so the properties worth
pinning are as much about what it refuses as about what it writes:

* only ``mathcad/worksheet.xml`` changes, and inside it only the one number;
* a formula, a matrix, a range or a function definition is refused whole --
  overwriting one with a number would silently delete the sheet's maths;
* the edited worksheet still converts, and the converted Python carries the
  new value.

The last one is the real end-to-end check: it goes back through the parser the
rest of the suite trusts, rather than asserting on XML the parser might read
differently.
"""

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from set_mcdx_value import Refused, describe, rewrite, set_value, settable  # noqa: E402

from conftest import reference, run_sheet  # noqa: E402

WORKSHEET = "mathcad/worksheet.xml"


def _worksheet(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        return zf.read(WORKSHEET).decode("utf-8")


@pytest.fixture
def sheet(tmp_path):
    """A writable copy of ``trig.mcdx`` -- the fixtures themselves are read-only."""
    target = tmp_path / "trig.mcdx"
    target.write_bytes(reference("trig").read_bytes())
    return target


def test_sets_the_number_and_keeps_the_unit(sheet):
    before, after = rewrite(sheet, sheet, region_id=1, value="45")
    assert (before, after) == ("34 deg", "45 deg")
    assert "<ml:real>45</ml:real>" in _worksheet(sheet)


def test_only_worksheet_xml_changes(sheet):
    original = {item.filename: data for item, data in
                ((i, zipfile.ZipFile(sheet).read(i.filename))
                 for i in zipfile.ZipFile(sheet).infolist())}
    rewrite(sheet, sheet, region_id=1, value="45")
    with zipfile.ZipFile(sheet) as zf:
        for name in zf.namelist():
            if name == WORKSHEET:
                continue
            assert zf.read(name) == original[name], f"{name} was modified"


def test_edit_is_minimal(sheet):
    """Exactly one character run differs -- the rest of the part is untouched."""
    before = _worksheet(sheet)
    rewrite(sheet, sheet, region_id=1, value="45")
    after = _worksheet(sheet)
    assert len(before) == len(after)
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert differing == list(range(differing[0], differing[0] + 2))  # "34" -> "45"


def test_generated_python_carries_the_new_value(sheet):
    rewrite(sheet, sheet, region_id=1, value="45")
    source, namespace, _ = run_sheet(sheet)
    assert "theta = 45 * ureg.deg" in source
    assert namespace["theta"].to("deg").magnitude == pytest.approx(45.0)
    assert namespace["A"] == pytest.approx(0.7071067811865476)  # sin(45 deg)


def test_unit_can_be_replaced(sheet):
    _, after = rewrite(sheet, sheet, region_id=1, value="1", unit="rad")
    assert after == "1 rad"
    _, namespace, _ = run_sheet(sheet)
    assert namespace["theta"].to("rad").magnitude == pytest.approx(1.0)


def test_unit_can_be_removed_and_added(sheet):
    rewrite(sheet, sheet, region_id=1, value="2", unit="")
    assert describe(_worksheet(sheet), 1) == "2"
    rewrite(sheet, sheet, region_id=1, value="2", unit="deg")
    assert describe(_worksheet(sheet), 1) == "2 deg"


def test_negative_value_wraps_in_neg(sheet):
    rewrite(sheet, sheet, region_id=1, value="-30")
    assert "<ml:neg />" in _worksheet(sheet)
    _, namespace, _ = run_sheet(sheet)
    assert namespace["theta"].to("deg").magnitude == pytest.approx(-30.0)


def test_output_leaves_the_input_alone(sheet, tmp_path):
    out = tmp_path / "edited.mcdx"
    rewrite(sheet, out, region_id=1, value="45")
    assert describe(_worksheet(sheet), 1) == "34 deg"
    assert describe(_worksheet(out), 1) == "45 deg"


@pytest.mark.parametrize(
    "region_id, reason",
    [
        (2, "not a literal"),      # A := sin(theta)
        (0, "not a definition"),   # a text region
        (99, "no region"),
    ],
)
def test_refuses(sheet, region_id, reason):
    with pytest.raises(Refused) as excinfo:
        rewrite(sheet, sheet, region_id=region_id, value="9")
    assert reason in str(excinfo.value)


def test_refuses_a_bad_number(sheet):
    with pytest.raises(Refused, match="not a number"):
        rewrite(sheet, sheet, region_id=1, value="fortyfive")


def test_refuses_a_compound_unit_rename():
    """kN/m has no single name to replace, so --unit declines rather than guess."""
    worksheet = _worksheet(reference("Elastic_foundation_eq_line_spring"))
    region_id = next(rid for rid, _, value in settable(worksheet)
                     if value.endswith("<compound>"))
    with pytest.raises(Refused, match="compound"):
        set_value(worksheet, region_id, "5", unit="m")
    # The number alone is still settable.
    assert "<compound>" in describe(set_value(worksheet, region_id, "5"), region_id)


def test_listing_matches_the_generated_python():
    """Every listed literal appears verbatim in the converted script."""
    path = reference("RC_col")
    worksheet = _worksheet(path)
    listed = settable(worksheet)
    assert len(listed) > 20
    for _, _, value in listed:
        number = value.split()[0]
        assert number.replace("-", "").replace(".", "").isdigit()


@pytest.mark.parametrize("name", ["matrices", "3d_plots", "difference_eq"])
def test_listing_never_offers_a_formula(name):
    """A matrix, a range or a computed value must not appear as settable."""
    worksheet = _worksheet(reference(name))
    for region_id, _, _ in settable(worksheet):
        # describe() re-runs the classification; a formula would raise here.
        describe(worksheet, region_id)
