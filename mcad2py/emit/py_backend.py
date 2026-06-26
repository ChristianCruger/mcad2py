"""Emit a plain ``.py`` script from an IR worksheet (print-style evaluations)."""

from __future__ import annotations

from .. import ir
from .codegen import assignment_line, echo_expr, expr_to_str, header_lines


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

    if isinstance(region, ir.Define):
        out = ["", assignment_line(region)]
        echo = echo_expr(region)
        if echo is not None:
            out.append(f"print({echo})")
        return out

    if isinstance(region, ir.Evaluate):
        echo = echo_expr(region)
        return ["", f"print({echo})"] if echo is not None else []

    if isinstance(region, ir.UnsupportedRegion):
        return ["", f"# TODO unsupported region: {region.note}"]

    return []
