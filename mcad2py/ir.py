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
class MatrixLiteral(Expr):
    """A Mathcad matrix/vector literal.

    ``elements`` is stored in the XML's own order, which is **column-major**
    (confirmed against Prime's ``<ml:matrix>``: the first ``rows`` elements
    are column 0, the next ``rows`` are column 1, etc.) -- the ``matrix()``
    runtime helper reshapes accordingly. Column and row vectors (``rows == 1``
    or ``cols == 1``) emit a 1-D NumPy/Pint array instead, via ``col()``, so
    they index, broadcast, and ``len()`` like Mathcad vectors.
    """

    rows: int
    cols: int
    elements: list[Expr]


@dataclass
class Index(Expr):
    """Element access (Mathcad ``indexer``): ``v[i]`` (indices are 0-based)."""

    base: Expr
    index: Expr


@dataclass
class Vectorize(Expr):
    """Mathcad's element-wise 'arrow' over an expression.

    Emitted as ``vectorize(<operand>)``; the runtime helper is an identity
    pass-through because vectors are NumPy/Pint arrays and ``min``/``max`` map
    to ``np.minimum``/``np.maximum``, so the wrapped expression already
    evaluates element-wise.
    """

    operand: Expr


@dataclass
class Transpose(Expr):
    """Mathcad matrix/vector transpose (``<ml:transpose>``).

    Emitted as ``transpose(<operand>)``; the runtime helper is unit-aware and,
    for the 1-D vectors we build with ``col()``, is effectively identity (a row
    vector and a column vector are the same NumPy 1-D array) -- enough for the
    common case of feeding ``linterp`` a transposed data column.
    """

    operand: Expr


@dataclass
class Range(Expr):
    """A Mathcad range ``start, next .. stop`` -> ``np.arange`` (inclusive)."""

    start: Expr
    stop: Expr
    step: Expr | None = None


@dataclass
class Program(Expr):
    """A Mathcad program body of if/elif/else branches.

    Each branch is ``(test, result)``; a ``None`` test is the final ``else``.
    A :class:`Define` whose value is a ``Program`` emits a ``def`` (not a
    ``lambda``) so the branching is preserved.
    """

    branches: list[tuple[Expr | None, Expr]]


@dataclass
class Lambda(Expr):
    """An inline anonymous function (Mathcad ``<ml:lambda>``).

    Used as the integrand of an :class:`Integral` and the summand of a
    :class:`Summation`; emits ``lambda <params>: <body>``.
    """

    params: list[str]
    body: Expr


@dataclass
class Integral(Expr):
    """A definite *numeric* integral (Mathcad ``∫…=``).

    Emitted as ``integral(<func>, <lower>, <upper>)`` -> a unit-aware
    ``scipy.integrate.quad`` wrapper. (The symbolic ``∫…→`` arrow would route to
    SymPy instead, like the symbolic ``solve``.)
    """

    func: Lambda
    lower: Expr
    upper: Expr


@dataclass
class Summation(Expr):
    """A discrete summation over an integer index range (inclusive bounds).

    Emitted as ``summation(<func>, <lower>, <upper>)`` -> a plain Python sum.
    """

    func: Lambda
    lower: Expr
    upper: Expr


@dataclass
class Equation(Expr):
    """A symbolic equation (Mathcad boolean/symbolic ``=``) -> SymPy ``Eq``.

    Unlike ``Define`` (``:=``) this binds nothing; it states a relation.
    """

    lhs: Expr
    rhs: Expr


@dataclass
class Str(Expr):
    """A Mathcad string literal (``<ml:str>``) -> a Python ``str``."""

    value: str


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
    ``display_unit`` is the unit expression the result should be shown in (from
    ``unitOverride``) -- a single unit or a compound like ``kN*m`` -- or None
    for automatic units. ``params`` is non-empty for a function definition
    (``f(x) := ...``), in which case ``value`` is the body and the define emits
    a ``lambda``. ``comment`` is an optional note rendered as ``#`` lines above
    the assignment (used to document a scriptable control's cached value).
    """

    target: Name
    value: Expr
    evaluate: bool = False
    display_unit: Expr | None = None
    params: list[str] = field(default_factory=list)
    comment: str | None = None


@dataclass
class Evaluate(Region):
    """A bare ``expr =`` evaluation with no definition."""

    value: Expr
    display_unit: Expr | None = None


@dataclass
class IndexAssign(Region):
    """A range-indexed vector assignment: ``X[i] := expr`` with ``i`` a range.

    Mathcad iterates ``index`` over its range and *builds* the 0-based vector
    ``target``, zero-filling any lower index never written. Emitted as
    ``X = index_build(i, lambda i: expr)`` -- the lambda's ``i`` is a *scalar*
    index, so the right-hand side (and any ``X[i]`` reads inside it) evaluates
    per-element with the ordinary scalar codegen. ``evaluate``/``display_unit``
    mirror :class:`Define` for an inline ``=`` that shows ``X[i]``.
    """

    target: Name
    index: Name
    value: Expr
    evaluate: bool = False
    display_unit: Expr | None = None


@dataclass
class ComboBoxAssign(Region):
    """A Mathcad ``<ml:ComboBoxControl>`` row-selector assignment.

    A native (non-scripted) control: the user picks a row (``SelectedRow``) from
    a table of named rows, and the row's column value(s) are assigned to the
    left-hand-side target(s) -- a single ``<ml:id>`` or a ``<ml:matrix>`` of ids.
    A control with no ``<ml:ComboBoxValues>`` yields the selected row *name* (a
    string). ``targets`` and ``values`` are parallel; ``comment`` documents the
    selection (the embedded option list isn't otherwise represented).
    """

    targets: list[Name]
    values: list[Expr]
    comment: str | None = None


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
class SolveBlock(Region):
    """A Mathcad numeric solve block (Given/Find).

    ``guesses`` seed the unknowns; ``constraints`` are numeric equations the
    solution must satisfy; ``unknowns`` are the variables passed to ``find``;
    ``targets`` are where the result is stored (``[e_1; k_1] := find(e, k)``).
    Emits a ``scipy.optimize`` solve via the ``solve_block`` runtime helper.

    ``params`` is non-empty when the solver region *defines a function* —
    ``f(a, b) := find(x)`` — in which case ``targets`` holds the single function
    name and the whole solve is emitted inside ``def f(a, b):`` so the
    constraints close over the parameters, returning the solved unknown(s).
    """

    guesses: list[Define]
    constraints: list[Equation]
    unknowns: list[Name]
    targets: list[Name]
    command: str = "find"
    display_unit: Expr | None = None
    params: list[str] = field(default_factory=list)


@dataclass
class PlotTrace:
    """One curve of an X-Y plot: paired x/y expressions and their axis units."""

    x: Expr
    y: Expr
    x_unit: Expr | None = None
    y_unit: Expr | None = None
    color: str | None = None


@dataclass
class Plot(Region):
    """A Mathcad X-Y plot (``<xyPlot>``) → a matplotlib figure.

    ``domain`` is the independent array variable (the bare-``Name`` axis, e.g.
    ``e_plot``/``z_plot``); trace expressions are sampled element-wise over it
    so branching programs and units survive.
    """

    traces: list[PlotTrace]
    domain: str | None = None


@dataclass
class GridPlot(Region):
    """A Mathcad contour or 3D plot (``<contourPlot>``/``<plot3D>``) -> a
    matplotlib ``contourf``/``plot_surface`` (or scatter) figure.

    Unlike ``<xyPlot>``, there's a single plot equation resolving to the whole
    surface, in one of two shapes (see ``resolve_plot_grid`` in runtime.py):
    an expression referencing exactly two *range* variables (defined earlier
    in the sheet as ``<ml:range>``s, not plain vectors), anywhere in it --
    a direct call (``f(x0, y0)``) or a composition (``sigma(epsilon(x0*mm,
    y0*mm))``) alike -- since Mathcad takes the ranges' outer product rather
    than zipping them; ``mesh_names`` holds ``(x_name, y_name)`` (in order of
    first appearance) for this case, and codegen wraps the whole expression in
    ``mesh_grid(lambda x, y: <expr>, x, y)``. Or a bare matrix/mesh reference
    (``mesh_names`` is ``None``, ``expr`` is evaluated as-is and resolved at
    runtime). ``threed`` distinguishes ``<plot3D>`` (``mplot3d``) from
    ``<contourPlot>``.
    """

    expr: Expr
    z_unit: Expr | None = None
    mesh_names: tuple[str, str] | None = None
    threed: bool = False


@dataclass
class TextRegion(Region):
    """A text/comment region."""

    text: str


@dataclass
class ImageRegion(Region):
    """An embedded image (Mathcad ``<picture>``). ``data`` is the raw bytes."""

    data: bytes
    mime: str
    name: str = ""


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
    if isinstance(node, MatrixLiteral):
        return list(node.elements)
    if isinstance(node, Index):
        return [node.base, node.index]
    if isinstance(node, Vectorize):
        return [node.operand]
    if isinstance(node, Transpose):
        return [node.operand]
    if isinstance(node, Range):
        return [node.start, node.stop] + ([node.step] if node.step is not None else [])
    if isinstance(node, Program):
        out: list[Expr] = []
        for test, result in node.branches:
            if test is not None:
                out.append(test)
            out.append(result)
        return out
    if isinstance(node, Lambda):
        return [node.body]
    if isinstance(node, (Integral, Summation)):
        return [node.func, node.lower, node.upper]
    return []
