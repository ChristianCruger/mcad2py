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
    # Boolean connectives (program tests, e.g. ``rho <= x and crack = "Yes"``).
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
    # Trigonometric: the forward ones read an angle (deg/rad) and the inverse
    # ones return bare radians, as Mathcad does. ``atan2``/``angle`` take their
    # arguments as (x, y) -- the reverse of Python's ``math.atan2``.
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "cot": "cot",
    "sec": "sec",
    "csc": "csc",
    "sinc": "sinc",
    "asin": "asin",
    "acos": "acos",
    "atan": "atan",
    "acot": "acot",
    "asec": "asec",
    "acsc": "acsc",
    "atan2": "atan2",
    "angle": "angle",
    # Hyperbolic: the argument is a pure number; an angle reduces to radians.
    "sinh": "sinh",
    "cosh": "cosh",
    "tanh": "tanh",
    "coth": "coth",
    "sech": "sech",
    "csch": "csch",
    "asinh": "asinh",
    "acosh": "acosh",
    "atanh": "atanh",
    "acoth": "acoth",
    "asech": "asech",
    "acsch": "acsch",
    "exp": "math.exp",
    # ``ln``/``log`` are runtime helpers (not bare ``math.log``/``math.log10``):
    # Mathcad returns a *complex* value for a negative argument
    # (``ln(-3) = ln(3) + iπ``) rather than raising -- only ``ln(0)`` is a
    # genuine Mathcad domain error, which ``math.log(0)`` also raises on.
    # ``log`` also takes an optional explicit base (``log(x, b)``).
    "ln": "ln",
    "log": "log",
    # ``ln0``: natural log, but ``ln0(0)`` returns a large negative number
    # instead of raising (Mathcad's own domain-error avoidance for x=0).
    "ln0": "ln0",
    # n logarithmically spaced points between two *values* (not exponents,
    # unlike ``numpy.logspace``).
    "logspace": "logspace",
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
    # --- Vector & matrix builtins (all runtime helpers; see runtime.py) ------
    # Shape / structure
    "augment": "augment",
    "stack": "stack",
    "rows": "rows",
    "cols": "cols",
    "last": "last",
    "identity": "identity",
    "diag": "diag",
    "submatrix": "submatrix",
    "matrix": "matrix",
    # Linear algebra
    "det": "det",
    "tr": "tr",
    "lsolve": "lsolve",
    "geninv": "geninv",
    "rank": "rank",
    "rref": "rref",
    "cross": "cross",
    # Norms & condition numbers
    "norm": "norm",
    "norm1": "norm1",
    "norm2": "norm2",
    "norme": "norme",
    "normi": "normi",
    "cond1": "cond1",
    "cond2": "cond2",
    "conde": "conde",
    "condi": "condi",
    # Eigen / singular values
    "eigenvals": "eigenvals",
    "eigenvec": "eigenvec",
    "eigenvecs": "eigenvecs",
    "genvals": "genvals",
    "genvecs": "genvecs",
    "svds": "svds",
    # Ordering, reduction, predicates
    "sort": "sort",
    "reverse": "reverse",
    "csort": "csort",
    "rsort": "rsort",
    "mean": "mean",
    "IsArray": "IsArray",
    "IsScalar": "IsScalar",
    # Table search
    "match": "match",
    "lookup": "lookup",
    "vlookup": "vlookup",
    "hlookup": "hlookup",
    "vhlookup": "vhlookup",
    # --- Statistics (all runtime helpers; see runtime.py) -------------------
    # Note the capitalisation: Mathcad's ``var``/``stdev`` divide by n (the
    # population forms) and ``Var``/``Stdev`` by n-1 (the sample forms).
    "median": "median",
    "mode": "mode",
    "gmean": "gmean",
    "hmean": "hmean",
    "var": "var",
    "Var": "Var",
    "stdev": "stdev",
    "Stdev": "Stdev",
    "skew": "skew",
    "kurt": "kurt",
    "percentile": "percentile",
    "Rank": "Rank",
    "histogram": "histogram",
    "hist": "histogram",
    # Regression, correlation and hypothesis tests
    "cvar": "cvar",
    "corr": "corr",
    "slope": "slope",
    "intercept": "intercept",
    "Ftest": "Ftest",
    "Spear": "Spear",
    "kendltau": "kendltau",
    "kendltau2": "kendltau2",
    "contingtbl": "contingtbl",
    # Distributions: d = density, p = cumulative, q = quantile, r = random draws
    "dnorm": "dnorm",
    "pnorm": "pnorm",
    "qnorm": "qnorm",
    "rnorm": "rnorm",
    "dt": "dt",
    "pt": "pt",
    "qt": "qt",
    "rt": "rt",
    "dweibull": "dweibull",
    "pweibull": "pweibull",
    "qweibull": "qweibull",
    "rweibull": "rweibull",
}

# Mathcad symbolic command keyword (first id of a <ml:command> sequence) ->
# SymPy callable. Symbolic regions emit ``<callable>(expr, *args)``.
SYMBOLIC_COMMANDS = {
    "solve": "solve",
    "simplify": "simplify",
    "factor": "factor",
    "expand": "expand",
}

# Mathcad constants -> Python expression. Keyed by the *display* name and only
# consulted for an id Prime labelled CONSTANT, so a worksheet's own ``c``, ``g``
# or ``R`` (all labelled VARIABLE) is untouched.
#
# The physics set is Prime's built-in "Constants" label (see
# references/Constants.mcdx). Values are the CODATA/SI numbers Prime itself
# caches, written in **base SI units** rather than the friendlier compound ones
# (``h`` as ``kg·m²/s``, not ``J·s``): a display override on such a constant is a
# pure numeric scale (``10⁻³⁴ kg·m²/s``), and ``disp`` renders that by *dividing*
# -- which only reduces to a plain number when the two agree unit-for-unit.
CONSTANTS = {
    "π": "math.pi",
    "pi": "math.pi",
    "e": "math.e",
    # Mathcad's ∞ is really 10³⁰⁷ (that is what result.xml caches); math.inf is
    # the faithful reading of what the symbol *means*, and the one that behaves
    # as an integration limit or a comparison bound.
    "∞": "math.inf",
    "γ": "0.5772156649015329",  # Euler-Mascheroni
    # -- physics -----------------------------------------------------------
    "c": "(299792458 * ureg.m / ureg.s)",  # speed of light
    "g": "(9.80665 * ureg.m / ureg.s**2)",  # standard gravity
    "e_c": "(1.602176634e-19 * ureg.coulomb)",  # elementary charge
    "h": "(6.62607015e-34 * ureg.kg * ureg.m**2 / ureg.s)",  # Planck
    "ℏ": "(1.054571817e-34 * ureg.kg * ureg.m**2 / ureg.s)",  # reduced Planck
    "k": "(1.380649e-23 * ureg.kg * ureg.m**2 / (ureg.s**2 * ureg.K))",  # Boltzmann
    "m_u": "(1.66053906892e-27 * ureg.kg)",  # atomic mass unit
    "N_A": "(6.02214076e23 / ureg.mol)",  # Avogadro
    "R": "(8.314462618 * ureg.kg * ureg.m**2 / (ureg.s**2 * ureg.K * ureg.mol))",  # gas
    "R_∞": "(10973731.56816 / ureg.m)",  # Rydberg
    "α": "0.0072973525643",  # fine-structure
    "ε_0": "(8.8541878188e-12 * ureg.A**2 * ureg.s**4 / (ureg.kg * ureg.m**3))",
    "μ_0": "(1.25663706127e-6 * ureg.kg * ureg.m / (ureg.s**2 * ureg.A**2))",
    "σ": "(5.670374419e-8 * ureg.kg / (ureg.s**3 * ureg.K**4))",  # Stefan-Boltzmann
    "Φ_0": "(2.067833848e-15 * ureg.weber)",  # magnetic flux quantum
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
    # Mathcad's percent is a *unit* -- dimensionless, worth 0.01 -- so ``50%``
    # is a scale apply like ``50 mm``. Pint spells it ``percent``.
    "%": "percent",
    # e.g. "tonne": "metric_ton",  -- add as samples reveal mismatches
}


def unit_attr(name: str) -> str:
    """Pint attribute for a Mathcad unit name."""
    return UNIT_ALIASES.get(name, name)
