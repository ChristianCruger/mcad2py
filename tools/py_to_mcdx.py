#!/usr/bin/env python3
"""Proof of concept: build a new ``.mcdx`` from the Python mcad2py emits.

    python tools/py_to_mcdx.py sheet.py -o sheet.mcdx
    python tools/recalc_mcdx.py sheet.mcdx          # let Prime fill result.xml

The input is the *flat* dialect ``mcad2py convert -f py`` writes:

* ``name = expr``                       -> a definition ``name := expr``
* ``print(name)`` / ``print(disp(name[, unit]))`` straight after it
                                         -> that definition also shows ``=``
* ``print(expr)`` on its own             -> an evaluation ``expr =``
* ``# comment`` lines                    -> skipped (text regions need XAML)
* imports and the module docstring       -> skipped

Expressions: numbers, ``ureg.<unit>``, names, ``+ - * / **``, negation, the
calls ``f(x, ...)`` of a Mathcad builtin, ``nth_root(x, n)``, ``math.pi``,
``math.exp``. Everything else is refused, naming the line.

The new names a sheet defines are turned back into Mathcad names by a fixed
rule (``sigma_c`` -> ``σ`` with subscript ``c``), because ``sanitize()`` has
no inverse. ``result.xml`` is written empty: Prime computes on open.
"""

from __future__ import annotations

import argparse
import ast
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcad2py import ir  # noqa: E402
from mcad2py.emit import mcdx_backend as mb  # noqa: E402
from mcad2py.mapping import FUNCTIONS, GREEK, UNIT_ALIASES  # noqa: E402


class Refused(Exception):
    pass


# ---------------------------------------------------------------------------
# Python -> IR
# ---------------------------------------------------------------------------

# Python transliteration -> Greek letter. First entry wins (σ, not ς; φ, not ϕ).
_GREEK_BACK: dict[str, str] = {}
for _ch, _py in GREEK.items():
    _GREEK_BACK.setdefault(_py.rstrip("_"), _ch)

# Generated Python call head -> Mathcad builtin name.
_FUNC_BACK: dict[str, str] = {}
for _mc, _py in FUNCTIONS.items():
    if isinstance(_py, str):
        _FUNC_BACK.setdefault(_py, _mc)
_FUNC_BACK.update({"math.exp": "exp", "math.log": "ln", "math.sqrt": "sqrt"})

_UNIT_BACK = {py: mc for mc, py in UNIT_ALIASES.items()}

_OPS = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div", ast.Pow: "pow"}


def mathcad_name(py: str) -> str:
    """``sigma_c`` -> ``σ_c``: the inverse of sanitize() by convention."""
    head, sep, sub = py.partition("_")
    head = _GREEK_BACK.get(head, head)
    return head + sep + sub


class Reader:
    def __init__(self, text: str):
        self.text = text

    def expr(self, node: ast.expr) -> ir.Expr:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return ir.Number(ast.get_source_segment(self.text, node) or repr(node.value))
        if isinstance(node, ast.Name):
            return ir.Name(py=node.id, original=mathcad_name(node.id))
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "ureg":
                return ir.UnitRef(_UNIT_BACK.get(node.attr, node.attr))
            if ast.unparse(node) == "math.pi":
                return ir.Name(py="pi", original="π", role="CONSTANT")
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            op = _OPS[type(node.op)]
            left, right = self.expr(node.left), self.expr(node.right)
            if op == "mul" and isinstance(left, ir.Number) and isinstance(right, ir.UnitRef):
                return ir.Quantity(value=left, unit=right)
            return ir.BinOp(op=op, left=left, right=right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = self.expr(node.operand)
            if isinstance(inner, ir.Number) and not inner.value.startswith("-"):
                return ir.Number("-" + inner.value)
            return ir.UnaryOp(op="neg", operand=inner)
        if isinstance(node, ast.Call) and not node.keywords:
            head = ast.unparse(node.func)
            args = [self.expr(a) for a in node.args]
            if head == "nth_root" and len(args) == 2:
                degree = args[1]
                square = isinstance(degree, ir.Number) and degree.value == "2"
                return ir.Root(operand=args[0], degree=None if square else degree)
            if head == "power" and len(args) == 2:
                return ir.BinOp(op="pow", left=args[0], right=args[1])
            if head in _FUNC_BACK:
                return ir.Call(func=_FUNC_BACK[head], args=args)
        raise Refused(f"line {node.lineno}: {ast.unparse(node)!r} is outside the subset")

    def shown(self, stmt: ast.stmt) -> tuple[ir.Expr, ir.Expr | None] | None:
        """``print(x)`` / ``print(disp(x[, unit]))`` -> (x, unit)."""
        if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                and ast.unparse(stmt.value.func) == "print" and len(stmt.value.args) == 1):
            return None
        arg = stmt.value.args[0]
        if isinstance(arg, ast.Call) and ast.unparse(arg.func) == "disp":
            unit = self.expr(arg.args[1]) if len(arg.args) > 1 else None
            return self.expr(arg.args[0]), unit
        if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                and arg.func.attr == "to" and len(arg.args) == 1):
            return self.expr(arg.func.value), self.expr(arg.args[0])
        return self.expr(arg), None


def read_python(text: str) -> list[ir.Region]:
    tree = ast.parse(text)
    reader = Reader(text)
    body = [s for s in tree.body if not isinstance(s, (ast.Import, ast.ImportFrom))]
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # docstring
    regions: list[ir.Region] = []
    i = 0
    while i < len(body):
        stmt = body[i]
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)):
            target = reader.expr(stmt.targets[0])
            define = ir.Define(target=target, value=reader.expr(stmt.value))
            nxt = reader.shown(body[i + 1]) if i + 1 < len(body) else None
            if nxt and isinstance(nxt[0], ir.Name) and nxt[0].py == target.py:
                define.evaluate, define.display_unit = True, nxt[1]
                i += 1
            regions.append(define)
        elif (shown := reader.shown(stmt)) is not None:
            regions.append(ir.Evaluate(value=shown[0], display_unit=shown[1]))
        else:
            raise Refused(f"line {stmt.lineno}: {ast.unparse(stmt)[:60]!r} is not a "
                          "definition or an evaluation")
        i += 1
    return regions


# ---------------------------------------------------------------------------
# IR -> math50 (the stage-A writer, plus calls, roots and constants)
# ---------------------------------------------------------------------------


class Writer(mb._Writer):
    def emit(self, node):
        if isinstance(node, ir.Call):
            head = mb.ID_TEMPLATE.format(role="FUNCTION", body=mb._escape(node.func))
            args = [self.emit(a)[0] for a in node.args]
            inner = args[0] if len(args) == 1 else f"<ml:sequence>{''.join(args)}</ml:sequence>"
            return f"<ml:apply>{head}{inner}</ml:apply>", mb.ATOM_PREC
        if isinstance(node, ir.Root):
            degree = "<ml:placeholder />" if node.degree is None else self.emit(node.degree)[0]
            return (f"<ml:apply><ml:nthRoot />{degree}{self.emit(node.operand)[0]}</ml:apply>",
                    mb.ATOM_PREC)
        return super().emit(node)


def override_xml(writer: Writer, unit: ir.Expr | None) -> str:
    inner = "<ml:placeholder />" if unit is None else writer.emit(unit)[0]
    return f"<ml:unitOverride>{inner}</ml:unitOverride>"


def region_xml(region: ir.Region, rid: int, top: float, writer: Writer) -> str:
    if isinstance(region, ir.Define):
        target = writer.emit(region.target)[0]
        value = writer.emit(region.value)[0]
        if region.evaluate:
            value = f"<ml:eval>{value}{override_xml(writer, region.display_unit)}</ml:eval>"
        math = f"<ml:define>{target}{value}</ml:define>"
    else:
        value = writer.emit(region.value)[0]
        math = f"<ml:eval>{value}{override_xml(writer, region.display_unit)}</ml:eval>"
    return (f'<region region-id="{rid}" top="{top}" left="38.4">'
            f'<math resultRef="{rid}">{math}</math></region>')


# ---------------------------------------------------------------------------
# The package
# ---------------------------------------------------------------------------

_NS = ('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
       'xmlns:ve="http://schemas.openxmlformats.org/markup-compatibility/2006" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
       'xmlns:ws="http://schemas.mathsoft.com/worksheet50" '
       'xmlns:ml="http://schemas.mathsoft.com/math50" '
       'xmlns:u="http://schemas.mathsoft.com/units10" '
       'xmlns:p="http://schemas.mathsoft.com/provenance10" '
       'xmlns="http://schemas.mathsoft.com/worksheet50"')

_XML = '<?xml version="1.0" encoding="utf-8"?>'
_CT = "application/vnd.openxmlformats-officedocument.mathprocessingml.mathcad"

PARTS = {
    "[Content_Types].xml": _XML + (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f'<Default Extension="xml" ContentType="{_CT}.main+xml" />'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
        '<Default Extension="XamlPackage" ContentType="application/zip" />'
        f'<Override PartName="/mathcad/settings/calculation.xml" ContentType="{_CT}.settings.calculation+xml" />'
        f'<Override PartName="/mathcad/result.xml" ContentType="{_CT}.result+xml" />'
        f'<Override PartName="/mathcad/integration.xml" ContentType="{_CT}.integration+xml" />'
        '</Types>'),
    "_rels/.rels": _XML + (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="/mathcad/worksheet.xml" Id="R0" /></Relationships>'),
    "mathcad/settings/calculation.xml": _XML + (
        '<calculation cache-worksheet="true" xmlns="http://schemas.ptc.com/mathcad/settings/calculation10">'
        '<builtInVariables array-origin="0" convergence-tolerance="0.001" constraint-tolerance="0.001" '
        'prn-col-width="8" prn-precision="4" random-seed="1" />'
        '<calculationBehavior automatic-recalculation="true" strings-use-origin="false" '
        'matrix-strict-singularity-check="false" exact-boolean="true" units-in-symbolics="false" '
        'constants-in-symbolics="false" symbolic-engine="axiom" bin-oct-hex-mode="false" />'
        '<units><customUnitSystem base-unit-system="si"><baseUnits /><derivedUnits /></customUnitSystem>'
        '<currentUnitSystem name="si" /></units></calculation>'),
    "mathcad/result.xml": _XML + (
        '<resultsList xmlns:ml="http://schemas.mathsoft.com/math50" '
        'xmlns:u="http://schemas.mathsoft.com/units10" xmlns="http://schemas.mathsoft.com/result10" />'),
    "mathcad/integration.xml": _XML + '<regions xmlns="http://schemas.ptc.com/integration10" />',
}

ROW = 38.4  # one grid row in Prime's default layout, in device-independent px


# Prime refuses to open a package without this part (found by removing parts
# one at a time from a working sheet). It holds styles only, so one copy from
# a Prime-saved sheet serves every generated one.
PRESENTATION = Path(__file__).with_name("mcdx_template") / "presentation.xml"


def build(regions: list[ir.Region]) -> dict[str, str]:
    writer = Writer({})
    body = "".join(region_xml(r, i, ROW * (2 + 1.5 * i), writer)
                   for i, r in enumerate(regions))
    parts = dict(PARTS)
    parts["mathcad/settings/presentation.xml"] = PRESENTATION.read_text(encoding="utf-8-sig")
    parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
        "</Types>",
        '<Override PartName="/mathcad/settings/presentation.xml" '
        f'ContentType="{_CT}.settings.presentation+xml" /></Types>')
    parts["mathcad/worksheet.xml"] = (f'<worksheet {_NS}><regions>{body}</regions></worksheet>')
    return parts


def write_mcdx(parts: dict[str, str], out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in parts.items():
            zf.writestr(name, text.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="py_to_mcdx", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        regions = read_python(args.file.read_text(encoding="utf-8"))
        parts = build(regions)
    except (Refused, mb.Unsupported, SyntaxError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_mcdx(parts, args.output)
    print(f"{len(regions)} regions -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
