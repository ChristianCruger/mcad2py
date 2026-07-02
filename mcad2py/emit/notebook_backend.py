"""Emit a Jupyter notebook (``.ipynb``) from an IR worksheet.

One worksheet region becomes one cell. Evaluated regions end with a bare
expression so the notebook echoes the result inline, mirroring Mathcad's ``=``.
Text regions become markdown cells.
"""

from __future__ import annotations

import base64

import nbformat

from .. import ir
from .codegen import (
    assignment_line,
    combobox_assign_lines,
    declaration_lines,
    echo_expr,
    expr_to_str,
    grid_plot_lines,
    header_lines,
    index_assign_line,
    multi_assign_lines,
    plot_lines,
    solve_block_lines,
    status_control_line,
    symbolic_eval_expr,
)


def to_notebook(ws: ir.Worksheet) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    cells: list[nbformat.NotebookNode] = [
        nbformat.v4.new_markdown_cell(
            "*Auto-generated from a Mathcad worksheet by mcad2py.*"
        ),
        nbformat.v4.new_code_cell("\n".join(header_lines(ws))),
    ]

    for region in ws.regions:
        cell = _render_region(region)
        if cell is not None:
            cells.append(cell)

    nb["cells"] = cells
    return nb


def to_ipynb_string(ws: ir.Worksheet) -> str:
    return nbformat.writes(to_notebook(ws))


def _render_region(region: ir.Region) -> nbformat.NotebookNode | None:
    if isinstance(region, ir.TextRegion):
        return nbformat.v4.new_markdown_cell(region.text)

    if isinstance(region, ir.ImageRegion):
        return _image_cell(region)

    if isinstance(region, ir.Define):
        lines = [assignment_line(region)]
        echo = echo_expr(region)
        if echo is not None:
            lines.append(echo)  # bare last line -> inline result, like Mathcad "="
        return nbformat.v4.new_code_cell("\n".join(lines))

    if isinstance(region, ir.MultiAssign):
        lines = multi_assign_lines(region)
        echo = echo_expr(region)
        if echo is not None:
            lines.append(echo)
        return nbformat.v4.new_code_cell("\n".join(lines))

    if isinstance(region, ir.ComboBoxAssign):
        return nbformat.v4.new_code_cell("\n".join(combobox_assign_lines(region)))

    if isinstance(region, ir.IndexAssign):
        lines = [index_assign_line(region)]
        echo = echo_expr(region)
        if echo is not None:
            lines.append(echo)  # bare last line -> inline result, like Mathcad "="
        return nbformat.v4.new_code_cell("\n".join(lines))

    if isinstance(region, ir.Evaluate):
        echo = echo_expr(region)
        return nbformat.v4.new_code_cell(echo) if echo is not None else None

    if isinstance(region, ir.StatusControl):
        return nbformat.v4.new_code_cell(status_control_line(region))

    if isinstance(region, ir.SymbolDeclarations):
        return nbformat.v4.new_code_cell("\n".join(declaration_lines(region)))

    if isinstance(region, ir.SymbolicEquation):
        # Bare Eq(...) last line -> the notebook renders the typeset equation.
        return nbformat.v4.new_code_cell(expr_to_str(region.equation))

    if isinstance(region, ir.SymbolicEval):
        return nbformat.v4.new_code_cell(symbolic_eval_expr(region))

    if isinstance(region, ir.SolveBlock):
        return nbformat.v4.new_code_cell("\n".join(solve_block_lines(region)))

    if isinstance(region, ir.Plot):
        return nbformat.v4.new_code_cell("\n".join(plot_lines(region)))

    if isinstance(region, ir.GridPlot):
        return nbformat.v4.new_code_cell("\n".join(grid_plot_lines(region)))

    if isinstance(region, ir.UnsupportedRegion):
        return nbformat.v4.new_markdown_cell(f"> **TODO** unsupported region: {region.note}")

    return None


# ---------------------------------------------------------------------------
# Image embedding
# ---------------------------------------------------------------------------

# MIME types front-ends render directly as a notebook output.
_RASTER_MIME = {"image/png", "image/jpeg", "image/gif"}


def _image_cell(region: ir.ImageRegion) -> nbformat.NotebookNode:
    """A code cell that displays an embedded image.

    The image is stored both as a pre-rendered cell output (so it shows on
    open, no execution needed, in VS Code / Jupyter / nbviewer / GitHub) and as
    source that regenerates it on re-run. Non-web formats (Mathcad often emits
    BMP) are converted to PNG; ``data:`` URIs in markdown are avoided because
    several renderers sanitize or truncate them.
    """
    data, mime = _as_raster(region)
    b64 = base64.b64encode(data).decode("ascii")
    alt = region.name or "image"

    source = (
        "import base64\n"
        "from IPython.display import Image\n"
        f'Image(base64.b64decode(\n    "{b64}"\n))  # {alt}'
    )
    cell = nbformat.v4.new_code_cell(source)
    cell.outputs = [
        nbformat.v4.new_output(
            output_type="display_data",
            data={mime: b64, "text/plain": f"<image: {alt}>"},
        )
    ]
    return cell


def _as_raster(region: ir.ImageRegion) -> tuple[bytes, str]:
    """Return image bytes in a directly-renderable raster format (PNG/JPEG/GIF).

    Already-web formats pass through; anything else (BMP, TIFF, ...) is
    converted to PNG via Pillow. If conversion is unavailable, the original
    bytes/MIME are returned unchanged (best effort).
    """
    if region.mime in _RASTER_MIME:
        return region.data, region.mime
    try:
        import io

        from PIL import Image as PILImage

        im = PILImage.open(io.BytesIO(region.data))
        if im.mode not in ("RGB", "RGBA", "L", "LA"):
            im = im.convert("RGBA")
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue(), "image/png"
    except Exception:
        return region.data, region.mime
