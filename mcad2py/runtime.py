"""Runtime helpers imported by generated code.

Mathcad's trig functions interpret an angle-with-units (e.g. ``37 deg``)
correctly, and a bare number as radians. Pint quantities can't be passed to
``math.tan`` directly, so these wrappers convert angle quantities to radians
first. This keeps generated code clean (``tan(phi)`` instead of
``math.tan(phi.to(ureg.radian).magnitude)``) while matching Mathcad semantics.
"""

from __future__ import annotations

import math

import numpy as np


def _radians(x: object) -> float:
    """Coerce ``x`` to a float number of radians.

    Accepts a plain number (already radians, per Mathcad) or a Pint quantity
    carrying an angle/dimensionless unit (e.g. ``deg``, ``rad``).
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


def col(*elements: object) -> object:
    """Build a 1-D vector (a Mathcad column/row vector) from scalar elements.

    When the elements carry Pint units the result is a Pint ``Quantity`` array
    (so units survive and ``.to(...)`` works on the whole vector); otherwise it
    is a plain NumPy array. Either way it indexes, broadcasts, and ``len()``
    like a Mathcad vector.
    """
    first = next((e for e in elements if hasattr(e, "units")), None)
    if first is not None:
        # Build the array in the *elements'* registry (not a globally imported
        # one) so it stays compatible with the rest of the generated module.
        reg = first._REGISTRY
        unit = first.units
        mags = [
            (e.to(unit).magnitude if hasattr(e, "units") else e) for e in elements
        ]
        return reg.Quantity(np.array(mags, dtype=float), unit)
    return np.array(elements)


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


def solve_block(residual, guesses):
    """Numeric solve block (Mathcad Given/Find) via ``scipy.optimize.fsolve``.

    ``guesses`` are the seed values of the unknowns (Pint quantities or plain
    numbers); ``residual`` takes the unknowns (units reattached) and returns the
    constraint residuals (``lhs - rhs``). All Pint bookkeeping lives here:
    unknowns are solved as bare magnitudes in their guess units, residuals are
    compared in base units, and the solution is returned with units restored --
    so generated code can pass quantities straight through.
    """
    from scipy.optimize import fsolve

    units = [getattr(g, "units", None) for g in guesses]
    x0 = [
        float(g.magnitude) if u is not None else float(g)
        for g, u in zip(guesses, units)
    ]

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

    solution = np.atleast_1d(fsolve(_wrapped, x0))
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
    if unit is None:
        if hasattr(data, "to_base_units"):
            data = data.to_base_units()
        return np.asarray(getattr(data, "magnitude", data), dtype=float)
    ratio = data / unit
    return np.asarray(getattr(ratio, "magnitude", ratio), dtype=float)


def vectorize(value: object) -> object:
    """Mathcad's element-wise 'arrow'.

    Vectors are NumPy/Pint arrays and ``min``/``max`` map to
    ``np.minimum``/``np.maximum``, so the wrapped expression already evaluates
    element-wise -- this is an identity pass-through that keeps the operator
    visible in generated code. (A *branching* program applied to an array would
    need ``np.vectorize`` of the function; not yet handled.)
    """
    return value
