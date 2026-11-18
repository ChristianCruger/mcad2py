#!/usr/bin/env python3
"""Proof of concept: build a new ``.mcdx`` from the Python mcad2py emits.

    python tools/py_to_mcdx.py sheet.py -o sheet.mcdx
    python tools/recalc_mcdx.py sheet.mcdx          # let Prime fill result.xml

The input is the *flat* dialect ``mcad2py convert -f py`` writes:

* ``name = expr``                       -> a definition ``name := expr``
* ``print(name)`` / ``print(disp(name[, unit]))`` straight after it
                                         -> that definition also shows ``=``
* ``print(expr)`` on its own             -> an evaluation ``expr =``
* a block of ``# comment`` lines         -> a text region, one paragraph per line
* imports and the module docstring       -> skipped

A comment *after* code on the same line (``# mcdx region 3`` from
``--trace-source``) is not text and is ignored.

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
import io
import sys
import tokenize
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


def comment_blocks(text: str) -> list[tuple[int, list[str]]]:
    """``(first line, [paragraph, ...])`` for each run of whole-line comments.

    A run ends at a blank line or at code, which is how the backends separate
    one text region from the next. A comment that shares its line with code is
    an annotation, not text.
    """
    blocks: list[tuple[int, list[str]]] = []
    last_line = -2
    code_lines: set[int] = set()
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    for tok in tokens:
        if tok.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                            tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
            code_lines.update(range(tok.start[0], tok.end[0] + 1))
    for tok in tokens:
        if tok.type != tokenize.COMMENT or tok.start[0] in code_lines:
            continue
        line = tok.start[0]
        body = tok.string[1:].removeprefix(" ").rstrip()
        if blocks and line == last_line + 1:
            blocks[-1][1].append(body)
        else:
            blocks.append((line, [body]))
        last_line = line
    return [(line, paras) for line, paras in blocks if any(p.strip() for p in paras)]


def read_python(text: str) -> list[ir.Region]:
    tree = ast.parse(text)
    reader = Reader(text)
    body = [s for s in tree.body if not isinstance(s, (ast.Import, ast.ImportFrom))]
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # docstring
    texts = comment_blocks(text)
    regions: list[ir.Region] = []
    i = 0
    while i < len(body) or texts:
        if texts and (i >= len(body) or texts[0][0] < body[i].lineno):
            _line, paras = texts.pop(0)
            regions.append(ir.TextRegion(text="\n".join(paras)))
            continue
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


# What Prime writes inline for a text region; the real content lives in the
# XamlPackage the ``item-idref`` names.
FLOW_DOC = ('<FlowDocument FontFamily="Tahoma" FontStyle="Normal" FontWeight="Normal" '
            'FontSize="14.6666666666667" Foreground="#FF000000" Background="#00FFFFFF" '
            'TextAlignment="Left" xml:lang="en-us" Typography.Variants="Normal" '
            'xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" />')

_XAML_NS = "http://schemas.microsoft.com/winfx/2006/xaml/presentation"


def xaml_package(paragraphs: list[str]) -> bytes:
    """A FlowDocument XamlPackage: a zip in the zip, one ``Document.xaml``."""
    paras = "".join(
        f'<Paragraph><Run>{mb._escape(p)}</Run></Paragraph>' if p else "<Paragraph />"
        for p in paragraphs)
    doc = (f'<Section xmlns="{_XAML_NS}" xml:space="preserve" TextAlignment="Left" '
           'xml:lang="en-us" FontFamily="Tahoma" FontSize="14.6666666666667" '
           f'Foreground="#FF000000">{paras}</Section>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _XML + (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xaml" ContentType="application/vnd.ms-wpf.xaml+xml" />'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
            '</Types>'))
        zf.writestr("_rels/.rels", _XML + (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Type="http://schemas.microsoft.com/wpf/2005/10/xaml/entry" '
            'Target="/Xaml/Document.xaml" Id="R0" /></Relationships>'))
        zf.writestr("Xaml/Document.xaml", doc)
    return buf.getvalue()


# Text a region is this wide before it wraps, in px; about 7 px per character
# of 11 pt Tahoma.
TEXT_MIN_WIDTH, TEXT_MAX_WIDTH, CHAR_WIDTH = 200, 600, 7.5


def text_width(paragraphs: list[str]) -> float:
    longest = max((len(p) for p in paragraphs), default=0)
    return max(TEXT_MIN_WIDTH, min(TEXT_MAX_WIDTH, round(longest * CHAR_WIDTH)))


def region_xml(region: ir.Region, rid: int, top: float, writer: Writer) -> str:
    if isinstance(region, ir.TextRegion):
        width = text_width(region.text.split("\n"))
        return (f'<region region-id="{rid}" width="{width}" top="{top}" left="38.4">'
                f'<text item-idref="Rtext{rid}">{FLOW_DOC}</text></region>')
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


def rows(region: ir.Region) -> float:
    """Grid rows ``region`` takes, including the gap below it."""
    if isinstance(region, ir.TextRegion):
        lines = sum(1 + len(p) * CHAR_WIDTH // TEXT_MAX_WIDTH
                    for p in region.text.split("\n"))
        return 0.5 + 0.5 * lines
    return 1.5


def build(regions: list[ir.Region]) -> dict[str, str | bytes]:
    writer = Writer({})
    body, top, rels = [], 2 * ROW, []
    parts: dict[str, str | bytes] = dict(PARTS)
    math_id = 0
    for rid, region in enumerate(regions):
        if isinstance(region, ir.TextRegion):
            target = f"/mathcad/xaml/FlowDocument{rid}.XamlPackage"
            parts[target.lstrip("/")] = xaml_package(region.text.split("\n"))
            rels.append('<Relationship Type="http://schemas.openxmlformats.org/officeDocument/'
                        f'2006/relationships/flowDocument" Target="{target}" Id="Rtext{rid}" />')
            body.append(region_xml(region, rid, round(top, 4), writer))
        else:
            # resultRef numbers the math regions only, as Prime does.
            body.append(region_xml(region, rid, round(top, 4), writer)
                        .replace(f'resultRef="{rid}"', f'resultRef="{math_id}"'))
            math_id += 1
        top += rows(region) * ROW
    if rels:
        parts["mathcad/_rels/worksheet.xml.rels"] = _XML + (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels) + "</Relationships>")
    body = "".join(body)
    parts["mathcad/settings/presentation.xml"] = PRESENTATION.read_text(encoding="utf-8-sig")
    parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
        "</Types>",
        '<Override PartName="/mathcad/settings/presentation.xml" '
        f'ContentType="{_CT}.settings.presentation+xml" /></Types>')
    parts["mathcad/worksheet.xml"] = (f'<worksheet {_NS}><regions>{body}</regions></worksheet>')
    return parts


def write_mcdx(parts: dict[str, str | bytes], out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in parts.items():
            zf.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))


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
