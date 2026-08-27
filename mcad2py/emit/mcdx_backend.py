"""IR -> Mathcad Prime ``math50`` XML: the reverse of :mod:`parser.expressions`.

Everything else in this package reads a worksheet. This backend writes one, so
a tool can replace a region's expression tree instead of splicing text over a
single number (which is all ``tools/set_mcdx_literal.py`` can do).

Two things shape it:

* **It emits prefixed text, not ElementTree.** The output uses the literal
  ``ml:`` prefix and is therefore only valid spliced into a worksheet that
  binds that prefix -- which every ``worksheet.xml`` does, on its root element.
  Text keeps the write byte-minimal: nothing outside the replaced span is
  re-serialised, so an unrelated part of the region cannot be reformatted.
* **The subset is deliberately small** (stage A: numbers, units, the five
  arithmetic operators, negation and names). Anything outside it raises
  :class:`Unsupported`, because emitting a half-understood construct into a
  proprietary format is worse than refusing.

The parser drops ``<ml:parens>`` -- the tree already carries precedence -- but
Prime *displays* from the tree, so this backend puts them back wherever Python
would need parentheses. That mirrors what Prime writes itself and can never
change the meaning.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping

from .. import ir
from ..mapping import BINARY_OPS, UNARY_PREC
from ..parser.expressions import read_identifier
from ..parser.namespaces import localname

# Canonical IR op -> Mathcad operator tag, for the ops this backend emits.
# Kept as a narrow whitelist rather than an inversion of ``OPERATOR_TAGS``:
# comparisons and boolean connectives only ever appear inside a program, which
# is not in the subset.
ARITHMETIC_TAGS = {
    "add": "plus",
    "sub": "minus",
    "mul": "mult",
    "div": "div",
    "pow": "pow",
}

# What Prime writes into an <ml:real>. ``.87`` (a leading dot, no zero) is
# Prime's own form, so it is accepted as well as produced.
REAL = re.compile(r"-?(\d+(\.\d*)?|\.\d+)")

ID_TEMPLATE = '<ml:id labels="{role}" label-is-contextual="true" xml:space="preserve">{body}</ml:id>'

# Prime writes a subscripted name as inline XAML, declaring both namespaces on
# the Span itself (the worksheet root does not bind them).
SPAN_TEMPLATE = (
    '<Span xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"'
    ' xmlns:pw="clr-namespace:Ptc.Wpf;assembly=Ptc.Core">'
    "{head}<pw:Subscript>{sub}</pw:Subscript></Span>"
)

# An atom needs no parentheses anywhere.
ATOM_PREC = 99


class Unsupported(Exception):
    """The IR node has no Mathcad XML form in this backend's subset."""


def emit_expr(node: ir.Expr, ids: Mapping[tuple[str, str], str] | None = None) -> str:
    """Mathcad ``math50`` XML text for ``node``.

    ``ids`` maps ``(role, display name)`` to the verbatim ``<ml:id>`` XML the
    worksheet already uses for that name -- see :func:`harvest_ids`. Pass it
    whenever rewriting an existing sheet: Prime has **two** encodings for a
    subscripted name (inline XAML, and plain text with an underscore) and the
    parser reads both to the same IR, so synthesising one would silently
    restyle a name the author typed the other way.

    Raises :class:`Unsupported` for any node outside the supported subset.
    """
    text, _prec = _Writer(ids or {}).emit(node)
    return text


def supported(node: ir.Expr) -> bool:
    """Whether :func:`emit_expr` can write ``node``."""
    try:
        emit_expr(node)
    except Unsupported:
        return False
    return True


# ---------------------------------------------------------------------------
# Harvesting the names a worksheet already uses
# ---------------------------------------------------------------------------

# ``<ml:id>`` never nests, so a non-greedy match is safe; the body can still
# hold a XAML <Span>, hence DOTALL.
_ID = re.compile(r"<ml:id[^>]*/>|<ml:id(?P<attrs>[^>]*)>(?P<body>.*?)</ml:id>", re.S)
_LABELS = re.compile(r'labels="([^"]*)"')


def harvest_ids(worksheet_xml: str) -> dict[tuple[str, str], str]:
    """Map ``(role, display name)`` to the ``<ml:id>`` XML the sheet uses.

    The pairing is positional -- the *n*-th ``<ml:id>`` in the text is the
    *n*-th one ElementTree walks -- so a disagreement in the counts means the
    text held something the walk did not, and the whole map is dropped rather
    than risking a name being given another name's XML. The caller then falls
    back to a synthesised id, which is correct but may restyle a subscript.
    """
    try:
        root = ET.fromstring(worksheet_xml)
    except ET.ParseError:
        return {}
    nodes = [e for e in root.iter() if localname(e.tag) == "id"]
    spans = list(_ID.finditer(worksheet_xml))
    if len(nodes) != len(spans):
        return {}

    found: dict[tuple[str, str], str] = {}
    for node, span in zip(nodes, spans):
        name = read_identifier(node)
        role = node.get("labels", "VARIABLE")
        text = span.group(0)
        key = (role, name)
        # Prefer an id from inside an expression: the same unit written in a
        # <ml:unitOverride> carries no ``label-is-contextual``.
        if key not in found or "label-is-contextual" in text:
            found[key] = text
    return found


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------


class _Writer:
    """Carries the harvested ids through the recursive emit."""

    def __init__(self, ids: Mapping[tuple[str, str], str]):
        self.ids = ids

    def emit(self, node: ir.Expr) -> tuple[str, int]:
        """The XML for ``node`` and its precedence, for the parens rule."""
        if isinstance(node, ir.Number):
            return f"<ml:real>{_number(node.value)}</ml:real>", ATOM_PREC

        if isinstance(node, ir.UnitRef):
            return self.unit(node.name), ATOM_PREC

        if isinstance(node, ir.Name):
            return self.identifier(node.original, node.role), ATOM_PREC

        if isinstance(node, ir.Parens):
            # An explicit group in the IR: keep it, whatever precedence says.
            inner, _prec = self.emit(node.inner)
            return f"<ml:parens>{inner}</ml:parens>", ATOM_PREC

        if isinstance(node, ir.Quantity):
            value = self.scale_value(node.value)
            unit = self.wrap(node.unit, _MUL_PREC, parent_op="scale")
            return f"<ml:apply><ml:scale />{value}{unit}</ml:apply>", _MUL_PREC

        if isinstance(node, ir.BinOp):
            return self.binop(node)

        if isinstance(node, ir.UnaryOp):
            if node.op != "neg":
                raise Unsupported(f"unary {node.op!r} is outside the subset")
            operand = self.wrap(node.operand, UNARY_PREC, parent_op="neg")
            return f"<ml:apply><ml:neg />{operand}</ml:apply>", UNARY_PREC

        raise Unsupported(f"{type(node).__name__} is outside the subset")

    def binop(self, node: ir.BinOp) -> tuple[str, int]:
        tag = ARITHMETIC_TAGS.get(node.op)
        if tag is None:
            raise Unsupported(f"operator {node.op!r} is outside the subset")
        prec = BINARY_OPS[node.op][1]
        # ``**`` is right-associative, so its *left* operand is the one that
        # needs a group at equal precedence; every other operator is the
        # mirror of that.
        right_assoc = node.op == "pow"
        left = self.wrap(node.left, prec, tighter=right_assoc, parent_op=node.op)
        right = self.wrap(node.right, prec, tighter=not right_assoc,
                          parent_op=node.op)
        return f"<ml:apply><ml:{tag} />{left}{right}</ml:apply>", prec

    def scale_value(self, node: ir.Expr) -> str:
        """The value slot of a ``<ml:scale/>``, grouped where Prime groups it.

        A scale is drawn as juxtaposition (``30 MPa``), so anything drawn *in
        line* has to be bracketed or it reads as part of the product:
        ``(0.85 · 30) MPa``. Anything Prime draws two-dimensionally does not --
        a power is a superscript, a division is a stacked fraction -- and the
        fixtures hold exactly those two unbracketed.

        Confirmed by Prime itself: it added this group when it re-saved a sheet
        this backend had written without one.
        """
        text, _prec = self.emit(node)
        if isinstance(node, (ir.Number, ir.Name, ir.UnitRef, ir.Quantity, ir.Parens)):
            return text
        if isinstance(node, ir.BinOp) and node.op in ("pow", "div"):
            return text
        return f"<ml:parens>{text}</ml:parens>"

    def wrap(self, node: ir.Expr, parent_prec: int, *, tighter: bool = False,
             parent_op: str | None = None) -> str:
        """``node``'s XML, in ``<ml:parens>`` if Prime would show a group.

        ``tighter`` marks the operand that must bind strictly tighter than its
        parent -- the right of ``a - b``, the left of ``a ** b``.

        Two shapes need no group whatever the precedence says, because Prime
        does not *draw* them in line: a scaled quantity is juxtaposition
        (``30 MPa``), and a division is a stacked fraction. Both are read
        unambiguously without brackets, and Prime writes none -- except for a
        fraction under a power, where it does (``(RH/100)³``). Everywhere else
        the rule stays a superset of Prime's: it can add a group Prime omits,
        never drop one Prime needs.
        """
        text, prec = self.emit(node)
        if isinstance(node, ir.Quantity):
            return text
        if isinstance(node, ir.BinOp) and node.op == "div" and parent_op != "pow":
            return text
        if prec < parent_prec or (tighter and prec == parent_prec):
            return f"<ml:parens>{text}</ml:parens>"
        return text

    # -- leaves that may come from the sheet ------------------------------

    def unit(self, name: str) -> str:
        # ``%`` is a real Mathcad unit but Prime labels it FUNCTION, not UNIT.
        role = "FUNCTION" if name == "%" else "UNIT"
        existing = self.ids.get((role, name))
        return existing if existing else ID_TEMPLATE.format(
            role=role, body=_escape(name))

    def identifier(self, original: str, role: str) -> str:
        if role not in ("VARIABLE", "CONSTANT"):
            raise Unsupported(f"identifier role {role!r} is outside the subset")
        if not original:
            raise Unsupported("an identifier with no name")
        existing = self.ids.get((role, original))
        if existing:
            return existing
        head, sep, sub = original.partition("_")
        if not sep:
            body = _escape(original)
        elif not head or "_" in sub:
            # Mathcad has no way to type a leading or a second underscore: one
            # underscore opens the subscript and the rest of the name is in it.
            raise Unsupported(f"{original!r} is not a name Mathcad can display")
        else:
            body = SPAN_TEMPLATE.format(head=_escape(head), sub=_escape(sub))
        return ID_TEMPLATE.format(role=role, body=body)


_MUL_PREC = BINARY_OPS["mul"][1]


# ---------------------------------------------------------------------------
# Leaves
# ---------------------------------------------------------------------------


def _number(value: str) -> str:
    """Validate a numeric literal and return the text Prime should store."""
    text = value.strip()
    if not REAL.fullmatch(text):
        # A complex literal (``2j``) has its own <ml:imag> element, and a
        # rendered float such as ``1e-05`` is not a form Prime writes.
        raise Unsupported(f"{value!r} is not a Mathcad real literal")
    return text


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
