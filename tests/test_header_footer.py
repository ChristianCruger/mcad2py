"""Worksheet headers and footers are preserved as display-only context."""

from pathlib import Path

import nbformat

from mcad2py import ir
from mcad2py.cli import main
from mcad2py.convert import _context_regions, convert_file, convert_worksheet
from mcad2py.emit.codegen import context_comment_lines
from mcad2py.emit.py_backend import to_python
from mcad2py.loader import McdxPackage, load_mcdx
from mcad2py.parser.regions import _field_pattern, parse_worksheet

REFERENCE = Path(__file__).parent.parent / "references" / "header_footer.mcdx"


def test_header_and_footer_are_parsed_separately_from_the_body():
    ws = convert_worksheet(load_mcdx(REFERENCE))

    assert [type(region) for region in ws.header] == [
        ir.TextRegion,
        ir.TextRegion,
        ir.TextRegion,
        ir.Evaluate,
        ir.Define,
        ir.Evaluate,
        ir.Evaluate,
    ]
    assert [region.text for region in ws.header[:3]] == [
        "Author: John Smith",
        "Date: 24/12/1990",
        "Project: Mcad test",
    ]
    assert [region.text for region in ws.footer] == ["Footer"]


def test_non_page_field_text_is_kept_and_page_text_is_omitted():
    xml = """<footer xmlns="http://schemas.mathsoft.com/worksheet50">
        <regions>
            <region top="1" left="1">
                <fieldText><text><FlowDocument><Paragraph>Revision A</Paragraph></FlowDocument></text></fieldText>
            </region>
            <region top="2" left="1">
                <fieldText><text><FlowDocument><Paragraph>Page 1 of 2</Paragraph></FlowDocument></text><pageNumber /></fieldText>
            </region>
        </regions>
    </footer>"""

    ws = parse_worksheet(xml)
    assert [region.text for region in ws.regions] == ["Revision A"]


def test_a_page_field_loses_only_the_paragraph_its_template_renders():
    """A footer field can hold a project name beside the page number. Dropping
    the whole region for the number would take the name with it."""
    xml = """<footer xmlns="http://schemas.mathsoft.com/worksheet50">
        <regions>
            <region top="1" left="1">
                <fieldText>
                    <text><FlowDocument>
                        <Paragraph>Project 12345</Paragraph>
                        <Paragraph>Page 1 of 2</Paragraph>
                    </FlowDocument></text>
                    <pageNumber template="Page_@PageNo_of_@PagesTotal" />
                </fieldText>
            </region>
        </regions>
    </footer>"""

    ws = parse_worksheet(xml)
    assert [region.text for region in ws.regions] == ["Project 12345"]


def test_a_template_matches_whatever_language_the_sheet_is_in():
    """The match is built from the template, not from the English words."""
    pattern = _field_pattern("Seite_@PageNo_von_@PagesTotal")

    assert pattern.fullmatch("Seite 3 von 12")
    assert not pattern.fullmatch("Seite 3")
    assert _field_pattern("") is None
    assert _field_pattern("   ") is None


def test_multiline_display_math_stays_fully_commented():
    matrix = ir.MatrixLiteral(
        rows=2,
        cols=10,
        elements=[ir.Number("123456789") for _ in range(20)],
    )
    region = ir.Define(target=ir.Name("M", "M"), value=matrix)

    lines = context_comment_lines("header", [region])
    assert len(lines) > 2
    assert all(line.startswith("#") for line in lines)


def test_package_positional_arguments_keep_their_original_meaning():
    package = McdxPackage("worksheet", "results", "integration")
    assert package.worksheet_xml == "worksheet"
    assert package.result_xml == "results"
    assert package.integration_xml == "integration"


def test_python_output_includes_context_but_not_page_fields(capsys):
    source = convert_file(REFERENCE, fmt="py")

    expected = """# Mathcad header
# Author: John Smith
# Date: 24/12/1990
# Project: Mcad test
# [display math] x**2 + y**2
# [display math] X = 1
# [display math] X**2
# [display math] 1 + 1"""
    assert expected in source
    assert source.rstrip().endswith("# Mathcad footer\n# Footer")
    assert "Page 1 of 2" not in source
    compile(source, "<generated>", "exec")

    namespace: dict = {}
    exec(source, namespace)
    output = capsys.readouterr().out
    assert "X" not in namespace
    assert output.count("name 'X' is not defined") == 2


def test_notebook_output_uses_non_executable_comment_cells():
    notebook = nbformat.reads(convert_file(REFERENCE), as_version=4)
    nbformat.validate(notebook)

    header = next(cell for cell in notebook.cells if "Mathcad header" in cell.source)
    assert header.cell_type == "code"
    assert all(line.startswith("#") for line in header.source.splitlines())
    assert notebook.cells[-1].source == "# Mathcad footer\n# Footer"


def test_context_can_be_excluded_from_both_formats():
    source = convert_file(REFERENCE, fmt="py", include_header_footer=False)
    notebook = convert_file(
        REFERENCE,
        fmt="notebook",
        include_header_footer=False,
    )

    assert "Mathcad header" not in source
    assert "Author: John Smith" not in source
    assert "Mathcad header" not in notebook
    assert "Author: John Smith" not in notebook


def test_cli_can_exclude_header_and_footer(capsys):
    code = main(
        [
            "convert",
            str(REFERENCE),
            "-f",
            "py",
            "-o",
            "-",
            "--no-header-footer",
        ]
    )
    output = capsys.readouterr().out

    assert code == 0
    assert "Mathcad header" not in output
    assert "Author: John Smith" not in output


def test_a_header_that_cannot_be_parsed_does_not_stop_the_conversion(monkeypatch):
    """Document context is decoration. Before it was parsed at all, no header
    could stop a sheet converting -- that has to stay true."""
    import mcad2py.convert as convert

    def explode(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(convert, "parse_worksheet", explode)
    regions = _context_regions(
        "<header />",
        {},
        "header",
        text_resolver=lambda rels: (lambda idref: ""),
        image_resolver=lambda rels: (lambda idref: None),
    )

    assert [type(region) for region in regions] == [ir.UnsupportedRegion]
    assert regions[0].note == "header could not be parsed: boom"


def test_a_broken_header_still_yields_a_module_that_loads(monkeypatch):
    real = convert_worksheet(load_mcdx(REFERENCE))
    broken = ir.Worksheet(
        regions=real.regions,
        header=[ir.UnsupportedRegion(note="header could not be parsed: boom")],
    )
    source = to_python(broken)

    assert "header could not be parsed: boom" in source
    compile(source, "<generated>", "exec")


def test_a_missing_header_part_gives_no_context():
    assert (
        _context_regions(
            None,
            {},
            "header",
            text_resolver=lambda rels: (lambda idref: ""),
            image_resolver=lambda rels: (lambda idref: None),
        )
        == []
    )


def test_only_math_carries_the_display_math_label():
    """`[display math] TODO unsupported: ...` would claim the note was an
    equation; a plot is not display math either."""
    lines = context_comment_lines(
        "header",
        [
            ir.TextRegion(text="Project: Mcad test"),
            ir.Define(target=ir.Name("X", "X"), value=ir.Number("1")),
            ir.UnsupportedRegion(note="header could not be parsed: boom"),
        ],
    )

    assert lines == [
        "# Mathcad header",
        "# Project: Mcad test",
        "# [display math] X = 1",
        "# TODO unsupported: header could not be parsed: boom",
    ]


def test_a_comment_line_never_carries_trailing_whitespace():
    lines = context_comment_lines(
        "header",
        [ir.TextRegion(text="Project: Mcad test\n\nDate: 24/12/1990")],
    )

    assert lines == [
        "# Mathcad header",
        "# Project: Mcad test",
        "#",
        "# Date: 24/12/1990",
    ]
    assert all(line == line.rstrip() for line in lines)
