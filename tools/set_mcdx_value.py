#!/usr/bin/env python3
"""Set the value of a literal input in a Mathcad Prime ``.mcdx`` worksheet.

This is the *write* counterpart to ``mcad2py convert --trace-source``: that
flag prints ``# mcdx region <id>`` above every generated statement, and this
tool edits the region with that id.

    mcad2py convert sheet.mcdx -f py --trace-source     # find the region id
    python tools/set_mcdx_value.py sheet.mcdx --region 1 --value 45

Only a **literal** definition can be set -- ``theta := 34 deg``, ``n := 5``.
A region whose right-hand side is a formula, a matrix, a range or a function
is refused rather than half-edited, because overwriting a formula with a
number would silently delete the sheet's maths.

    python tools/set_mcdx_value.py sheet.mcdx --list                 # what is settable
    python tools/set_mcdx_value.py sheet.mcdx --region 1 --value 45 --unit rad
    python tools/set_mcdx_value.py sheet.mcdx --region 1 --value 45 -o edited.mcdx
    python tools/set_mcdx_value.py sheet.mcdx --region 1 --value 45 --dry-run

Only ``mathcad/worksheet.xml`` is rewritten, and only the one number (and unit)
inside the one region; every other byte of that part, and every other part of
the zip, is copied through untouched.

**The cached results go stale.** ``mathcad/result.xml`` still holds the numbers
Mathcad computed for the *old* input, and neither this tool nor ``mcad2py``
recomputes them -- reading that cache after an edit gives wrong answers. Run
``tools/recalc_mcdx.py`` (needs Mathcad Prime on the machine) to make Prime
recompute and refresh the cache, or just run the generated Python, which
evaluates the new value for real.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

_WORKSHEET = "mathcad/worksheet.xml"

# A worksheet real. Prime writes plain decimal text here (the E-notation in
# result.xml is a different part with a different writer).
_REAL = r"<ml:real>([^<]*)</ml:real>"

# The four right-hand sides we accept, most specific first. Each captures the
# number as group "num"; the scaled forms also capture the whole unit
# expression as group "unit" (which may itself be an <ml:apply> of a division,
# e.g. kN/m, and is left alone unless --unit is given).
_LITERAL_FORMS = (
    ("scaled_neg", re.compile(
        r'\A<ml:apply><ml:neg\s*/><ml:apply><ml:scale\s*/>'
        r'<ml:real>(?P<num>[^<]*)</ml:real>(?P<unit>.*)</ml:apply></ml:apply>\Z', re.S)),
    ("plain_neg", re.compile(
        r'\A<ml:apply><ml:neg\s*/><ml:real>(?P<num>[^<]*)</ml:real></ml:apply>\Z', re.S)),
    ("scaled", re.compile(
        r'\A<ml:apply><ml:scale\s*/><ml:real>(?P<num>[^<]*)</ml:real>'
        r'(?P<unit>.*)</ml:apply>\Z', re.S)),
    ("plain", re.compile(r'\A<ml:real>(?P<num>[^<]*)</ml:real>\Z', re.S)),
)

# A unit expression we can rename: one bare unit identifier. A compound one
# (<ml:apply><ml:div/>...) has no single name to replace, so --unit refuses it.
_BARE_UNIT = re.compile(r'\A<ml:id labels="UNIT"(?P<attrs>[^>]*)>(?P<name>[^<]*)</ml:id>\Z')

_UNIT_TEMPLATE = (
    '<ml:id labels="UNIT" label-is-contextual="true" xml:space="preserve">{}</ml:id>'
)


class Refused(Exception):
    """The requested edit is not a safe literal write."""


def _element_span(text: str, tag: str, start: int) -> tuple[int, int]:
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


def _find_region(ws: str, region_id: int) -> tuple[int, int]:
    match = re.search(rf'<region region-id="{region_id}"[\s>]', ws)
    if not match:
        raise Refused(f"no region with region-id={region_id} in {_WORKSHEET}")
    return _element_span(ws, "region", match.start())


def _split_rhs(region: str) -> tuple[int, int]:
    """Span (within ``region``) of the right-hand side of its definition.

    Refuses anything that is not ``<ml:define>`` of a plain name. A
    ``<ml:function>`` target is a function definition and an ``<ml:indexer>``
    target is an element assignment; neither is an input to set.
    """
    if "<ml:globalDefine>" in region:
        raise Refused("region is a global define (:=' with three lines); not handled")
    start = region.find("<ml:define>")
    if start == -1:
        raise Refused("region is not a definition (no <ml:define>) -- "
                      "only 'name := value' regions can be set")
    d_start, d_end = _element_span(region, "ml:define", start)
    inner_start = d_start + len("<ml:define>")
    inner_end = d_end - len("</ml:define>")

    if not region.startswith("<ml:id", inner_start):
        kind = re.match(r"<(ml:[\w]+)", region[inner_start:])
        raise Refused(
            f"the definition target is <{kind.group(1) if kind else '?'}>, not a plain "
            "name -- a function or indexed assignment is not a settable input")
    _, id_end = _element_span(region, "ml:id", inner_start)

    rhs_start, rhs_end = id_end, inner_end
    # An inline-displayed define wraps its value in <ml:eval>, with the display
    # unit trailing in <ml:unitOverride>. Step inside; leave the override alone.
    if region.startswith("<ml:eval>", rhs_start):
        e_start, e_end = _element_span(region, "ml:eval", rhs_start)
        rhs_start = e_start + len("<ml:eval>")
        rhs_end = e_end - len("</ml:eval>")
        override = region.find("<ml:unitOverride>", rhs_start, rhs_end)
        if override != -1:
            rhs_end = override
    return rhs_start, rhs_end


def _classify(rhs: str):
    for name, pattern in _LITERAL_FORMS:
        match = pattern.match(rhs)
        if match:
            return name, match
    snippet = rhs if len(rhs) <= 70 else rhs[:70] + "..."
    raise Refused(
        "the right-hand side is not a literal number -- refusing to overwrite it.\n"
        f"    {snippet}")


def _format_number(text: str) -> str:
    """Validate ``text`` as a real and return the text Prime should store."""
    try:
        value = float(text)
    except ValueError as exc:
        raise Refused(f"--value {text!r} is not a number") from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise Refused(f"--value {text!r} is not a finite number")
    # Pass the typed text through where it is already a clean decimal, so
    # "45" stays "45" and "0.1" does not become "0.1000000000000000055".
    return text.strip() if re.fullmatch(r"-?\d+(\.\d+)?", text.strip()) else repr(value)


def _build_rhs(form: str, match: re.Match, value: str, unit: str | None) -> str:
    """The replacement right-hand side XML."""
    negative = value.startswith("-")
    number = value.lstrip("-")
    unit_xml = match.groupdict().get("unit")

    if unit is not None:
        if unit == "":
            unit_xml = None
        elif unit_xml is None:
            unit_xml = _UNIT_TEMPLATE.format(unit)
        else:
            bare = _BARE_UNIT.match(unit_xml)
            if not bare:
                raise Refused(
                    "the existing unit is a compound expression (e.g. kN/m); --unit "
                    "can only rename a single unit. Edit the number only, or set the "
                    "unit in Prime.")
            unit_xml = f'<ml:id labels="UNIT"{bare.group("attrs")}>{unit}</ml:id>'
    elif form.startswith("scaled"):
        pass  # keep whatever unit expression was there

    core = f"<ml:real>{number}</ml:real>"
    if unit_xml is not None:
        core = f"<ml:apply><ml:scale />{core}{unit_xml}</ml:apply>"
    if negative:
        core = f"<ml:apply><ml:neg />{core}</ml:apply>"
    return core


def describe(ws: str, region_id: int) -> str:
    """One line describing region ``region_id``'s current literal value."""
    r_start, r_end = _find_region(ws, region_id)
    region = ws[r_start:r_end]
    rhs_start, rhs_end = _split_rhs(region)
    _, match = _classify(region[rhs_start:rhs_end])
    unit_xml = match.groupdict().get("unit") or ""
    bare = _BARE_UNIT.match(unit_xml) if unit_xml else None
    unit = bare.group("name") if bare else ("<compound>" if unit_xml else "")
    return f"{match.group('num')} {unit}".strip()


def settable(ws: str) -> list[tuple[int, str, str]]:
    """``(region_id, name, value)`` for every region this tool can set."""
    found = []
    for match in re.finditer(r'<region region-id="(\d+)"[\s>]', ws):
        region_id = int(match.group(1))
        _, r_end = _element_span(ws, "region", match.start())
        region = ws[match.start():r_end]
        try:
            rhs_start, rhs_end = _split_rhs(region)
            _classify(region[rhs_start:rhs_end])
        except Refused:
            continue
        name_match = re.search(r'<ml:id labels="VARIABLE"[^>]*>(.*?)</ml:id>', region, re.S)
        name = re.sub(r"<[^>]+>", "", name_match.group(1)) if name_match else "?"
        found.append((region_id, name, describe(ws, region_id)))
    return found


def set_value(ws: str, region_id: int, value: str, unit: str | None = None) -> str:
    """Return ``ws`` with region ``region_id``'s literal replaced."""
    r_start, r_end = _find_region(ws, region_id)
    region = ws[r_start:r_end]
    rhs_start, rhs_end = _split_rhs(region)
    form, match = _classify(region[rhs_start:rhs_end])
    new_rhs = _build_rhs(form, match, _format_number(value), unit)
    new_region = region[:rhs_start] + new_rhs + region[rhs_end:]
    return ws[:r_start] + new_region + ws[r_end:]


def rewrite(path: Path, out: Path, region_id: int, value: str,
            unit: str | None = None) -> tuple[str, str]:
    """Edit ``path`` into ``out``. Returns the before/after value descriptions."""
    with zipfile.ZipFile(path) as zf:
        if _WORKSHEET not in zf.namelist():
            raise Refused(f"{path} has no {_WORKSHEET} -- is it a .mcdx?")
        entries = [(item, zf.read(item.filename)) for item in zf.infolist()]

    ws = next(data for item, data in entries
              if item.filename == _WORKSHEET).decode("utf-8")
    before = describe(ws, region_id)
    new_ws = set_value(ws, region_id, value, unit)
    after = describe(new_ws, region_id)

    # Write beside the destination and move into place, so an interrupted run
    # cannot leave a half-written worksheet where a good one was.
    fd, tmp_name = tempfile.mkstemp(suffix=".mcdx", dir=out.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item, data in entries:
                payload = new_ws.encode("utf-8") if item.filename == _WORKSHEET else data
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
    return before, after


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="set_mcdx_value",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", type=Path, help="the .mcdx worksheet")
    parser.add_argument("--region", type=int, help="region-id to set "
                        "(from 'mcad2py convert --trace-source')")
    parser.add_argument("--value", help="the new number")
    parser.add_argument("--unit", help="new unit name; '' removes the unit. "
                        "Omit to keep the existing one.")
    parser.add_argument("-o", "--output", type=Path,
                        help="write here instead of editing the file in place")
    parser.add_argument("--list", action="store_true",
                        help="list every region this tool can set, and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="report the change without writing anything")
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"error: no such file: {args.file}", file=sys.stderr)
        return 2

    try:
        if args.list:
            with zipfile.ZipFile(args.file) as zf:
                ws = zf.read(_WORKSHEET).decode("utf-8")
            rows = settable(ws)
            if not rows:
                print(f"{args.file.name}: no settable literal regions")
            for region_id, name, value in rows:
                print(f"  region {region_id:<4} {name:<16} = {value}")
            return 0

        if args.region is None or args.value is None:
            parser.error("--region and --value are required (or use --list)")

        out = args.output or args.file
        if args.dry_run:
            with zipfile.ZipFile(args.file) as zf:
                ws = zf.read(_WORKSHEET).decode("utf-8")
            before = describe(ws, args.region)
            after = describe(set_value(ws, args.region, args.value, args.unit),
                             args.region)
            print(f"region {args.region}: {before} -> {after}  (dry run, nothing written)")
            return 0

        before, after = rewrite(args.file, out, args.region, args.value, args.unit)
        print(f"region {args.region}: {before} -> {after}")
        print(f"wrote {out}")
        print("note: mathcad/result.xml still holds the OLD cached results. Run "
              "tools/recalc_mcdx.py to have Mathcad Prime recompute them.")
        return 0
    except Refused as exc:
        print(f"error: {args.file.name}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
