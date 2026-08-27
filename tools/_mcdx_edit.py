"""Shared machinery for the ``.mcdx`` write tools.

Both ``set_mcdx_value.py`` (set a literal input by region) and
``set_mcdx_literal.py`` (set one number *inside* a formula) do the same three
things: find a ``<region>`` in ``mathcad/worksheet.xml``, replace a short span
of text inside it, and rezip every other part untouched. That machinery lives
here so the two tools cannot drift apart on the part that must not go wrong.

Nothing here knows what a *settable* region is -- that judgement belongs to
each tool.
"""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path

WORKSHEET = "mathcad/worksheet.xml"

# A unit expression we can rename: one bare unit identifier. A compound one
# (<ml:apply><ml:div/>...) has no single name to replace, so --unit refuses it.
BARE_UNIT = re.compile(r'\A<ml:id labels="UNIT"(?P<attrs>[^>]*)>(?P<name>[^<]*)</ml:id>\Z')

UNIT_TEMPLATE = (
    '<ml:id labels="UNIT" label-is-contextual="true" xml:space="preserve">{}</ml:id>'
)


class Refused(Exception):
    """The requested edit is not a safe write."""


def element_span(text: str, tag: str, start: int) -> tuple[int, int]:
    """Span of the ``tag`` element beginning at ``start``, counting nesting.

    ``<region>`` nests (a collapsible ``<area>`` holds more regions) and so
    does ``<ml:apply>``, so a non-greedy ``.*?</tag>`` would stop at the first
    inner close tag and silently truncate the element.
    """
    open_re = re.compile(rf"<{re.escape(tag)}(\s[^>]*)?(/?)>")
    close = f"</{tag}>"
    depth = 0
    pos = start
    while pos < len(text):
        opening = open_re.search(text, pos)
        closing = text.find(close, pos)
        if opening and (closing == -1 or opening.start() < closing):
            if opening.group(2) != "/":  # not self-closing
                depth += 1
            pos = opening.end()
            continue
        if closing == -1:
            break
        depth -= 1
        pos = closing + len(close)
        if depth == 0:
            return start, pos
    raise Refused(f"malformed XML: <{tag}> at offset {start} is never closed")


def find_region(ws: str, region_id: int) -> tuple[int, int]:
    """Span of ``<region region-id="region_id">`` within the worksheet text."""
    match = re.search(rf'<region region-id="{region_id}"[\s>]', ws)
    if not match:
        raise Refused(f"no region with region-id={region_id} in {WORKSHEET}")
    return element_span(ws, "region", match.start())


def region_ids(ws: str) -> list[int]:
    """Every ``region-id`` in the worksheet, in document order."""
    return [int(m.group(1)) for m in re.finditer(r'<region region-id="(\d+)"[\s>]', ws)]


def format_number(text: str, what: str = "--value") -> str:
    """Validate ``text`` as a real and return the text Prime should store."""
    try:
        value = float(text)
    except (TypeError, ValueError) as exc:
        raise Refused(f"{what} {text!r} is not a number") from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise Refused(f"{what} {text!r} is not a finite number")
    # Pass the typed text through where it is already a clean decimal, so "45"
    # stays "45" and "0.1" does not become "0.1000000000000000055". The
    # leading-dot form matters too: Prime writes ".87", and normalising that to
    # "0.87" would rewrite bytes for no gain.
    clean = text.strip()
    return clean if re.fullmatch(r"-?(\d+(\.\d*)?|\.\d+)", clean) else repr(value)


def read_worksheet(path: Path) -> str:
    """``mathcad/worksheet.xml`` out of the ``.mcdx`` at ``path``."""
    with zipfile.ZipFile(path) as zf:
        if WORKSHEET not in zf.namelist():
            raise Refused(f"{path} has no {WORKSHEET} -- is it a .mcdx?")
        return zf.read(WORKSHEET).decode("utf-8")


def rewrite_zip(path: Path, out: Path, new_worksheet: str) -> None:
    """Copy the ``.mcdx`` at ``path`` to ``out`` with a new worksheet part.

    Every other part, and every zip entry's metadata, is carried across
    untouched. The new file is built beside the destination and moved into
    place, so an interrupted run cannot leave a half-written worksheet where a
    good one was.
    """
    with zipfile.ZipFile(path) as zf:
        if WORKSHEET not in zf.namelist():
            raise Refused(f"{path} has no {WORKSHEET} -- is it a .mcdx?")
        entries = [(item, zf.read(item.filename)) for item in zf.infolist()]

    fd, tmp_name = tempfile.mkstemp(suffix=".mcdx", dir=out.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item, data in entries:
                payload = (new_worksheet.encode("utf-8")
                           if item.filename == WORKSHEET else data)
                info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                zout.writestr(info, payload)
        os.replace(tmp, out)
    except PermissionError as exc:
        tmp.unlink(missing_ok=True)
        raise Refused(
            f"{out}: could not be written ({exc}). Close it in Mathcad Prime and "
            "run again -- the original is untouched.") from exc
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
