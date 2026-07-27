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


def matrix(rows: int, cols: int, *elements: object) -> object:
    """Build a genuine ``rows``x``cols`` Mathcad matrix (both > 1).

    ``elements`` arrive in Prime's own ``<ml:matrix>`` order, which is
    column-major, hence ``order="F"`` on the reshape. Unit handling mirrors
    ``col()``: a matrix with one consistent unit is a fused Pint array, while a
    heterogeneous one (mixed/plain units) becomes an object array of per-element
    values.
    """
    return _build_array(elements, shape=(rows, cols))


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
    heterogeneous/gappy array (mixed units, zero-fill gaps, nested sub-vectors)
    stays as-is.
    """
    flat = list(vec.reshape(-1))
    if not flat:
        return vec
    if all(hasattr(x, "units") for x in flat):
        reg = flat[0]._REGISTRY
        unit = flat[0].units
        try:
            mags = [float(x.to(unit).magnitude) for x in flat]
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


def augment(*cols):
    """Mathcad ``augment``: stack column vectors side by side into a matrix.

    Each argument is a 1-D vector; they become the columns of the result. The
    columns may carry *different* units (Mathcad allows a heterogeneous matrix
    here, e.g. ``augment(ones(n), Xs, Ys)`` mixing a dimensionless column with
    length columns), so the result is an object array of per-element Pint
    scalars -- a later ``matmul`` then propagates units column by column.
    """
    columns = [_to_object_matrix(c).reshape(-1) for c in cols]
    nrows = max((len(c) for c in columns), default=0)
    out = np.empty((nrows, len(columns)), dtype=object)
    for j, c in enumerate(columns):
        for i in range(nrows):
            out[i, j] = c[i]
    return out


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
    # An all-integer range (e.g. an index variable ``i := 1 .. n``) returns an
    # *integer* array so it can index NumPy/Pint vectors directly.
    if lo.is_integer() and hi.is_integer() and d.is_integer():
        return np.arange(int(lo), int(hi) + 1, int(d))
    return np.arange(lo, hi + d / 2, d)


def sample(func, xs):
    """Evaluate ``func`` element-wise over the array ``xs``, rebuilding a vector.

    Unlike ``np.vectorize`` this preserves Pint units and copes with *branching*
    functions (a Mathcad program's ``if``/``elif`` can't take an array), so it's
    how plot trace expressions are applied to the domain array.
    """
    return col(*[func(x) for x in xs])


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
