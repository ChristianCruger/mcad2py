"""Mappings from Mathcad names/operators to Python.

Kept as plain data so it is easy to extend as new sample worksheets surface
unmapped builtins or units.
"""

from __future__ import annotations

# Mathcad operator tag (local name) -> canonical IR op name.
OPERATOR_TAGS = {
    "plus": "add",
    "minus": "sub",
    "mult": "mul",
    "div": "div",
    "pow": "pow",
    "neg": "neg",
    # Comparisons (used in program tests, e.g. ``e < epsilon_c2``).
    "lessThan": "lt",
    "greaterThan": "gt",
    "lessOrEqual": "le",
    "greaterOrEqual": "ge",
    "equal": "eq",
    # Boolean connectives (program tests, e.g. ``rho <= x and revne = "Ja"``).
    "and": "and_",
    "or": "or_",
}

# Canonical op -> (python infix symbol, precedence). Higher binds tighter.
BINARY_OPS = {
    "or_": ("or", -2),
    "and_": ("and", -1),
    "lt": ("<", 0),
    "gt": (">", 0),
    "le": ("<=", 0),
    "ge": (">=", 0),
    "eq": ("==", 0),
    "add": ("+", 1),
    "sub": ("-", 1),
    "mul": ("*", 2),
    "div": ("/", 2),
    "pow": ("**", 4),
}
UNARY_PREC = 3

# Mathcad builtin functions -> Python expression for the callable.
# Trig functions resolve to angle-aware helpers from mcad2py.runtime
# (imported by name into the generated module), so they appear bare here.
FUNCTIONS = {
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "cot": "cot",
    "asin": "math.asin",
    "acos": "math.acos",
    "atan": "math.atan",
    "exp": "math.exp",
    "ln": "math.log",
    "log": "math.log10",
    # ``** 0.5`` via a runtime helper so a unit-bearing radicand keeps its unit
    # (Pint), unlike ``math.sqrt`` which rejects a dimensioned argument.
    "sqrt": "sqrt",
    "abs": "abs",
    "length": "len",
    # Dimensionless-aware runtime helpers (Mathcad reduces e.g. l/s to a pure
    # number before rounding; Pint keeps it as m/mm, so these reduce first).
    "ceil": "ceil",
    "floor": "floor",
    "round": "mround",
    # Element-wise (2-arg) min/max so they broadcast over arrays under a
    # vectorize 'arrow'; ``np.minimum``/``np.maximum`` also work on scalars.
    "min": "np.minimum",
    "max": "np.maximum",
    # Build a matrix by stacking column vectors side by side (unit-aware).
    "augment": "augment",
}

# Runtime helpers that are *called by name* in generated code (so a Call to one
# triggers its import): the angle-aware trig wrappers, ``linterp`` (Mathcad's
# linear interpolation, which reorders args and is unit-aware), and
# ``CreateMesh`` (a 3D-plot grid builder) -- see runtime.py.
RUNTIME_IMPORTS = (
    "sin", "cos", "tan", "cot", "linterp", "CreateMesh", "augment",
    "ceil", "floor", "mround", "sqrt", "nth_root", "power", "disp", "elementwise",
    "mc_min", "mc_max",
)

# Mathcad symbolic command keyword (first id of a <ml:command> sequence) ->
# SymPy callable. Symbolic regions emit ``<callable>(expr, *args)``.
SYMBOLIC_COMMANDS = {
    "solve": "solve",
    "simplify": "simplify",
    "factor": "factor",
    "expand": "expand",
}

# Mathcad constants -> Python expression.
CONSTANTS = {
    "π": "math.pi",
    "pi": "math.pi",
    "e": "math.e",
    "∞": "math.inf",
}

# Greek letters -> ASCII transliteration for Python identifiers (matches the
# convention in the hand-written reference output: β -> beta, ϕ -> phi, ...).
GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda_", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "ς": "sigma", "τ": "tau",
    "υ": "upsilon", "φ": "phi", "ϕ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Α": "Alpha", "Β": "Beta", "Γ": "Gamma", "Δ": "Delta", "Θ": "Theta",
    "Λ": "Lambda", "Π": "Pi", "Σ": "Sigma", "Φ": "Phi", "Ω": "Omega",
}

# Mathcad unit name -> Pint unit attribute, where they differ. Default is to
# use the Mathcad name verbatim (Pint knows MPa, kN, deg, mm, ...).
UNIT_ALIASES: dict[str, str] = {
    # e.g. "tonne": "metric_ton",  -- add as samples reveal mismatches
}


def unit_attr(name: str) -> str:
    """Pint attribute for a Mathcad unit name."""
    return UNIT_ALIASES.get(name, name)
