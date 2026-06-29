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


def vectorize(value: object) -> object:
    """Mathcad's element-wise 'arrow'.

    Vectors are NumPy/Pint arrays and ``min``/``max`` map to
    ``np.minimum``/``np.maximum``, so the wrapped expression already evaluates
    element-wise -- this is an identity pass-through that keeps the operator
    visible in generated code. (A *branching* program applied to an array would
    need ``np.vectorize`` of the function; not yet handled.)
    """
    return value
