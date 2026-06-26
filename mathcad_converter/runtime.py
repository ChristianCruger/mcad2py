"""Runtime helpers imported by generated code.

Mathcad's trig functions interpret an angle-with-units (e.g. ``37 deg``)
correctly, and a bare number as radians. Pint quantities can't be passed to
``math.tan`` directly, so these wrappers convert angle quantities to radians
first. This keeps generated code clean (``tan(phi)`` instead of
``math.tan(phi.to(ureg.radian).magnitude)``) while matching Mathcad semantics.
"""

from __future__ import annotations

import math


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
