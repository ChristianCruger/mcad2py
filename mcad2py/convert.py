"""High-level conversion: ``.mcdx`` -> IR -> notebook / python."""

from __future__ import annotations

from pathlib import Path

from . import ir
from .emit.notebook_backend import to_ipynb_string
from .emit.py_backend import to_python
from .loader import McdxPackage, load_mcdx
from .parser.regions import parse_worksheet
from .text import extract_text


def convert_worksheet(pkg: McdxPackage) -> ir.Worksheet:
    """Parse a loaded package into an IR worksheet (with text resolved)."""

    def resolve_text(idref: str) -> str:
        data = pkg.text_package(idref)
        return extract_text(data) if data else ""

    return parse_worksheet(
        pkg.worksheet_xml,
        text_resolver=resolve_text,
        image_resolver=pkg.image,
        integration_xml=pkg.integration_xml,
        result_xml=pkg.result_xml,
    )


def convert_file(
    path: str | Path,
    *,
    fmt: str = "notebook",
    trace_source: bool = False,
) -> str:
    """Convert a ``.mcdx`` file to source. ``fmt`` is ``"notebook"`` or ``"py"``.

    ``trace_source`` annotates each generated statement with a back-reference
    to its originating Mathcad worksheet region (see ``--trace-source``).
    """
    pkg = load_mcdx(path)
    ws = convert_worksheet(pkg)
    if fmt == "py":
        return to_python(ws, trace_source=trace_source)
    if fmt == "notebook":
        return to_ipynb_string(ws, trace_source=trace_source)
    raise ValueError(f"unknown format: {fmt!r} (expected 'notebook' or 'py')")
