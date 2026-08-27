#!/usr/bin/env python3
"""Set one number *inside* a formula in a Mathcad Prime ``.mcdx`` worksheet.

``set_mcdx_value.py`` sets a whole literal input (``theta := 34 deg``) and
refuses a formula, because overwriting one with a number would delete the
sheet's maths. This tool takes the other half of the job: it leaves the
expression tree exactly as it is and replaces a single ``<ml:real>`` node
inside it -- the ``1.5`` in ``f_cd := 30 MPa / 1.5``.

It is meant for an **agent**, so the contract is built to fail loudly:

* every number in the region is addressed by an ordinal ``--index``, listed by
  ``--list`` (add ``--json`` for machine output);
* ``--expect`` is required, and states the number you believe is there. A
  wrong index then stops the run instead of quietly changing the wrong number;
* the edit is verified before anything is written -- the region is converted
  to Python before and after, and both lines are reported.

    python tools/set_mcdx_literal.py sheet.mcdx --region 0 --list --json
    python tools/set_mcdx_literal.py sheet.mcdx --region 0 --index 1 \
        --expect 1.5 --value 1.4

Each number carries a **kind**, because not every number in a formula is a
quantity you meant to tune:

    value           an ordinary operand                 editable
    factor          the divisor of a division           editable
    matrix-element  a cell of a literal matrix          editable
    exponent        a power, or an nth-root degree      needs --allow-kind
    index           a subscript                         needs --allow-kind
    display-scale   a number in the unit override       needs --allow-kind

The three gated kinds change *what the formula means* rather than what it is
worth, and an accidental edit there produces a plausible wrong answer.

Only ``mathcad/worksheet.xml`` is rewritten, and inside it only the one number
(and its unit, with ``--unit``). Every other byte of the zip is copied through.

**The cached results go stale**, exactly as for ``set_mcdx_value.py``:
``mathcad/result.xml`` still holds the numbers Mathcad computed for the old
formula. Run ``tools/recalc_mcdx.py`` to have Prime recompute them, or run the
generated Python, which evaluates the new formula for real.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _mcdx_edit import (  # noqa: E402
    BARE_UNIT,
    Refused,
    find_region,
    format_number,
    read_worksheet,
    region_ids,
    rewrite_zip,
)

# Kinds we will edit without being asked twice, and the rest.
SAFE_KINDS = ("value", "factor", "matrix-element")
GATED_KINDS = ("exponent", "index", "display-scale")

# The number, in the raw worksheet text. Prime writes plain decimal text here
# (the E-notation in result.xml is a different part with a different writer).
_REAL = re.compile(r"<ml:real>([^<]*)</ml:real>")

# A unit id immediately following the number -- the <ml:scale/> form, and the
# only shape where a unit belongs to one number unambiguously.
_TRAILING_UNIT = re.compile(r'\A<ml:id labels="UNIT"[^>]*>[^<]*</ml:id>')


@dataclass(frozen=True)
class Literal:
    """One ``<ml:real>`` inside a region."""

    index: int
    value: str
    unit: str
    kind: str
    start: int  # span of the <ml:real> element, relative to the region text
    end: int

    @property
    def editable(self) -> bool:
        return self.kind in SAFE_KINDS

    def as_dict(self) -> dict:
        row = dataclasses.asdict(self)
        row.pop("start")
        row.pop("end")
        row["editable"] = self.editable
        return row


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _kind(node: ET.Element, parents: dict[ET.Element, ET.Element]) -> str:
    """What role this number plays in the expression tree."""
    ancestor = parents.get(node)
    while ancestor is not None:
        if _localname(ancestor.tag) == "unitOverride":
            return "display-scale"
        ancestor = parents.get(ancestor)

    parent = parents.get(node)
    if parent is None:
        return "value"
    parent_tag = _localname(parent.tag)

    if parent_tag == "matrix":
        return "matrix-element"
    if parent_tag == "sequence":
        # A <sequence> under an indexer is the (row, col) pair of a 2-D read.
        grandparent = parents.get(parent)
        if grandparent is not None and _localname(grandparent.tag) == "apply":
            head = list(grandparent)[0] if len(grandparent) else None
            if head is not None and _localname(head.tag) == "indexer":
                return "index"
        return "value"
    if parent_tag != "apply":
        return "value"

    children = list(parent)
    head = _localname(children[0].tag) if children else ""
    operand = children.index(node) - 1  # children[0] is the operator
    if head == "pow" and operand == 1:
        return "exponent"
    if head == "nthRoot" and operand == 0:
        return "exponent"  # the root degree: 3 in the cube root
    if head == "indexer" and operand >= 1:
        return "index"
    if head == "div" and operand == 1:
        return "factor"
    return "value"


def _unit_of(node: ET.Element, parents: dict[ET.Element, ET.Element]) -> str:
    """The unit attached to this number, or ``""``.

    Only the ``<ml:scale/>`` form counts -- ``30 MPa`` is one number with one
    unit. In ``a / m`` the unit belongs to the division, not to a number.
    """
    parent = parents.get(node)
    if parent is None or _localname(parent.tag) != "apply":
        return ""
    children = list(parent)
    if len(children) < 2 or _localname(children[0].tag) != "scale":
        return ""
    if children[1] is not node:
        return ""
    return "".join(children[2].itertext()) if len(children) > 2 else ""


def _region_tree(ws: str, region: str) -> ET.Element:
    """Parse a region fragment, borrowing the worksheet root's namespaces."""
    root_tag = ws[: ws.index(">", ws.index("<worksheet")) + 1]
    try:
        return ET.fromstring(root_tag + region + "</worksheet>")
    except ET.ParseError as exc:
        raise Refused(f"region XML did not parse: {exc}") from exc


def literals(ws: str, region_id: int) -> list[Literal]:
    """Every number inside region ``region_id``, in document order."""
    r_start, r_end = find_region(ws, region_id)
    region = ws[r_start:r_end]

    root = _region_tree(ws, region)
    parents = {child: parent for parent in root.iter() for child in parent}
    nodes = [e for e in root.iter() if _localname(e.tag) == "real"]
    spans = list(_REAL.finditer(region))
    if len(nodes) != len(spans):
        # An empty <ml:real/> would put the ordinals out of step with the text,
        # and every later index would then address the wrong number.
        raise Refused(
            f"region {region_id}: found {len(nodes)} number nodes but "
            f"{len(spans)} in the text -- refusing to guess which is which")

    found = []
    for index, (node, span) in enumerate(zip(nodes, spans)):
        found.append(Literal(
            index=index,
            value=span.group(1),
            unit=_unit_of(node, parents),
            kind=_kind(node, parents),
            start=span.start(),
            end=span.end(),
        ))
    return found


def _find(ws: str, region_id: int, index: int) -> Literal:
    found = literals(ws, region_id)
    if not found:
        raise Refused(f"region {region_id} holds no numbers to set")
    if not 0 <= index < len(found):
        raise Refused(
            f"region {region_id} has {len(found)} numbers (index 0..{len(found) - 1}); "
            f"--index {index} is out of range")
    return found[index]


def set_literal(ws: str, region_id: int, index: int, expect: str, value: str,
                unit: str | None = None, allow_kinds: tuple[str, ...] = ()) -> str:
    """Return ``ws`` with one number inside region ``region_id`` replaced."""
    target = _find(ws, region_id, index)

    try:
        wrong = float(expect) != float(target.value)
    except ValueError as exc:
        raise Refused(f"--expect {expect!r} is not a number") from exc
    if wrong:
        raise Refused(
            f"region {region_id} index {index} holds {target.value}, not the "
            f"expected {expect} -- refusing to edit a number you did not mean.\n"
            "    Run --list again: the region may have changed.")
    if not target.editable and target.kind not in allow_kinds:
        raise Refused(
            f"region {region_id} index {index} is of kind '{target.kind}', which changes "
            f"what the formula means. Pass --allow-kind {target.kind} if that is intended.")

    # A minus sign needs no <ml:neg/> wrapper: Prime writes a negative straight
    # into <ml:real> (every matrix of measurements in statistics.mcdx does).
    number = format_number(value)

    r_start, r_end = find_region(ws, region_id)
    region = ws[r_start:r_end]
    new_region = (region[:target.start] + f"<ml:real>{number}</ml:real>"
                  + region[target.end:])
    if unit is not None:
        new_region = _set_unit(new_region, target, unit)
    return ws[:r_start] + new_region + ws[r_end:]


def _set_unit(region: str, target: Literal, unit: str) -> str:
    """Rename (or remove) the unit that immediately follows the number."""
    # Search from the number's end tag: its new text length is irrelevant.
    end = region.index("</ml:real>", target.start) + len("</ml:real>")
    match = _TRAILING_UNIT.match(region[end:])
    if not match:
        raise Refused(
            "this number carries no unit of its own -- --unit can only rename the "
            "unit of a scaled number such as '30 MPa'.")
    existing = match.group(0)
    bare = BARE_UNIT.match(existing)
    if not bare:
        raise Refused("the existing unit is not a single name; set it in Prime.")
    if unit == "":
        raise Refused(
            "removing a unit changes the <ml:scale/> node, not just its name -- "
            "not supported inside a formula.")
    replacement = f'<ml:id labels="UNIT"{bare.group("attrs")}>{unit}</ml:id>'
    return region[:end] + replacement + region[end + len(existing):]


def python_lines(ws: str, pkg, region_id: int) -> list[str]:
    """The generated Python for one region, for the before/after report.


    This is the real check that the edit produced valid maths: it goes back
    through the parser the rest of the project trusts, rather than trusting
    the XML surgery.
    """
    from mcad2py.convert import convert_worksheet
    from mcad2py.emit.py_backend import _render_region

    worksheet = convert_worksheet(dataclasses.replace(pkg, worksheet_xml=ws))
    for region in worksheet.regions:
        if region.source is not None and region.source.region_id == region_id:
            lines = [line for line in _render_region(region) if line.strip()]
            return lines or ["(no code)"]
    raise Refused(
        f"region {region_id} did not survive conversion -- the edit is not being "
        "written. This is a bug in the tool; report the worksheet.")


def rewrite(path: Path, out: Path, region_id: int, index: int, expect: str,
            value: str, unit: str | None = None,
            allow_kinds: tuple[str, ...] = ()) -> tuple[list[str], list[str]]:
    """Edit ``path`` into ``out``. Returns the before/after Python lines."""
    from mcad2py.loader import load_mcdx

    ws = read_worksheet(path)
    new_ws = set_literal(ws, region_id, index, expect, value, unit, allow_kinds)

    pkg = load_mcdx(path)
    before = python_lines(ws, pkg, region_id)
    after = python_lines(new_ws, pkg, region_id)  # raises before anything is written

    rewrite_zip(path, out, new_ws)
    return before, after


def _list_payload(ws: str, region_id: int | None) -> list[dict]:
    ids = region_ids(ws) if region_id is None else [region_id]
    rows = []
    for rid in ids:
        try:
            found = literals(ws, rid)
        except Refused:
            continue
        if found:
            rows.append({"region": rid, "literals": [lit.as_dict() for lit in found]})
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="set_mcdx_literal",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", type=Path, help="the .mcdx worksheet")
    parser.add_argument("--region", type=int, help="region-id "
                        "(from 'mcad2py convert --trace-source')")
    parser.add_argument("--index", type=int, help="which number in that region "
                        "(from --list)")
    parser.add_argument("--expect", help="the number you believe is at --index; "
                        "required, and checked before anything is written")
    parser.add_argument("--value", help="the new number")
    parser.add_argument("--unit", help="rename the unit of a scaled number")
    parser.add_argument("--allow-kind", action="append", default=[],
                        choices=list(GATED_KINDS),
                        help="permit editing a number of this kind")
    parser.add_argument("-o", "--output", type=Path,
                        help="write here instead of editing the file in place")
    parser.add_argument("--list", action="store_true",
                        help="list the numbers in --region (or in every region)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--dry-run", action="store_true",
                        help="report the change without writing anything")
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"error: no such file: {args.file}", file=sys.stderr)
        return 2

    try:
        ws = read_worksheet(args.file)

        if args.list:
            payload = _list_payload(ws, args.region)
            if args.json:
                print(json.dumps(payload, indent=2))
                return 0
            if not payload:
                print(f"{args.file.name}: no numbers found")
            for entry in payload:
                print(f"  region {entry['region']}")
                for lit in entry["literals"]:
                    unit = f" {lit['unit']}" if lit["unit"] else ""
                    gate = "" if lit["editable"] else "   (needs --allow-kind)"
                    print(f"    [{lit['index']}] {lit['value']}{unit:<8} "
                          f"{lit['kind']}{gate}")
            return 0

        missing = [name for name, val in (("--region", args.region),
                                          ("--index", args.index),
                                          ("--expect", args.expect),
                                          ("--value", args.value)) if val is None]
        if missing:
            parser.error(f"{', '.join(missing)} required (or use --list)")

        allow = tuple(args.allow_kind)
        if args.dry_run:
            new_ws = set_literal(ws, args.region, args.index, args.expect,
                                 args.value, args.unit, allow)
            from mcad2py.loader import load_mcdx
            pkg = load_mcdx(args.file)
            before = python_lines(ws, pkg, args.region)
            after = python_lines(new_ws, pkg, args.region)
            out_path = None
        else:
            out_path = args.output or args.file
            before, after = rewrite(args.file, out_path, args.region, args.index,
                                    args.expect, args.value, args.unit, allow)

        if args.json:
            print(json.dumps({"region": args.region, "index": args.index,
                              "before": before, "after": after,
                              "written": None if out_path is None else str(out_path),
                              "results_stale": True}, indent=2))
            return 0
        print(f"region {args.region}, index {args.index}:")
        for line in before:
            print(f"  - {line}")
        for line in after:
            print(f"  + {line}")
        if out_path is None:
            print("(dry run, nothing written)")
            return 0
        print(f"wrote {out_path}")
        print("note: mathcad/result.xml still holds the OLD cached results. Run "
              "tools/recalc_mcdx.py to have Mathcad Prime recompute them.")
        return 0
    except Refused as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"error: {args.file.name}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
