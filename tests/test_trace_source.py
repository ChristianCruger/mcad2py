"""``--trace-source``: back-references from generated code to the original
Mathcad worksheet (``# mcdx region <id>``), plus, when present:

- a renamed target's original Mathcad name (Greek/subscripted identifiers), and
- an Input/Output alias from ``mathcad/integration.xml`` (set via Prime's
  Input/Output panel, for Application Automation / MathcadPy).

The flag is opt-in and must not change anyone's existing output, so the first
test pins that off-by-default parity; the rest exercise the annotation itself.
"""

from pathlib import Path

from mcad2py import ir
from mcad2py.cli import main
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.emit.codegen import source_comment
from mcad2py.emit.notebook_backend import to_notebook
from mcad2py.emit.py_backend import to_python
from mcad2py.loader import load_mcdx

AREAS = Path(__file__).parent.parent / "references" / "collapsable-area.mcdx"
RC_COL = Path(__file__).parent.parent / "references" / "RC_col.mcdx"
IO = Path(__file__).parent.parent / "references" / "io.mcdx"


def test_default_output_is_unchanged_by_the_feature():
    plain = convert_file(AREAS, fmt="py")
    assert convert_file(AREAS, fmt="py", trace_source=False) == plain
    assert "mcdx region" not in plain


def test_source_is_always_populated_regardless_of_the_flag():
    ws = convert_worksheet(load_mcdx(AREAS))
    # Known region-ids from references/collapsable-area.mcdx's worksheet.xml,
    # in reading order: two texts flanking `x`, then a text/`y` pair inside the
    # (flattened) area, then a trailing text and the final evaluation. This
    # sheet has no Input/Output tags, so io_kind/io_alias stay None.
    kinds_and_ids = [(type(r).__name__, r.source.region_id) for r in ws.regions]
    assert kinds_and_ids == [
        ("TextRegion", 0),
        ("Define", 1),
        ("TextRegion", 3),
        ("Define", 4),
        ("TextRegion", 5),
        ("Evaluate", 6),
    ]
    assert all(r.source.io_kind is None for r in ws.regions)


def test_py_backend_annotates_each_statement_when_enabled():
    ws = convert_worksheet(load_mcdx(AREAS))
    src = to_python(ws, trace_source=True)
    assert "# mcdx region 1" in src
    assert "# mcdx region 4" in src
    lines = src.splitlines()
    x_line = next(i for i, l in enumerate(lines) if l == "x = 1")
    assert lines[x_line - 1] == "# mcdx region 1"


def test_renamed_target_shows_its_original_mathcad_name():
    ws = convert_worksheet(load_mcdx(RC_COL))
    src = to_python(ws, trace_source=True)
    assert '# mcdx region 31, "σ_c" -> sigma_c' in src


def test_plain_ascii_target_has_no_arrow_suffix():
    ws = convert_worksheet(load_mcdx(AREAS))
    src = to_python(ws, trace_source=True)
    # `x`/`y` are plain ASCII names (original == py) -- just the region id.
    assert "# mcdx region 1" in src.splitlines()
    assert "# mcdx region 4" in src.splitlines()


def test_notebook_backend_prefixes_code_cells_only():
    ws = convert_worksheet(load_mcdx(AREAS))
    nb = to_notebook(ws, trace_source=True)
    code_cells = [c for c in nb["cells"] if c.cell_type == "code"]
    markdown_cells = [c for c in nb["cells"] if c.cell_type == "markdown"]
    assert any(c.source.startswith("# mcdx region") for c in code_cells)
    assert not any("mcdx region" in c.source for c in markdown_cells)


def test_source_comment_returns_none_without_a_source():
    assert source_comment(ir.Evaluate(value=ir.Number("1"))) is None


def test_cli_trace_source_flag(capsys):
    code = main(["convert", str(RC_COL), "-f", "py", "-o", "-", "--trace-source"])
    out = capsys.readouterr().out
    assert code == 0
    assert '# mcdx region 31, "σ_c" -> sigma_c' in out


# ---------------------------------------------------------------------------
# Input/Output tags (mathcad/integration.xml, for MathcadPy automation)
# ---------------------------------------------------------------------------


def test_io_tags_are_read_from_integration_xml():
    ws = convert_worksheet(load_mcdx(IO))
    tags = {r.source.region_id: (r.source.io_kind, r.source.io_alias) for r in ws.regions}
    # x, y are flagged Input (default alias = the variable name); the `A =`
    # echo and the `σ := F/A` define are flagged Output (default aliases
    # "out"/"out_0", which Prime assigns when the author didn't type one --
    # note this alias does NOT match either region's Mathcad/Python name).
    assert tags[0] == ("Input", "x")
    assert tags[1] == ("Input", "y")
    assert tags[4] == ("Output", "out")
    assert tags[5] == ("Output", "out_0")
    # `F` and `A`'s own definition are untagged.
    assert tags[2] == (None, None)
    assert tags[3] == (None, None)


def test_io_alias_is_emitted_and_combines_with_a_renamed_target():
    src = convert_file(IO, fmt="py", trace_source=True)
    assert '# mcdx region 0, input alias "x"' in src
    assert '# mcdx region 4, output alias "out"' in src
    # `σ` -> `sigma` is also an Output, so both annotations appear on one line.
    assert '# mcdx region 5, output alias "out_0", "σ" -> sigma' in src


def test_a_sheet_without_io_tags_has_no_io_alias_text():
    # references/collapsable-area.mcdx's integration.xml is a bare <regions/>.
    src = to_python(convert_worksheet(load_mcdx(AREAS)), trace_source=True)
    assert "alias" not in src
