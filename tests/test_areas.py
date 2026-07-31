"""Collapsible **areas** (``<region><Area><regions>…``).

An area is a container region Mathcad can fold shut in the UI; the math inside
is still evaluated. We flatten it away, so ``references/collapsable-area.mcdx``
converts exactly as if the area weren't there -- ``x := 1`` outside, ``y := 2·x``
inside, ``y + x =`` after it, in that reading order.
"""

import io
import contextlib
import xml.etree.ElementTree as ET
from pathlib import Path

from mcad2py import ir
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.loader import load_mcdx
from mcad2py.parser.regions import parse_worksheet

REFERENCE = Path(__file__).parent.parent / "references" / "collapsable-area.mcdx"


def _run() -> tuple[dict, str]:
    src = convert_file(REFERENCE, fmt="py")
    namespace: dict = {}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(src, "<generated>", "exec"), namespace)  # noqa: S102
    return namespace, out.getvalue()


def test_area_contents_are_converted_and_match_cache():
    ns, printed = _run()
    assert ns["x"] == 1
    assert ns["y"] == 2  # defined *inside* the area
    # Mathcad's cached result for the ``y + x =`` region below the area.
    assert printed.strip() == "3"


def test_area_contents_keep_reading_order():
    ws = convert_worksheet(load_mcdx(REFERENCE))
    # The area's ``y`` is spliced in at the area's own position: after ``x``
    # (defined above it) and before the evaluation below it.
    assert [r.target.py for r in ws.regions if isinstance(r, ir.Define)] == ["x", "y"]
    texts = [r.text.strip() for r in ws.regions if isinstance(r, ir.TextRegion)]
    assert texts == ["outside area", "inside area", "after area:"]
    assert isinstance(ws.regions[-1], ir.Evaluate)


def _synthetic(body: str) -> ir.Worksheet:
    return parse_worksheet(
        '<worksheet xmlns="http://schemas.mathsoft.com/worksheet50" '
        'xmlns:ml="http://schemas.mathsoft.com/math50">'
        f"<regions>{body}</regions></worksheet>"
    )


def _define(name: str, value: str, top: str) -> str:
    return (
        f'<region top="{top}" left="0"><math><ml:define>'
        f'<ml:id labels="VARIABLE">{name}</ml:id><ml:real>{value}</ml:real>'
        "</ml:define></math></region>"
    )


def test_nested_areas_flatten_and_sort_area_relative():
    """Areas nest, and a nested region's ``top`` is relative to its area.

    Here the inner regions' coordinates (10, 20) are *smaller* than those of the
    plain regions around the area (100, 300) -- ordering them globally would
    hoist them to the top of the sheet, so each area has to be sorted within
    itself and spliced in at the area's own position.
    """
    ws = _synthetic(
        _define("a", "1", "100")
        + '<region top="200" left="0"><Area><regions>'
        + _define("b", "2", "10")
        + '<region top="20" left="0"><Area><regions>'
        + _define("c", "3", "20")
        + _define("d", "4", "10")
        + "</regions></Area></region>"
        + "</regions></Area></region>"
        + _define("e", "5", "300")
    )
    assert [r.target.py for r in ws.regions] == ["a", "b", "d", "c", "e"]


def test_empty_area_is_dropped_not_unsupported():
    ws = _synthetic(
        _define("a", "1", "10")
        + '<region top="20" left="0"><Area><regions /></Area></region>'
    )
    assert [type(r).__name__ for r in ws.regions] == ["Define"]


def test_area_element_is_matched_by_local_name():
    """Guard the namespace assumption: ``<Area>`` sits in the *worksheet*
    namespace (no ``ml:`` prefix), and Prime bumps schema version numbers, so
    the match has to be on the local name.
    """
    root = ET.fromstring(load_mcdx(REFERENCE).worksheet_xml)
    areas = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "Area"]
    assert len(areas) == 1
    assert areas[0].tag.startswith("{http://schemas.mathsoft.com/worksheet50}")
