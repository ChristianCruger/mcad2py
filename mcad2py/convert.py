"""High-level conversion: ``.mcdx`` -> IR -> notebook / python."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from . import ir
from .emit.notebook_backend import to_ipynb_string
from .emit.py_backend import to_python
from .loader import McdxPackage, load_mcdx
from .parser.regions import ImageResolver, TextResolver, parse_worksheet
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
        image_resolver=image_resolver(pkg.rels),
        integration_xml=pkg.integration_xml,
        result_xml=pkg.result_xml,
    )
    context = dict(text_resolver=text_resolver, image_resolver=image_resolver)
    ws.header = _context_regions(pkg.header_xml, pkg.header_rels, "header", **context)
    ws.footer = _context_regions(pkg.footer_xml, pkg.footer_rels, "footer", **context)
    return ws


def _context_regions(
    xml: str | None,
    rels: dict[str, str],
    kind: str,
    *,
    text_resolver: Callable[[dict[str, str]], TextResolver],
    image_resolver: Callable[[dict[str, str]], ImageResolver],
) -> list[ir.Region]:
    """Parse a printed header/footer, never letting it break the conversion.

    The document context is decoration: before it was parsed at all, nothing a
    header contained could stop a sheet converting, and that has to stay true.
    A construct the parser can't reach here becomes one visible note, the same
    way an unsupported *region* does -- the point of the TODO convention is
    that the output still loads.
    """
    if not xml:
        return []
    try:
        return parse_worksheet(
            xml,
            text_resolver=text_resolver(rels),
            image_resolver=image_resolver(rels),
        ).regions
    except Exception as exc:  # noqa: BLE001 -- any parse failure, see docstring
        return [ir.UnsupportedRegion(note=f"{kind} could not be parsed: {exc}")]


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
