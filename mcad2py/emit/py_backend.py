"""Emit a plain ``.py`` script from an IR worksheet (print-style evaluations)."""

from __future__ import annotations

from .. import ir
from .codegen import (
    assignment_line,
    combobox_assign_lines,
    declaration_lines,
    echo_expr,
    expr_to_str,
    grid_plot_lines,
    guard_cached_error,
    header_lines,
    index_assign_line,
    multi_assign_lines,
    plot_lines,
    recurrence_lines,
    solve_block_lines,
    source_comment,
    status_control_line,
    symbolic_eval_expr,
)


def to_python(ws: ir.Worksheet, *, trace_source: bool = False) -> str:
    # The body is rendered first: the header's imports are read off the text it
    # will sit above, rather than predicted from the IR (see `header_lines`).
    body: list[str] = []
    for region in ws.regions:
        out = _guarded(_render_region(region), region)
        if trace_source and out:
            comment = source_comment(region)
            if comment is not None:
                # Keep the leading blank separator (if any) ahead of the comment.
                out = (
                    [out[0], comment, *out[1:]]
                    if out[0] == ""
                    else [comment, *out]
                )
        body += out

    lines: list[str] = ['"""Auto-generated from a Mathcad worksheet by mcad2py."""']
    lines += header_lines(ws, "\n".join(body))
    lines.append("")
    return "\n".join(lines + body) + "\n"


def _guarded(lines: list[str], region: ir.Region) -> list[str]:
    """Guard a region Mathcad's cache flags as an error, keeping the separator."""
    lead = 1 if lines and lines[0] == "" else 0
    return lines[:lead] + guard_cached_error(lines[lead:], region)


def _render_region(region: ir.Region) -> list[str]:
    if isinstance(region, ir.TextRegion):
        return [""] + [f"# {line}" for line in region.text.splitlines()]

    if isinstance(region, ir.ImageRegion):
        return ["", f"# [image: {region.name or 'embedded image'}]"]

    if isinstance(region, ir.Define):
        out = ["", assignment_line(region)]
        echo = echo_expr(region)
        if echo is not None:
            out.append(f"print({echo})")
        return out

    if isinstance(region, ir.MultiAssign):
        out = ["", *multi_assign_lines(region)]
        echo = echo_expr(region)
        if echo is not None:
            out.append(f"print({echo})")
        return out

    if isinstance(region, ir.ComboBoxAssign):
        return ["", *combobox_assign_lines(region)]

    if isinstance(region, ir.IndexAssign):
        out = ["", index_assign_line(region)]
        echo = echo_expr(region)
        if echo is not None:
            out.append(f"print({echo})")
        return out

    if isinstance(region, ir.Recurrence):
        out = ["", *recurrence_lines(region)]
        echo = echo_expr(region)
        if echo is not None:
            out.append(f"print({echo})")
        return out

    if isinstance(region, ir.Evaluate):
        echo = echo_expr(region)
        return ["", f"print({echo})"] if echo is not None else []

    if isinstance(region, ir.StatusControl):
        return ["", status_control_line(region)]

    if isinstance(region, ir.SymbolDeclarations):
        return ["", *declaration_lines(region)]

    if isinstance(region, ir.SymbolicEquation):
        # A step shown for context; assigned to nothing, like the Mathcad sheet.
        return ["", expr_to_str(region.equation)]

    if isinstance(region, ir.SymbolicEval):
        return ["", f"print({symbolic_eval_expr(region)})"]

    if isinstance(region, ir.SolveBlock):
        return ["", *solve_block_lines(region)]

    if isinstance(region, ir.Plot):
        return ["", *plot_lines(region)]

    if isinstance(region, ir.GridPlot):
        return ["", *grid_plot_lines(region)]

    if isinstance(region, ir.UnsupportedRegion):
        return ["", f"# TODO unsupported region: {region.note}"]

    return []
