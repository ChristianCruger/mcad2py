"""Emit a plain ``.py`` script from an IR worksheet (print-style evaluations)."""

from __future__ import annotations

from .. import ir
from .codegen import (
    assignment_line,
    declaration_lines,
    echo_expr,
    expr_to_str,
    header_lines,
    plot_lines,
    solve_block_lines,
    symbolic_eval_expr,
)


def to_python(ws: ir.Worksheet) -> str:
    lines: list[str] = ['"""Auto-generated from a Mathcad worksheet by mcad2py."""']
    lines += header_lines(ws)
    lines.append("")

    for region in ws.regions:
        lines += _render_region(region)
    return "\n".join(lines) + "\n"


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

    if isinstance(region, ir.Evaluate):
        echo = echo_expr(region)
        return ["", f"print({echo})"] if echo is not None else []

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

    if isinstance(region, ir.UnsupportedRegion):
        return ["", f"# TODO unsupported region: {region.note}"]

    return []
