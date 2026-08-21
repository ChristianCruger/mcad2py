"""Runtime helpers imported by generated code.

Mathcad's trig functions interpret an angle-with-units (e.g. ``37 deg``)
correctly, and a bare number as radians. Pint quantities can't be passed to
``math.tan`` directly, so these wrappers convert angle quantities to radians
first. This keeps generated code clean (``tan(phi)`` instead of
``math.tan(phi.to(ureg.radian).magnitude)``) while matching Mathcad semantics.
"""

from __future__ import annotations

import cmath
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

    An override can also carry a **numeric scale** -- Mathcad shows Planck's
    constant as ``10⁻³⁴ kg·m²/s`` -- which arrives here as a Pint *Quantity*
    rather than a *Unit*. Dividing is the only faithful rendering: ``.to()``
    accepts a quantity but silently uses its units alone, dropping the ``10⁻³⁴``
    and reporting the unscaled number.

    With **no** override (Mathcad's automatic display) a *dimensionless but
    unreduced* quantity is collapsed to a plain number: Pint leaves ``sin(θ)/θ``
    as ``0.0164 1/degree`` and ``l/s`` as ``m/mm``, where Mathcad -- for which
    ``deg`` is a plain π/180 scale -- shows the reduced ``0.9423``.
    """
    if unit is None:
        return _reduce_dimensionless(value)
    scale = getattr(unit, "magnitude", 1)
    if scale != 1:
        return _reduce_dimensionless(value / unit)
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


def xor(a, b):
    """Mathcad's ``⊕`` -- a *logical* exclusive-or returning 1 or 0.

    Python's ``^`` is bitwise on integers (``3 ^ 2`` is 1), so it can't stand in:
    Mathcad reads every non-zero operand as true, making ``3 ⊕ 2`` zero.
    """
    return int(bool(a) != bool(b))


# Mathcad's number sets. ``ℚ`` is the odd one out -- see :func:`element_of`.
_NUMBER_SETS = {"ℕ", "ℤ", "ℚ", "ℝ", "ℂ"}


def element_of(value, number_set):
    """Mathcad's ``∈``: is ``value`` in ``ℕ``/``ℤ``/``ℚ``/``ℝ``/``ℂ``? -> 1 or 0.

    ``ℚ`` cannot be answered by looking at a float -- every float *is* a rational
    -- which is why Mathcad itself refuses to evaluate ``π ∈ ℚ`` numerically and
    the worksheet reaches for the symbolic ``→``. SymPy's ``nsimplify`` recovers
    the closed form a float came from (0.3333… -> 1/3, 3.14159… -> π) and answers
    from that. The caveat is inherent to the question: a float that merely
    approximates π reads as irrational, because as far as anything downstream is
    concerned it *is* π.
    """
    if number_set not in _NUMBER_SETS:
        raise ValueError(f"unknown number set {number_set!r}")
    x = getattr(value, "magnitude", value)
    if number_set == "ℂ":
        return int(isinstance(x, (int, float, complex)))
    if isinstance(x, complex) and x.imag:
        return 0  # ℕ/ℤ/ℚ/ℝ are all real
    x = x.real if isinstance(x, complex) else x
    if number_set == "ℝ":
        return int(isinstance(x, (int, float)))
    if number_set == "ℚ":
        from sympy import nsimplify  # local: keeps SymPy off the import path

        return int(bool(nsimplify(x, rational=False).is_rational))
    integral = float(x).is_integer()
    return int(integral and (x >= 0 if number_set == "ℕ" else True))


def _is_negative_real(x):
    return isinstance(x, (int, float)) and x < 0


def ln(x):
    """Mathcad ``ln``: natural log. A negative real returns a complex value
    (``ln(-3) = ln(3) + iπ``) rather than raising -- only ``ln(0)`` is a
    genuine Mathcad domain error, which ``math.log(0)`` also raises on.
    """
    if isinstance(x, complex) or _is_negative_real(x):
        return cmath.log(x)
    return math.log(x)


def log(x, base=10):
    """Mathcad ``log(x)`` (base 10 by default) / ``log(x, b)`` (explicit
    base). Negative-argument behaviour matches :func:`ln`.
    """
    if isinstance(x, complex) or _is_negative_real(x):
        return cmath.log(x, base)
    if base == 10:
        return math.log10(x)
    return math.log(x, base)


def ln0(x):
    """Mathcad ``ln0(x)``: natural log, but ``ln0(0)`` returns a large negative
    number (``-1e307``) instead of raising a domain error like plain ``ln``.
    """
    if x == 0:
        return -1e307
    return math.log(x)


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


def matrix(*rows: object) -> object:
    """Build a Mathcad matrix from one list per **row**::

        matrix([3, 2, 1], [2, 3, 2])   # 2 x 3

    The shape is implied by the rows, and the literal reads in the same order
    it is written in Prime (the IR stores elements column-major, as the XML
    does; the emitter regroups them here). Unit handling mirrors ``col()``: a
    matrix with one consistent unit is a fused Pint array, while a heterogeneous
    one (mixed/plain units) becomes an object array of per-element values.

    This doubles as Mathcad's ``matrix(m, n, f)`` *builtin*, which fills an
    ``m x n`` matrix from a function of the (0-based) row and column index --
    the two spellings are distinguished by the trailing callable argument.
    """
    if len(rows) == 3 and callable(rows[2]):
        nrows, ncols, f = int(rows[0]), int(rows[1]), rows[2]
        elements = tuple(f(i, j) for j in range(ncols) for i in range(nrows))
        return _build_array(elements, shape=(nrows, ncols))

    if not rows or not all(isinstance(r, (list, tuple)) for r in rows):
        raise TypeError(
            "matrix() takes one list per row -- matrix([1, 2], [3, 4]) -- "
            "or Mathcad's matrix(m, n, f) builtin"
        )
    nrows, ncols = len(rows), len(rows[0])
    if any(len(r) != ncols for r in rows):
        raise ValueError("matrix(): every row must have the same length")
    # ``_build_array`` reshapes with ``order="F"``, so hand it column-major.
    elements = tuple(rows[i][j] for j in range(ncols) for i in range(nrows))
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


def _transposed(mag):
    """``mag`` transposed in this module's vector representation.

    A **column** vector is 1-D here (what ``col()`` builds) while a **row**
    vector is a genuine ``1 x N``, so transpose has to move between the two
    rather than lean on NumPy -- ``np.transpose`` of a 1-D array is itself.
    That matters for Mathcad's common ``(a b c)ᵀ`` idiom, which writes a column
    vector as a transposed row literal and must come back 1-D.
    """
    if mag.ndim == 1:
        return mag.reshape(1, -1)
    if mag.ndim == 2 and mag.shape[0] == 1:
        return mag.reshape(-1)
    return np.transpose(mag)


def transpose(x):
    """Mathcad matrix/vector transpose, unit-aware.

    A true 2-D matrix transposes normally; a vector flips orientation between
    the 1-D column form and the ``1 x N`` row form (see :func:`_transposed`).
    Pint quantities keep their units.
    """
    if hasattr(x, "magnitude"):
        return x._REGISTRY.Quantity(_transposed(np.asarray(x.magnitude)), x.units)
    return _transposed(np.asarray(x))


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


def col_set(mat, index, values):
    """Assign a whole column of a growable program matrix (``M^<i> := v``).

    The column form of :func:`vec_set`, and it shares that helper's growth
    rules: ``mat`` starts as ``None`` (codegen pre-declares it), the matrix
    auto-grows to fit, gaps zero-fill, and the result is consolidated back to a
    fused Pint array once homogeneous. ``values`` goes through
    :func:`_to_object_matrix` so a dimensioned column keeps its units per
    element rather than being flattened to magnitudes.
    """
    k = _as_int(index)
    vals = _to_object_matrix(values).reshape(-1)
    mat = _grow_2d(_explode(mat), len(vals), k + 1)
    for row in range(len(vals)):
        mat[row, k] = vals[row]
    return _consolidate(mat)


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


def _blocks(items):
    """Each of ``items`` as a 2-D object block, ready to be tiled.

    A **scalar** is ``1 x 1`` (Mathcad lets a bare value be a block -- e.g. a
    string caption above a data column); a **1-D vector** is a column ``n x 1``,
    this module's column-vector form; a **matrix** is itself. Blocks may carry
    different units, so they stay object arrays and a later ``matmul``
    propagates units element by element.
    """
    parts = [_to_object_matrix(b) for b in items]
    return [
        p.reshape(1, 1) if p.ndim == 0 else p.reshape(-1, 1) if p.ndim == 1 else p
        for p in parts
    ]


def augment(*blocks):
    """Mathcad ``augment``: join matrices/vectors side by side.

    The horizontal counterpart of :func:`stack`. Blocks must have the same
    number of rows; a shorter one is zero-filled. Augmenting a header *column*
    onto a matrix (``augment(("X" "Y" "Z")ᵀ, s)``) is the labelled-table idiom,
    so a matrix block has to keep all of its columns rather than be flattened.

    A single-column result is a column vector, returned 1-D (see :func:`stack`).
    """
    parts = _blocks(blocks)
    nrows = max((p.shape[0] for p in parts), default=0)
    ncols = sum(p.shape[1] for p in parts)
    out = np.empty((nrows, ncols), dtype=object)
    out[:] = 0
    c = 0
    for p in parts:
        out[: p.shape[0], c : c + p.shape[1]] = p
        c += p.shape[1]
    return out.reshape(-1) if ncols == 1 else out


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
    parts = _blocks(blocks)
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


# ---------------------------------------------------------------------------
# Statistics
#
# Mathcad's "Statistics" function category. Three conventions run through it:
#
# * **Capitalisation marks the estimator.** ``var``/``stdev`` are the
#   *population* forms (divide by n); ``Var``/``Stdev`` are the *sample* forms
#   (divide by n-1). ``skew``/``kurt`` are the sample-corrected coefficients, and
#   ``kurt`` is *excess* kurtosis (0 for a normal distribution).
# * **Units follow the statistic.** A mean/median/percentile keeps the data's
#   unit, a variance squares it, a correlation or moment coefficient is a pure
#   number. Everything reads the data through :func:`_split`, as the vector and
#   matrix family does.
# * **The correlation set is Numerical Recipes.** ``Spear``/``kendltau``/
#   ``kendltau2``/``contingtbl``/``Ftest`` return the whole vector of statistics
#   those routines compute (coefficient, test statistic, p-value, …) rather than
#   just the coefficient -- that is what Mathcad's cache holds.
# ---------------------------------------------------------------------------


def _data(a):
    """``(1-D float array of every element, unit or None)`` for a data sample.

    Mathcad's statistics take a vector *or* a matrix and treat it as a flat bag
    of values, so this flattens whatever shape comes in.
    """
    mag, unit = _split(a)
    return np.atleast_1d(mag).reshape(-1), unit


def median(a):
    """Mathcad ``median``: the middle value (the mean of the middle two if even)."""
    mag, unit = _data(a)
    return _join(float(np.median(mag)), unit)


def mode(a):
    """Mathcad ``mode``: the single most frequent value.

    Mathcad refuses to guess: it is an error when nothing repeats, and an error
    when the highest frequency is shared. Both raise here with Mathcad's own
    wording, so a sheet that *demonstrates* the error (``result.xml`` caches it,
    and the backends guard the region) still reads the same way.
    """
    mag, unit = _data(a)
    values, counts = np.unique(mag, return_counts=True)
    top = counts.max()
    if top == 1:
        raise ValueError("No value occurs more frequently than any others.")
    if int((counts == top).sum()) > 1:
        raise ValueError(
            "Can not return the mode of the data, because the data is multimodal. "
            "More than one value occurs at the highest frequency."
        )
    return _join(float(values[counts.argmax()]), unit)


def gmean(a):
    """Mathcad ``gmean``: the geometric mean, ``(∏ x)**(1/n)``."""
    mag, unit = _data(a)
    return _join(float(np.exp(np.mean(np.log(mag)))), unit)


def hmean(a):
    """Mathcad ``hmean``: the harmonic mean, ``n / Σ(1/x)``."""
    mag, unit = _data(a)
    return _join(float(mag.size / np.sum(1.0 / mag)), unit)


def var(a):
    """Mathcad ``var``: the **population** variance (divides by n)."""
    mag, unit = _data(a)
    return _join(float(np.var(mag)), None if unit is None else unit**2)


def Var(a):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Var``: the **sample** variance (divides by n-1)."""
    mag, unit = _data(a)
    return _join(float(np.var(mag, ddof=1)), None if unit is None else unit**2)


def stdev(a):
    """Mathcad ``stdev``: the **population** standard deviation (divides by n)."""
    mag, unit = _data(a)
    return _join(float(np.std(mag)), unit)


def Stdev(a):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Stdev``: the **sample** standard deviation (divides by n-1)."""
    mag, unit = _data(a)
    return _join(float(np.std(mag, ddof=1)), unit)


def skew(a):
    """Mathcad ``skew``: the sample skewness coefficient (dimensionless).

    ``n/((n-1)(n-2)) · Σ((x - x̄)/s)³`` with ``s`` the *sample* deviation -- the
    bias-corrected form, matching the sheet-level formula Mathcad's own
    documentation gives alongside it.
    """
    mag, _ = _data(a)
    n = mag.size
    z = (mag - mag.mean()) / np.std(mag, ddof=1)
    return float(n / ((n - 1) * (n - 2)) * np.sum(z**3))


def kurt(a):
    """Mathcad ``kurt``: the sample **excess** kurtosis coefficient.

    ``n(n+1)/((n-1)(n-2)(n-3)) · Σ((x - x̄)/s)⁴ - 3(n-1)²/((n-2)(n-3))``, so a
    normal sample sits near 0. ``statistics.mcdx`` spells this formula out by
    hand next to the ``kurt`` call and gets the same number.
    """
    mag, _ = _data(a)
    n = mag.size
    z = (mag - mag.mean()) / np.std(mag, ddof=1)
    return float(
        n * (n + 1) / ((n - 1) * (n - 2) * (n - 3)) * np.sum(z**4)
        - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
    )


def percentile(a, p):
    """Mathcad ``percentile(A, p)``: the value below which a fraction ``p`` falls.

    ``p`` is a *fraction* (``0.9``), or equivalently ``90%`` -- Mathcad's ``%``
    is a dimensionless unit worth 0.01, so a Pint quantity is reduced first.
    Interpolates at position ``p·(n+1)`` of the 1-based sorted sample (NumPy's
    ``"weibull"`` method), which is what reproduces the cache: the 90th
    percentile of ``0 … 10`` is 9.8, not 9.
    """
    mag, unit = _data(a)
    fraction = float(_reduce_dimensionless(p))
    return _join(
        float(np.percentile(mag, fraction * 100.0, method="weibull")), unit
    )


def Rank(a):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Rank``: each element's **1-based** position in ascending order."""
    mag, _ = _data(a)
    order = np.argsort(mag, kind="stable")
    ranks = np.empty(mag.size, dtype=float)
    ranks[order] = np.arange(1, mag.size + 1, dtype=float)
    return ranks


def histogram(n_or_intvls, a):
    """Mathcad ``histogram``, both overloads.

    ``histogram(n, A)`` -- ``n`` equal-width intervals spanning the data --
    returns an ``n x 2`` matrix of bin midpoints (column 0, in the data's
    unit) and counts (column 1). ``histogram(intvls, A)`` -- an explicit
    vector of ``m`` interval boundaries -- returns just the ``m - 1`` counts,
    one per interval between consecutive boundaries.

    Boundaries are converted into the data's unit first: comparing raw
    magnitudes would bin ``mm`` edges against ``m`` data silently, and a
    genuinely incompatible unit should raise (Pint's ``.to``) rather than
    return a plausible-looking wrong count.
    """
    mag, unit = _data(a)
    if _is_arraylike(n_or_intvls):
        intvls = n_or_intvls
        if unit is not None and hasattr(intvls, "to"):
            intvls = intvls.to(unit)
        edges, _ = _data(intvls)
        counts, _ = np.histogram(mag, bins=edges)
        return counts.astype(float)
    n = int(n_or_intvls)
    counts, edges = np.histogram(mag, bins=n)
    midpoints = (edges[:-1] + edges[1:]) / 2.0
    out = np.empty((n, 2), dtype=object)
    out[:, 0] = [_join(float(m), unit) for m in midpoints]
    out[:, 1] = counts.astype(float)
    return out


# --- Regression, correlation and hypothesis tests ---------------------------


def _pair(vx, vy):
    """Two same-length samples as flat float arrays, with their units."""
    x, x_unit = _data(vx)
    y, y_unit = _data(vy)
    return x, y, x_unit, y_unit


def cvar(vx, vy):
    """Mathcad ``cvar``: the **population** covariance of two samples."""
    x, y, x_unit, y_unit = _pair(vx, vy)
    value = float(np.mean((x - x.mean()) * (y - y.mean())))
    unit = None if x_unit is None or y_unit is None else x_unit * y_unit
    return _join(value, unit)


def corr(vx, vy):
    """Mathcad ``corr``: Pearson's correlation coefficient (dimensionless)."""
    x, y, _, _ = _pair(vx, vy)
    return float(np.corrcoef(x, y)[0, 1])


def slope(vx, vy):
    """Mathcad ``slope(vx, vy)``: the least-squares regression slope."""
    x, y, x_unit, y_unit = _pair(vx, vy)
    value = float(np.mean((x - x.mean()) * (y - y.mean())) / np.var(x))
    unit = None if x_unit is None or y_unit is None else y_unit / x_unit
    return _join(value, unit)


def intercept(vx, vy):
    """Mathcad ``intercept(vx, vy)``: the least-squares regression intercept."""
    x, y, _, y_unit = _pair(vx, vy)
    m = float(np.mean((x - x.mean()) * (y - y.mean())) / np.var(x))
    return _join(float(y.mean() - m * x.mean()), y_unit)


def Ftest(v1, v2):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Ftest``: ``(F, p)`` for "do these samples have equal variance?".

    ``F`` is the ratio of the two *sample* variances and ``p`` the two-tailed
    significance of it differing from 1 (Numerical Recipes' ``ftest``: the
    degrees of freedom follow whichever variance ended up on top, and the
    one-tailed tail probability is doubled).

    NR's own ``ftest`` reports the *larger over smaller* ratio, so its ``F`` is
    always >= 1; this returns ``var1/var2`` as asked, which is what the sheet's
    own ``Var(batch1)/Var(batch2)`` next to the call computes. The fixture can't
    tell the two apart -- its ratio happens to exceed 1 -- but the plain ratio is
    the more useful answer and ``p`` is unaffected either way.
    """
    from scipy.special import betainc

    x, y, _, _ = _pair(v1, v2)
    var1, var2 = np.var(x, ddof=1), np.var(y, ddof=1)
    df1, df2 = x.size - 1, y.size - 1
    f = var1 / var2
    if f < 1.0:  # NR keeps F >= 1 by swapping, so the tail below is the upper one
        f, df1, df2 = 1.0 / f, df2, df1
    prob = 2.0 * betainc(0.5 * df2, 0.5 * df1, df2 / (df2 + df1 * f))
    if prob > 1.0:
        prob = 2.0 - prob
    return col(float(var1 / var2), float(prob))


def _crank(sorted_values):
    """Replace sorted values by their ranks, ties sharing the average rank.

    Returns ``(ranks, s)`` where ``s`` is Numerical Recipes' ``Σ(m³ - m)`` over
    the tie groups of length ``m`` -- the correction :func:`Spear` needs.
    """
    ranks = np.arange(1.0, sorted_values.size + 1.0)
    s = 0.0
    j = 0
    while j < sorted_values.size:
        k = j
        while k + 1 < sorted_values.size and sorted_values[k + 1] == sorted_values[j]:
            k += 1
        if k > j:
            m = k - j + 1
            ranks[j : k + 1] = 0.5 * (j + k) + 1.0
            s += m**3 - m
        j = k + 1
    return ranks, s


def Spear(vx, vy):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Spear``: Spearman's rank correlation, as five statistics.

    ``(D, zd, probd, rs, probrs)`` -- Numerical Recipes' ``spear``: the sum of
    squared rank differences, how many standard deviations that sits from its
    null expectation, its two-sided p-value, the rank correlation itself, and
    *its* two-sided p-value.
    """
    from scipy.special import betainc, erfc

    x, y, _, _ = _pair(vx, vy)
    n = x.size
    order = np.argsort(x, kind="stable")
    rank_x, sf = _crank(x[order])
    rank_x = rank_x[np.argsort(order, kind="stable")]
    order = np.argsort(y, kind="stable")
    rank_y, sg = _crank(y[order])
    rank_y = rank_y[np.argsort(order, kind="stable")]

    d = float(np.sum((rank_x - rank_y) ** 2))
    en3n = n**3 - n
    aved = en3n / 6.0 - (sf + sg) / 12.0
    fac = (1.0 - sf / en3n) * (1.0 - sg / en3n)
    vard = ((n - 1) * n**2 * (n + 1) ** 2 / 36.0) * fac
    zd = (d - aved) / math.sqrt(vard)
    probd = float(erfc(abs(zd) / math.sqrt(2.0)))
    rs = (1.0 - (6.0 / en3n) * (d + (sf + sg) / 12.0)) / math.sqrt(fac)
    tail = (rs + 1.0) * (1.0 - rs)
    if tail > 0.0:
        t = rs * math.sqrt((n - 2) / tail)
        df = n - 2
        probrs = float(betainc(0.5 * df, 0.5, df / (df + t * t)))
    else:
        probrs = 0.0
    return col(d, float(zd), probd, float(rs), probrs)


def kendltau(vx, vy):
    """Mathcad ``kendltau``: Kendall's tau for two samples, as ``(tau, z, p)``.

    Numerical Recipes' ``kendl1``: every pair of points is concordant,
    discordant, or tied on one axis; ``z`` is the null-hypothesis standard score
    and ``p`` its two-sided significance.
    """
    from scipy.special import erfc

    x, y, _, _ = _pair(vx, vy)
    n = x.size
    a1 = x[:, None] - x[None, :]
    a2 = y[:, None] - y[None, :]
    upper = np.triu(np.ones((n, n), dtype=bool), 1)
    aa = (a1 * a2)[upper]
    n1 = int(np.count_nonzero(a1[upper]))
    n2 = int(np.count_nonzero(a2[upper]))
    score = float(np.sum(np.sign(aa)))
    tau = score / (math.sqrt(n1) * math.sqrt(n2))
    svar = (4.0 * n + 10.0) / (9.0 * n * (n - 1.0))
    z = tau / math.sqrt(svar)
    return col(tau, z, float(erfc(abs(z) / math.sqrt(2.0))))


def kendltau2(tab):
    """Mathcad ``kendltau2``: Kendall's tau for a **contingency table**.

    Numerical Recipes' ``kendl2``: the table's row and column indices are the
    two ordinal variables and each cell's count weights the pairs it forms.
    Returns ``(tau, z, p)`` like :func:`kendltau`.
    """
    from scipy.special import erfc

    mag, _ = _split(tab)
    m = _as_2d(mag)
    rows_n, cols_n = m.shape
    points = float(m.sum())
    en1 = en2 = s = 0.0
    for k in range(rows_n * cols_n - 1):
        ki, kj = divmod(k, cols_n)
        for l in range(k + 1, rows_n * cols_n):  # noqa: E741 -- NR's own name
            li, lj = divmod(l, cols_n)
            m1, m2 = li - ki, lj - kj
            pairs = float(m[ki, kj] * m[li, lj])
            if m1 * m2:
                en1 += pairs
                en2 += pairs
                s += pairs if m1 * m2 > 0 else -pairs
            else:
                if m1:
                    en1 += pairs
                if m2:
                    en2 += pairs
    tau = s / math.sqrt(en1 * en2)
    svar = (4.0 * points + 10.0) / (9.0 * points * (points - 1.0))
    z = tau / math.sqrt(svar)
    return col(tau, z, float(erfc(abs(z) / math.sqrt(2.0))))


def contingtbl(tab):
    """Mathcad ``contingtbl``: chi-square association statistics for a table.

    Numerical Recipes' ``cntab1``, returning ``(χ², df, p, Cramér's V, C)`` --
    the last two being the two standard ways of scaling χ² into a 0..1 measure
    of association. Rows and columns that are entirely empty drop out of the
    degrees of freedom, as they carry no information.
    """
    from scipy.stats import chi2

    mag, _ = _split(tab)
    m = _as_2d(mag)
    total_n = float(m.sum())
    row_sums, col_sums = m.sum(axis=1), m.sum(axis=0)
    nn_i = int(np.count_nonzero(row_sums))
    nn_j = int(np.count_nonzero(col_sums))
    df = nn_i * nn_j - nn_i - nn_j + 1
    expected = np.outer(row_sums, col_sums) / total_n
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(expected > 0, (m - expected) ** 2 / expected, 0.0)
    chisq = float(terms.sum())
    prob = float(chi2.sf(chisq, df))
    minij = min(nn_i, nn_j) - 1
    cramrv = math.sqrt(chisq / (total_n * minij))
    ccc = math.sqrt(chisq / (chisq + total_n))
    return col(chisq, float(df), prob, cramrv, ccc)


# --- Outlier detection and removal ------------------------------------------
#
# ``Grubbs``/``GrubbsClassic`` take a *confidence* ``a``, not a significance:
# PTC's own worked example calls ``Grubbs(y, 1 - alpha)``, so the significance
# level used inside is ``1 - a``.
#
# The test statistic is ``|x - mean(v)| / stdev(v)`` with the **population**
# deviation (Mathcad's lowercase ``stdev``), and the critical value is the
# standard Grubbs bound built on the Student's t quantile at ``alpha / (2N)``
# with ``N - 2`` degrees of freedom -- the formula PTC's "Grubbs' Method for
# Detecting Outliers" example spells out beside the call. The choice of
# deviation is pinned, not assumed: the "Outlier Removal" example's
# ``Grubbs(y, 0.85)`` returns three rows (3, 19, 188), and the *sample*
# deviation puts row 188 just under the bound and drops it.
#
# Each row is ``(index, test statistic, crit - statistic)``. The third column is
# therefore **negative** for a point that failed the test, matching the cached
# ``-0.207 / -0.312 / -0.003`` of that same example.


def _outlier_stats(v):
    """``(statistic per element, N)`` for an outlier test on ``v``."""
    mag, _ = _split(v)
    flat = np.atleast_1d(mag).reshape(-1)
    if np.asarray(mag).ndim == 2 and min(np.asarray(mag).shape) > 1:
        raise NotImplementedError(
            "Mathcad's outlier functions return nested index pairs for a "
            "matrix argument; only the vector form is implemented"
        )
    return np.abs(flat - flat.mean()) / np.std(flat), flat.size


def _grubbs_critical(n, a):
    """The Grubbs bound at confidence ``a`` for a sample of ``n`` points."""
    from scipy.stats import t as _t

    alpha = 1.0 - _num(a)
    quantile = float(_t.ppf(alpha / (2.0 * n), n - 2))
    return float(
        (n - 1)
        / math.sqrt(n)
        * math.sqrt(quantile**2 / (n - 2 + quantile**2))
    )


def _outlier_rows(indices, stat, crit=None):
    """Pack an ascending index list into Mathcad's result matrix."""
    idx = np.asarray(indices, dtype=int)
    columns = [idx.astype(float), stat[idx]]
    if crit is not None:
        columns.append(crit - stat[idx])
    return np.column_stack(columns)


def Grubbs(v, a):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Grubbs``: every point whose test statistic beats the bound.

    Returns one row ``(index, statistic, crit - statistic)`` per candidate, in
    ascending index order. Mathcad's own note applies: more than one row does
    not mean every one is an outlier, because both the bound and the statistic
    move once a candidate is removed.

    With no candidate at all an empty (0x3) matrix comes back. That case is
    *not* pinned by any example -- ``ThreeSigma`` documents a fall back to the
    closest point, but ``Grubbs`` does not, and inventing a row would be worse
    than returning nothing.
    """
    stat, n = _outlier_stats(v)
    crit = _grubbs_critical(n, a)
    return _outlier_rows(np.flatnonzero(stat > crit), stat, crit)


def GrubbsClassic(v, a):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``GrubbsClassic``: the one point most likely to be an outlier.

    One row, ``(index, statistic, crit - statistic)``, for the largest
    statistic in ``v``. The point is *not* necessarily an outlier -- a positive
    third column says it stayed inside the bound.
    """
    stat, n = _outlier_stats(v)
    crit = _grubbs_critical(n, a)
    return _outlier_rows([int(np.argmax(stat))], stat, crit)


def ThreeSigma(v):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``ThreeSigma``: the points more than three deviations out.

    Two columns, ``(index, statistic)``, in ascending index order. With no such
    point the closest one is returned instead, which Mathcad documents.
    """
    stat, _ = _outlier_stats(v)
    found = np.flatnonzero(stat > 3.0)
    if found.size == 0:
        found = np.array([int(np.argmax(stat))])
    return _outlier_rows(found, stat)


def trim(v, vindex):
    """Mathcad ``trim``: ``v`` without the rows ``vindex`` names.

    ``v`` is a vector or a matrix and keeps its shape and unit; ``vindex`` is
    one index or a vector of them, 0-based like everything else here. Indices
    are read through the dimensionless seam, so a count a worksheet still
    carries as a Pint ratio reduces rather than being read raw.
    """
    mag, unit = _split(v)
    wanted = np.atleast_1d(
        np.asarray(_reduce_dimensionless(vindex), dtype=float)
    ).reshape(-1)
    drop = {int(round(i)) for i in wanted}
    height = mag.shape[0] if mag.ndim else 1
    keep = [r for r in range(height) if r not in drop]
    return _join(mag[keep] if mag.ndim == 1 else mag[keep, :], unit)


# --- Probability distributions ----------------------------------------------
#
# Mathcad names these ``<letter><distribution>``: ``d`` the density, ``p`` the
# cumulative probability, ``q`` the quantile (inverse cumulative), and ``r`` a
# vector of ``m`` random draws. A random one obviously can't reproduce a cached
# worksheet value -- the numbers below it differ every run, by design.
#
# Every argument goes through ``_reduce_dimensionless`` (via ``_num``/``_count``
# for the plain-number parameters a draw needs): a worksheet routinely feeds
# these a ratio Pint still carries as ``m/mm``, and a bare ``float()`` on that
# reads the unreduced magnitude.
#
# The ``d``/``p``/``q`` wrappers return SciPy's own result rather than coercing
# to ``float``, because Mathcad applies these **element-wise to a vector**
# without needing a vectorize arrow -- ``dweibull(x, s)`` over a column of
# measurements is an ordinary worksheet line, and it reaches here as one call
# with an array ``x``. A ``float()`` around the result raises on exactly that
# call, which is what the Weibull and Poisson blocks of ``probability.mcdx``
# now pin.


def _num(x):
    """A distribution parameter as a plain ``float``, dimensionless-reduced."""
    return float(_reduce_dimensionless(x))


def _count(m):
    """A draw count (or integer parameter) as a plain ``int``."""
    return int(_reduce_dimensionless(m))


# ---------------------------------------------------------------------------
# Mathcad's own random number generator
#
# Prime's generator is the Microsoft C runtime ``rand()``: a 32-bit LCG whose
# output is bits 16..30 of the state.  ``Seed(n)`` is ``srand(n)``.  One
# ``runif`` draw consumes **two** ``rand()`` calls, packed into 30 bits --
# confirmed exact (0.0 error) against ``references/seed.mcdx``'s cached values.
#
# Reproducing the stream is what makes ``Seed`` meaningful, so the whole family
# below deliberately does *not* use NumPy's generator.  ``rt`` and
# ``rhypergeom`` are the two exceptions and still do -- ``seed.mcdx`` does not
# pin either (``rt`` draws one uniform more than its value accounts for,
# ``rhypergeom``'s only block is degenerate), and a guess there would be a
# plausible wrong number rather than an error.  ``Seed`` reseeds NumPy as well,
# so those two stay repeatable run-to-run even though their values are not
# Mathcad's; a sheet that calls either desynchronises the stream after it.


class _MathcadRNG:
    """The Microsoft C runtime ``rand()``, which is Prime's generator."""

    def __init__(self, seed: int = 1) -> None:
        self.state = seed & 0xFFFFFFFF

    def rand(self) -> int:
        """One 15-bit ``rand()`` output."""
        self.state = (self.state * 214013 + 2531011) & 0xFFFFFFFF
        return (self.state >> 16) & 0x7FFF

    def unif(self) -> float:
        """One uniform on [0, 1), from two ``rand()`` calls (30 bits)."""
        return (self.rand() * 32768 + self.rand()) / 1073741824.0


# Prime opens a new worksheet at state 1, the same place ``Seed(1)`` puts it --
# confirmed by typing ``runif(4,0,1)`` as the first region of a fresh sheet.  A
# worksheet that never calls ``Seed`` is therefore reproducible as well.
_RNG = _MathcadRNG(1)

# sqrt(8/e), the Kinderman-Monahan ratio-of-uniforms constant.  Mathcad uses
# the exact value, not Numerical Recipes' rounded 1.7156.
_KM_C = math.sqrt(8.0 / math.e)


def Seed(n):
    """Mathcad ``Seed``: restart the random stream at ``n``.

    Returns the generator's **previous** 32-bit state, not the new seed and not
    a status code.  ``Seed(1)`` twice in a row therefore returns ``1`` the
    second time, which is why the value looks constant until a draw moves the
    stream; after ``runif(20, 0, 1)`` it returns that run's end state.
    """
    seed = _count(n)
    previous = _RNG.state
    _RNG.state = seed & 0xFFFFFFFF
    np.random.seed(seed & 0xFFFFFFFF)
    return previous


def _standard_normal():
    """One N(0, 1) draw by Kinderman-Monahan ratio of uniforms, as Prime does."""
    while True:
        u = _RNG.unif()
        if u <= 0.0:
            continue
        v = _KM_C * (_RNG.unif() - 0.5)
        x = v / u
        if x * x <= -4.0 * math.log(u):
            return x


def _exponential():
    """One unit-mean exponential: Prime's inverse CDF on ``u``, not ``1 - u``."""
    return -math.log(_RNG.unif())


def _johnk_gamma(a):
    """One Gamma(``a``, 1) draw for ``0 < a < 1``, by Johnk's ratio.

    Two uniforms per attempt plus one exponential, so three in the common case
    of a first-attempt accept -- which is the count ``seed.mcdx``'s
    ``rchisq(1, 0.5)`` block measures.  The two powers are deliberately spelled
    differently: ``exp(log(u)/a)`` for the first and ``**`` for the second is
    what reproduces Prime's last two bits, and ``**`` for both does not.
    """
    while True:
        x = math.exp(math.log(_RNG.unif()) / a)
        y = _RNG.unif() ** (1.0 / (1.0 - a))
        if x + y <= 1.0:
            return (x / (x + y)) * _exponential()


def _gamma(a):
    """One Gamma(``a``, 1) draw, split the way Prime splits the shape.

    Gamma shapes add, so Prime builds ``a`` from pieces it can draw directly:
    the whole part as that many exponentials, a remaining half as one squared
    normal over two, and any other fraction by :func:`_johnk_gamma`.  Each
    piece is pinned by a ``seed.mcdx`` block -- ``a = 1`` (inside ``rnbinom``
    and ``rbeta``), ``a = 1/2`` (``rgamma``), ``a = 1/4`` (``rchisq``) -- but
    no block mixes two of them, so the *order* of the pieces is inferred.
    """
    whole = math.floor(a)
    total = math.fsum(_exponential() for _ in range(int(whole)))
    frac = a - whole
    if frac == 0.0:
        return total
    if frac == 0.5:
        z = _standard_normal()
        return total + z * z / 2.0
    return total + _johnk_gamma(frac)


def _chisq(d):
    """One chi-squared draw with ``d`` degrees of freedom: ``2 * Gamma(d/2)``.

    Integer ``d`` therefore lands on the squared-normal arm -- ``chisq(1)`` is
    exactly ``z**2``, which is what makes ``rF(1, 1, 1)`` two normals.
    """
    return 2.0 * _gamma(d / 2.0)


def _poisson(lamb):
    """One Poisson draw by Knuth's multiplication method.

    Consumes ``k + 1`` uniforms to return ``k``.  ``seed.mcdx`` pins it twice:
    directly as ``rpois(1, 1)``, and as the second half of ``rnbinom``.
    """
    limit = math.exp(-lamb)
    product = 1.0
    k = 0
    while True:
        product *= _RNG.unif()
        if product < limit:
            return k
        k += 1


def _draws(m, one):
    """``m`` draws from a scalar generator, as an array."""
    return np.array([one() for _ in range(_count(m))])


def dnorm(x, mu=0.0, sigma=1.0):
    """Mathcad ``dnorm``: the normal probability *density* at ``x``."""
    from scipy.stats import norm

    return norm.pdf(_reduce_dimensionless(x), _num(mu), _num(sigma))


def pnorm(x, mu=0.0, sigma=1.0):
    """Mathcad ``pnorm``: the normal *cumulative* probability up to ``x``."""
    from scipy.stats import norm

    return norm.cdf(_reduce_dimensionless(x), _num(mu), _num(sigma))


def qnorm(p, mu=0.0, sigma=1.0):
    """Mathcad ``qnorm``: the normal quantile -- the inverse of :func:`pnorm`."""
    from scipy.stats import norm

    return norm.ppf(_reduce_dimensionless(p), _num(mu), _num(sigma))


def rnorm(m, mu=0.0, sigma=1.0):
    """Mathcad ``rnorm``: ``m`` random draws from a normal distribution.

    Byte-exact against Prime for a given :func:`Seed`.
    """
    mu, sigma = _num(mu), _num(sigma)
    return np.array([mu + sigma * _standard_normal() for _ in range(_count(m))])


def dt(x, d):
    """Mathcad ``dt``: the Student's *t* density at ``x`` with ``d`` d.o.f."""
    from scipy.stats import t

    return t.pdf(_reduce_dimensionless(x), _num(d))


def pt(x, d):
    """Mathcad ``pt``: the Student's *t* cumulative probability up to ``x``."""
    from scipy.stats import t

    return t.cdf(_reduce_dimensionless(x), _num(d))


def qt(p, d):
    """Mathcad ``qt``: the Student's *t* quantile -- the inverse of :func:`pt`."""
    from scipy.stats import t

    return t.ppf(_reduce_dimensionless(p), _num(d))


def rt(m, d):
    """Mathcad ``rt``: ``m`` random draws from a Student's *t* distribution."""
    return np.random.standard_t(_num(d), _count(m))


def dweibull(x, s):
    """Mathcad ``dweibull``: the Weibull density (shape ``s``, unit scale)."""
    from scipy.stats import weibull_min

    return weibull_min.pdf(_reduce_dimensionless(x), _num(s))


def pweibull(x, s):
    """Mathcad ``pweibull``: the Weibull cumulative probability up to ``x``."""
    from scipy.stats import weibull_min

    return weibull_min.cdf(_reduce_dimensionless(x), _num(s))


def qweibull(p, s):
    """Mathcad ``qweibull``: the Weibull quantile (inverse of :func:`pweibull`)."""
    from scipy.stats import weibull_min

    return weibull_min.ppf(_reduce_dimensionless(p), _num(s))


def rweibull(m, s):
    """Mathcad ``rweibull``: ``m`` random draws from a Weibull distribution.

    Prime's inverse CDF, on ``u`` rather than ``1 - u``: ``(-ln u) ** (1/s)``.
    """
    s = _num(s)
    return _draws(m, lambda: _exponential() ** (1.0 / s))


def Re(x):
    """Mathcad ``Re(z)``: the real part of a (possibly complex) value.

    Unit-aware: Mathcad takes ``Re`` of a *dimensioned* complex value as
    readily as of a plain number (a complex impedance in ohms, a complex
    modulus in MPa), and ``np.real`` has no implementation for a Pint
    quantity -- it raises rather than reaching the magnitude.
    """
    if hasattr(x, "units"):
        return _join(np.real(x.magnitude), x.units)
    return np.real(x)


def cnorm(x):
    """Mathcad ``cnorm``: the standard normal cumulative probability -- a
    Mathcad-15-era alias for ``pnorm(x, 0, 1)``, kept for compatibility."""
    return pnorm(x, 0.0, 1.0)


def dunif(x, a, b):
    """Mathcad ``dunif``: the uniform density on ``[a, b]``."""
    from scipy.stats import uniform

    a, b = _reduce_dimensionless(a), _reduce_dimensionless(b)
    return uniform.pdf(_reduce_dimensionless(x), a, b - a)


def punif(x, a, b):
    """Mathcad ``punif``: the uniform cumulative probability up to ``x``."""
    from scipy.stats import uniform

    a, b = _reduce_dimensionless(a), _reduce_dimensionless(b)
    return uniform.cdf(_reduce_dimensionless(x), a, b - a)


def qunif(p, a, b):
    """Mathcad ``qunif``: the uniform quantile -- the inverse of :func:`punif`."""
    from scipy.stats import uniform

    a, b = _reduce_dimensionless(a), _reduce_dimensionless(b)
    return uniform.ppf(_reduce_dimensionless(p), a, b - a)


def runif(m, a, b):
    """Mathcad ``runif``: ``m`` random draws from a uniform distribution.

    Byte-exact against Prime for a given :func:`Seed`.
    """
    a, b = _num(a), _num(b)
    return np.array([a + (b - a) * _RNG.unif() for _ in range(_count(m))])


def dexp(x, r):
    """Mathcad ``dexp``: the exponential density with rate ``r``."""
    from scipy.stats import expon

    return expon.pdf(_reduce_dimensionless(x), scale=1.0 / _reduce_dimensionless(r))


def pexp(x, r):
    """Mathcad ``pexp``: the exponential cumulative probability up to ``x``."""
    from scipy.stats import expon

    return expon.cdf(_reduce_dimensionless(x), scale=1.0 / _reduce_dimensionless(r))


def qexp(p, r):
    """Mathcad ``qexp``: the exponential quantile -- the inverse of :func:`pexp`."""
    from scipy.stats import expon

    return expon.ppf(_reduce_dimensionless(p), scale=1.0 / _reduce_dimensionless(r))


def rexp(m, r):
    """Mathcad ``rexp``: ``m`` random draws from an exponential distribution.

    Prime's inverse CDF: ``-ln(u) / r``, one uniform per draw.
    """
    r = _num(r)
    return _draws(m, lambda: _exponential() / r)


def dgamma(x, s):
    """Mathcad ``dgamma``: the gamma density (shape ``s``, unit scale)."""
    from scipy.stats import gamma

    return gamma.pdf(_reduce_dimensionless(x), _reduce_dimensionless(s))


def pgamma(x, s):
    """Mathcad ``pgamma``: the gamma cumulative probability up to ``x``."""
    from scipy.stats import gamma

    return gamma.cdf(_reduce_dimensionless(x), _reduce_dimensionless(s))


def qgamma(p, s):
    """Mathcad ``qgamma``: the gamma quantile -- the inverse of :func:`pgamma`."""
    from scipy.stats import gamma

    return gamma.ppf(_reduce_dimensionless(p), _reduce_dimensionless(s))


def rgamma(m, s):
    """Mathcad ``rgamma``: ``m`` random draws from a gamma distribution."""
    s = _num(s)
    return _draws(m, lambda: _gamma(s))


def dlogis(x, loc, s):
    """Mathcad ``dlogis``: the logistic density (location, scale ``s``).

    Mathcad spells the location parameter ``l``; it is ``loc`` here because a
    bare ``l`` is an ambiguous identifier. Both are positional either way."""
    from scipy.stats import logistic

    return logistic.pdf(_reduce_dimensionless(x), _reduce_dimensionless(loc), _reduce_dimensionless(s))


def plogis(x, loc, s):
    """Mathcad ``plogis``: the logistic cumulative probability up to ``x``."""
    from scipy.stats import logistic

    return logistic.cdf(_reduce_dimensionless(x), _reduce_dimensionless(loc), _reduce_dimensionless(s))


def qlogis(p, loc, s):
    """Mathcad ``qlogis``: the logistic quantile -- the inverse of :func:`plogis`."""
    from scipy.stats import logistic

    return logistic.ppf(_reduce_dimensionless(p), _reduce_dimensionless(loc), _reduce_dimensionless(s))


def rlogis(m, loc, s):
    """Mathcad ``rlogis``: ``m`` random draws from a logistic distribution.

    Prime's inverse CDF: ``loc + s * ln(u / (1 - u))``.
    """
    loc, s = _num(loc), _num(s)
    def one():
        u = _RNG.unif()
        return loc + s * math.log(u / (1.0 - u))
    return _draws(m, one)


def dcauchy(x, loc, s):
    """Mathcad ``dcauchy``: the Cauchy density (location ``loc``, scale ``s``);
    Mathcad's own name for ``loc`` is ``l`` -- see :func:`dlogis`."""
    from scipy.stats import cauchy

    return cauchy.pdf(_reduce_dimensionless(x), _reduce_dimensionless(loc), _reduce_dimensionless(s))


def pcauchy(x, loc, s):
    """Mathcad ``pcauchy``: the Cauchy cumulative probability up to ``x``."""
    from scipy.stats import cauchy

    return cauchy.cdf(_reduce_dimensionless(x), _reduce_dimensionless(loc), _reduce_dimensionless(s))


def qcauchy(p, loc, s):
    """Mathcad ``qcauchy``: the Cauchy quantile -- the inverse of :func:`pcauchy`."""
    from scipy.stats import cauchy

    return cauchy.ppf(_reduce_dimensionless(p), _reduce_dimensionless(loc), _reduce_dimensionless(s))


def rcauchy(m, loc, s):
    """Mathcad ``rcauchy``: ``m`` random draws from a Cauchy distribution.

    Prime's inverse CDF: ``loc + s * tan(pi * (u - 1/2))``.
    """
    loc, s = _num(loc), _num(s)
    return _draws(m, lambda: loc + s * math.tan(math.pi * (_RNG.unif() - 0.5)))


def dgeom(k, q):
    """Mathcad ``dgeom``: probability of ``k`` failures before the first success
    (success probability ``q``). Mathcad's ``k`` starts at 0; SciPy's ``geom``
    counts the trial of the first success starting at 1, hence the ``k + 1``."""
    from scipy.stats import geom

    return geom.pmf(_reduce_dimensionless(k) + 1, _reduce_dimensionless(q))


def pgeom(k, q):
    """Mathcad ``pgeom``: cumulative probability of at most ``k`` failures
    before the first success."""
    from scipy.stats import geom

    return geom.cdf(_reduce_dimensionless(k) + 1, _reduce_dimensionless(q))


def qgeom(p, q):
    """Mathcad ``qgeom``: the geometric quantile -- the inverse of :func:`pgeom`."""
    from scipy.stats import geom

    return geom.ppf(_reduce_dimensionless(p), _reduce_dimensionless(q)) - 1


def rgeom(m, q):
    """Mathcad ``rgeom``: ``m`` random draws (failures before first success)
    from a geometric distribution.

    Prime's inverse CDF: ``floor(ln(u) / ln(1 - q))``.
    """
    denom = math.log(1.0 - _num(q))
    return _draws(m, lambda: float(math.floor(math.log(_RNG.unif()) / denom)))


def dhypergeom(k, a, b, n):
    """Mathcad ``dhypergeom``: probability of ``k`` successes when drawing a
    sample of size ``n`` without replacement from ``a`` successes + ``b``
    failures."""
    from scipy.stats import hypergeom

    a, b, n = _reduce_dimensionless(a), _reduce_dimensionless(b), _reduce_dimensionless(n)
    return hypergeom.pmf(_reduce_dimensionless(k), a + b, a, n)


def phypergeom(k, a, b, n):
    """Mathcad ``phypergeom``: cumulative probability of at most ``k``
    successes."""
    from scipy.stats import hypergeom

    a, b, n = _reduce_dimensionless(a), _reduce_dimensionless(b), _reduce_dimensionless(n)
    return hypergeom.cdf(_reduce_dimensionless(k), a + b, a, n)


def qhypergeom(p, a, b, n):
    """Mathcad ``qhypergeom``: the hypergeometric quantile -- the inverse of
    :func:`phypergeom`."""
    from scipy.stats import hypergeom

    a, b, n = _reduce_dimensionless(a), _reduce_dimensionless(b), _reduce_dimensionless(n)
    return hypergeom.ppf(_reduce_dimensionless(p), a + b, a, n)


def rhypergeom(m, a, b, n):
    """Mathcad ``rhypergeom``: ``m`` random draws from a hypergeometric
    distribution."""
    return np.random.hypergeometric(_count(a), _count(b), _count(n), _count(m))


def dbinom(k, n, q):
    """Mathcad ``dbinom``: probability of ``k`` successes in ``n`` trials
    (success probability ``q``)."""
    from scipy.stats import binom

    return binom.pmf(_reduce_dimensionless(k), _reduce_dimensionless(n), _reduce_dimensionless(q))


def pbinom(k, n, q):
    """Mathcad ``pbinom``: cumulative probability of at most ``k`` successes."""
    from scipy.stats import binom

    return binom.cdf(_reduce_dimensionless(k), _reduce_dimensionless(n), _reduce_dimensionless(q))


def qbinom(p, n, q):
    """Mathcad ``qbinom``: the binomial quantile -- the inverse of :func:`pbinom`."""
    from scipy.stats import binom

    return binom.ppf(_reduce_dimensionless(p), _reduce_dimensionless(n), _reduce_dimensionless(q))


def rbinom(m, n, q):
    """Mathcad ``rbinom``: ``m`` random draws from a binomial distribution.

    Inverse CDF: walk the mass function until it covers ``u``, one uniform per
    draw.  ``seed.mcdx`` only calls it with ``n = 1``, where this and a single
    Bernoulli trial agree on both the value and the uniform count, so ``n > 1``
    rests on the one-uniform count rather than on a cached number.
    """
    n, q = _count(n), _num(q)
    def one():
        u = _RNG.unif()
        term = (1.0 - q) ** n
        total = term
        for k in range(n):
            if u < total:
                return float(k)
            term *= (n - k) / (k + 1.0) * q / (1.0 - q)
            total += term
        return float(n)
    return _draws(m, one)


def dnbinom(k, n, q):
    """Mathcad ``dnbinom``: probability of ``k`` failures before the ``n``-th
    success (success probability ``q``)."""
    from scipy.stats import nbinom

    return nbinom.pmf(_reduce_dimensionless(k), _reduce_dimensionless(n), _reduce_dimensionless(q))


def pnbinom(k, n, q):
    """Mathcad ``pnbinom``: cumulative probability of at most ``k`` failures."""
    from scipy.stats import nbinom

    return nbinom.cdf(_reduce_dimensionless(k), _reduce_dimensionless(n), _reduce_dimensionless(q))


def qnbinom(p, n, q):
    """Mathcad ``qnbinom``: the negative-binomial quantile -- the inverse of
    :func:`pnbinom`."""
    from scipy.stats import nbinom

    return nbinom.ppf(_reduce_dimensionless(p), _reduce_dimensionless(n), _reduce_dimensionless(q))


def rnbinom(m, n, q):
    """Mathcad ``rnbinom``: ``m`` random draws from a negative-binomial
    distribution.

    Prime draws it as a gamma-Poisson mixture: a Gamma(``n``) rate scaled by
    ``(1 - q) / q``, then one Poisson draw at that rate.
    """
    n, q = _num(n), _num(q)
    scale = (1.0 - q) / q
    return _draws(m, lambda: float(_poisson(_gamma(n) * scale)))


def dbeta(x, s1, s2):
    """Mathcad ``dbeta``: the beta density (shape parameters ``s1``, ``s2``)."""
    from scipy.stats import beta

    return beta.pdf(_reduce_dimensionless(x), _reduce_dimensionless(s1), _reduce_dimensionless(s2))


def pbeta(x, s1, s2):
    """Mathcad ``pbeta``: the beta cumulative probability up to ``x``."""
    from scipy.stats import beta

    return beta.cdf(_reduce_dimensionless(x), _reduce_dimensionless(s1), _reduce_dimensionless(s2))


def qbeta(p, s1, s2):
    """Mathcad ``qbeta``: the beta quantile -- the inverse of :func:`pbeta`."""
    from scipy.stats import beta

    return beta.ppf(_reduce_dimensionless(p), _reduce_dimensionless(s1), _reduce_dimensionless(s2))


def rbeta(m, s1, s2):
    """Mathcad ``rbeta``: ``m`` random draws from a beta distribution.

    Built from two gamma draws, ``G(s1) / (G(s1) + G(s2))``.
    """
    s1, s2 = _num(s1), _num(s2)
    def one():
        a, b = _gamma(s1), _gamma(s2)
        return a / (a + b)
    return _draws(m, one)


def dchisq(x, d):
    """Mathcad ``dchisq``: the chi-squared density with ``d`` degrees of
    freedom."""
    from scipy.stats import chi2

    return chi2.pdf(_reduce_dimensionless(x), _reduce_dimensionless(d))


def pchisq(x, d):
    """Mathcad ``pchisq``: the chi-squared cumulative probability up to ``x``."""
    from scipy.stats import chi2

    return chi2.cdf(_reduce_dimensionless(x), _reduce_dimensionless(d))


def qchisq(p, d):
    """Mathcad ``qchisq``: the chi-squared quantile -- the inverse of
    :func:`pchisq`."""
    from scipy.stats import chi2

    return chi2.ppf(_reduce_dimensionless(p), _reduce_dimensionless(d))


def rchisq(m, d):
    """Mathcad ``rchisq``: ``m`` random draws from a chi-squared distribution."""
    d = _num(d)
    return _draws(m, lambda: _chisq(d))


def dF(x, d1, d2):
    """Mathcad ``dF``: the F density with ``d1``/``d2`` degrees of freedom."""
    from scipy.stats import f

    return f.pdf(_reduce_dimensionless(x), _reduce_dimensionless(d1), _reduce_dimensionless(d2))


def pF(x, d1, d2):
    """Mathcad ``pF``: the F cumulative probability up to ``x``."""
    from scipy.stats import f

    return f.cdf(_reduce_dimensionless(x), _reduce_dimensionless(d1), _reduce_dimensionless(d2))


def qF(p, d1, d2):
    """Mathcad ``qF``: the F quantile -- the inverse of :func:`pF`."""
    from scipy.stats import f

    return f.ppf(_reduce_dimensionless(p), _reduce_dimensionless(d1), _reduce_dimensionless(d2))


def rF(m, d1, d2):
    """Mathcad ``rF``: ``m`` random draws from an F distribution.

    The ratio of two chi-squared draws over their degrees of freedom.  For
    ``d1 = d2 = 1`` that is two squared normals, which is the six-uniform
    fingerprint ``seed.mcdx`` records.
    """
    d1, d2 = _num(d1), _num(d2)
    return _draws(m, lambda: (_chisq(d1) / d1) / (_chisq(d2) / d2))


def dlnorm(x, mu, sigma):
    """Mathcad ``dlnorm``: the log-normal density (``mu``/``sigma`` are the
    underlying normal's mean and standard deviation)."""
    from scipy.stats import lognorm

    mu, sigma = _reduce_dimensionless(mu), _reduce_dimensionless(sigma)
    return lognorm.pdf(_reduce_dimensionless(x), sigma, scale=np.exp(mu))


def plnorm(x, mu, sigma):
    """Mathcad ``plnorm``: the log-normal cumulative probability up to ``x``."""
    from scipy.stats import lognorm

    mu, sigma = _reduce_dimensionless(mu), _reduce_dimensionless(sigma)
    return lognorm.cdf(_reduce_dimensionless(x), sigma, scale=np.exp(mu))


def qlnorm(p, mu, sigma):
    """Mathcad ``qlnorm``: the log-normal quantile -- the inverse of
    :func:`plnorm`."""
    from scipy.stats import lognorm

    mu, sigma = _reduce_dimensionless(mu), _reduce_dimensionless(sigma)
    return lognorm.ppf(_reduce_dimensionless(p), sigma, scale=np.exp(mu))


def rlnorm(m, mu, sigma):
    """Mathcad ``rlnorm``: ``m`` random draws from a log-normal distribution.

    The exponential of a normal draw.  ``seed.mcdx`` has no ``rlnorm`` block,
    so the value follows from :func:`rnorm` rather than from a cached number.
    """
    mu, sigma = _num(mu), _num(sigma)
    return _draws(m, lambda: math.exp(mu + sigma * _standard_normal()))


def dpois(k, lamb):
    """Mathcad ``dpois``: probability of exactly ``k`` events when the mean
    rate is ``lambda``."""
    from scipy.stats import poisson

    return poisson.pmf(_reduce_dimensionless(k), _reduce_dimensionless(lamb))


def ppois(k, lamb):
    """Mathcad ``ppois``: cumulative probability of at most ``k`` events."""
    from scipy.stats import poisson

    return poisson.cdf(_reduce_dimensionless(k), _reduce_dimensionless(lamb))


def qpois(p, lamb):
    """Mathcad ``qpois``: the Poisson quantile -- the inverse of :func:`ppois`."""
    from scipy.stats import poisson

    return poisson.ppf(_reduce_dimensionless(p), _reduce_dimensionless(lamb))


def rpois(m, lamb):
    """Mathcad ``rpois``: ``m`` random draws from a Poisson distribution."""
    lamb = _num(lamb)
    return _draws(m, lambda: float(_poisson(lamb)))


# --- Table search (match / lookup / vlookup / hlookup / vhlookup) -----------
#
# Mathcad scans a matrix **column-major** and every one of these returns a
# *vector* of results, even when there is exactly one hit (its cache shows a
# 1x1 matrix, not a bare scalar). Not finding the value at all is an error in
# Mathcad, so these raise rather than return an empty vector.


def _same(a, b):
    """Mathcad's equality for a table search: never raises, never coerces.

    A search table routinely mixes strings with numbers (a labelled table), and
    a bare number is not a dimensioned one, so a mismatch of *kind* is simply
    "not equal" rather than an error.
    """
    if isinstance(a, str) or isinstance(b, str):
        return isinstance(a, str) and isinstance(b, str) and a == b
    try:
        return bool(a == b)
    except Exception:
        return False


def _search_grid(a):
    """``a`` as an object array, keeping its 1-D/2-D distinction."""
    return _to_object_matrix(a)


def _found(hits, z, what):
    if len(hits) == 0:
        raise ValueError(f"{what}: {z!r} not found")
    return col(*hits)


def _positions(z, grid):
    """Indices of ``z`` in ``grid``, column-major.

    A 1-D grid (a column vector) yields plain integer indices; a 2-D grid
    yields ``(row, col)`` pairs -- which is why Mathcad's cache for
    ``match(7, R)`` on a ``1x3`` *row* holds a nested ``[0; 2]`` while
    ``match(3, V)`` on a ``3x1`` column holds the bare ``2``.
    """
    if grid.ndim == 1:
        return [i for i, v in enumerate(grid) if _same(v, z)]
    nrows, ncols = grid.shape
    return [
        col(i, j)
        for j in range(ncols)
        for i in range(nrows)
        if _same(grid[i, j], z)
    ]


def match(z, A):
    """Mathcad ``match(z, A)``: the indices at which ``z`` occurs in ``A``.

    A vector gives scalar indices, a matrix ``(row, col)`` index pairs.
    """
    return _found(_positions(z, _search_grid(A)), z, "match")


def lookup(z, A, B):
    """Mathcad ``lookup(z, A, B)``: the elements of ``B`` at the positions
    where ``A`` equals ``z`` (``A`` and ``B`` sharing a shape)."""
    grid, out = _search_grid(A), _search_grid(B)
    values = [
        out[p] if grid.ndim == 1 else out[int(p[0]), int(p[1])]
        for p in _positions(z, grid)
    ]
    return _found(values, z, "lookup")


def vlookup(z, A, c):
    """Mathcad ``vlookup(z, A, c)``: search the **first column** of ``A`` for
    ``z``; return column ``c`` of each matching row."""
    grid = _as_2d_grid(A)
    values = [grid[i, int(c)] for i in range(grid.shape[0]) if _same(grid[i, 0], z)]
    return _found(values, z, "vlookup")


def hlookup(z, A, r):
    """Mathcad ``hlookup(z, A, r)``: search the **first row** of ``A`` for
    ``z``; return row ``r`` of each matching column."""
    grid = _as_2d_grid(A)
    values = [grid[int(r), j] for j in range(grid.shape[1]) if _same(grid[0, j], z)]
    return _found(values, z, "hlookup")


def vhlookup(z_v, z_h, A):
    """Mathcad ``vhlookup(z_v, z_h, A)``: the elements where the row labelled
    ``z_v`` (first column) meets the column labelled ``z_h`` (first row)."""
    grid = _as_2d_grid(A)
    rows = [i for i in range(grid.shape[0]) if _same(grid[i, 0], z_v)]
    cols_ = [j for j in range(grid.shape[1]) if _same(grid[0, j], z_h)]
    if not rows:
        raise ValueError(f"vhlookup: {z_v!r} not found in the first column")
    if not cols_:
        raise ValueError(f"vhlookup: {z_h!r} not found in the first row")
    return col(*[grid[i, j] for j in cols_ for i in rows])


def _as_2d_grid(a):
    """A 2-D object view; a 1-D vector counts as a single column."""
    grid = _search_grid(a)
    return grid.reshape(-1, 1) if grid.ndim == 1 else grid


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


# ---------------------------------------------------------------------------
# Interpolation & prediction
#
# Mathcad's "Interpolation and Prediction" family, in the order the PTC help
# tutorial (``references/interpolation_prediction.mcdx``) walks through it.
# Everything below is exact against that sheet's cached ``result.xml``: the
# polynomial set is Numerical Recipes' ``polint``/``polcoe``/``ratint``, the
# Thiele set is the classic reciprocal-difference recursion, and ``predict``
# is Burg's maximum-entropy method (NR ``memcof`` + ``predic``).
#
# Every entry point takes its data as Pint quantities or plain numbers alike:
# the abscissae, the ordinates and the query point are split into magnitudes,
# the query is converted into the abscissae's unit, and the ordinates' unit is
# put back on the answer.
# ---------------------------------------------------------------------------


def _xy_query(vx, vy, x):
    """``(xs, ys, xq, y_unit)`` for an interpolator called as ``f(vx, vy, x)``.

    ``x`` is converted into ``vx``'s unit before its magnitude is taken -- an
    ``x`` in mm against knots in m would otherwise interpolate at a point a
    thousand times too small, which is a plausible wrong answer rather than an
    error. ``xq`` keeps ``x``'s shape, so a whole vector of query points (which
    Mathcad applies element-wise, with no vectorize arrow) passes straight
    through.
    """
    x_unit = getattr(vx, "units", None)
    y_unit = getattr(vy, "units", None)
    xs = _magnitudes(vx).reshape(-1)
    ys = _magnitudes(vy).reshape(-1)
    if x_unit is not None and hasattr(x, "to"):
        xq = np.asarray(x.to(x_unit).magnitude, dtype=float)
    else:
        xq = np.asarray(_magnitudes(_reduce_dimensionless(x)), dtype=float)
    return xs, ys, xq, y_unit


def _elementwise_query(xq, fn):
    """Apply a scalar-query interpolator over ``xq``, keeping its shape."""
    if xq.ndim == 0:
        return fn(float(xq))
    return np.array([fn(float(v)) for v in xq.reshape(-1)]).reshape(xq.shape)


# -- Cubic splines ----------------------------------------------------------


class _Spline:
    """The coefficient vector ``cspline``/``lspline``/``pspline`` hands to
    :func:`interp`. Private: the generated module never names it, and a public
    name here would be picked up as an import by any sheet whose prose says
    "spline".

    Mathcad returns this as a numeric vector whose first three elements are
    documented only as "internal"; the rest are the spline's second derivatives
    at the knots. Nothing but ``interp`` reads them, and inventing values for
    that header would put plausible wrong numbers into any sheet that echoed the
    vector -- so this is an opaque object instead, and prints as one.
    """

    __slots__ = ("kind", "xs", "ys", "y2", "x_unit", "y_unit")

    def __init__(self, kind, xs, ys, y2, x_unit, y_unit):
        self.kind = kind
        self.xs = xs
        self.ys = ys
        self.y2 = y2
        self.x_unit = x_unit
        self.y_unit = y_unit

    def __repr__(self):
        return f"<{self.kind} spline over {len(self.xs)} knots>"


def _spline_second_derivatives(xs, ys, kind):
    """The spline's second derivatives at the knots, for Mathcad's three end
    conditions.

    ``lspline`` makes the curve approach a **straight line** at each end (the
    second derivative there is zero -- the natural cubic spline), ``pspline`` a
    **parabola** (the end piece has no cubic term, so the second derivative is
    constant across it), and ``cspline`` a **cubic** (the third derivative runs
    on through the first and last interior knot -- the not-a-knot condition).
    """
    n = len(xs)
    if n < 3:
        return np.zeros(n)
    h = np.diff(xs)
    slope = np.diff(ys) / h

    a = np.zeros((n, n))
    rhs = np.zeros(n)
    for i in range(1, n - 1):
        a[i, i - 1] = h[i - 1]
        a[i, i] = 2.0 * (h[i - 1] + h[i])
        a[i, i + 1] = h[i]
        rhs[i] = 6.0 * (slope[i] - slope[i - 1])

    if kind == "linear":            # lspline: y'' = 0 at both ends
        a[0, 0] = a[n - 1, n - 1] = 1.0
    elif kind == "parabolic":       # pspline: y'' constant over the end pieces
        a[0, 0], a[0, 1] = 1.0, -1.0
        a[n - 1, n - 1], a[n - 1, n - 2] = 1.0, -1.0
    elif n == 3:                    # cspline: not-a-knot needs an interior knot
        a[0, 0] = a[n - 1, n - 1] = 1.0
    else:
        a[0, 0], a[0, 1], a[0, 2] = h[1], -(h[0] + h[1]), h[0]
        a[n - 1, n - 3] = h[n - 2]
        a[n - 1, n - 2] = -(h[n - 3] + h[n - 2])
        a[n - 1, n - 1] = h[n - 3]
    return np.linalg.solve(a, rhs)


def _spline(vx, vy, kind):
    x_unit = getattr(vx, "units", None)
    y_unit = getattr(vy, "units", None)
    xs = _magnitudes(vx).reshape(-1)
    ys = _magnitudes(vy).reshape(-1)
    if len(xs) != len(ys):
        raise ValueError("spline: vx and vy must have the same length")
    order = np.argsort(xs, kind="stable")
    xs, ys = xs[order], ys[order]
    return _Spline(kind, xs, ys, _spline_second_derivatives(xs, ys, kind),
                  x_unit, y_unit)


def lspline(vx, vy):
    """Mathcad ``lspline(vx, vy)``: spline coefficients with **linear** ends."""
    return _spline(vx, vy, "linear")


def pspline(vx, vy):
    """Mathcad ``pspline(vx, vy)``: spline coefficients, **parabolic** ends."""
    return _spline(vx, vy, "parabolic")


def cspline(vx, vy):
    """Mathcad ``cspline(vx, vy)``: spline coefficients with **cubic** ends."""
    return _spline(vx, vy, "cubic")


def interp(vs, vx, vy, x):
    """Mathcad ``interp(vs, vx, vy, x)``: the spline ``vs`` evaluated at ``x``.

    ``x`` may be a whole vector -- Mathcad applies ``interp`` element-wise with
    no vectorize arrow, and the tutorial sheet plots ``fit(x)`` over a range
    that way. Outside the knots the end cubic is continued, as Mathcad does.
    """
    if not isinstance(vs, _Spline):
        raise TypeError("interp: the first argument must come from "
                        "cspline/lspline/pspline")
    xs, ys, y2 = vs.xs, vs.ys, vs.y2
    _, _, xq, y_unit = _xy_query(vx, vy, x)

    def at(xv):
        i = int(np.clip(np.searchsorted(xs, xv) - 1, 0, len(xs) - 2))
        h = xs[i + 1] - xs[i]
        a = (xs[i + 1] - xv) / h
        b = (xv - xs[i]) / h
        return (a * ys[i] + b * ys[i + 1]
                + ((a ** 3 - a) * y2[i] + (b ** 3 - b) * y2[i + 1])
                * h * h / 6.0)

    return _join(_elementwise_query(xq, at), y_unit)


# -- Polynomial interpolation ------------------------------------------------


def _polint(xa, ya, x):
    """Neville's algorithm (Numerical Recipes ``polint``) -> ``(y, dy)``.

    ``dy`` is the last correction applied, which is Mathcad's error estimate.
    """
    n = len(xa)
    c = np.array(ya, dtype=float)
    d = c.copy()
    ns, dif = 0, abs(x - xa[0])
    for i in range(n):
        dift = abs(x - xa[i])
        if dift < dif:
            ns, dif = i, dift
    y, dy = float(ya[ns]), 0.0
    ns -= 1
    for m in range(1, n):
        for i in range(n - m):
            ho, hp = xa[i] - x, xa[i + m] - x
            den = (c[i + 1] - d[i]) / (ho - hp)
            d[i], c[i] = hp * den, ho * den
        if 2 * (ns + 1) < n - m:
            dy = c[ns + 1]
        else:
            dy = d[ns]
            ns -= 1
        y = y + dy
    return float(y), float(dy)


def polyint(vx, vy, x):
    """Mathcad ``polyint(vx, vy, x)``: the polynomial through **all** the data,
    as a 2-vector ``[value, error estimate]``.

    Both elements carry ``vy``'s unit -- that is how Mathcad caches the result.
    """
    xs, ys, xq, y_unit = _xy_query(vx, vy, x)
    value, error = _polint(xs, ys, float(xq))
    return _join(np.array([value, error]), y_unit)


def polyiter(vx, vy, x, n, eps):
    """Mathcad ``polyiter(vx, vy, x, n, ε)``: polynomial interpolation of
    **rising order**, as a 3-vector ``[converged, order, value]``.

    The order climbs from 1 to ``n``, each step taking one more of the data
    points in the order given, and stops as soon as two successive
    interpolations differ by less than ``ε``. ``converged`` is 1 if it stopped
    that way and 0 if it ran out of order first. Every element carries ``vy``'s
    unit, matching Mathcad's own cached result.
    """
    xs, ys, xq, y_unit = _xy_query(vx, vy, x)
    xq = float(xq)
    limit = min(_count(n), len(xs) - 1)
    if y_unit is not None and hasattr(eps, "to"):
        tol = abs(float(eps.to(y_unit).magnitude))
    else:
        tol = abs(_num(eps))
    previous, value, order = None, float(ys[0]), 1
    for order in range(1, limit + 1):
        value, _ = _polint(xs[:order + 1], ys[:order + 1], xq)
        if previous is not None and abs(value - previous) < tol:
            return _join(np.array([1.0, float(order), value]), y_unit)
        previous = value
    return _join(np.array([0.0, float(order), value]), y_unit)


def polycoeff(vx, vy):
    """Mathcad ``polycoeff(vx, vy)``: the coefficients of the interpolating
    polynomial, **lowest power first** (Numerical Recipes ``polcoe``)."""
    if getattr(vx, "units", None) is not None:
        raise ValueError("polycoeff: the abscissae must be dimensionless -- "
                         "each coefficient would otherwise carry its own unit")
    xs = _magnitudes(vx).reshape(-1)
    ys = _magnitudes(vy).reshape(-1)
    n = len(xs)
    s = np.zeros(n)
    cof = np.zeros(n)
    s[n - 1] = -xs[0]
    for i in range(1, n):
        for j in range(n - 1 - i, n - 1):
            s[j] -= xs[i] * s[j + 1]
        s[n - 1] -= xs[i]
    for j in range(n):
        phi = float(n)
        for k in range(n - 1, 0, -1):
            phi = k * s[k] + xs[j] * phi
        ff = ys[j] / phi
        b = 1.0
        for k in range(n - 1, -1, -1):
            cof[k] += b * ff
            b = s[k] + xs[j] * b
    return _join(cof, getattr(vy, "units", None))


def rationalint(vx, vy, x):
    """Mathcad ``rationalint(vx, vy, x)``: diagonal rational-function
    interpolation through all the data, as ``[value, error estimate]``
    (Numerical Recipes ``ratint``, the Bulirsch-Stoer algorithm)."""
    xs, ys, xq, y_unit = _xy_query(vx, vy, x)
    xq = float(xq)
    n = len(xs)
    c = np.array(ys, dtype=float)
    d = c + 1e-25
    ns, hh = 0, abs(xq - xs[0])
    for i in range(n):
        h = abs(xq - xs[i])
        if h == 0.0:
            return _join(np.array([float(ys[i]), 0.0]), y_unit)
        if h < hh:
            ns, hh = i, h
    y, dy = float(ys[ns]), 0.0
    ns -= 1
    for m in range(1, n):
        for i in range(n - m):
            w = c[i + 1] - d[i]
            h = xs[i + m] - xq
            t = (xs[i] - xq) * d[i] / h
            dd = t - c[i + 1]
            if dd == 0.0:
                raise ValueError("rationalint: the interpolating function has "
                                 "a pole at this point")
            dd = w / dd
            d[i] = c[i + 1] * dd
            c[i] = t * dd
        if 2 * (ns + 1) < n - m:
            dy = c[ns + 1]
        else:
            dy = d[ns]
            ns -= 1
        y += dy
    return _join(np.array([y, dy]), y_unit)


# -- Thiele continued-fraction interpolation ---------------------------------

# Mathcad substitutes this for a zero denominator in the reciprocal-difference
# recursion rather than raising: two equal ordinates give a coefficient of 1e65
# where the mathematics says infinity. Reproducing the substitution -- and then
# letting ordinary floating point run on from it -- is what makes
# ``Thielecoeff`` byte-exact on the tutorial sheet's degenerate second example,
# whose last coefficient (-4.2764235361e-50) is a pure rounding artefact of it.
_THIELE_TINY = 1e-65


def Thielecoeff(vx, vy):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Thielecoeff(vx, vy)``: the continued-fraction coefficients of
    the Thiele interpolant, by reciprocal differences."""
    xs = _magnitudes(vx).reshape(-1)
    ys = _magnitudes(vy).reshape(-1)
    n = len(xs)
    coeff = np.zeros(n)
    coeff[0] = ys[0]
    level = np.array(ys, dtype=float)
    for k in range(1, n):
        nxt = np.zeros(n)
        for i in range(k, n):
            den = level[i] - level[k - 1]
            nxt[i] = (xs[i] - xs[k - 1]) / (den if den != 0.0 else _THIELE_TINY)
        coeff[k] = nxt[k]
        level = nxt
    return coeff


def Thiele(vx, c, x):  # noqa: N802 -- Mathcad's own spelling
    """Mathcad ``Thiele(vx, c, x)``: the Thiele continued fraction with
    coefficients ``c`` (from :func:`Thielecoeff`) evaluated at ``x``."""
    xs = _magnitudes(vx).reshape(-1)
    cs = _magnitudes(c).reshape(-1)
    xq = np.asarray(_magnitudes(_reduce_dimensionless(x)), dtype=float)

    def at(xv):
        value = cs[-1]
        for k in range(len(cs) - 2, -1, -1):
            value = cs[k] + (xv - xs[k]) / value
        return value

    return _elementwise_query(xq, at)


# -- Linear prediction -------------------------------------------------------


def _memcof(data, m):
    """Burg's maximum-entropy coefficients (Numerical Recipes ``memcof``).

    Returns ``d`` with ``x_k = Σ d[j]·x_{k-1-j}`` -- ``d[0]`` weights the most
    recent sample, so Mathcad's own display of the coefficients (oldest first)
    is this vector reversed.
    """
    n = len(data)
    wk1 = data[:n - 1].copy()
    wk2 = data[1:].copy()
    d = np.zeros(m)
    wkm = np.zeros(m)
    for k in range(1, m + 1):
        num = float(np.dot(wk1[:n - k], wk2[:n - k]))
        den = float(np.dot(wk1[:n - k], wk1[:n - k])
                    + np.dot(wk2[:n - k], wk2[:n - k]))
        d[k - 1] = 2.0 * num / den
        for i in range(1, k):
            d[i - 1] = wkm[i - 1] - d[k - 1] * wkm[k - i - 1]
        if k == m:
            return d
        wkm[:k] = d[:k]
        for j in range(n - k - 1):
            wk1[j] = wk1[j] - wkm[k - 1] * wk2[j]
            wk2[j] = wk2[j + 1] - wkm[k - 1] * wk1[j + 1]
    return d


def predict(v, m, n):
    """Mathcad ``predict(v, m, n)``: ``n`` values continuing the evenly-spaced
    series ``v``, from a linear predictor fitted to ``m`` of its terms.

    The predictor is Burg's maximum-entropy method, and each predicted value
    feeds back in as data for the next -- so the run extrapolates rather than
    repeating the last window. Mathcad rejects ``m >= rows(v)``: the predicted
    values cannot be a linear function of *all* the data points.
    """
    unit = getattr(v, "units", None)
    data = _magnitudes(v).reshape(-1)
    m, n = _count(m), _count(n)
    if m >= len(data):
        raise ValueError("This value must be less than the number of data "
                         "points.")
    if m < 1 or n < 1:
        raise ValueError("predict: both counts must be at least 1")
    d = _memcof(data, m)
    window = list(data[-m:][::-1])
    out = []
    for _ in range(n):
        nxt = float(np.dot(d, window))
        window = [nxt] + window[:-1]
        out.append(nxt)
    return _join(np.array(out), unit)


# -- Least-squares B-splines: Spline2 / Binterp / DWS -----------------------
#
# ``Spline2`` returns one packed vector, whose layout the reference sheet's
# cached 79-element example pins exactly (see the schema note):
#
#     [order, m, <m+1 knots>, <m+3 coefficients>, rse, 0, DWS, ?, ?]
#
# where ``m`` is the interval count and ``rse`` is ``sqrt(SSE/(N-p))``. Only
# the knot *placement* is Mathcad's own; everything else is reproducible, and
# is reproduced here to the last bit. A call that has to place its own knots
# raises rather than guessing -- see ``mapping.UNIMPLEMENTED``.

# Prime caps the spline at cubic: a degree-4 call comes back with an
# ``order_too_big`` engine error whose argument is the cap itself.
_SPLINE2_MAX_DEGREE = 3

_SPLINE2_ADAPTIVE = (
    "Spline2 chooses its own knots here, and Mathcad's placement rule is not "
    "reproduced; pass an explicit knot vector as the last argument"
)


class _PackedSpline(np.ndarray):
    """The vector ``Spline2`` returns, carrying the units it was built from.

    It *is* an ``ndarray`` -- a worksheet indexes it (``b[1]``), measures it
    (``last(b)``) and echoes it exactly as Mathcad does. The packed layout
    mixes abscissa units (the knots) with ordinate units (the coefficients),
    so no single Pint unit can be attached to the vector itself; the two are
    carried alongside instead, and :func:`Binterp` puts them back on its
    result.
    """

    def __new__(cls, values, x_unit=None, y_unit=None):
        obj = np.asarray(values, dtype=float).view(cls)
        obj.x_unit = x_unit
        obj.y_unit = y_unit
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.x_unit = getattr(obj, "x_unit", None)
        self.y_unit = getattr(obj, "y_unit", None)


def _clamped_knots(knots, degree):
    """Mathcad's knot vector: the breakpoints with both ends repeated."""
    return np.concatenate([
        np.full(degree + 1, knots[0]),
        np.asarray(knots[1:-1], dtype=float),
        np.full(degree + 1, knots[-1]),
    ])


def _bspline_design(t, degree, xq):
    """The B-spline design matrix of the basis ``t`` evaluated at ``xq``."""
    from scipy.interpolate import BSpline

    count = len(t) - degree - 1
    design = np.empty((len(xq), count))
    for j in range(count):
        unit_coef = np.zeros(count)
        unit_coef[j] = 1.0
        design[:, j] = BSpline(t, unit_coef, degree, extrapolate=True)(xq)
    return design


def _durbin_watson_bounds(n, params, statistic):
    """The two p-values Mathcad stores after the Durbin-Watson statistic.

    They are the classical **bounds** of the Durbin-Watson test. The exact null
    distribution of the statistic depends on the design matrix, which is why
    Durbin and Watson published two design-free bounds instead: both are
    weighted sums of the eigenvalues of the difference operator,
    ``nu[j] = 2*(1 - cos(pi*j/n))``, taking the ``n - params`` smallest for the
    upper bound and the ``n - params`` largest for the lower one. Each is then
    approximated by a Beta distribution on ``[0, 4]`` matched to its own mean
    and variance -- Durbin and Watson's own approximation, and the one their
    tables were built from.

    Returns ``(upper, lower)``, in Mathcad's storage order. The upper value is
    the one the fit is judged by: it is the probability of no positive residual
    autocorrelation, so it rises towards 1 as the spline stops leaving
    structure in the residuals.
    """
    from scipy import stats

    spare = n - params
    if spare < 2:
        return float("nan"), float("nan")
    nu = 2.0 * (1.0 - np.cos(np.pi * np.arange(1, n) / n))

    def beta_cdf(eigenvalues):
        count = len(eigenvalues)
        mean = eigenvalues.sum() / count
        variance = 2.0 * (np.sum(eigenvalues ** 2)
                          - eigenvalues.sum() ** 2 / count) / (
                              count * (count + 2))
        located = mean / 4.0
        shape = located * (1.0 - located) / (variance / 16.0) - 1.0
        return float(stats.beta.cdf(statistic / 4.0, located * shape,
                                    (1.0 - located) * shape))

    return (beta_cdf(nu[:spare]),
            beta_cdf(nu[params - 1:params - 1 + spare]))


def _durbin_watson(residuals):
    """The Durbin-Watson statistic of a residual sequence."""
    return float((np.diff(residuals) ** 2).sum() / (residuals ** 2).sum())


def _spline2_knots(candidate):
    """``candidate`` read as a knot vector, or None if it is not one.

    Mathcad takes a vector fourth argument as the knots and a vector fifth
    argument always as the knots. An *unsorted* fourth argument is no knot
    vector, and Prime falls back to placing its own -- which is what the
    reference sheet's ``Spline2(x, y, n, w)`` does, echoing the same statistic
    as the three-argument ``Spline2(x, y, n)`` to all 17 digits.
    """
    if candidate is None:
        return None
    values = np.asarray(_magnitudes(candidate), dtype=float).reshape(-1)
    if values.size < 2 or np.any(np.diff(values) <= 0):
        return None
    return values


def Spline2(vx, vy, n, *rest):
    """Mathcad's least-squares B-spline fit, ``Spline2(vx, vy, n[, w][, knots])``.

    ``n`` is the spline's degree, ``w`` a vector of the ordinates' **standard
    deviations** (so the fit weight is ``1/w**2``, not ``w``), and ``knots`` the
    breakpoints. Data points that fall outside the knot range are **dropped** --
    the detail that makes every downstream number match; the reference sheet's
    knot vector stops short of ``max(x)`` by five points, and keeping them moves
    the fit by 0.2%.

    Raises when no knot vector is given: placing knots is Mathcad's own adaptive
    rule and is not reproduced here, so a fitted-looking answer would be a wrong
    one.
    """
    degree = _count(n)
    if degree > _SPLINE2_MAX_DEGREE:
        # Mathcad's own refusal: an ``order_too_big`` engine error naming 3.
        raise ValueError("The order of this spline must be no greater than 3.")
    x_unit = getattr(vx, "units", None)
    y_unit = getattr(vy, "units", None)
    xs = _magnitudes(vx).reshape(-1)
    ys = _magnitudes(vy).reshape(-1)

    sigma, knots = None, None
    if len(rest) >= 2:
        sigma, knots = rest[0], _spline2_knots(rest[1])
    elif len(rest) == 1:
        knots = _spline2_knots(rest[0])
        if knots is None:
            sigma = rest[0]
    if knots is None:
        raise NotImplementedError(_SPLINE2_ADAPTIVE)
    if x_unit is not None and hasattr(rest[-1], "to"):
        knots = np.asarray(rest[-1].to(x_unit).magnitude, dtype=float).reshape(-1)

    inside = (xs >= knots[0]) & (xs <= knots[-1])
    xf, yf = xs[inside], ys[inside]
    if sigma is None:
        scale = np.ones_like(xf)
    else:
        deviation = _magnitudes(sigma).reshape(-1)[inside]
        scale = 1.0 / deviation

    t = _clamped_knots(knots, degree)
    design = _bspline_design(t, degree, xf)
    coef, *_ = np.linalg.lstsq(design * scale[:, None], yf * scale, rcond=None)

    residuals = yf - design @ coef
    statistic = _durbin_watson(residuals * scale)
    freedom = max(len(xf) - len(coef), 1)
    packed = np.concatenate([
        [degree + 1.0, float(len(knots) - 1)],
        knots,
        coef,
        [float(np.sqrt((residuals ** 2).sum() / freedom)),
         0.0,
         statistic,
         *_durbin_watson_bounds(len(xf), len(coef), statistic)],
    ])
    return _PackedSpline(packed, x_unit, y_unit)


def _unpack_spline(b):
    """``(knot vector, coefficients, degree)`` out of a ``Spline2`` result."""
    values = np.asarray(_magnitudes(b), dtype=float).reshape(-1)
    degree = int(round(values[0])) - 1
    intervals = int(round(values[1]))
    knots = values[2:3 + intervals]
    coef = values[3 + intervals:6 + 2 * intervals]
    return _clamped_knots(knots, degree), coef, degree


def Binterp(u, b):
    """Evaluate a ``Spline2`` result at ``u``: the value and three derivatives.

    Mathcad returns four rows -- ``f``, ``f'``, ``f''``, ``f'''`` -- so the
    worksheet idiom ``Binterp(range, b)ᵀ`` gives one column per order. Outside
    the knot range the end polynomial is extended, as Mathcad does.
    """
    from scipy.interpolate import BSpline

    t, coef, degree = _unpack_spline(b)
    x_unit = getattr(b, "x_unit", None)
    y_unit = getattr(b, "y_unit", None)
    if x_unit is not None and hasattr(u, "to"):
        xq = np.asarray(u.to(x_unit).magnitude, dtype=float)
    else:
        xq = np.asarray(_magnitudes(_reduce_dimensionless(u)), dtype=float)

    spline = BSpline(t, coef, degree, extrapolate=True)
    rows = [spline(xq)]
    for order in (1, 2, 3):
        rows.append(spline.derivative(order)(xq))
    if y_unit is None:
        return np.array(rows)
    # Each successive derivative divides the ordinate unit by one more
    # abscissa unit; with no abscissa unit the whole block keeps ``y``'s.
    if x_unit is None:
        return _join(np.array(rows), y_unit)
    # Each successive derivative divides the ordinate unit by one more abscissa
    # unit, so the four rows cannot share one unit. Filling an object array
    # element by element keeps each row a Quantity; ``np.array([...])`` would
    # downcast and strip them.
    block = np.empty(len(rows), dtype=object)
    for order, row in enumerate(rows):
        block[order] = _join(row, y_unit / x_unit ** order)
    return block


def DWS(b):
    """The Durbin-Watson statistic Mathcad stored in a ``Spline2`` result.

    It is the third element from the end of the packed vector -- the reference
    sheet proves it by echoing ``DWS(b)`` and ``b[last(b) - 2]`` side by side.
    A statistic below 2 means the residuals are positively autocorrelated, i.e.
    the fit still has structure left in it.
    """
    values = np.asarray(_magnitudes(b), dtype=float).reshape(-1)
    return float(values[-3])


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


def range_sum(idx, func):
    """Mathcad's ``Σ`` over a **range variable**: ``func`` summed at every value
    of ``idx``.

    Unlike :func:`summation` (which reads written-out integer bounds) the limits
    come from the range itself, so a range with a step other than 1 -- or one
    that counts down -- sums exactly the terms Mathcad shows. Accumulates from
    the first term so a unit-bearing summand never has to be added to a bare 0.
    """
    values = np.atleast_1d(getattr(idx, "magnitude", idx)).reshape(-1)
    if len(values) == 0:
        return 0
    total_ = func(values[0])
    for value in values[1:]:
        total_ = total_ + func(value)
    return total_


# Ridders' step-shrinking ratio and table size, as in Numerical Recipes'
# ``dfridr``: each column of the Richardson tableau cancels the next order of
# the central difference's h² error series, and the extrapolation is stopped as
# soon as the estimated error starts to grow (round-off overtaking truncation).
_RIDDERS_RATIO = 1.4
_RIDDERS_STEPS = 10


def _central_difference(func, x, n, h):
    """The order-``n`` central difference of ``func`` at ``x`` with step ``h``.

    Built from the binomial form, so odd orders land on half-integer offsets and
    every order keeps the O(h²) error the Richardson extrapolation below assumes.
    """
    total_ = None
    for k in range(n + 1):
        weight = (-1) ** k * math.comb(n, k)
        term = weight * func(x + (n / 2.0 - k) * h)
        total_ = term if total_ is None else total_ + term
    return total_ / h ** n


def derivative(func, x, degree=1):
    """Mathcad's numeric derivative ``dⁿ/dxⁿ func(x)``, evaluated at ``x``.

    Ridders' method: a central difference at a shrinking step, Richardson-
    extrapolated to h -> 0, stopping when the error estimate starts to grow.
    Unit-aware -- the step is a fraction of ``x`` and carries its unit, so the
    answer comes back in ``func``'s unit divided by ``x``'s to the ``degree``.

    Being a numeric method, this agrees with Mathcad to about 1e-6 relative
    rather than to the ~1e-14 the closed-form helpers hit; the two use different
    step schedules and neither is the exact value.
    """
    n = _count(degree)
    if n == 0:
        return func(x)
    x_mag, x_unit = _split(x)
    x_mag = float(x_mag)
    scale = abs(x_mag) if x_mag != 0.0 else 1.0
    step = 0.01 * scale

    def at(value):
        return func(_join(value, x_unit))

    table = [[_central_difference(at, x_mag, n, step)]]
    best, best_error = table[0][0], math.inf
    for i in range(1, _RIDDERS_STEPS):
        step /= _RIDDERS_RATIO
        row = [_central_difference(at, x_mag, n, step)]
        factor = _RIDDERS_RATIO ** 2
        for j in range(1, i + 1):
            row.append((row[j - 1] * factor - table[i - 1][j - 1])
                       / (factor - 1.0))
            factor *= _RIDDERS_RATIO ** 2
            error = max(_error_size(row[j] - row[j - 1]),
                        _error_size(row[j] - table[i - 1][j - 1]))
            if error < best_error:
                best, best_error = row[j], error
        table.append(row)
        # Round-off has overtaken truncation: shrinking the step further only
        # makes it worse, so stop where the tableau was best.
        if _error_size(row[i] - table[i - 1][i - 1]) >= 2.0 * best_error:
            break
    # The step was differenced as a bare magnitude, so ``x``'s unit still has to
    # come off the answer -- once per order taken.
    return best if x_unit is None else best / x_unit ** n


def _error_size(difference):
    """The magnitude of a Richardson-tableau difference, as a plain float."""
    value = getattr(difference, "magnitude", difference)
    return float(abs(np.asarray(value, dtype=float).reshape(-1)[0]))


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


def logspace(start, stop, n):
    """Mathcad ``logspace(x1, x2, n)``: ``n`` points logarithmically spaced
    between the *values* ``x1`` and ``x2`` (inclusive), unlike
    ``numpy.logspace`` whose bounds are exponents.
    """
    n = int(n)
    log_lo, log_hi = math.log10(start), math.log10(stop)
    if n == 1:
        return col(start)
    step = (log_hi - log_lo) / (n - 1)
    return col(*(10 ** (log_lo + i * step) for i in range(n)))


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


def plot_trace(x, y):
    """A trace's ``(x, y)`` arrays, NaN-padded to a common length.

    Mathcad plots a trace whose two axes are *different* lengths by extending
    the shorter one with blanks -- a seeded iteration is the usual way to get
    there, since ``guess[i+1] :=`` over ``i := 0..N`` leaves ``guess`` one
    element longer than the index range plotted against it. Its cached trace
    shows this literally: ``[0,1,…,8,NaN]`` against ten values. matplotlib
    instead rejects mismatched axes, so pad here and let the NaN drop out of the
    line the same way Mathcad's blank does.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if not (x.ndim and y.ndim) or x.shape[0] == y.shape[0]:
        return x, y
    n = max(x.shape[0], y.shape[0])

    def pad(axis):
        missing = n - axis.shape[0]
        if missing == 0:
            return axis
        fill = np.full((missing,) + axis.shape[1:], np.nan)
        return np.concatenate([axis, fill])

    return pad(x), pad(y)


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
