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
import re
import sys
from pathlib import Path

from _mcdx_edit import (
    BARE_UNIT as _BARE_UNIT,
    UNIT_TEMPLATE as _UNIT_TEMPLATE,
    Refused,
    element_span as _element_span,
    find_region as _find_region,
    format_number as _format_number,
    read_worksheet as _read_worksheet,
    rewrite_zip as _rewrite_zip,
)


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
    ws = _read_worksheet(path)
    before = describe(ws, region_id)
    new_ws = set_value(ws, region_id, value, unit)
    after = describe(new_ws, region_id)
    _rewrite_zip(path, out, new_ws)
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
            ws = _read_worksheet(args.file)
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
            ws = _read_worksheet(args.file)
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
