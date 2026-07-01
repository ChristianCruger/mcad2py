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


def matrix(rows: int, cols: int, *elements: object) -> object:
    """Build a genuine ``rows``x``cols`` Mathcad matrix (both > 1).

    ``elements`` arrive in Prime's own ``<ml:matrix>`` order, which is
    column-major, hence ``order="F"`` on the reshape. Unit handling mirrors
    ``col()``: Mathcad requires one consistent unit across an entire matrix
    (there's no per-column unit), so a single unit conversion covers it.
    """
    first = next((e for e in elements if hasattr(e, "units")), None)
    if first is not None:
        reg = first._REGISTRY
        unit = first.units
        mags = [
            (e.to(unit).magnitude if hasattr(e, "units") else e) for e in elements
        ]
        arr = np.array(mags, dtype=float).reshape((rows, cols), order="F")
        return reg.Quantity(arr, unit)
    return np.array(elements, dtype=float).reshape((rows, cols), order="F")


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
    if unit is None:
        if hasattr(data, "to_base_units"):
            data = data.to_base_units()
        return np.asarray(getattr(data, "magnitude", data), dtype=float)
    ratio = data / unit
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
