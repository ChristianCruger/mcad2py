"""Tests for ``tools/strip_mcdx_metadata.py``.

The invariant that matters most here was learned the hard way: an earlier
version of the tool replaced ``docProps/app.xml`` with an OOXML-style stub,
assuming the name meant what it does in a .docx. It does not -- Prime keeps its
*format manifest* there (``serializationVersion``, ``engineVersion``,
``schemaPropertiesList``), and without it the application refuses the file with
"The file type is not supported." So the first test below pins down exactly
which parts the tool is allowed to touch, and every other part -- app.xml above
all -- must come through byte-identical.
"""

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from strip_mcdx_metadata import inspect, strip  # noqa: E402

# The parts the tool may rewrite. Anything else must survive untouched.
REWRITABLE = {"docProps/core.xml", "mathcad/header.xml", "mathcad/footer.xml"}

APP_XML = (
    b'<?xml version="1.0" encoding="utf-8"?><properties '
    b'xmlns="http://schemas.mathsoft.com/extended-properties">'
    b"<appVersion>11.0.1.0</appVersion>"
    b'<serializationVersion architecture="x64" Culture="en-DK" '
    b'UiCulture="en-US">11.0.0.1</serializationVersion>'
    b"<engineVersion>11.0.1.7</engineVersion>"
    b"<schemaPropertiesList>"
    b'<schemaProperties name="Worksheet" version="5.10.7" />'
    b"</schemaPropertiesList></properties>"
)
CORE_XML = (
    b'<?xml version="1.0" encoding="utf-8"?>\r\n'
    b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/'
    b'2006/metadata/core-properties">\r\n'
    b'  <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">DOMAIN\\user'
    b"</dc:creator>\r\n"
    b"  <cp:lastModifiedBy>DOMAIN\\someone_else</cp:lastModifiedBy>\r\n"
    b"  <cp:revision>14</cp:revision>\r\n"
    b"</cp:coreProperties>"
)
FOOTER_XML = (
    b'<footer xmlns="http://schemas.mathsoft.com/worksheet50"><regions>'
    b'<region region-id="64"><fieldText><text><FlowDocument>'
    # \xe2\x80\x94 is an em dash in UTF-8 -- footers are rarely pure ASCII.
    b"<Paragraph>Project 12345 \xe2\x80\x94 30/06/2026</Paragraph>"
    b"</FlowDocument></text></fieldText></region></regions></footer>"
)
WORKSHEET_XML = b'<worksheet xmlns="http://schemas.mathsoft.com/worksheet50"/>'
RESULT_XML = b'<resultsList xmlns="http://schemas.mathsoft.com/result10"/>'


@pytest.fixture
def sheet(tmp_path: Path) -> Path:
    """A minimal .mcdx carrying every part the tool cares about."""
    path = tmp_path / "sample.mcdx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mathcad/worksheet.xml", WORKSHEET_XML)
        zf.writestr("mathcad/result.xml", RESULT_XML)
        zf.writestr("docProps/core.xml", CORE_XML)
        zf.writestr("docProps/app.xml", APP_XML)
        zf.writestr("mathcad/footer.xml", FOOTER_XML)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    return path


def _parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {n: zf.read(n) for n in zf.namelist()}


def test_only_the_metadata_parts_are_rewritten(sheet):
    """Regression: ``docProps/app.xml`` is Prime's *format manifest*, not an
    Office properties part. Rewriting it makes Prime reject the worksheet."""
    before = _parts(sheet)
    strip(sheet)
    after = _parts(sheet)

    assert set(before) == set(after), "no part may be added or dropped"
    changed = {n for n in before if before[n] != after[n]}
    assert changed <= REWRITABLE, f"tool rewrote parts it must not: {changed - REWRITABLE}"
    assert after["docProps/app.xml"] == APP_XML
    assert b"serializationVersion" in after["docProps/app.xml"]


def test_the_maths_is_untouched(sheet):
    """worksheet.xml and result.xml carry every value the tests assert on."""
    strip(sheet)
    after = _parts(sheet)
    assert after["mathcad/worksheet.xml"] == WORKSHEET_XML
    assert after["mathcad/result.xml"] == RESULT_XML


def test_core_fields_are_blanked_in_place(sheet):
    """The identifying text goes; the declaration, namespaces and revision stay."""
    strip(sheet)
    core = _parts(sheet)["docProps/core.xml"]
    assert b"DOMAIN" not in core
    assert b"<cp:revision>14</cp:revision>" in core     # untouched
    assert core.startswith(b'<?xml version="1.0" encoding="utf-8"?>')
    assert b'xmlns:dc="http://purl.org/dc/elements/1.1/"' in core
    assert b"<cp:lastModifiedBy></cp:lastModifiedBy>" in core


def test_author_can_be_substituted(sheet):
    strip(sheet, author="A. Engineer")
    core = _parts(sheet)["docProps/core.xml"]
    assert b"<cp:lastModifiedBy>A. Engineer</cp:lastModifiedBy>" in core
    assert b"DOMAIN" not in core


def test_footer_regions_are_emptied(sheet):
    """The printed footer carries a project number and date; emptying the region
    list is the state Prime itself writes for a sheet without one."""
    strip(sheet)
    footer = _parts(sheet)["mathcad/footer.xml"]
    assert b"Project 12345" not in footer
    assert b"<regions />" in footer
    assert footer.startswith(b"<footer") and footer.endswith(b"</footer>")


def test_inspect_reports_then_reports_clean(sheet):
    findings = inspect(sheet)
    assert any("creator" in f for f in findings)
    assert any("footer" in f for f in findings)
    strip(sheet)
    assert inspect(sheet) == []


def test_strip_is_idempotent(sheet):
    assert strip(sheet) is True
    once = _parts(sheet)
    assert strip(sheet) is False, "a second pass must find nothing to change"
    assert _parts(sheet) == once


def test_a_sheet_with_no_metadata_parts_is_left_alone(tmp_path):
    path = tmp_path / "bare.mcdx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mathcad/worksheet.xml", WORKSHEET_XML)
    before = _parts(path)
    assert strip(path) is False
    assert _parts(path) == before
