#!/usr/bin/env python3
"""Replace a whole formula in a Mathcad Prime ``.mcdx`` worksheet.

The other two write tools change a *number*: ``set_mcdx_value.py`` sets a
literal input, ``set_mcdx_literal.py`` sets one number inside an expression.
Neither can change the maths. This one can -- it replaces the right-hand side
of one region with a new expression, written as the same Python this project
generates when it reads the sheet.

    python tools/set_mcdx_formula.py sheet.mcdx --region 0 --list
    python tools/set_mcdx_formula.py sheet.mcdx --region 0 \\
        --expect "30 * ureg.MPa / 1.5" \\
        --value  "0.85 * 30 * ureg.MPa / 1.5"

It is meant for an **agent**, so every guard fails loudly rather than guessing:

* ``--expect`` is required and states the formula you believe is there. Read
  it from ``--list`` or from ``mcad2py convert -f py --trace-source``. A sheet
  that has moved on then stops the run instead of overwriting someone's work.
* The new text must parse into the small subset both halves of the write path
  agree on: numbers, units, ``+ - * / **``, negation, and **names the sheet
  already uses**. A call, a matrix, an index or an unknown name is refused --
  see ``mcad2py/parser/python_expr.py``.
* The edit is verified before anything is written. The new XML is spliced into
  a copy of the worksheet, the whole sheet is converted again, and the region's
  expression is compared with what you asked for. A mismatch refuses.
* Only the *value* subtree is replaced -- not the region, not the target name,
  not the unit override, not the result format. Everything Prime wrote around
  the formula is kept byte for byte.

Two Mathcad constructs the generated Python cannot express are preserved by
copying them from the expression being replaced (see ``reconcile``): whether a
number carrying a unit is a ``<ml:scale/>`` or a ``<ml:mult/>``, and how a
sheet converted from ``.xmcd`` labels its names.

**The cached results go stale.** ``mathcad/result.xml`` still holds the numbers
Mathcad computed for the old formula. Run ``tools/recalc_mcdx.py`` to have
Prime recompute them, or run the generated Python, which evaluates the new
formula for real.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _mcdx_edit import (  # noqa: E402
    Refused,
    element_span,
    find_region,
    python_lines,
    read_worksheet,
    region_ids,
    rewrite_zip,
)

from mcad2py import ir  # noqa: E402
from mcad2py.convert import convert_worksheet  # noqa: E402
from mcad2py.emit.codegen import expr_to_str  # noqa: E402
from mcad2py.emit.mcdx_backend import Unsupported, emit_expr, harvest_ids  # noqa: E402
from mcad2py.parser.expressions import parse_expr  # noqa: E402
from mcad2py.parser.python_expr import (  # noqa: E402
    InvalidExpression,
    parse_python,
    symbol_table,
)

# The element that holds a define's target: a plain name, or a function
# signature (``f(x) :=``). The value is whatever element follows it.
TARGET_TAGS = ("ml:id", "ml:function")


# ---------------------------------------------------------------------------
# Finding the value subtree
# ---------------------------------------------------------------------------


def value_span(ws: str, region_id: int) -> tuple[int, int]:
    """The span of the expression a region evaluates, within ``ws``.

    Deliberately the *smallest* subtree that carries the maths: inside
    ``<ml:eval>`` where there is one, so a ``<ml:unitOverride>`` beside it is
    untouched, and never the ``<ml:define>``, so the target name keeps its own
    bytes.
    """
    start, end = find_region(ws, region_id)
    region = ws[start:end]

    open_define = re.search(r"<ml:(global)?[Dd]efine[\s>]", region)
    if open_define:
        if len(re.findall(r"<ml:(?:global)?[Dd]efine[\s>]", region)) > 1:
            raise Refused(
                f"region {region_id} holds more than one definition -- refusing "
                "to guess which formula you mean.")
        pos = _after_open_tag(region, open_define.start())
        pos = _skip_element(region, pos, region_id, expected=TARGET_TAGS)
    else:
        eval_at = region.find("<ml:eval")
        if eval_at == -1:
            raise Refused(
                f"region {region_id} has no definition and no evaluation -- it is "
                "not a formula region. Use 'mcad2py convert --trace-source' to "
                "find one.")
        pos = eval_at

    tag = _tag_at(region, pos)
    if tag == "ml:eval":
        pos = _after_open_tag(region, pos)
        tag = _tag_at(region, pos)
    while tag == "ml:parens":
        # A group wrapping the whole formula is Prime's cosmetics, not part of
        # the maths (the parser drops it). Replacing it would rewrite bytes the
        # edit has no opinion about, so descend inside and leave it standing.
        pos = _after_open_tag(region, pos)
        tag = _tag_at(region, pos)
    if tag is None:
        raise Refused(f"region {region_id}: found no expression to replace")

    inner_start, inner_end = element_span(region, tag, pos)
    return start + inner_start, start + inner_end


def _tag_at(text: str, pos: int) -> str | None:
    match = re.match(r"<([\w:]+)", text[pos:])
    return match.group(1) if match else None


def _after_open_tag(text: str, pos: int) -> int:
    """The index just past the ``>`` of the element opening at ``pos``."""
    return text.index(">", pos) + 1


def _skip_element(text: str, pos: int, region_id: int,
                  expected: tuple[str, ...]) -> int:
    tag = _tag_at(text, pos)
    if tag not in expected:
        raise Refused(
            f"region {region_id}: expected {' or '.join(expected)} after the "
            f"definition, found <{tag}>. This is not a shape the tool knows.")
    return element_span(text, tag, pos)[1]


def current_expr(ws: str, region_id: int) -> ir.Expr:
    """The IR of the expression :func:`value_span` points at."""
    start, end = value_span(ws, region_id)
    root_tag = ws[: ws.index(">", ws.index("<worksheet")) + 1]
    try:
        root = ET.fromstring(root_tag + ws[start:end] + "</worksheet>")
    except ET.ParseError as exc:
        raise Refused(f"region {region_id}: its XML did not parse: {exc}") from exc
    return parse_expr(list(root)[0])


# ---------------------------------------------------------------------------
# The edit
# ---------------------------------------------------------------------------


def set_formula(ws: str, pkg, region_id: int, expect: str, value: str) -> str:
    """The worksheet text with region ``region_id``'s formula replaced.

    Every guard runs here, before the caller touches a file.
    """
    start, end = value_span(ws, region_id)
    old = current_expr(ws, region_id)
    _check_rewritable(ws[start:end], old, region_id)

    shown = expr_to_str(old)
    if _normalise(expect) != _normalise(shown):
        raise Refused(
            f"region {region_id} holds {shown!r}, not the expected {expect.strip()!r}"
            " -- refusing to overwrite a formula that is not the one you read.")

    worksheet = convert_worksheet(dataclasses.replace(pkg, worksheet_xml=ws))
    try:
        new = parse_python(value, symbol_table(worksheet), like=old)
    except InvalidExpression as exc:
        raise Refused(str(exc)) from exc

    try:
        xml = emit_expr(new, harvest_ids(ws))
    except Unsupported as exc:
        raise Refused(
            f"{expr_to_str(new)!r} cannot be written to a worksheet: {exc}") from exc

    edited = ws[:start] + xml + ws[end:]
    _verify(edited, pkg, region_id, new)
    return edited


def _check_rewritable(xml: str, old: ir.Expr, region_id: int) -> None:
    """Refuse a region this tool cannot reproduce, before it changes anything.

    The test is one line: re-emit the formula that is *already* there and
    compare with the bytes Prime wrote. Equal means the whole chain -- parser,
    code generator, front end, backend -- agrees on this region, so a real edit
    will change only the part you asked to change. Unequal means something in
    the region does not survive the round trip, and rewriting it would quietly
    restyle maths the edit never touched.

    Three things fail it, all seen in the fixtures: ``<ml:percent/>`` (read as
    ``x / 100``, so ``80%`` would come back as ``80/100``), Prime's
    ``split=``/``inline=`` line-break hints, and a redundant group the author
    typed (``k * (c * f_ctd)``), which the parser drops. None is worth guessing
    about.
    """
    try:
        again = emit_expr(old, harvest_ids(xml))
    except Unsupported as exc:
        raise Refused(
            f"region {region_id} holds maths this tool cannot write back "
            f"({exc}). Use tools/set_mcdx_literal.py to change one number in "
            "it, or edit it in Prime.") from exc
    if again != xml:
        raise Refused(
            f"region {region_id} would not survive a rewrite byte for byte -- "
            "it holds a percent sign, a line break inside the equation, or a "
            "redundant bracket. Refusing rather than restyle maths the edit "
            "does not touch. Use tools/set_mcdx_literal.py for one number.")


def _verify(edited: str, pkg, region_id: int, expected: ir.Expr) -> None:
    """Convert the edited sheet and check the region now says what we meant.

    The point of doing it here rather than after writing: the real parser is
    the judge, and a splice that landed in the wrong place, or XML the parser
    reads differently from the way we wrote it, is caught while the file on
    disk is still untouched.
    """
    worksheet = convert_worksheet(dataclasses.replace(pkg, worksheet_xml=edited))
    for region in worksheet.regions:
        if region.source is None or region.source.region_id != region_id:
            continue
        value = getattr(region, "value", None)
        if value is None:
            break
        if expr_to_str(value) != expr_to_str(expected):
            raise Refused(
                f"the edit did not land as written: region {region_id} reads "
                f"{expr_to_str(value)!r}, not {expr_to_str(expected)!r}. Nothing "
                "was written.")
        return
    raise Refused(
        f"region {region_id} did not survive conversion -- nothing was written. "
        "This is a bug in the tool; report the worksheet.")


def _normalise(text: str) -> str:
    """Compare expressions ignoring whitespace entirely.

    ``--expect`` states what the agent read, and ``30*ureg.MPa/1.5`` means the
    same thing as ``30 * ureg.MPa / 1.5``. Spacing is not worth a refusal.
    """
    return re.sub(r"\s+", "", text)


def rewrite(path: Path, out: Path, region_id: int, expect: str,
            value: str) -> tuple[list[str], list[str]]:
    """Edit ``path`` into ``out``. Returns the before/after Python lines."""
    from mcad2py.loader import load_mcdx

    ws = read_worksheet(path)
    pkg = load_mcdx(path)
    new_ws = set_formula(ws, pkg, region_id, expect, value)

    before = python_lines(ws, pkg, region_id)
    after = python_lines(new_ws, pkg, region_id)
    rewrite_zip(path, out, new_ws)
    return before, after


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _list_payload(ws: str, region_id: int | None) -> list[dict]:
    ids = region_ids(ws) if region_id is None else [region_id]
    rows = []
    for rid in ids:
        try:
            expr = current_expr(ws, rid)
        except Refused:
            continue
        row = {"region": rid, "formula": expr_to_str(expr)}
        try:
            emit_expr(expr)
        except Unsupported as exc:
            row["note"] = f"outside the writable subset ({exc})"
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="set_mcdx_formula",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", type=Path, help="the .mcdx worksheet")
    parser.add_argument("--region", type=int, help="region-id "
                        "(from 'mcad2py convert --trace-source')")
    parser.add_argument("--expect", help="the formula you believe is there, as "
                        "Python; required, and checked before anything is written")
    parser.add_argument("--value", help="the new formula, as Python")
    parser.add_argument("-o", "--output", type=Path,
                        help="write here instead of editing the file in place")
    parser.add_argument("--list", action="store_true",
                        help="show the formula in --region (or in every region)")
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
                print(f"{args.file.name}: no formula regions found")
            for entry in payload:
                note = f"   ({entry['note']})" if "note" in entry else ""
                print(f"  region {entry['region']}: {entry['formula']}{note}")
            return 0

        missing = [name for name, val in (("--region", args.region),
                                          ("--expect", args.expect),
                                          ("--value", args.value)) if val is None]
        if missing:
            parser.error(f"{', '.join(missing)} required (or use --list)")

        from mcad2py.loader import load_mcdx

        if args.dry_run:
            pkg = load_mcdx(args.file)
            new_ws = set_formula(ws, pkg, args.region, args.expect, args.value)
            before = python_lines(ws, pkg, args.region)
            after = python_lines(new_ws, pkg, args.region)
            out_path = None
        else:
            out_path = args.output or args.file
            before, after = rewrite(args.file, out_path, args.region,
                                    args.expect, args.value)

        if args.json:
            print(json.dumps({"region": args.region,
                              "before": before, "after": after,
                              "written": None if out_path is None else str(out_path),
                              "results_stale": True}, indent=2))
            return 0
        print(f"region {args.region}:")
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
