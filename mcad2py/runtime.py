"""Runtime helpers imported by generated code.

Mathcad's trig functions interpret an angle-with-units (e.g. ``37 deg``)
correctly, and a bare number as radians. Pint quantities can't be passed to
``math.tan`` directly, so these wrappers convert angle quantities to radians
first. This keeps generated code clean (``tan(phi)`` instead of
``math.tan(phi.to(ureg.radian).magnitude)``) while matching Mathcad semantics.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np


def _radians(x: object) -> float:
    """Coerce ``x`` to a float number of radians.

    Accepts a plain number (already radians, per Mathcad) or a Pint quantity
    carrying an angle/dimensionless unit (e.g. ``deg``, ``rad``).

    Mathcad's angle units are *dimensionless scales* (``deg`` = π/180), so this
    doubles as "reduce a pure-number argument to a float": the hyperbolic and
    inverse-trig builtins below take a plain number, and feeding one an angle
    (or an unreduced ratio like ``mm/mm``) must give its radian/reduced value.
    """
    to = getattr(x, "to", None)
    if callable(to):
        try:
            return float(to("radian").magnitude)
        except Exception:
            return float(getattr(x, "magnitude", x))
    return float(x)


def sin(x: object) -> float:
    return math.sin(_radians(x))


def cos(x: object) -> float:
    return math.cos(_radians(x))


def tan(x: object) -> float:
    return math.tan(_radians(x))


def cot(x: object) -> float:
    return 1.0 / math.tan(_radians(x))


def sec(x: object) -> float:
    return 1.0 / math.cos(_radians(x))


def csc(x: object) -> float:
    return 1.0 / math.sin(_radians(x))


def sinc(x: object) -> float:
    """Mathcad ``sinc(z) = sin(z)/z`` (``1`` at ``0``).

    The *unnormalised* sinc -- note ``np.sinc`` is the normalised
    ``sin(πx)/(πx)`` and would be wrong here.
    """
    z = _radians(x)
    return 1.0 if z == 0.0 else math.sin(z) / z


# Inverse trig / hyperbolic results are angles in radians, returned as plain
# floats -- exactly as Mathcad stores them (its ``deg`` is a dimensionless
# π/180 scale, so a ``deg`` display override is applied by ``disp``).


def asin(x: object) -> float:
    return math.asin(_radians(x))


def acos(x: object) -> float:
    return math.acos(_radians(x))


def atan(x: object) -> float:
    return math.atan(_radians(x))


def acot(x: object) -> float:
    """Inverse cotangent, ``π/2 - atan(x)`` -- the branch on ``(0, π)``.

    Mathcad follows the Maple/MuPAD convention here (continuous across ``x=0``),
    not Mathematica's ``atan(1/x)``. The two agree for positive ``x`` and differ
    for negative: ``references/trig.mcdx`` caches ``acot(-2) = 2.67794``, i.e.
    ``π/2 - atan(-2)``, not ``atan(-0.5) = -0.46365``.
    """
    return math.pi / 2 - math.atan(_radians(x))


def asec(x: object) -> float:
    return math.acos(1.0 / _radians(x))


def acsc(x: object) -> float:
    return math.asin(1.0 / _radians(x))


def atan2(x: object, y: object) -> float:
    """Mathcad ``atan2(x, y)``: the angle of the point ``(x, y)``, in ``(-π, π]``.

    Note the argument order is the *opposite* of Python's ``math.atan2(y, x)``.
    """
    return math.atan2(_radians(y), _radians(x))


def angle(x: object, y: object) -> float:
    """Mathcad ``angle(x, y)``: like :func:`atan2` but wrapped to ``[0, 2π)``."""
    return math.atan2(_radians(y), _radians(x)) % (2 * math.pi)


def sinh(x: object) -> float:
    return math.sinh(_radians(x))


def cosh(x: object) -> float:
    return math.cosh(_radians(x))


def tanh(x: object) -> float:
    return math.tanh(_radians(x))


def coth(x: object) -> float:
    return 1.0 / math.tanh(_radians(x))


def sech(x: object) -> float:
    return 1.0 / math.cosh(_radians(x))


def csch(x: object) -> float:
    return 1.0 / math.sinh(_radians(x))


def asinh(x: object) -> float:
    return math.asinh(_radians(x))


def acosh(x: object) -> float:
    return math.acosh(_radians(x))


def atanh(x: object) -> float:
    return math.atanh(_radians(x))


def acoth(x: object) -> float:
    return math.atanh(1.0 / _radians(x))


def asech(x: object) -> float:
    return math.acosh(1.0 / _radians(x))


def acsch(x: object) -> float:
    return math.asinh(1.0 / _radians(x))


def elementwise(fn):
    """Wrap a scalar (possibly *branching*) function so it also maps over a vector.

    Mathcad's vectorize arrow applies such a function element-wise; a Python
    ``def`` with ``if`` can't take an array, so for an array argument we apply
    ``fn`` per element (unit-aware, via ``col``) and a scalar passes straight
    through. This covers a piecewise stress-strain law ``σ(ε)`` sampled over a
    vector of fiber strains.
    """

    def wrapped(x):
        if _is_arraylike(x):
            return col(*[fn(xi) for xi in x])
        return fn(x)

    return wrapped


def _flatten_scalars(args):
    """All scalar elements across ``args`` (scalars and/or vectors), unit-aware.

    A Pint vector contributes its elements as Pint scalars; a plain vector its
    numbers; a scalar contributes itself.
    """
    out = []
    for a in args:
        if _is_arraylike(a):
            unit = getattr(a, "units", None)
            mag = np.atleast_1d(getattr(a, "magnitude", a)).reshape(-1)
            out.extend((m * unit) if unit is not None else m for m in mag)
        else:
            out.append(a)
    return out


def mc_max(*args):
    """Mathcad ``max`` -- the single largest element across *all* arguments,
    flattening vector arguments (a reduction to a scalar). Element-wise ``max``
    is Mathcad's vectorize arrow, which codegen emits as ``np.maximum`` instead."""
    return max(_flatten_scalars(args))


def mc_min(*args):
    """Mathcad ``min`` -- the single smallest element across all arguments
    (flattening vectors); see :func:`mc_max`."""
    return min(_flatten_scalars(args))


# Pint names of the angle units, whose Mathcad meaning is a dimensionless scale.
_ANGLE_UNITS = frozenset(
    ("radian", "degree", "gradian", "arcminute", "arcsecond", "turn", "revolution")
)


def disp(value, unit=None):
    """Render ``value`` for a Mathcad inline ``=``.

    With a display-unit override, converts when dimensionally compatible;
    otherwise divides, giving the residual-unit form Mathcad shows for a *loose*
    override (e.g. a ``kN·m`` moment displayed with a ``kN`` override shows as
    ``… m``). Never raises, so a stray display override can't crash the
    computation.

    A *plain number* displayed with an angle unit is the one case where the
    value isn't a Pint quantity yet still converts: the inverse trig/hyperbolic
    builtins return bare radians (Mathcad's ``deg`` being just the π/180 scale),
    so ``atan(B) = … deg`` has to rescale rather than divide.

    With **no** override (Mathcad's automatic display) a *dimensionless but
    unreduced* quantity is collapsed to a plain number: Pint leaves ``sin(θ)/θ``
    as ``0.0164 1/degree`` and ``l/s`` as ``m/mm``, where Mathcad -- for which
    ``deg`` is a plain π/180 scale -- shows the reduced ``0.9423``.
    """
    if unit is None:
        return _reduce_dimensionless(value)
    if not hasattr(value, "to") and str(getattr(unit, "units", unit)) in _ANGLE_UNITS:
        return unit._REGISTRY.Quantity(value, "radian").to(unit)
    try:
        return value.to(unit)
    except Exception:
        return value / unit


def nth_root(x, n):
    """``x ** (1/n)`` so a unit-bearing radicand keeps its unit (Pint handles
    ``(m**2) ** (1/2) = m``); ``math.sqrt`` would reject the unit.

    A *dimensionless* radicand is reduced to a plain number first, so a ratio
    Pint stores unreduced (``200 mm / d`` = ``mm/mm``) doesn't leave fractional
    ``mm ** 0.5`` unit noise that then contaminates everything downstream.
    """
    return _reduce_dimensionless(x) ** (1.0 / n)


def sqrt(x):
    """Mathcad ``sqrt(x)`` builtin -> :func:`nth_root` with ``n = 2``."""
    return nth_root(x, 2)


def power(base, exp):
    """``base ** exp`` for a *fractional* exponent, reducing a dimensionless base
    first. A ratio Pint stores unreduced (``ρ = A/(b·d)`` = ``mm²/mm²``) raised to
    ``1/3`` would otherwise leave fractional ``mm ** (2/3)`` unit noise (and even
    floating-point ``m ** 1e-16`` residue that breaks a later ``< 1`` comparison).
    A dimensioned base keeps its (fractional) unit, as Pint intends.
    """
    return _reduce_dimensionless(base) ** exp


def _reduce_dimensionless(x):
    """A dimensionless Pint quantity (even *unreduced*, e.g. ``m/mm``) -> a plain
    number (or plain array); a dimensioned quantity or plain number is returned
    unchanged.

    Mathcad reduces ``l/s`` (both lengths) to a pure number before ``round`` etc.,
    but Pint keeps ``1.3 m / (300 mm)`` as magnitude ``0.00433`` with unit
    ``m/mm``, so rounding the raw magnitude would give ``0``. This collapses that.
    """
    if hasattr(x, "dimensionality") and x.dimensionless:
        mag = x.to("dimensionless").magnitude
        return mag if _is_arraylike(mag) else float(mag)
    return x


def ceil(x):
    """Mathcad ``ceil`` (dimensionless-aware; keeps a unit if dimensioned)."""
    x = _reduce_dimensionless(x)
    if hasattr(x, "units"):
        return x._REGISTRY.Quantity(math.ceil(x.magnitude), x.units)
    return math.ceil(x)


def floor(x):
    """Mathcad ``floor`` (dimensionless-aware; keeps a unit if dimensioned)."""
    x = _reduce_dimensionless(x)
    if hasattr(x, "units"):
        return x._REGISTRY.Quantity(math.floor(x.magnitude), x.units)
    return math.floor(x)


def mround(x):
    """Mathcad ``round`` (dimensionless-aware; keeps a unit if dimensioned)."""
    x = _reduce_dimensionless(x)
    if hasattr(x, "units"):
        return x._REGISTRY.Quantity(round(x.magnitude), x.units)
    return round(x)


def col(*elements: object) -> object:
    """Build a 1-D vector (a Mathcad column/row vector) from scalar elements.

    When the elements carry Pint units the result is a Pint ``Quantity`` array
    (so units survive and ``.to(...)`` works on the whole vector); otherwise it
    is a plain NumPy array. Either way it indexes, broadcasts, and ``len()``
    like a Mathcad vector.
    """
    return _build_array(elements, shape=None)


def matrix(nrows: int, ncols: int, *elements: object) -> object:
    """Build a genuine ``nrows``x``ncols`` Mathcad matrix (both > 1).

    ``elements`` arrive in Prime's own ``<ml:matrix>`` order, which is
    column-major, hence ``order="F"`` on the reshape. Unit handling mirrors
    ``col()``: a matrix with one consistent unit is a fused Pint array, while a
    heterogeneous one (mixed/plain units) becomes an object array of per-element
    values.

    This doubles as Mathcad's ``matrix(m, n, f)`` *builtin*, which fills the
    matrix from a function of the (0-based) row and column index -- the two
    spellings are distinguished by the single callable argument.
    """
    if len(elements) == 1 and callable(elements[0]):
        f = elements[0]
        elements = tuple(
            f(i, j) for j in range(int(ncols)) for i in range(int(nrows))
        )
    return _build_array(elements, shape=(nrows, ncols))


def _object_array(elements, shape):
    """A 1-D (``shape=None``) or column-major 2-D object array holding each
    element exactly as-is (Pint scalars, plain numbers, or nested vectors)."""
    out = np.empty(len(elements), dtype=object)
    for i, e in enumerate(elements):
        out[i] = e
    return out if shape is None else out.reshape(shape, order="F")


def _build_array(elements, shape):
    """Build a Mathcad vector/matrix from ``elements`` (column-major for 2-D).

    A homogeneous, single-unit set becomes a fused Pint/NumPy array (so
    ``.to(...)`` works on the whole thing); a *heterogeneous* set -- elements
    that are themselves vectors (nested arrays), a mix of dimensioned and plain
    (dimensionless) entries, or incompatible units -- becomes an object array of
    the elements as-is, so each keeps its own unit and unit-aware ops (``matmul``,
    ``total``) propagate per element. This matches Mathcad, which allows a
    heterogeneous matrix (e.g. ``[1; -l/2; -w/2]`` = dimensionless + lengths, or
    ``augment(ones, Xs, Ys)``).
    """
    # Nested arrays (a vector of vectors) -> object array.
    if any(_is_arraylike(e) for e in elements):
        return _object_array(elements, shape)

    united = [e for e in elements if hasattr(e, "units")]
    if not united:  # all plain
        try:
            arr = np.array(elements, dtype=float)
        except (ValueError, TypeError):
            arr = np.array(elements)  # non-numeric (e.g. a string column)
        return arr if shape is None else arr.reshape(shape, order="F")

    # A plain *nonzero* entry mixed with dimensioned ones is genuinely
    # dimensionless (e.g. ``[1; -l/2; -w/2]``, the constant column of a strain
    # matrix) -> keep each element as-is. A plain *zero* is unit-agnostic (``0``
    # is ``0`` in any unit, as with the off-diagonal ``0``s of ``[[w,0],[0,l]]``),
    # so it's absorbed into the prevailing unit below.
    if any(not hasattr(e, "units") and e != 0 for e in elements):
        return _object_array(elements, shape)

    reg = united[0]._REGISTRY
    unit = united[0].units
    try:
        mags = [
            (e.to(unit).magnitude if hasattr(e, "units") else e) for e in elements
        ]
    except Exception:
        # Incompatible units (e.g. ``[strain; curvature]``).
        return _object_array(elements, shape)
    arr = np.array(mags, dtype=float)
    return reg.Quantity(arr if shape is None else arr.reshape(shape, order="F"), unit)


def _magnitudes(v):
    """A plain float NumPy array of ``v``'s magnitudes (Pint or already plain)."""
    if hasattr(v, "magnitude"):
        return np.asarray(v.magnitude, dtype=float)
    return np.asarray(v, dtype=float)


def transpose(x):
    """Mathcad matrix/vector transpose, unit-aware.

    For the 1-D vectors built by ``col()`` this is effectively identity (NumPy
    treats a 1-D array's transpose as itself), which is exactly what feeding a
    transposed data column to ``linterp`` needs; a true 2-D matrix transposes
    normally. Pint quantities keep their units.
    """
    if hasattr(x, "magnitude"):
        return x._REGISTRY.Quantity(np.transpose(x.magnitude), x.units)
    return np.transpose(np.asarray(x))


def _is_arraylike(x):
    """True if ``x`` is a vector/matrix (ndim > 0) or a Python list/tuple.

    Avoids ``np.asarray`` (which would call ``float()`` on a list of Pint
    quantities and raise on a dimensioned one).
    """
    if isinstance(x, (list, tuple)):
        return True
    return getattr(getattr(x, "magnitude", x), "ndim", 0) > 0


def _as_int(x):
    return int(getattr(x, "magnitude", x))


def _is_plain_zero(x):
    """True for a bare (unitless) numeric zero -- a zero-fill gap.

    ``0`` is ``0`` in any unit, so such an entry is unit-agnostic and must not
    stop a vector fusing into a single dimensioned array.
    """
    if hasattr(x, "units") or _is_arraylike(x) or isinstance(x, str):
        return False
    try:
        return x == 0
    except Exception:
        return False


def _grow_1d(vec, n):
    if vec is None:
        out = np.empty(n, dtype=object)
        out[:] = 0
        return out
    if len(vec) >= n:
        return vec
    out = np.empty(n, dtype=object)
    out[:] = 0
    out[: len(vec)] = vec
    return out


def _grow_2d(vec, rows, cols):
    if vec is None:
        out = np.empty((rows, cols), dtype=object)
        out[:] = 0
        return out
    r, c = vec.shape
    if r >= rows and c >= cols:
        return vec
    out = np.empty((max(r, rows), max(c, cols)), dtype=object)
    out[:] = 0
    out[:r, :c] = vec
    return out


def _explode(vec):
    """An object-array copy of ``vec`` (Pint scalars kept), for growable editing.

    A fused Pint/plain array is expanded into per-element objects so growth and
    element assignment are uniform; an already-object array is returned as-is.
    """
    if vec is None:
        return None
    unit = getattr(vec, "units", None)
    mag = np.atleast_1d(vec.magnitude if unit is not None else np.asarray(vec))
    out = np.empty(mag.shape, dtype=object)
    for idx in np.ndindex(mag.shape):
        out[idx] = (mag[idx] * unit) if unit is not None else mag[idx]
    return out


def _consolidate(vec):
    """Fuse a homogeneous object array back into a Pint (or plain) array.

    When every element is a Pint scalar of one unit, return a fused Pint array
    (so ``kx * X`` and the like broadcast correctly instead of Pint mis-wrapping
    an object array); when every element is a plain number, a float array; a
    genuinely heterogeneous array (mixed units, nested sub-vectors) stays as-is.

    A **zero-fill gap** does not make an array heterogeneous: a Mathcad program
    that writes ``z[i] :=`` from ``i = 1`` leaves a bare ``0`` at index 0, and
    ``0`` is ``0`` in any unit. Those entries are absorbed into the prevailing
    unit -- the same rule ``_build_array`` applies to a literal ``[[w,0],[0,l]]``.
    Left unabsorbed the array stays ``dtype=object``, and any later ``z / m``
    then reads as ``1/meter`` instead of dimensionless.
    """
    flat = list(vec.reshape(-1))
    if not flat:
        return vec
    united = [x for x in flat if hasattr(x, "units")]
    if united and all(hasattr(x, "units") or _is_plain_zero(x) for x in flat):
        reg = united[0]._REGISTRY
        unit = united[0].units
        try:
            mags = [
                float(x.to(unit).magnitude) if hasattr(x, "units") else float(x)
                for x in flat
            ]
        except Exception:
            return vec
        return reg.Quantity(np.array(mags).reshape(vec.shape), unit)
    if all(
        not hasattr(x, "units")
        and not _is_arraylike(x)
        and not isinstance(x, (list, tuple))
        for x in flat
    ):
        try:
            return np.array([float(x) for x in flat]).reshape(vec.shape)
        except (ValueError, TypeError):
            return vec
    return vec


def vec_set(vec, index, value):
    """Assign into a growable Mathcad program vector/matrix (``X[i] := …``).

    A Mathcad program auto-grows its vectors/matrices as elements are written,
    zero-filling any gap. ``index`` is an ``int`` (1-D) or a ``(row, col)`` tuple
    (2-D); ``vec`` starts as ``None`` (codegen pre-declares it) and is created on
    first write. The possibly-reallocated array is returned so the caller rebinds
    it (``X = vec_set(X, i, v)``). Growth happens on an object array (so units and
    nested sub-vectors survive); the result is consolidated back to a fused Pint
    array once it's homogeneous, so downstream ``kx * X`` broadcasts correctly.
    """
    vec = _explode(vec)
    if isinstance(index, tuple):
        i, k = _as_int(index[0]), _as_int(index[1])
        vec = _grow_2d(vec, i + 1, k + 1)
        vec[i, k] = value
    else:
        i = _as_int(index)
        vec = _grow_1d(vec, i + 1)
        vec[i] = value
    return _consolidate(vec)


def _to_object_matrix(x):
    """A per-element object array of ``x`` (Pint scalars kept with their units).

    A homogeneous Pint quantity array is exploded into an object array of scalar
    quantities so NumPy's object-dtype ``@``/``*`` propagate units element by
    element (needed for a matrix/vector whose columns carry *different* units).
    A plain or already-object array is returned as-is.
    """
    if hasattr(x, "units") and getattr(x.magnitude, "dtype", None) != object:
        reg = x._REGISTRY
        unit = x.units
        mag = np.asarray(x.magnitude)
        out = np.empty(mag.shape, dtype=object)
        flat_out, flat_in = out.reshape(-1), mag.reshape(-1)
        for i in range(flat_in.size):
            flat_out[i] = reg.Quantity(float(flat_in[i]), unit)
        return out
    return np.asarray(x)


def _has_object(x):
    """True if ``x`` is (or wraps) an object-dtype array of per-element scalars."""
    mag = getattr(x, "magnitude", x)
    return getattr(np.asarray(mag), "dtype", None) == object


def augment(*columns):
    """Mathcad ``augment``: stack column vectors side by side into a matrix.

    Each argument is a 1-D vector; they become the columns of the result. The
    columns may carry *different* units (Mathcad allows a heterogeneous matrix
    here, e.g. a dimensionless column beside two length columns), so the result
    is an object array of per-element Pint scalars -- a later ``matmul`` then
    propagates units column by column.
    """
    cols_ = [_to_object_matrix(c).reshape(-1) for c in columns]
    nrows = max((len(c) for c in cols_), default=0)
    out = np.empty((nrows, len(cols_)), dtype=object)
    for j, c in enumerate(cols_):
        for i in range(nrows):
            out[i, j] = c[i]
    return out


def stack(*blocks):
    """Mathcad ``stack``: join matrices/vectors one *above* the other.

    The vertical counterpart of :func:`augment`. Every block must have the same
    number of columns (a 1-D vector counts as one column); the result is an
    object array of per-element values so blocks with different units survive.

    Stacking column vectors gives a column vector, which this module represents
    **1-D** (as :func:`col` does), not as an ``n x 1`` matrix -- so that a single
    subscript ``z[0]`` reads the element rather than a one-row slice.

    A **scalar** block counts as ``1 x 1``: ``stack("α", v)`` -- Mathcad's idiom
    for captioning a data column with a string header -- is a scalar above a
    vector, and a 0-d block would otherwise have no ``shape[1]`` at all.
    """
    parts = [_to_object_matrix(b) for b in blocks]
    parts = [p.reshape(1, 1) if p.ndim == 0 else p for p in parts]
    parts = [p.reshape(-1, 1) if p.ndim == 1 else p for p in parts]
    ncols = max((p.shape[1] for p in parts), default=0)
    nrows = sum(p.shape[0] for p in parts)
    out = np.empty((nrows, ncols), dtype=object)
    out[:] = 0
    r = 0
    for p in parts:
        out[r : r + p.shape[0], : p.shape[1]] = p
        r += p.shape[0]
    if ncols == 1:
        out = out.reshape(-1)
    return _consolidate(out)


def _mag(x):
    return x.magnitude if hasattr(x, "magnitude") else np.asarray(x)


def matmul(a, b):
    """Matrix (or matrix-vector) product, unit-aware (Mathcad ``A * B``).

    When neither operand is a heterogeneous (object) array, the magnitudes are
    multiplied with NumPy ``@`` and the units multiplied
    (``unit_a * unit_b``) -- the fast, clean path covering a genuine matrix
    with one consistent unit. When either operand carries per-element units
    (from :func:`augment`/a mixed ``col``), the product is done on object
    arrays so Pint propagates each element's unit and the summed terms keep
    their (necessarily consistent) result unit.
    """
    if not _has_object(a) and not _has_object(b):
        res = _mag(a) @ _mag(b)
        ua = getattr(a, "units", None)
        ub = getattr(b, "units", None)
        if ua is None and ub is None:
            return res
        reg = (a if ua is not None else b)._REGISTRY
        unit = ua if ua is not None else 1
        if ub is not None:
            unit = unit * ub
        return reg.Quantity(res, unit)
    # Object-dtype product (mixed per-element units): consolidate the result back
    # to a fused Pint array when it turns out homogeneous (e.g. a strain vector),
    # so downstream ``E * strain`` broadcasts instead of Pint mis-wrapping.
    return _consolidate(_to_object_matrix(a) @ _to_object_matrix(b))


def matcol(m, i):
    """Extract column ``i`` of a matrix as a 1-D vector (Mathcad ``A^<i>``)."""
    i = int(getattr(i, "magnitude", i))
    if hasattr(m, "units") and getattr(m.magnitude, "dtype", None) != object:
        return m._REGISTRY.Quantity(np.asarray(m.magnitude)[:, i], m.units)
    return np.asarray(m)[:, i]


# ---------------------------------------------------------------------------
# Vector & matrix builtins
#
# Mathcad's "Vector and Matrix" function category. Two conventions run through
# all of them:
#
# * **Vectors are 1-D.** A Mathcad n×1 column and 1×n row both become a plain
#   1-D array (that's what ``col()``/``transpose()`` build), so the row/column
#   distinction is not carried -- ``rows``/``cols`` report a 1-D array as n×1,
#   and :func:`matelem` resolves a two-subscript access on one by taking
#   whichever subscript is non-zero.
# * **Linear algebra runs on magnitudes.** ``det``/``norm``-family/``eigen``-
#   family/``lsolve``/``geninv``/``rref`` strip Pint units, compute, and (where
#   the unit is meaningful and unambiguous, e.g. ``tr``/``norm``/``sort``)
#   reattach it. A determinant's ``unit**n`` and a mixed-unit system are not
#   modelled -- Mathcad itself rejects most of those.
# ---------------------------------------------------------------------------


def _split(x):
    """``(plain ndarray of magnitudes, Pint unit or None)`` for an array/scalar.

    A heterogeneous (object) array is consolidated first, so a matrix built by
    ``augment``/``vec_set`` from per-element quantities enters linear algebra as
    a fused numeric array.
    """
    if isinstance(x, np.ndarray) and x.dtype == object:
        x = _consolidate(x)
    unit = getattr(x, "units", None)
    mag = np.asarray(getattr(x, "magnitude", x))
    if mag.dtype == object:
        mag = mag.astype(float)
    return mag, unit


def _join(arr, unit):
    """Reattach ``unit`` (or None) to a computed magnitude array/scalar."""
    return arr if unit is None else unit._REGISTRY.Quantity(arr, unit)


def _as_2d(mag):
    """A 2-D view of ``mag``, treating a 1-D vector as a single column."""
    return mag.reshape(-1, 1) if mag.ndim == 1 else mag


def _real_if_close(arr):
    """Drop a negligible imaginary part (LAPACK returns complex dtype even for
    a real spectrum; Mathcad shows those results as plain reals)."""
    arr = np.asarray(arr)
    if np.iscomplexobj(arr) and np.allclose(arr.imag, 0.0, atol=1e-12):
        return arr.real
    return arr


def rows(a):
    """Mathcad ``rows``: the number of rows (a 1-D vector counts as n×1)."""
    return int(_as_2d(_split(a)[0]).shape[0])


def cols(a):
    """Mathcad ``cols``: the number of columns (a 1-D vector counts as n×1)."""
    return int(_as_2d(_split(a)[0]).shape[1])


def last(v):
    """Mathcad ``last``: the index of a vector's final element.

    Worksheets converted here are read with ``ORIGIN = 0`` (the parser emits
    0-based indices throughout), so this is ``length(v) - 1``.
    """
    return len(v) - 1


def identity(n):
    """Mathcad ``identity(n)``: the n×n identity matrix."""
    return np.eye(int(n))


def diag(a):
    """Mathcad ``diag``: a vector's elements on a diagonal matrix, or a
    matrix's diagonal as a vector -- whichever the argument calls for."""
    mag, unit = _split(a)
    return _join(np.diag(mag), unit)


def tr(a):
    """Mathcad ``tr``: the trace (sum of the diagonal) of a square matrix."""
    mag, unit = _split(a)
    return _join(float(np.trace(mag)), unit)


def det(a):
    """Mathcad ``det``: the determinant of a square matrix (on magnitudes)."""
    return float(np.linalg.det(_split(a)[0]))


def determinant(a):
    """Mathcad's ``|x|`` operator -- determinant *or* magnitude.

    Prime uses one pair of bars for both: on a square matrix it is the
    determinant, on a vector the Euclidean magnitude, on a scalar the absolute
    value. (Prime's *other* bars operator, elementwise absolute value, parses as
    ``absval`` and emits plain ``abs``.)
    """
    mag, unit = _split(a)
    if mag.ndim == 2 and mag.shape[0] > 1 and mag.shape[1] > 1:
        return float(np.linalg.det(mag))
    if mag.ndim >= 1:
        return _join(float(np.linalg.norm(mag.reshape(-1))), unit)
    return abs(a)


def matrow(m, i):
    """Extract row ``i`` of a matrix as a 1-D vector (Mathcad's row operator)."""
    mag, unit = _split(m)
    return _join(_as_2d(mag)[int(getattr(i, "magnitude", i)), :], unit)


def matelem(m, i, j):
    """Mathcad's two-subscript element access ``M[i, j]`` (0-based).

    A genuine 2-D matrix indexes straight through. A *vector* is stored 1-D
    here (see the section note), so one of the two subscripts is necessarily
    ``0`` and the other selects the element -- which is what a Mathcad sheet
    means by ``A[1, 0]`` on a column or ``B[0, 2]`` on a row.
    """
    i, j = int(getattr(i, "magnitude", i)), int(getattr(j, "magnitude", j))
    mag = getattr(m, "magnitude", m)
    if getattr(np.asarray(mag), "ndim", 0) == 1:
        return m[i if j == 0 else j]
    return m[i, j]


def submatrix(a, row_lo, row_hi, col_lo, col_hi):
    """Mathcad ``submatrix``: the block spanning rows ``row_lo..row_hi`` and
    columns ``col_lo..col_hi`` -- both bounds *inclusive*, unlike a Python
    slice."""
    mag, unit = _split(a)
    lo_r, hi_r = int(row_lo), int(row_hi)
    lo_c, hi_c = int(col_lo), int(col_hi)
    return _join(_as_2d(mag)[lo_r : hi_r + 1, lo_c : hi_c + 1], unit)


def cross(a, b):
    """Mathcad's vector cross product ``a × b`` (3-element vectors)."""
    ma, ua = _split(a)
    mb, ub = _split(b)
    out = np.cross(ma.reshape(-1), mb.reshape(-1))
    if ua is None and ub is None:
        return out
    unit = (ua if ua is not None else 1) * (ub if ub is not None else 1)
    reg = (a if ua is not None else b)._REGISTRY
    return reg.Quantity(out, unit)


def lsolve(a, b):
    """Mathcad ``lsolve(A, b)``: solve the linear system ``A·x = b``."""
    return np.linalg.solve(_split(a)[0], _split(b)[0])


def geninv(a):
    """Mathcad ``geninv``: the Moore-Penrose (pseudo) inverse."""
    return np.linalg.pinv(_split(a)[0])


def rank(a):
    """Mathcad ``rank``: the number of linearly independent columns."""
    return int(np.linalg.matrix_rank(_split(a)[0]))


def rref(a, tol=1e-12):
    """Mathcad ``rref``: the row-reduced echelon form (Gauss-Jordan)."""
    m = _as_2d(_split(a)[0]).astype(float).copy()
    nrows, ncols = m.shape
    pivot = 0
    for c in range(ncols):
        if pivot >= nrows:
            break
        r = pivot + int(np.argmax(np.abs(m[pivot:, c])))
        if abs(m[r, c]) <= tol:
            continue
        m[[pivot, r]] = m[[r, pivot]]
        m[pivot] = m[pivot] / m[pivot, c]
        for other in range(nrows):
            if other != pivot and m[other, c] != 0.0:
                m[other] = m[other] - m[other, c] * m[pivot]
        pivot += 1
    return m


def norm(v):
    """Mathcad ``norm``: the Euclidean length of a vector."""
    mag, unit = _split(v)
    return _join(float(np.linalg.norm(mag.reshape(-1))), unit)


def norm1(a):
    """Mathcad ``norm1``: the L1 matrix norm (largest absolute column sum)."""
    return float(np.linalg.norm(_as_2d(_split(a)[0]), 1))


def norm2(a):
    """Mathcad ``norm2``: the L2 matrix norm (largest singular value)."""
    return float(np.linalg.norm(_as_2d(_split(a)[0]), 2))


def norme(a):
    """Mathcad ``norme``: the Euclidean (Frobenius) matrix norm."""
    return float(np.linalg.norm(_as_2d(_split(a)[0]), "fro"))


def normi(a):
    """Mathcad ``normi``: the infinity matrix norm (largest absolute row sum)."""
    return float(np.linalg.norm(_as_2d(_split(a)[0]), np.inf))


def _cond(a, order):
    """``‖A‖ · ‖A⁻¹‖`` in the given norm -- Mathcad's condition numbers.

    ``np.linalg.cond`` covers 1/2/inf; the Euclidean (Frobenius) one it does not
    define the same way, so the product is taken explicitly for all of them.
    """
    mag = _as_2d(_split(a)[0])
    inv = np.linalg.inv(mag)
    return float(np.linalg.norm(mag, order) * np.linalg.norm(inv, order))


def cond1(a):
    """Mathcad ``cond1``: the condition number in the L1 norm."""
    return _cond(a, 1)


def cond2(a):
    """Mathcad ``cond2``: the condition number in the L2 norm."""
    return _cond(a, 2)


def conde(a):
    """Mathcad ``conde``: the condition number in the Euclidean norm."""
    return _cond(a, "fro")


def condi(a):
    """Mathcad ``condi``: the condition number in the infinity norm."""
    return _cond(a, np.inf)


def eigenvals(a):
    """Mathcad ``eigenvals``: the eigenvalues of a square matrix.

    LAPACK's ordering, which is what Mathcad reports too (it is *not* sorted --
    see ``sort``/``reverse`` for that). A real spectrum comes back real.
    """
    return _real_if_close(np.linalg.eigvals(_split(a)[0]))


def eigenvecs(a, side="R"):
    """Mathcad ``eigenvecs``: a matrix whose *columns* are the eigenvectors.

    ``side`` is Mathcad's optional second argument: ``"R"`` (default) for right
    eigenvectors ``A·v = λ·v``, ``"L"`` for left ones ``vᵀ·A = λ·vᵀ`` (returned,
    as Mathcad does, as columns of the result). Each column is normalised to
    unit length, matching Mathcad's convention.
    """
    from scipy.linalg import eig

    mag = _split(a)[0]
    want_left = str(side).upper().startswith("L")
    left, right = eig(mag, left=True, right=True)[1:]
    return _real_if_close(left if want_left else right)


def eigenvec(a, value):
    """Mathcad ``eigenvec(M, λ)``: the (unit-length) eigenvector for ``λ``.

    Found as the null space of ``M - λ·I`` via an SVD -- the right singular
    vector belonging to the smallest singular value.
    """
    mag = _split(a)[0]
    lam = complex(getattr(value, "magnitude", value))
    n = mag.shape[0]
    shifted = mag.astype(complex) - lam * np.eye(n)
    _u, _s, vh = np.linalg.svd(shifted)
    vec = vh[-1].conj()
    # Fix the arbitrary SVD sign the way LAPACK's eigensolver reports it: make
    # the largest-magnitude component positive real.
    lead = vec[int(np.argmax(np.abs(vec)))]
    if lead != 0:
        vec = vec * (abs(lead) / lead)
    return _real_if_close(vec)


def genvals(a, b):
    """Mathcad ``genvals``: eigenvalues of the generalized problem ``A·v = λ·B·v``."""
    from scipy.linalg import eig

    return _real_if_close(eig(_split(a)[0], _split(b)[0], right=False))


def genvecs(a, b, side="R"):
    """Mathcad ``genvecs``: eigenvectors of ``A·v = λ·B·v``, as columns.

    ``side`` selects right (default) or left vectors, as in :func:`eigenvecs`.
    Mathcad normalises each column so its largest-magnitude component is ``1``
    (not to unit length, as it does for ``eigenvecs``).
    """
    from scipy.linalg import eig

    want_left = str(side).upper().startswith("L")
    left, right = eig(_split(a)[0], _split(b)[0], left=True, right=True)[1:]
    vecs = np.asarray(left if want_left else right)
    out = np.empty_like(vecs)
    for j in range(vecs.shape[1]):
        column = vecs[:, j]
        lead = column[int(np.argmax(np.abs(column)))]
        out[:, j] = column / lead if lead != 0 else column
    return _real_if_close(out)


def svds(a):
    """Mathcad ``svds``: the singular values of a matrix, largest first."""
    return np.linalg.svd(_as_2d(_split(a)[0]), compute_uv=False)


def mean(a):
    """Mathcad ``mean``: the arithmetic mean of every element."""
    mag, unit = _split(a)
    return _join(float(np.mean(mag)), unit)


def sort(v):
    """Mathcad ``sort``: a vector's elements in ascending order."""
    mag, unit = _split(v)
    return _join(np.sort(mag.reshape(-1)), unit)


def reverse(v):
    """Mathcad ``reverse``: a vector's elements (or a matrix's rows) reversed."""
    mag, unit = _split(v)
    return _join(mag[::-1].copy(), unit)


def csort(a, n):
    """Mathcad ``csort(A, n)``: sort a matrix's *rows* by column ``n``."""
    mag, unit = _split(a)
    m = _as_2d(mag)
    return _join(m[np.argsort(m[:, int(n)], kind="stable")], unit)


def rsort(a, n):
    """Mathcad ``rsort(A, n)``: sort a matrix's *columns* by row ``n``."""
    mag, unit = _split(a)
    m = _as_2d(mag)
    return _join(m[:, np.argsort(m[int(n), :], kind="stable")], unit)


def IsArray(x):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``IsArray``: ``1`` if ``x`` is a vector/matrix, else ``0``.

    Mathcad's booleans display as 1/0 (and that is what ``result.xml`` caches),
    so these return ints rather than Python ``bool``s.
    """
    return 1 if _is_arraylike(x) else 0


def IsScalar(x):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``IsScalar``: ``1`` if ``x`` is a single value, else ``0``."""
    return 0 if _is_arraylike(x) else 1


def linterp(vx, vy, x):
    """Linear interpolation ``linterp(vx, vy, x)`` (Mathcad builtin).

    ``vx`` (knot abscissae, increasing) and ``vy`` (knot ordinates) are vectors;
    ``x`` is the query point. Note the argument order differs from
    ``np.interp(x, xp, fp)``. Beyond the data range Mathcad *extrapolates* along
    the first/last segment (``np.interp`` only clamps), so the ends are extended
    by hand. Unit-aware: ``x`` is converted into ``vx``'s unit and the result
    carries ``vy``'s unit.
    """
    x_unit = getattr(vx, "units", None)
    y_unit = getattr(vy, "units", None)
    xs = _magnitudes(vx)
    ys = _magnitudes(vy)
    if x_unit is not None and hasattr(x, "to"):
        xq = float(x.to(x_unit).magnitude)
    else:
        xq = float(getattr(x, "magnitude", x))

    if xq <= xs[0]:
        slope = (ys[1] - ys[0]) / (xs[1] - xs[0])
        y = ys[0] + slope * (xq - xs[0])
    elif xq >= xs[-1]:
        slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        y = ys[-1] + slope * (xq - xs[-1])
    else:
        y = float(np.interp(xq, xs, ys))
    return (float(y) * y_unit) if y_unit is not None else float(y)


def index_build(idx, fn):
    """Build a 0-based Mathcad vector by iterating an index range.

    Mathcad's ``X[i] := expr`` (with ``i`` a range variable) writes ``expr`` at
    each index ``i`` and zero-fills any lower index never assigned. ``idx`` is
    the integer index array; ``fn`` maps a scalar index to the element value, so
    the right-hand side -- including ``X[i]`` reads of other vectors -- evaluates
    per-element with ordinary scalar semantics. Elements may be plain numbers,
    Pint quantities (the vector then carries their unit), or strings (built as an
    object array).
    """
    keys = [int(k) for k in np.atleast_1d(getattr(idx, "magnitude", idx))]
    results = {k: fn(k) for k in keys}
    n = max(keys) + 1
    sample = results[keys[0]]

    # Elements that are themselves vectors (``x[j] := eigenvec(S, V[j])``) build
    # a vector *of* vectors -- an object array, like a heterogeneous ``col()``.
    if _is_arraylike(sample):
        vec = np.empty(n, dtype=object)
        vec[:] = 0
        for k, v in results.items():
            vec[k] = v
        return vec

    if hasattr(sample, "units"):
        reg = sample._REGISTRY
        unit = sample.units
        mags = np.zeros(n, dtype=float)
        for k, v in results.items():
            mags[k] = v.to(unit).magnitude
        return reg.Quantity(mags, unit)

    dtype = object if isinstance(sample, str) else float
    vec = np.zeros(n, dtype=dtype)
    for k, v in results.items():
        vec[k] = v
    return vec


def index_build_2d(row_idx, col_idx, fn):
    """Build a 0-based Mathcad *matrix* by iterating two index ranges.

    The two-subscript form of :func:`index_build` -- ``X[i, j] := expr`` with
    both ``i`` and ``j`` range variables. ``fn(i, j)`` is evaluated for every
    combination (Mathcad takes the ranges' outer product, not a zip), and any
    lower row/column never written is zero-filled.
    """
    ri = [int(k) for k in np.atleast_1d(getattr(row_idx, "magnitude", row_idx))]
    ci = [int(k) for k in np.atleast_1d(getattr(col_idx, "magnitude", col_idx))]
    out = np.empty((max(ri) + 1, max(ci) + 1), dtype=object)
    out[:] = 0
    for i in ri:
        for j in ci:
            out[i, j] = fn(i, j)
    return _consolidate(out)


def unpack(value):
    """Flatten a matrix **column-major** for a destructuring assignment.

    Mathcad's ``[a b; c d] := M`` lists its target names column by column (the
    same order ``<ml:matrix>`` stores elements in), so a 2-D right-hand side has
    to be flattened the same way before being unpacked. A 1-D vector passes
    through unchanged.
    """
    mag = getattr(value, "magnitude", value)
    if getattr(np.asarray(mag), "ndim", 0) < 2:
        return value
    flat = np.asarray(mag).reshape(-1, order="F")
    unit = getattr(value, "units", None)
    return flat if unit is None else unit._REGISTRY.Quantity(flat, unit)


def integral(func, lower, upper):
    """Definite numeric integral (Mathcad ``∫…=``) via ``scipy.integrate.quad``.

    ``func`` takes the integration variable and returns the integrand.
    Pint-aware: integrates the magnitudes (variable in ``lower``'s unit,
    integrand in its own unit) and reattaches ``integrand_unit * variable_unit``
    -- which assumes a consistent integrand unit across the interval, as
    Mathcad itself requires.
    """
    from scipy.integrate import quad

    z_unit = getattr(lower, "units", None)
    if z_unit is not None:
        lo = lower.to(z_unit).magnitude
        hi = upper.to(z_unit).magnitude
        probe = func(lower)
        f_unit = getattr(probe, "units", None)
        if f_unit is not None:
            reg = probe._REGISTRY
            value, _ = quad(
                lambda z: func(z * z_unit).to(f_unit).magnitude, lo, hi
            )
            return reg.Quantity(value, f_unit * z_unit)
        value, _ = quad(lambda z: float(func(z * z_unit)), lo, hi)
        return value
    value, _ = quad(lambda z: float(func(z)), float(lower), float(upper))
    return value


def double_integral(func, x_lower, x_upper, y_lower, y_upper):
    """Definite rectangular double integral (nested Mathcad ``∫∫…=``) via
    ``scipy.integrate.dblquad``.

    ``func(x, y)`` is the integrand; ``x`` ranges ``[x_lower, x_upper]`` and
    ``y`` ranges ``[y_lower, y_upper]`` -- constant bounds, i.e. a rectangular
    domain (the only shape Mathcad's nested-``∫`` UI can express, since the
    inner integral's bounds can't reference the outer variable). Pint-aware
    like :func:`integral`: magnitudes are integrated in ``x_lower``/``y_lower``'s
    units and ``integrand_unit * x_unit * y_unit`` is reattached.
    """
    from scipy.integrate import dblquad

    x_unit = getattr(x_lower, "units", None)
    y_unit = getattr(y_lower, "units", None)
    if x_unit is not None or y_unit is not None:
        xlo = x_lower.to(x_unit).magnitude if x_unit is not None else float(x_lower)
        xhi = x_upper.to(x_unit).magnitude if x_unit is not None else float(x_upper)
        ylo = y_lower.to(y_unit).magnitude if y_unit is not None else float(y_lower)
        yhi = y_upper.to(y_unit).magnitude if y_unit is not None else float(y_upper)

        def _dequantize(x, y):
            xq = x * x_unit if x_unit is not None else x
            yq = y * y_unit if y_unit is not None else y
            return xq, yq

        probe = func(*_dequantize(xlo, ylo))
        f_unit = getattr(probe, "units", None)
        if f_unit is not None:
            reg = probe._REGISTRY
            value, _ = dblquad(
                lambda y, x: func(*_dequantize(x, y)).to(f_unit).magnitude,
                xlo, xhi, ylo, yhi,
            )
            unit = f_unit
            if x_unit is not None:
                unit = unit * x_unit
            if y_unit is not None:
                unit = unit * y_unit
            return reg.Quantity(value, unit)
        value, _ = dblquad(
            lambda y, x: float(func(*_dequantize(x, y))), xlo, xhi, ylo, yhi
        )
        return value
    value, _ = dblquad(
        lambda y, x: float(func(x, y)),
        float(x_lower), float(x_upper), float(y_lower), float(y_upper),
    )
    return value


def summation(func, lower, upper):
    """Inclusive discrete sum ``Σ_{i=lower}^{upper} func(i)`` (Mathcad sum).

    Accumulates from the first term so a unit-bearing summand never has to be
    added to a bare ``0``.
    """
    lower, upper = int(lower), int(upper)
    if upper < lower:
        return 0
    total = func(lower)
    for i in range(lower + 1, upper + 1):
        total = total + func(i)
    return total


def total(v):
    """Sum every element of a vector (Mathcad's bare ``Σ`` over an array).

    Unlike :func:`summation` (an indexed sum over integer bounds) this collapses
    an already-built vector. Unit-aware: a homogeneous Pint vector sums its
    magnitudes and keeps its unit; a mixed/object vector accumulates from the
    first element so per-element Pint scalars add correctly.
    """
    if hasattr(v, "units") and getattr(v.magnitude, "dtype", None) != object:
        return v._REGISTRY.Quantity(float(np.sum(v.magnitude)), v.units)
    arr = np.atleast_1d(v).reshape(-1)
    if len(arr) == 0:
        return 0
    tot = arr[0]
    for x in arr[1:]:
        tot = tot + x
    return tot


def _coarse_presearch(wrapped, x0, n_samples=15, seed=0):
    """Find a better `fsolve` seed by sampling broadly around ``x0``.

    Some solve blocks land their initial guess deep inside a flat plateau of
    a piecewise model (e.g. every point of a stress-strain law's saturated
    branch, all across the domain) where every unknown's finite-difference
    derivative is exactly zero -- ``fsolve``'s local Newton step can't move
    at all from there. Mathcad's own solver uses a more global algorithm and
    escapes such regions; this widened random search (kept at ``x0`` if
    nothing better turns up) is a cheap approximation, and only runs once
    ``fsolve`` has already failed from ``x0`` itself.

    Each sample costs one full residual evaluation, which for a residual
    built from double integrals can itself take a few seconds (Pint's
    per-call overhead over the tens of thousands of quadrature points a
    nested/``dblquad`` integration needs), so ``n_samples`` is kept modest --
    a worst case of a few minutes total, not tens.
    """
    rng = np.random.default_rng(seed)
    scale = np.maximum(np.abs(x0), 1e-6) * 10
    best_x, best_cost = x0, math.inf
    for _ in range(n_samples):
        trial = x0 + rng.uniform(-1.0, 1.0, size=x0.shape) * scale
        cost = sum(v * v for v in wrapped(trial))
        if cost < best_cost:
            best_cost, best_x = cost, trial
    return best_x


def solve_block(residual, guesses):
    """Numeric solve block (Mathcad Given/Find) via ``scipy.optimize.fsolve``.

    ``guesses`` are the seed values of the unknowns (Pint quantities or plain
    numbers); ``residual`` takes the unknowns (units reattached) and returns the
    constraint residuals (``lhs - rhs``). All Pint bookkeeping lives here:
    unknowns are solved as bare magnitudes in their guess units, residuals are
    compared in base units, and the solution is returned with units restored --
    so generated code can pass quantities straight through.

    If ``fsolve`` doesn't land on an actual root of ``guesses`` (e.g. the guess
    sits on a flat plateau with a locally zero Jacobian -- ``fsolve`` can
    report success there too, converged only in the sense that it stopped
    moving, not that the residual is small), :func:`_coarse_presearch` looks
    for a better starting point and ``fsolve`` is retried from there once. If
    that still doesn't confirm convergence, the best candidate found is
    returned anyway with a printed warning, rather than retrying further --
    each attempt can itself take a couple of minutes for solve blocks built
    on double integrals, so this is capped at one retry to keep a bad case
    bounded at a few minutes instead of open-ended.
    """
    from scipy.optimize import fsolve

    units = [getattr(g, "units", None) for g in guesses]
    x0 = np.array(
        [float(g.magnitude) if u is not None else float(g) for g, u in zip(guesses, units)]
    )

    def _wrapped(x):
        vals = [
            (float(xi) * u) if u is not None else float(xi)
            for xi, u in zip(x, units)
        ]
        out = []
        for r in residual(vals):
            out.append(
                float(r.to_base_units().magnitude)
                if hasattr(r, "to_base_units")
                else float(r)
            )
        return out

    def _cost(x):
        return sum(v * v for v in _wrapped(x))

    threshold = 1e-8 * max(_cost(x0), 1.0)

    solution, _, ier, _ = fsolve(_wrapped, x0, full_output=True)
    best_x, best_cost = solution, _cost(solution)

    if ier != 1 or best_cost > threshold:
        print(
            "solve_block: initial guess didn't converge to an actual root "
            "(likely a flat region of the model); searching for a better "
            "starting point. This can take a few minutes for solve blocks "
            "built on double integrals -- it hasn't frozen.",
            flush=True,
        )
        seeded = _coarse_presearch(_wrapped, x0)
        candidate, _, _, _ = fsolve(_wrapped, seeded, full_output=True)
        cost = _cost(candidate)
        if cost < best_cost:
            best_x, best_cost = candidate, cost
        if best_cost > threshold:
            print(
                "solve_block: could not confirm convergence after retrying; "
                "returning the best candidate found.",
                flush=True,
            )

    solution = np.atleast_1d(best_x)
    return [
        (float(s) * u) if u is not None else float(s)
        for s, u in zip(solution, units)
    ]


def arange(start, stop, step):
    """Inclusive numeric range (Mathcad ``start, next .. stop``), unit-aware.

    Plain ``np.arange`` can't build an array from Pint quantities, so when the
    bounds carry units we step over magnitudes (in ``start``'s unit) and
    reattach the unit. The ``+ step/2`` nudge makes the inclusive Mathcad
    endpoint land in the array without a spurious extra point, for either
    ascending or descending ranges.
    """
    unit = getattr(start, "units", None)
    if unit is not None:
        reg = start._REGISTRY
        lo = start.to(unit).magnitude
        hi = stop.to(unit).magnitude
        d = step.to(unit).magnitude
        return reg.Quantity(np.arange(lo, hi + d / 2, d), unit)
    lo, hi, d = float(start), float(stop), float(step)
    values = np.arange(lo, hi + d / 2, d)
    # A range whose *start and step* are whole numbers only ever takes integer
    # values, so it returns an integer array and can index NumPy/Pint vectors
    # directly. The endpoint need not be whole: ``j := 0 .. (length(v)-1)/28``
    # still runs 0, 1, … 7 -- and is still used as an index.
    if lo.is_integer() and d.is_integer():
        return values.astype(int)
    return values


def sample(func, xs):
    """Evaluate ``func`` element-wise over the array ``xs``, rebuilding a vector.

    Unlike ``np.vectorize`` this preserves Pint units and copes with *branching*
    functions (a Mathcad program's ``if``/``elif`` can't take an array), so it's
    how plot trace expressions are applied to the domain array.

    A point the function has no value at comes back ``None`` -- a Mathcad
    program whose ``if`` chain covers only part of the domain returns nothing
    there. Mathcad plots those as gaps (its cached trace holds a literal
    ``NaN``), so they become NaN here too, carrying the unit of the points that
    *are* defined so the trace stays one dimensioned array.
    """
    return col(*_nan_fill([func(x) for x in xs]))


def _nan_fill(values):
    """Replace ``None`` entries with NaN in the units of the defined ones."""
    if not any(v is None for v in values):
        return values
    defined = next((v for v in values if v is not None), None)
    units = getattr(defined, "units", None)
    blank = float("nan") if units is None else float("nan") * units
    return [blank if v is None else v for v in values]


def static_axis(value, domain):
    """A plot axis expression that doesn't reference the plotting variable.

    Two different things look alike in the worksheet, and only the value tells
    them apart. A **vector** is a parametric trace -- a section outline, a
    rebar scatter -- plotted as its own data, keeping its own length even when
    it shares a plot with a function of the plotting range (Mathcad caches the
    two as ``TraceType="Vector"`` and ``"Range"``, of different lengths). A
    **scalar** is a reference line, which spans the whole domain instead.
    """
    magnitude = getattr(value, "magnitude", value)
    if np.ndim(magnitude) > 0:
        return value
    units = getattr(value, "units", None)
    line = np.full(len(domain), magnitude, dtype=float)
    return line if units is None else line * units


def plot_domain(start=-10.0, stop=10.0, num=499):
    """The array Mathcad invents for a plot over an *undefined* variable.

    Plotting ``sin(x)`` against ``x`` with no ``x :=`` anywhere makes Mathcad
    sample the free variable over -10..10; the axis expression may then scale
    it (``x/2`` reads -5..5). Defaults match a cached ``<ml:Trace2dResult>``:
    499 points, i.e. a step of 20/498.
    """
    return np.linspace(float(start), float(stop), int(num))


def plot_axis(data, unit=None):
    """Magnitudes for a plot axis, applying Mathcad's value/unit scaling.

    ``unit`` may be a Pint unit (``ureg.MPa``) or a plain scale (``10**-3``);
    the axis shows ``data / unit``. A missing unit (Mathcad placeholder) falls
    back to base SI units, matching Mathcad's auto display.
    """
    # A heterogeneous (object) column -- e.g. one extracted from a mixed-unit
    # matrix -- is consolidated first so it becomes a fused Pint/plain array.
    if isinstance(data, np.ndarray) and data.dtype == object:
        data = _consolidate(data)
    if unit is None:
        if hasattr(data, "to_base_units"):
            data = data.to_base_units()
        return np.asarray(getattr(data, "magnitude", data), dtype=float)
    ratio = data / unit
    # ``data`` and ``unit`` may carry different prefixes of the same dimension
    # (e.g. a section outline in ``m`` shown in ``mm``): ``m / mm`` is
    # dimensionless but Pint leaves it unreduced, so collapse it to a pure
    # number before taking the magnitude (else ``0.65 m / mm`` reads ``0.65``).
    if hasattr(ratio, "dimensionless") and ratio.dimensionless:
        ratio = ratio.to("dimensionless")
    return np.asarray(getattr(ratio, "magnitude", ratio), dtype=float)


class Mesh(NamedTuple):
    """An (X, Y, Z) grid, as built by :func:`mesh_grid`/:func:`CreateMesh`.

    A distinct type (rather than a bare tuple) so :func:`resolve_plot_grid`
    can tell "already a grid" apart from "a matrix that still needs
    resolving" without any ambiguity.
    """

    X: object
    Y: object
    Z: object


def mesh_grid(func, xs, ys):
    """Evaluate ``func(x, y)`` over every combination of ``xs``/``ys``.

    Mathcad's contour/3D plots accept a function applied directly to two
    *range* variables (not two matching-length vectors): the ranges are
    implicitly combined as an outer product (a grid), not zipped elementwise.
    Element-wise like :func:`sample` -- needed since a branching program
    can't take an array -- but over the 2-D grid.
    """
    X, Y = np.meshgrid(xs, ys)
    rows = [[func(x, y) for x in xs] for y in ys]
    Z = col(*[v for row in rows for v in row])
    if hasattr(Z, "units"):
        Z = Z._REGISTRY.Quantity(Z.magnitude.reshape(len(ys), len(xs)), Z.units)
    else:
        Z = Z.reshape(len(ys), len(xs))
    return Mesh(X, Y, Z)


def CreateMesh(f, xlow, xhigh, ylow, yhigh, xdiv, ydiv):
    """Mathcad's ``CreateMesh`` builtin: sample ``f`` over a regular grid.

    ``xdiv``/``ydiv`` are the number of *divisions* (Mathcad's convention),
    so each axis gets ``div + 1`` sample points.
    """
    xs = np.linspace(float(xlow), float(xhigh), int(xdiv) + 1)
    ys = np.linspace(float(ylow), float(yhigh), int(ydiv) + 1)
    return mesh_grid(f, xs, ys)


def resolve_plot_grid(value):
    """Resolve a contour/3D plot equation's value into ``(X, Y, Z, kind)``.

    A Mathcad contour/3D plot's single equation can be: an already-built
    :class:`Mesh` (from ``mesh_grid``/``CreateMesh``); a matrix with *exactly
    3 columns*, Mathcad's documented convention for an irregular ``(x, y, z)``
    point list (``kind="scatter"``); or any other matrix, treated as a grid of
    z-values with the row/column index as the x/y coordinate
    (``kind="grid"``).
    """
    if isinstance(value, Mesh):
        return value.X, value.Y, value.Z, "grid"
    mag = np.asarray(getattr(value, "magnitude", value))
    if mag.ndim != 2:
        raise ValueError(
            "contour/3D plot equation resolved to a "
            f"{mag.ndim}-D value; expected a Mesh or a 2-D matrix "
            "(an (x,y,z) point list or a z-value grid)."
        )
    if mag.shape[1] == 3:
        unit = getattr(value, "units", None)
        cols = [
            (value[:, i] if unit is not None else mag[:, i]) for i in range(3)
        ]
        return cols[0], cols[1], cols[2], "scatter"
    rows, ncols = mag.shape
    X, Y = np.meshgrid(np.arange(ncols), np.arange(rows))
    return X, Y, value, "grid"


def vectorize(value: object) -> object:
    """Mathcad's element-wise 'arrow'.

    Vectors are NumPy/Pint arrays and ``min``/``max`` map to
    ``np.minimum``/``np.maximum``, so the wrapped expression already evaluates
    element-wise -- this is an identity pass-through that keeps the operator
    visible in generated code. (A *branching* program applied to an array would
    need ``np.vectorize`` of the function; not yet handled.)
    """
    return value
