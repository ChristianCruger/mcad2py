"""Emit a Jupyter notebook (``.ipynb``) from an IR worksheet.

One worksheet region becomes one cell. Evaluated regions end with a bare
expression so the notebook echoes the result inline, mirroring Mathcad's ``=``.
Text regions become markdown cells.
"""

from __future__ import annotations

import nbformat

from .. import ir
from .codegen import assignment_line, echo_expr, header_lines


def to_notebook(ws: ir.Worksheet) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    cells: list[nbformat.NotebookNode] = [
        nbformat.v4.new_markdown_cell(
            "*Auto-generated from a Mathcad worksheet by mathcad-converter.*"
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

    if isinstance(region, ir.Define):
        lines = [assignment_line(region)]
        echo = echo_expr(region)
        if echo is not None:
            lines.append(echo)  # bare last line -> inline result, like Mathcad "="
        return nbformat.v4.new_code_cell("\n".join(lines))

    if isinstance(region, ir.Evaluate):
        echo = echo_expr(region)
        return nbformat.v4.new_code_cell(echo) if echo is not None else None

    if isinstance(region, ir.UnsupportedRegion):
        return nbformat.v4.new_markdown_cell(f"> **TODO** unsupported region: {region.note}")

    return None
