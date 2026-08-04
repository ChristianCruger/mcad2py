"""Static shape inference: which Mathcad ``*`` is a *matrix* product.

Mathcad writes scalar multiplication, matrix multiplication and the vector dot
product with the same ``·``. Python does not: ``a * b`` on two NumPy arrays is
element-wise, so ``M · A`` would silently produce the wrong thing. Which meaning
applies depends on the operands' *shapes*, which the XML never states -- it has
to be inferred from how each name was defined earlier in the sheet.

This pass runs once over a parsed worksheet, in region order, tracking a
``name -> kind`` environment (scalar / vector / matrix / unknown) and rewriting
every ``BinOp("mul", …)`` whose **both** operands are array-shaped into a
``Call("matmul", …)``. Anything it cannot prove is an array stays an ordinary
``*``, so the inference only ever has to be right about what it does know:

* ``M · A`` (matrix × vector) and ``B · C`` (row × column, i.e. a dot product)
  become ``matmul``;
* ``2 · identity(4)``, ``λ · R`` and ``M · kg`` -- one side a scalar or a unit --
  stay ``*``;
* nothing inside a vectorize *arrow* is rewritten: the arrow is precisely
  Mathcad's way of asking for the element-wise product.

Names bound inside a smaller scope (a function's parameters, a program's locals,
a lambda's bound variable) are masked to ``unknown`` in that scope, so a product
there is only rewritten when the operands are structurally array-shaped on their
own (a matrix literal, ``augment(...)``, a transpose, ...).
"""

from __future__ import annotations

from . import ir

SCALAR = "scalar"
VECTOR = "vector"
MATRIX = "matrix"
UNKNOWN = "unknown"

_ARRAY = frozenset((VECTOR, MATRIX))
_RANK = {SCALAR: 0, UNKNOWN: 0, VECTOR: 1, MATRIX: 2}

# Builtins whose result shape is fixed regardless of the arguments. Everything
# absent from here is ``unknown`` -- deliberately, since an unknown operand
# never triggers the rewrite.
_CALL_KINDS = {
    # -> matrix
    "identity": MATRIX,
    "augment": MATRIX,
    "stack": MATRIX,
    "matrix": MATRIX,
    "submatrix": MATRIX,
    "rref": MATRIX,
    "geninv": MATRIX,
    "eigenvecs": MATRIX,
    "genvecs": MATRIX,
    "csort": MATRIX,
    "rsort": MATRIX,
    # -> vector
    "eigenvals": VECTOR,
    "eigenvec": VECTOR,
    "genvals": VECTOR,
    "svds": VECTOR,
    "lsolve": VECTOR,
    "cross": VECTOR,
    "matrow": VECTOR,
    # The table searches all return a *vector* of results, even for one hit.
    "match": VECTOR,
    "lookup": VECTOR,
    "vlookup": VECTOR,
    "hlookup": VECTOR,
    "vhlookup": VECTOR,
    # -> scalar
    "rows": SCALAR,
    "cols": SCALAR,
    "last": SCALAR,
    "length": SCALAR,
    "det": SCALAR,
    "determinant": SCALAR,
    "tr": SCALAR,
    "rank": SCALAR,
    "mean": SCALAR,
    "norm": SCALAR,
    "norm1": SCALAR,
    "norm2": SCALAR,
    "norme": SCALAR,
    "normi": SCALAR,
    "cond1": SCALAR,
    "cond2": SCALAR,
    "conde": SCALAR,
    "condi": SCALAR,
    "IsArray": SCALAR,
    "IsScalar": SCALAR,
}

# Builtins that hand back their argument's shape.
_SHAPE_PRESERVING = frozenset(("sort", "reverse", "abs"))


def annotate_products(ws: ir.Worksheet) -> None:
    """Rewrite array products in ``ws`` in place (see the module docstring)."""
    env: dict[str, str] = {}
    for region in ws.regions:
        _visit_region(region, env)


# ---------------------------------------------------------------------------
# Region walk: rewrite the region's expressions, then record what it defines
# ---------------------------------------------------------------------------


def _visit_region(region: ir.Region, env: dict[str, str]) -> None:
    if isinstance(region, ir.Define):
        inner = _masked(env, region.params)
        region.value = _rewrite(region.value, inner, vectorized=False)
        if not region.params:
            env[region.target.py] = _kind(region.value, env)
        else:
            env[region.target.py] = UNKNOWN
    elif isinstance(region, ir.IndexAssign):
        indices = [region.index.py] + (
            [region.col_index.py] if region.col_index is not None else []
        )
        inner = dict(env)
        for name in indices:  # inside the body an index is a *scalar*
            inner[name] = SCALAR
        region.value = _rewrite(region.value, inner, vectorized=False)
        env[region.target.py] = MATRIX if region.col_index is not None else VECTOR
    elif isinstance(region, ir.MultiAssign):
        region.value = _rewrite(region.value, env, vectorized=False)
        for target in region.targets:
            env[target.py] = SCALAR
    elif isinstance(region, ir.ComboBoxAssign):
        region.values = [_rewrite(v, env, vectorized=False) for v in region.values]
        for target in region.targets:
            env[target.py] = SCALAR
    elif isinstance(region, ir.Evaluate):
        region.value = _rewrite(region.value, env, vectorized=False)
    elif isinstance(region, ir.StatusControl):
        region.value = _rewrite(region.value, env, vectorized=False)
    elif isinstance(region, ir.SolveBlock):
        inner = _masked(env, region.params + [u.py for u in region.unknowns])
        for guess in region.guesses:
            guess.value = _rewrite(guess.value, inner, vectorized=False)
        for constraint in region.constraints:
            constraint.lhs = _rewrite(constraint.lhs, inner, vectorized=False)
            constraint.rhs = _rewrite(constraint.rhs, inner, vectorized=False)
        for target in region.targets:
            env[target.py] = UNKNOWN
    elif isinstance(region, ir.Plot):
        for trace in region.traces:
            trace.x = _rewrite(trace.x, env, vectorized=False)
            trace.y = _rewrite(trace.y, env, vectorized=False)
    elif isinstance(region, ir.GridPlot):
        region.expr = _rewrite(region.expr, env, vectorized=False)


def _masked(env: dict[str, str], names: list[str]) -> dict[str, str]:
    """A copy of ``env`` with locally-bound ``names`` hidden."""
    if not names:
        return env
    inner = dict(env)
    for name in names:
        inner[name] = UNKNOWN
    return inner


# ---------------------------------------------------------------------------
# Kind inference
# ---------------------------------------------------------------------------


def _kind(node: ir.Expr, env: dict[str, str]) -> str:
    if isinstance(node, ir.Name):
        return env.get(node.py, UNKNOWN)
    if isinstance(node, ir.MatrixLiteral):
        return MATRIX if node.rows > 1 and node.cols > 1 else VECTOR
    if isinstance(node, ir.Range):
        return VECTOR
    if isinstance(node, ir.MatCol):
        return VECTOR
    if isinstance(node, (ir.Index, ir.Index2D, ir.Number, ir.UnitRef, ir.Str)):
        return SCALAR
    if isinstance(node, ir.Quantity):
        return _kind(node.value, env)
    if isinstance(node, (ir.Transpose, ir.Vectorize, ir.UnaryOp)):
        return _kind(node.operand, env)
    if isinstance(node, ir.Root):
        return _kind(node.operand, env)
    if isinstance(node, ir.VectorSum):
        return SCALAR
    if isinstance(node, ir.Call):
        return _call_kind(node, env)
    if isinstance(node, ir.BinOp):
        if node.op == "div":
            return _kind(node.left, env)
        if node.op in ("add", "sub", "mul"):
            left, right = _kind(node.left, env), _kind(node.right, env)
            return left if _RANK[left] >= _RANK[right] else right
        return SCALAR
    return UNKNOWN


def _call_kind(node: ir.Call, env: dict[str, str]) -> str:
    if node.func == "matmul":  # already rewritten (a nested product)
        left = _kind(node.args[0], env)
        right = _kind(node.args[1], env)
        return MATRIX if MATRIX in (left, right) else VECTOR
    if node.func == "diag":
        # Mathcad's ``diag`` inverts its argument: a vector becomes a diagonal
        # matrix, a matrix's diagonal becomes a vector.
        arg = _kind(node.args[0], env) if node.args else UNKNOWN
        if arg == MATRIX:
            return VECTOR
        if arg == VECTOR:
            return MATRIX
        return UNKNOWN
    if node.func in _SHAPE_PRESERVING:
        return _kind(node.args[0], env) if node.args else UNKNOWN
    return _CALL_KINDS.get(node.func, UNKNOWN)


# ---------------------------------------------------------------------------
# Rewrite
# ---------------------------------------------------------------------------

# Single-expression attributes per node type, for the generic descent. Optional
# ones (``Root.degree``, ``Range.step``) may be None and are skipped.
_EXPR_FIELDS: dict[type, tuple[str, ...]] = {
    ir.Quantity: ("value", "unit"),
    ir.BinOp: ("left", "right"),
    ir.UnaryOp: ("operand",),
    ir.Root: ("operand", "degree"),
    ir.Equation: ("lhs", "rhs"),
    ir.Parens: ("inner",),
    ir.Index: ("base", "index"),
    ir.Index2D: ("base", "row", "col"),
    ir.MatCol: ("base", "index"),
    ir.VectorSum: ("operand",),
    ir.Vectorize: ("operand",),
    ir.Transpose: ("operand",),
    ir.Range: ("start", "stop", "step"),
    ir.Lambda: ("body",),
    ir.Integral: ("func", "lower", "upper"),
    ir.Summation: ("func", "lower", "upper"),
}


def _rewrite(node: ir.Expr, env: dict[str, str], *, vectorized: bool) -> ir.Expr:
    """Rewrite array products inside ``node``, returning the (possibly new) node.

    ``vectorized`` is True underneath a vectorize arrow, where Mathcad's ``·``
    means the element-wise product and must stay a plain ``*``.
    """
    if isinstance(node, ir.Vectorize):
        node.operand = _rewrite(node.operand, env, vectorized=True)
        return node

    if isinstance(node, ir.Lambda):
        node.body = _rewrite(node.body, _masked(env, node.params), vectorized=vectorized)
        return node

    if isinstance(node, ir.ProgramBlock):
        inner = _masked(env, _local_names(node))
        for stmt in node.statements:
            _rewrite_stmt(stmt, inner, vectorized=vectorized)
        return node

    if isinstance(node, ir.Program):
        node.branches = [
            (
                None if test is None else _rewrite(test, env, vectorized=vectorized),
                _rewrite(result, env, vectorized=vectorized),
            )
            for test, result in node.branches
        ]
        return node

    if isinstance(node, ir.Call):
        node.args = [_rewrite(a, env, vectorized=vectorized) for a in node.args]
        return node

    if isinstance(node, ir.MatrixLiteral):
        node.elements = [
            _rewrite(e, env, vectorized=vectorized) for e in node.elements
        ]
        return node

    for field in _EXPR_FIELDS.get(type(node), ()):
        child = getattr(node, field)
        if child is not None:
            setattr(node, field, _rewrite(child, env, vectorized=vectorized))

    if (
        isinstance(node, ir.BinOp)
        and node.op == "mul"
        and not vectorized
        and _kind(node.left, env) in _ARRAY
        and _kind(node.right, env) in _ARRAY
    ):
        return ir.Call(func="matmul", args=[node.left, node.right])
    return node


def _rewrite_stmt(stmt: ir.Stmt, env: dict[str, str], *, vectorized: bool) -> None:
    if isinstance(stmt, ir.LocalAssign):
        stmt.value = _rewrite(stmt.value, env, vectorized=vectorized)
    elif isinstance(stmt, ir.ForLoop):
        stmt.iterable = _rewrite(stmt.iterable, env, vectorized=vectorized)
        _rewrite(stmt.body, env, vectorized=vectorized)
    elif isinstance(stmt, ir.IfStmt):
        stmt.branches = [
            (
                None if test is None else _rewrite(test, env, vectorized=vectorized),
                body,
            )
            for test, body in stmt.branches
        ]
        for _test, body in stmt.branches:
            _rewrite(body, env, vectorized=vectorized)
    elif isinstance(stmt, ir.Return):
        stmt.value = _rewrite(stmt.value, env, vectorized=vectorized)
    elif isinstance(stmt, ir.TryCatch):
        _rewrite(stmt.body, env, vectorized=vectorized)
        _rewrite(stmt.handler, env, vectorized=vectorized)


def _local_names(block: ir.ProgramBlock) -> list[str]:
    """Names a program binds locally (``←`` assignments and loop variables)."""
    names: list[str] = []

    def scan(b: ir.ProgramBlock) -> None:
        for stmt in b.statements:
            if isinstance(stmt, ir.LocalAssign):
                target = stmt.target
                base = target.base if isinstance(target, (ir.Index, ir.Index2D)) else target
                if isinstance(base, ir.Name):
                    names.append(base.py)
            elif isinstance(stmt, ir.ForLoop):
                names.append(stmt.var.py)
                scan(stmt.body)
            elif isinstance(stmt, ir.IfStmt):
                for _test, body in stmt.branches:
                    scan(body)
            elif isinstance(stmt, ir.TryCatch):
                scan(stmt.body)
                scan(stmt.handler)

    scan(block)
    return names
