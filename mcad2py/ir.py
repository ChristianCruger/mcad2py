"""Intermediate representation (IR) for a converted Mathcad worksheet.

The parser turns Mathcad XML into these backend-agnostic nodes; the emit
backends (notebook, py) turn them into source. Keeping a real IR in the middle
means a future ``.xmcd`` parser or SymPy backend can be added without touching
the other half of the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Expression nodes
# ---------------------------------------------------------------------------


class Expr:
    """Base class for expression IR nodes."""


@dataclass
class Number(Expr):
    """A numeric literal, kept as the original string to preserve formatting."""

    value: str


@dataclass
class Name(Expr):
    """A reference to an identifier (variable, function, or constant).

    ``py`` is the sanitized Python-safe name; ``original`` is the Mathcad
    display name; ``role`` is the Mathcad label (VARIABLE/FUNCTION/CONSTANT/UNIT).
    """

    py: str
    original: str
    role: str = "VARIABLE"


@dataclass
class UnitRef(Expr):
    """A reference to a unit, e.g. ``MPa`` -> ``ureg.MPa``."""

    name: str


@dataclass
class Quantity(Expr):
    """A number scaled by a unit (Mathcad ``scale``): ``30 MPa``."""

    value: Expr
    unit: Expr


@dataclass
class BinOp(Expr):
    """Binary operator. ``op`` is a canonical name: add/sub/mul/div/pow."""

    op: str
    left: Expr
    right: Expr


@dataclass
class UnaryOp(Expr):
    op: str
    operand: Expr


@dataclass
class Call(Expr):
    """Function application, e.g. ``tan(phi)``."""

    func: str
    args: list[Expr]
    role: str = "FUNCTION"


@dataclass
class Root(Expr):
    """nth root. ``degree=None`` means square root."""

    operand: Expr
    degree: Expr | None = None


@dataclass
class Parens(Expr):
    inner: Expr


@dataclass
class Equation(Expr):
    """A symbolic equation (Mathcad boolean/symbolic ``=``) -> SymPy ``Eq``.

    Unlike ``Define`` (``:=``) this binds nothing; it states a relation.
    """

    lhs: Expr
    rhs: Expr


@dataclass
class Placeholder(Expr):
    """An empty Mathcad placeholder slot."""


@dataclass
class Unsupported(Expr):
    """A construct we do not yet translate; carries a note for a TODO marker."""

    note: str
    raw: str = ""


# ---------------------------------------------------------------------------
# Region (statement) nodes
# ---------------------------------------------------------------------------


class Region:
    """Base class for top-level worksheet regions (ordered by position)."""


@dataclass
class Define(Region):
    """A ``:=`` definition, optionally evaluated inline (``=``).

    ``evaluate`` is True when the worksheet shows the result inline.
    ``display_unit`` is the unit the result should be shown in (from
    ``unitOverride``), or None for automatic units.
    """

    target: Name
    value: Expr
    evaluate: bool = False
    display_unit: str | None = None


@dataclass
class Evaluate(Region):
    """A bare ``expr =`` evaluation with no definition."""

    value: Expr
    display_unit: str | None = None


@dataclass
class SymbolDeclarations(Region):
    """Declare free identifiers as SymPy ``Symbol``s before symbolic regions.

    Injected by the parser ahead of the first symbolic region so the equations
    that follow have something to bind to. ``names`` are Python-safe and are
    used verbatim both as the variable and as the symbol's string name.
    """

    names: list[str]


@dataclass
class SymbolicEquation(Region):
    """A standalone symbolic equation shown as a step (assigned to nothing)."""

    equation: Equation


@dataclass
class SymbolicEval(Region):
    """A Mathcad symbolic evaluation, e.g. ``... solve, C``.

    ``command`` is a SymPy callable name (``solve``/``simplify``/...); ``expr``
    is the input (often an :class:`Equation`); ``args`` are extra command
    arguments (for ``solve``, the variable(s) to solve for). ``result`` is
    Mathcad's cached symbolic answer, kept for tests (not emitted).
    """

    expr: Expr
    command: str
    args: list[Expr] = field(default_factory=list)
    result: Expr | None = None


@dataclass
class TextRegion(Region):
    """A text/comment region."""

    text: str


@dataclass
class UnsupportedRegion(Region):
    note: str
    raw: str = ""


# ---------------------------------------------------------------------------
# Worksheet
# ---------------------------------------------------------------------------


@dataclass
class Worksheet:
    regions: list[Region] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Structural traversal (backend-agnostic)
# ---------------------------------------------------------------------------


def child_exprs(node: object) -> list[Expr]:
    """The sub-expressions of an expression node, for generic tree walks."""
    if isinstance(node, Quantity):
        return [node.value, node.unit]
    if isinstance(node, BinOp):
        return [node.left, node.right]
    if isinstance(node, UnaryOp):
        return [node.operand]
    if isinstance(node, Call):
        return list(node.args)
    if isinstance(node, Root):
        return [node.operand] + ([node.degree] if node.degree is not None else [])
    if isinstance(node, Equation):
        return [node.lhs, node.rhs]
    if isinstance(node, Parens):
        return [node.inner]
    return []
