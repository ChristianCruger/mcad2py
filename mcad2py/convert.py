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

    def text_resolver(rels: dict[str, str]):
        def resolve(idref: str) -> str:
            data = pkg.text_package(idref, rels)
            return extract_text(data) if data else ""

        return resolve

    def image_resolver(rels: dict[str, str]):
        return lambda idref: pkg.image(idref, rels)

    ws = parse_worksheet(
        pkg.worksheet_xml,
        text_resolver=text_resolver(pkg.rels),
        image_resolver=pkg.image,
        integration_xml=pkg.integration_xml,
        result_xml=pkg.result_xml,
    )
    if pkg.header_xml:
        ws.header = parse_worksheet(
            pkg.header_xml,
            text_resolver=text_resolver(pkg.header_rels),
            image_resolver=image_resolver(pkg.header_rels),
        ).regions
    if pkg.footer_xml:
        ws.footer = parse_worksheet(
            pkg.footer_xml,
            text_resolver=text_resolver(pkg.footer_rels),
            image_resolver=image_resolver(pkg.footer_rels),
        ).regions
    return ws


def convert_file(
    path: str | Path,
    *,
    fmt: str = "notebook",
    trace_source: bool = False,
    include_header_footer: bool = True,
) -> str:
    """Convert a ``.mcdx`` file to source. ``fmt`` is ``"notebook"`` or ``"py"``.

    ``trace_source`` annotates each generated statement with a back-reference
    to its originating Mathcad worksheet region (see ``--trace-source``).
    ``include_header_footer`` preserves document context as comments.
    """
    pkg = load_mcdx(path)
    ws = convert_worksheet(pkg)
    if fmt == "py":
        return to_python(
            ws,
            trace_source=trace_source,
            include_header_footer=include_header_footer,
        )
    if fmt == "notebook":
        return to_ipynb_string(
            ws,
            trace_source=trace_source,
            include_header_footer=include_header_footer,
        )
    raise ValueError(f"unknown format: {fmt!r} (expected 'notebook' or 'py')")
