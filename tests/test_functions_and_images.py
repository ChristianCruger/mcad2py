"""Tests for function definitions and embedded images.

``Elastic_foundation_eq_line_spring.mcdx`` defines a function ``D(x)`` (emitted
as a Python ``lambda``) and embeds a picture. We execute the generated module
and compare to Mathcad's cached ``result.xml``, and check that the picture is
embedded in the notebook output.
"""

import base64
import contextlib
import io
import math
from pathlib import Path

import nbformat

from mcad2py import ir
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.loader import load_mcdx

REFERENCE = (
    Path(__file__).parent.parent / "references"
    / "Elastic_foundation_eq_line_spring.mcdx"
)

# Variable -> (unit to read in, Mathcad's cached magnitude).
EXPECTED = {
    "lambda_": ("1/m", 0.49999999999999994),
    "y": ("mm", 0.049909712904487605),
    "K": ("kN/m**2", 20036.180170254709),
}


def _exec_generated() -> dict:
    src = convert_file(REFERENCE, fmt="py")
    namespace: dict = {}
    with contextlib.redirect_stdout(io.StringIO()):  # eval regions print
        exec(compile(src, "<generated>", "exec"), namespace)  # noqa: S102
    return namespace


def test_function_definition_emits_lambda():
    src = convert_file(REFERENCE, fmt="py")
    assert "D = lambda x: math.exp(-lambda_ * x) * cos(lambda_ * x)" in src


def test_generated_values_match_mathcad():
    ns = _exec_generated()
    for name, (unit, expected) in EXPECTED.items():
        magnitude = ns[name].to(unit).magnitude
        assert math.isclose(magnitude, expected, rel_tol=1e-9), (
            f"{name}: got {magnitude}, expected {expected}"
        )


def test_function_is_callable_with_units():
    ns = _exec_generated()
    # D(x) takes a length and returns a dimensionless shape-function value.
    out = ns["D"](ns["a"])
    value = float(out)
    assert 0.0 < value < 1.0


def test_picture_region_parsed_with_real_mime():
    ws = convert_worksheet(load_mcdx(REFERENCE))
    img = next(r for r in ws.regions if isinstance(r, ir.ImageRegion))
    assert img.name == "Image15.png"
    # The .png is actually a BMP -> MIME is sniffed from content, not the name.
    assert img.mime == "image/bmp"
    assert img.data[:2] == b"BM"


def test_notebook_embeds_image_as_png_output():
    """The picture is embedded as a stored PNG cell output (renders on open),
    with re-runnable source -- not a markdown ``data:`` URI (which several
    renderers, including VS Code, sanitize/truncate). The source BMP is
    converted to PNG for universal renderer support.
    """
    from mcad2py.emit.notebook_backend import to_notebook

    ws = convert_worksheet(load_mcdx(REFERENCE))
    nb = to_notebook(ws)
    nbformat.validate(nb)

    cell = next(
        c for c in nb.cells
        if c.cell_type == "code" and "IPython.display import Image" in c.source
    )
    # Stored output renders without execution.
    output = cell.outputs[0]
    assert output.output_type == "display_data"
    assert base64.b64decode(output.data["image/png"])[:8].startswith(b"\x89PNG")
    # Source regenerates the same image on re-run.
    assert "base64.b64decode" in cell.source
    # No giant markdown data URI anywhere.
    assert not any("data:image" in c.source for c in nb.cells)
