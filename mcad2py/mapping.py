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
}

# Canonical op -> (python infix symbol, precedence). Higher binds tighter.
BINARY_OPS = {
    "add": ("+", 1),
    "sub": ("-", 1),
    "mul": ("*", 2),
    "div": ("/", 2),
    "pow": ("**", 4),
}
UNARY_PREC = 3

# Mathcad builtin functions -> Python expression for the callable.
# Trig functions resolve to angle-aware helpers from mathcad_converter.runtime
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
    "sqrt": "math.sqrt",
    "abs": "abs",
}

# Trig helpers that must be imported from the runtime into generated code.
RUNTIME_IMPORTS = ("sin", "cos", "tan", "cot")

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
