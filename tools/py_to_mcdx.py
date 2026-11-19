#!/usr/bin/env python3
"""Proof of concept: build a new ``.mcdx`` from the Python mcad2py emits.

    python tools/py_to_mcdx.py sheet.py -o sheet.mcdx
    python tools/recalc_mcdx.py sheet.mcdx          # let Prime fill result.xml

The input is the *flat* dialect ``mcad2py convert -f py`` writes:

* ``name = expr``                       -> a definition ``name := expr``
* ``print(name)`` / ``print(disp(name[, unit]))`` straight after it
                                         -> that definition also shows ``=``
* ``print(expr)`` on its own             -> an evaluation ``expr =``
* a block of ``# comment`` lines         -> a text region, one paragraph per line
* a figure, ``_fig, _ax = ...`` to ``plt.show()``
                                         -> an xy, contour or 3D plot; only the
                                            lines carrying math are read
* imports and the module docstring       -> skipped

A comment *after* code on the same line (``# mcdx region 3`` from
``--trace-source``) is not text and is ignored.

Also: programs (``def``), ranges, matrices, Σ/∫/d/dx (``summation``,
``range_sum``, ``integral``, ``double_integral``, ``derivative``), difference
equations (``vec_set`` seeds and ``_recur_`` loops), ``a, b = tuple(V)``,
solve blocks (``solve_block`` with its ``_residuals_`` function, also inside a
``def``), bare calls (``Seed(1)``), the constants of ``math`` and ``mcad2py.const``, and
codegen's ``try`` guard around a region Mathcad could not compute (dropped:
Prime finds the error again). Everything else is refused, naming the line.

The new names a sheet defines are turned back into Mathcad names by a fixed
rule (``sigma_c`` -> ``σ`` with subscript ``c``), because ``sanitize()`` has
no inverse. ``result.xml`` is written empty: Prime computes on open.
"""

from __future__ import annotations

import argparse
import ast
import io
import itertools
import sys
import tokenize
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcad2py import ir  # noqa: E402
from mcad2py.emit import mcdx_backend as mb  # noqa: E402
from mcad2py.mapping import CONSTANTS, FUNCTIONS, GREEK, UNIT_ALIASES  # noqa: E402


class Refused(Exception):
    pass


# ---------------------------------------------------------------------------
# Python -> IR
# ---------------------------------------------------------------------------

# Python transliteration -> Greek letter. First entry wins (σ, not ς; φ, not ϕ).
_GREEK_BACK: dict[str, str] = {}
for _ch, _py in GREEK.items():
    _GREEK_BACK.setdefault(_py.rstrip("_"), _ch)

# Generated Python call head -> Mathcad builtin name.
_FUNC_BACK: dict[str, str] = {}
for _mc, _py in FUNCTIONS.items():
    if isinstance(_py, str):
        _FUNC_BACK.setdefault(_py, _mc)
_FUNC_BACK.update({"math.exp": "exp", "math.log": "ln", "math.sqrt": "sqrt"})

_UNIT_BACK = {py: mc for mc, py in UNIT_ALIASES.items()}

# Name imported from mcad2py.const -> Mathcad's display name (``hbar`` -> ℏ).
_CONST_BACK: dict[str, str] = {}
for _mc, _py in CONSTANTS.items():
    if "." not in _py:
        _CONST_BACK.setdefault(_py, _mc)

# Runtime helpers that are *codegen idioms*, not Mathcad builtins: each one
# stands for an operator or a region shape, so a same-name call would be wrong.
_IDIOMS = {
    "disp", "index_build", "index_build_2d", "vec_set", "elementwise", "solve_block",
    "integral", "summation", "range_sum", "derivative", "sample", "plot_domain",
    "plot_axis", "plot_trace", "nth_root", "power", "col", "matrix", "arange",
    "matelem", "matcol", "transpose", "vectorize", "total", "matmul", "mc_min",
    "mc_max", "determinant", "cross",
}


def _runtime_names() -> set[str]:
    import mcad2py.runtime as runtime  # noqa: PLC0415
    return {n for n in dir(runtime)
            if not n.startswith("_") and callable(getattr(runtime, n))} - _IDIOMS


_RUNTIME_SAME_NAME = _runtime_names()

# Calls the parser makes from an operator element rather than a named builtin.
_OPERATOR_CALLS = {"matrow": "matrow", "abs": "absval", "determinant": "determinant",
                   "cross": "crossProduct", "math.factorial": "factorial", "xor": "xor"}

_OPS = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div", ast.Pow: "pow"}


def mathcad_name(py: str) -> str:
    """``sigma_c`` -> ``σ_c``: the inverse of sanitize() by convention."""
    # A trailing ``_`` is sanitize()'s guard against a Python keyword or
    # builtin (``lambda_``, ``range_``); Mathcad cannot end a name in one.
    py = py.rstrip("_")
    first, dunder, rest = py.partition("__")
    if dunder and first in _GREEK_BACK:
        # ``lambda__0``: the Greek head took a ``_`` guard (``lambda`` is a
        # keyword) before the subscript separator was added.
        py = f"{first}_{rest}"
    head, sep, sub = py.partition("_")
    head = _GREEK_BACK.get(head, head)
    return head + sep + sub


_CMP = {ast.Lt: "lt", ast.Gt: "gt", ast.LtE: "le", ast.GtE: "ge", ast.Eq: "eq",
        ast.NotEq: "ne"}


class Reader:
    def __init__(self, text: str):
        self.text = text
        # Python name -> Mathcad name of every user function defined so far.
        # A call to one is labelled VARIABLE, which is how Prime tells it from
        # a builtin.
        self.functions: dict[str, str] = {}
        # Names the module imports from mcad2py.const: Mathcad's built-in
        # constants, labelled CONSTANT rather than VARIABLE.
        self.constants = {
            alias.name for node in ast.parse(text).body
            if isinstance(node, ast.ImportFrom) and node.module == "mcad2py.const"
            for alias in node.names}

    def expr(self, node: ast.expr) -> ir.Expr:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return ir.Str(node.value)
        if isinstance(node, ast.Compare):
            # ``a <= e < b`` is Mathcad's chained comparison, which the parser
            # reads left-nested: ((a <= e) < b).
            left = self.expr(node.left)
            for op, right in zip(node.ops, node.comparators):
                if type(op) not in _CMP:
                    break
                left = ir.BinOp(op=_CMP[type(op)], left=left, right=self.expr(right))
            else:
                return left
        if isinstance(node, ast.BoolOp):
            op = "and_" if isinstance(node.op, ast.And) else "or_"
            out = self.expr(node.values[0])
            for v in node.values[1:]:
                out = ir.BinOp(op=op, left=out, right=self.expr(v))
            return out
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return ir.UnaryOp(op="not_", operand=self.expr(node.operand))
        if isinstance(node, ast.IfExp):
            # ``a if c else b`` is a one-line Mathcad program.
            branches = [(self.expr(node.test), self.expr(node.body))]
            rest = node.orelse
            while isinstance(rest, ast.IfExp):
                branches.append((self.expr(rest.test), self.expr(rest.body)))
                rest = rest.orelse
            branches.append((None, self.expr(rest)))
            return ir.Program(branches=branches)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in self.functions and not node.keywords):
            return ir.Call(func=node.func.id, args=[self.expr(a) for a in node.args],
                           role="VARIABLE")
        if (isinstance(node, ast.Constant) and isinstance(node.value, complex)
                and node.value.real == 0):
            # ``2j``: Mathcad's imaginary literal ``2i``.
            return ir.Number(ast.get_source_segment(self.text, node) or repr(node.value))
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return ir.Number(ast.get_source_segment(self.text, node) or repr(node.value))
        if isinstance(node, ast.Name):
            if node.id in self.constants and node.id in _CONST_BACK:
                return ir.Name(py=node.id, original=_CONST_BACK[node.id], role="CONSTANT")
            return ir.Name(py=node.id, original=mathcad_name(node.id))
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "ureg":
                return ir.UnitRef(_UNIT_BACK.get(node.attr, node.attr))
            if ast.unparse(node) == "math.pi":
                return ir.Name(py="pi", original="π", role="CONSTANT")
            if ast.unparse(node) == "math.e":
                return ir.Name(py="e", original="e", role="CONSTANT")
            if ast.unparse(node) == "math.inf":
                return ir.Name(py="inf", original="∞", role="CONSTANT")
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            op = _OPS[type(node.op)]
            left, right = self.expr(node.left), self.expr(node.right)
            if op == "mul" and isinstance(left, ir.Number) and isinstance(right, ir.UnitRef):
                return ir.Quantity(value=left, unit=right)
            return ir.BinOp(op=op, left=left, right=right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = self.expr(node.operand)
            if isinstance(inner, ir.Number) and not inner.value.startswith("-"):
                return ir.Number("-" + inner.value)
            return ir.UnaryOp(op="neg", operand=inner)
        if isinstance(node, ast.Subscript) and not isinstance(node.slice, ast.Tuple):
            return ir.Index(base=self.expr(node.value), index=self.expr(node.slice))
        if isinstance(node, ast.Call) and not node.keywords:
            head = ast.unparse(node.func)
            if head == "matrix" and node.args and all(
                    isinstance(a, ast.List) for a in node.args):
                rows = [[self.expr(e) for e in a.elts] for a in node.args]
                if len({len(r) for r in rows}) != 1:
                    raise Refused(f"line {node.lineno}: a matrix with ragged rows")
                # IR elements are column-major, as Prime stores them.
                return ir.MatrixLiteral(rows=len(rows), cols=len(rows[0]),
                                        elements=[r[j] for j in range(len(rows[0]))
                                                  for r in rows])
            if (operator := self.calculus(head, node)) is not None:
                return operator
            args = [self.expr(a) for a in node.args]
            if head == "col" and args:
                return ir.MatrixLiteral(rows=len(args), cols=1, elements=args)
            if head == "arange" and len(args) == 3:
                step = args[2]
                if isinstance(step, ir.Number) and step.value == "1":
                    step = None  # the implicit step: ``1 .. n``
                return ir.Range(start=args[0], stop=args[1], step=step)
            if head == "matelem" and len(args) == 3:
                return ir.Index2D(base=args[0], row=args[1], col=args[2])
            if head == "matcol" and len(args) == 2:
                return ir.MatCol(base=args[0], index=args[1])
            if head == "transpose" and len(args) == 1:
                return ir.Transpose(operand=args[0])
            if head == "vectorize" and len(args) == 1:
                return ir.Vectorize(operand=args[0])
            if head == "total" and len(args) == 1:
                return ir.VectorSum(operand=args[0])
            if head == "matmul" and len(args) == 2:
                # The shape pass's split of Mathcad's one ``·``; undo it.
                return ir.BinOp(op="mul", left=args[0], right=args[1])
            if head in ("mc_min", "mc_max"):
                return ir.Call(func=head[3:], args=args)
            if head in ("determinant", "cross", "math.factorial", "xor", "element_of"):
                return ir.Call(func=head, args=args)
            if head == "nth_root" and len(args) == 2:
                degree = args[1]
                square = isinstance(degree, ir.Number) and degree.value == "2"
                return ir.Root(operand=args[0], degree=None if square else degree)
            if head == "power" and len(args) == 2:
                return ir.BinOp(op="pow", left=args[0], right=args[1])
            if head in _FUNC_BACK:
                return ir.Call(func=_FUNC_BACK[head], args=args)
            if head in _RUNTIME_SAME_NAME:
                # A builtin with no FUNCTIONS entry keeps its Mathcad name.
                return ir.Call(func=head, args=args)
        raise Refused(f"line {node.lineno}: {ast.unparse(node)!r} is outside the subset")

    def lambda_(self, node: ast.expr, arity: int) -> ir.Lambda:
        if not (isinstance(node, ast.Lambda) and len(node.args.args) == arity):
            raise Refused(f"line {node.lineno}: expected a lambda of {arity} parameter(s)")
        return ir.Lambda(params=[a.arg for a in node.args.args], body=self.expr(node.body))

    def calculus(self, head: str, node: ast.Call) -> ir.Expr | None:
        """The operators codegen writes as a call on a lambda: Σ, ∫, d/dx."""
        args = node.args
        if head == "range_sum" and len(args) == 2:
            # ``range_sum(i, lambda i: E)``: Σ over a range variable, no bounds.
            return ir.RangeSum(func=self.lambda_(args[1], 1))
        if head in ("summation", "integral") and len(args) == 3:
            cls = ir.Summation if head == "summation" else ir.Integral
            return cls(func=self.lambda_(args[0], 1), lower=self.expr(args[1]),
                       upper=self.expr(args[2]))
        if head == "double_integral" and len(args) == 5:
            # codegen folds ∫∫ into one call; Mathcad nests two ∫, inner first.
            fn = args[0]
            if not (isinstance(fn, ast.Lambda) and len(fn.args.args) == 2):
                raise Refused(f"line {node.lineno}: double_integral needs a 2-argument lambda")
            inner_var, outer_var = (a.arg for a in fn.args.args)
            inner = ir.Integral(func=ir.Lambda(params=[inner_var], body=self.expr(fn.body)),
                                lower=self.expr(args[1]), upper=self.expr(args[2]))
            return ir.Integral(func=ir.Lambda(params=[outer_var], body=inner),
                               lower=self.expr(args[3]), upper=self.expr(args[4]))
        if head == "derivative" and len(args) == 3:
            func = self.lambda_(args[0], 1)
            if ast.unparse(args[1]) != func.params[0]:
                raise Refused(f"line {node.lineno}: derivative must be taken at its own variable")
            return ir.Derivative(func=func, var=func.params[0], degree=self.expr(args[2]))
        return None

    def program(self, fn: ast.FunctionDef) -> ir.Expr:
        return ProgramReader(self).read(fn)

    def shown(self, stmt: ast.stmt) -> tuple[ir.Expr, ir.Expr | None] | None:
        """``print(x)`` / ``print(disp(x[, unit]))`` -> (x, unit)."""
        if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                and ast.unparse(stmt.value.func) == "print" and len(stmt.value.args) == 1):
            return None
        arg = stmt.value.args[0]
        if isinstance(arg, ast.Call) and ast.unparse(arg.func) == "disp":
            unit = self.expr(arg.args[1]) if len(arg.args) > 1 else None
            return self.expr(arg.args[0]), unit
        if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                and arg.func.attr == "to" and len(arg.args) == 1):
            return self.expr(arg.func.value), self.expr(arg.args[0])
        return self.expr(arg), None


def comment_blocks(text: str) -> list[tuple[int, list[str]]]:
    """``(first line, [paragraph, ...])`` for each run of whole-line comments.

    A run ends at a blank line or at code, which is how the backends separate
    one text region from the next. A comment that shares its line with code is
    an annotation, not text.
    """
    blocks: list[tuple[int, list[str]]] = []
    last_line = -2
    code_lines: set[int] = set()
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    for tok in tokens:
        if tok.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                            tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
            code_lines.update(range(tok.start[0], tok.end[0] + 1))
    for tok in tokens:
        if tok.type != tokenize.COMMENT or tok.start[0] in code_lines:
            continue
        line = tok.start[0]
        body = tok.string[1:].removeprefix(" ").rstrip()
        if blocks and line == last_line + 1:
            blocks[-1][1].append(body)
        else:
            blocks.append((line, [body]))
        last_line = line
    return [(line, paras) for line, paras in blocks if any(p.strip() for p in paras)]


def expr_text(node: ir.Expr) -> str:
    from mcad2py.emit.codegen import expr_to_str  # noqa: PLC0415
    return expr_to_str(node)


def index_build(reader: Reader, stmt: ast.stmt) -> ir.IndexAssign | None:
    """``X = index_build(i, lambda i: expr)`` -> Mathcad ``X[i] := expr``.

    The two-subscript ``index_build_2d(i, j, lambda i, j: expr)`` is ``X[i, j]``.
    """
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Call)):
        return None
    call = stmt.value
    head = ast.unparse(call.func)
    arity = {"index_build": 1, "index_build_2d": 2}.get(head)
    if arity is None or len(call.args) != arity + 1:
        return None
    indices, fn = call.args[:arity], call.args[arity]
    params = [a.arg for a in fn.args.args] if isinstance(fn, ast.Lambda) else []
    if not (all(isinstance(x, ast.Name) for x in indices)
            and params == [x.id for x in indices]):
        raise Refused(f"line {stmt.lineno}: {head} must take a lambda over its own "
                      "range variables")
    names = [reader.expr(x) for x in indices]
    return ir.IndexAssign(target=reader.expr(stmt.targets[0]), index=names[0],
                          value=reader.expr(fn.body),
                          col_index=names[1] if arity == 2 else None)


def is_elementwise_line(stmt: ast.stmt) -> bool:
    return (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and ast.unparse(stmt.value) == f"elementwise({stmt.targets[0].id})")


class ProgramReader:
    """A ``def`` body -> Mathcad program IR (the inverse of codegen's two forms).

    ``_program_def`` prints a single if/elif chain whose branches each return
    one value, with a final bare ``return`` for the else: that is an
    :class:`ir.Program`. Anything else is an imperative
    :class:`ir.ProgramBlock`.
    """

    def __init__(self, reader: Reader):
        self.r = reader

    def read(self, fn: ast.FunctionDef) -> ir.Expr:
        body = list(fn.body)
        # ``X = None`` pre-declares a name the block builds with vec_set.
        while (body and isinstance(body[0], ast.Assign)
               and isinstance(body[0].value, ast.Constant) and body[0].value.value is None):
            body.pop(0)
        chain = self.if_chain(body)
        if chain is not None:
            return ir.Program(branches=chain)
        return self.block(body, fn.lineno)

    def if_chain(self, body: list[ast.stmt]):
        if not body or not isinstance(body[0], ast.If) or len(body) > 2:
            return None
        if len(body) == 2 and not isinstance(body[1], ast.Return):
            return None
        branches = []
        node: ast.stmt | None = body[0]
        while isinstance(node, ast.If):
            if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
                return None
            branches.append((self.r.expr(node.test), self.r.expr(node.body[0].value)))
            if not node.orelse:
                node = None
            elif len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                node = node.orelse[0]
            else:
                return None  # an ``else:`` block is the statement form
        if len(body) == 2:
            branches.append((None, self.r.expr(body[1].value)))
        return branches

    def block(self, stmts: list[ast.stmt], line: int) -> ir.ProgramBlock:
        if len(stmts) == 1 and isinstance(stmts[0], ast.Pass):
            stmts = []
        return ir.ProgramBlock(statements=[self.stmt(s) for s in stmts])

    def stmt(self, s: ast.stmt) -> ir.Stmt:
        r = self.r
        if isinstance(s, ast.Assign) and len(s.targets) == 1:
            target, value = s.targets[0], s.value
            if (isinstance(value, ast.Call) and isinstance(target, ast.Name)
                    and ast.unparse(value.func) in ("vec_set", "col_set")
                    and len(value.args) == 3 and ast.unparse(value.args[0]) == target.id):
                base = r.expr(target)
                where, new = value.args[1], r.expr(value.args[2])
                if ast.unparse(value.func) == "col_set":
                    return ir.LocalAssign(target=ir.MatCol(base=base, index=r.expr(where)),
                                          value=new)
                if isinstance(where, ast.Tuple) and len(where.elts) == 2:
                    return ir.LocalAssign(
                        target=ir.Index2D(base=base, row=r.expr(where.elts[0]),
                                          col=r.expr(where.elts[1])), value=new)
                return ir.LocalAssign(target=ir.Index(base=base, index=r.expr(where)),
                                      value=new)
            if isinstance(target, ast.Name):
                return ir.LocalAssign(target=r.expr(target), value=r.expr(value))
        if isinstance(s, ast.For) and isinstance(s.target, ast.Name) and not s.orelse:
            return ir.ForLoop(var=r.expr(s.target), iterable=r.expr(s.iter),
                              body=self.block(s.body, s.lineno))
        if isinstance(s, ast.If):
            branches = []
            node: ast.stmt = s
            while True:
                branches.append((r.expr(node.test), self.block(node.body, node.lineno)))
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    node = node.orelse[0]
                    continue
                if node.orelse:
                    branches.append((None, self.block(node.orelse, node.lineno)))
                break
            return ir.IfStmt(branches=branches)
        if isinstance(s, ast.Return) and s.value is not None:
            return ir.Return(value=r.expr(s.value))
        if isinstance(s, ast.Expr):
            return ir.ExprStmt(value=r.expr(s.value))
        if (isinstance(s, ast.Try) and len(s.handlers) == 1 and not s.orelse
                and not s.finalbody):
            return ir.TryCatch(body=self.block(s.body, s.lineno),
                               handler=self.block(s.handlers[0].body, s.lineno))
        raise Refused(f"line {s.lineno}: {ast.unparse(s)[:60]!r} has no Mathcad "
                      "program form")


def _call_named(node: ast.AST, head: str) -> bool:
    return isinstance(node, ast.Call) and ast.unparse(node.func) == head


def plot_block(reader: Reader, body: list[ast.stmt], i: int):
    """The statements of one figure -> ``(Plot | GridPlot, index of plt.show())``.

    codegen writes a figure as a fixed run of statements ending in
    ``plt.show()``. Only the lines that carry the plot's math are read; the
    styling lines around them are codegen's own and say nothing about the sheet.
    """
    stmt = body[i]
    implicit = None
    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and stmt.targets[0].id.startswith("_domain_")
            and _call_named(stmt.value, "plot_domain")):
        # A plot of a variable the sheet never defines: Mathcad invents it.
        bounds = [ast.literal_eval(a) for a in stmt.value.args]
        implicit = (stmt.targets[0].id, bounds)
        i += 1
        stmt = body[i]
    grid = (isinstance(stmt, ast.Assign)
            and ast.unparse(stmt.targets[0]) == "(_X, _Y, _Z, _kind)"
            and _call_named(stmt.value, "resolve_plot_grid"))
    if not grid and ast.unparse(stmt) != "_fig, _ax = plt.subplots()":
        if implicit:
            raise Refused(f"line {stmt.lineno}: plot_domain() not followed by a plot")
        return None
    end = i
    while end < len(body) and ast.unparse(body[end]) != "plt.show()":
        end += 1
    if end == len(body):
        raise Refused(f"line {stmt.lineno}: a figure with no plt.show()")
    block = body[i:end]
    region = grid_plot(reader, block) if grid else xy_plot(reader, block, implicit)
    return region, end


def xy_plot(reader: Reader, block: list[ast.stmt], implicit) -> ir.Plot:
    domain_var = implicit[0] if implicit else None

    def axis(node: ast.expr) -> tuple[ir.Expr, ir.Expr | None]:
        if not (_call_named(node, "plot_axis") and len(node.args) == 2):
            raise Refused(f"line {node.lineno}: a plot axis is not plot_axis(data, unit)")
        data, unit = node.args
        unit_ir = (None if isinstance(unit, ast.Constant) and unit.value is None
                   else reader.expr(unit))
        if isinstance(data, ast.Name) and data.id == domain_var:
            name = data.id.removeprefix("_domain_")
            return ir.Name(py=name, original=mathcad_name(name)), unit_ir
        if _call_named(data, "sample") and isinstance(data.args[0], ast.Lambda):
            # ``sample(lambda x: E, x)`` is E evaluated over the domain.
            return reader.expr(data.args[0].body), unit_ir
        if _call_named(data, "static_axis"):
            return reader.expr(data.args[0]), unit_ir
        return reader.expr(data), unit_ir

    traces = []
    for s in block:
        if not (isinstance(s, ast.Expr) and _call_named(s.value, "_ax.plot")):
            continue
        call = s.value
        pair = call.args[0].value if isinstance(call.args[0], ast.Starred) else None
        if not (_call_named(pair, "plot_trace") and len(pair.args) == 2):
            raise Refused(f"line {s.lineno}: a trace is not plot_trace(x, y)")
        (x, xu), (y, yu) = axis(pair.args[0]), axis(pair.args[1])
        color = next((ast.literal_eval(k.value) for k in call.keywords
                      if k.arg == "color"), None)
        traces.append(ir.PlotTrace(x=x, y=y, x_unit=xu, y_unit=yu, color=color))
    if not traces:
        raise Refused(f"line {block[0].lineno}: a figure with no traces")
    limits = None
    if implicit and tuple(implicit[1][:2]) != (-10.0, 10.0):
        limits = (float(implicit[1][0]), float(implicit[1][1]))
    return ir.Plot(traces=traces, x_limits=limits)


def grid_plot(reader: Reader, block: list[ast.stmt]) -> ir.GridPlot:
    value = block[0].value.args[0]
    mesh = None
    if (_call_named(value, "mesh_grid") and len(value.args) == 3
            and isinstance(value.args[0], ast.Lambda)):
        # ``mesh_grid(lambda x, y: E, x, y)`` is E over the two ranges' grid.
        mesh = tuple(ast.unparse(a) for a in value.args[1:])
        expr = reader.expr(value.args[0].body)
    else:
        expr = reader.expr(value)
    z_unit = None
    for s in block:
        if (isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "(_Xs, _Ys, _Zs)"
                and isinstance(s.value, ast.Tuple)):
            unit = s.value.elts[2].args[1] if len(s.value.elts[2].args) > 1 else None
            if unit is not None and not (isinstance(unit, ast.Constant) and unit.value is None):
                z_unit = reader.expr(unit)
    threed = any(ast.unparse(s) == "_ax = _fig.add_subplot(projection='3d')" for s in block)
    return ir.GridPlot(expr=expr, z_unit=z_unit, mesh_names=mesh, threed=threed)


# codegen's guard around a region Mathcad itself could not compute.
_GUARD_HANDLER = "print('error:', _err)"
_GUARD_NOTE = "Mathcad reports an error here:"


def unguard(body: list[ast.stmt]) -> list[ast.stmt]:
    """``try: <region> except Exception as _err: print('error:', _err)`` -> the
    region. The guard only exists because Mathcad cached an error there; Prime
    will find the same error again when it calculates."""
    out: list[ast.stmt] = []
    for s in body:
        if (isinstance(s, ast.Try) and len(s.handlers) == 1 and not s.orelse
                and not s.finalbody
                and "\n".join(ast.unparse(h) for h in s.handlers[0].body) == _GUARD_HANDLER):
            out.extend(s.body)
        else:
            out.append(s)
    return out


def _vec_set(stmt: ast.stmt) -> tuple[str, ast.expr, ast.expr, ast.expr] | None:
    """``X = vec_set(src, idx, value)`` -> (X, src, idx, value)."""
    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name) and _call_named(stmt.value, "vec_set")
            and len(stmt.value.args) == 3):
        return (stmt.targets[0].id, *stmt.value.args)
    return None


def _is_step(stmt: ast.stmt) -> bool:
    return (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and ast.unparse(stmt.targets[0]) == "_step")


def recurrence_writes(reader: Reader, stmts: list[ast.stmt]):
    """One step of a difference equation -> (targets, value, values).

    Several targets are staged through ``_step`` so they update together:
    ``_step = (a, b)`` is a matrix right-hand side, ``_step = tuple(V)`` one
    vector expression spread over the targets.
    """
    value, values = None, None
    writes = stmts
    if writes and _is_step(writes[0]):
        step, writes = writes[0].value, writes[1:]
        if isinstance(step, ast.Tuple):
            values = [reader.expr(e) for e in step.elts]
        elif _call_named(step, "tuple") and len(step.args) == 1:
            value = reader.expr(step.args[0])
        else:
            raise Refused(f"line {step.lineno}: an unknown _step form")
    targets = []
    for n, s in enumerate(writes):
        got = _vec_set(s)
        if got is None:
            raise Refused(f"line {s.lineno}: a difference equation writes with vec_set only")
        name, _src, idx, val = got
        base = ir.Name(py=name, original=mathcad_name(name))
        if isinstance(idx, ast.Tuple) and len(idx.elts) == 2:
            targets.append(ir.ElementTarget(base=base, index=reader.expr(idx.elts[0]),
                                            col=reader.expr(idx.elts[1])))
        else:
            targets.append(ir.ElementTarget(base=base, index=reader.expr(idx)))
        if value is None and values is None:
            value = reader.expr(val)
        elif ast.unparse(val) != f"_step[{n}]":
            raise Refused(f"line {s.lineno}: expected _step[{n}]")
    if not targets:
        raise Refused("a difference equation with no writes")
    return targets, value, values


def recurrence_def(reader: Reader, fn: ast.FunctionDef, call: ast.stmt | None):
    """``def _recur_X(_idx, X): for i in _idx: ...`` + ``X = _recur_X(i, X)``."""
    loop = fn.body[0] if len(fn.body) == 2 else None
    if not (isinstance(loop, ast.For) and isinstance(loop.target, ast.Name)
            and isinstance(call, ast.Assign) and _call_named(call.value, fn.name)):
        raise Refused(f"line {fn.lineno}: an unknown difference-equation shape")
    index = call.value.args[0]
    if ast.unparse(index) != loop.target.id:
        raise Refused(f"line {fn.lineno}: the loop must run over its own range variable")
    targets, value, values = recurrence_writes(reader, loop.body)
    return ir.Recurrence(targets=targets, value=value, values=values,
                         index=reader.expr(index))


def multi_assign(reader: Reader, stmt: ast.stmt) -> ir.MultiAssign | None:
    """``a, b, c = tuple(V)`` -> ``[a; b; c] := V``; ``tuple(unpack(M))`` is a
    matrix of names."""
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Tuple)
            and all(isinstance(e, ast.Name) for e in stmt.targets[0].elts)
            and _call_named(stmt.value, "tuple") and len(stmt.value.args) == 1):
        return None
    names = [reader.expr(e) for e in stmt.targets[0].elts]
    value = stmt.value.args[0]
    matrix_target = _call_named(value, "unpack")
    if matrix_target:
        value = value.args[0]
    return ir.MultiAssign(targets=names, value=reader.expr(value),
                          matrix_target=matrix_target)


def _solve_call(node: ast.expr | None):
    """``solve_block(_residuals_X, [u, v])`` -> (residual name, [u, v])."""
    if (_call_named(node, "solve_block") and len(node.args) == 2
            and isinstance(node.args[0], ast.Name) and isinstance(node.args[1], ast.List)
            and all(isinstance(e, ast.Name) for e in node.args[1].elts)):
        return node.args[0].id, [e.id for e in node.args[1].elts]
    return None


def residuals(reader: Reader, fn: ast.FunctionDef, unknowns: list[str]) -> list[ir.Equation]:
    """``def _residuals_X(_x): u, v = _x; return [lhs - (rhs), ...]`` -> the
    constraints ``lhs = rhs``. codegen brackets the right side, so it is
    always the right operand of the outermost minus."""
    if not (len(fn.body) == 2 and isinstance(fn.body[0], ast.Assign)
            and ast.unparse(fn.body[0].value) == "_x"
            and [e.id for e in getattr(fn.body[0].targets[0], "elts", [])] == unknowns
            and isinstance(fn.body[1], ast.Return) and isinstance(fn.body[1].value, ast.List)):
        raise Refused(f"line {fn.lineno}: an unknown residual function shape")
    out = []
    for item in fn.body[1].value.elts:
        if not (isinstance(item, ast.BinOp) and isinstance(item.op, ast.Sub)):
            raise Refused(f"line {item.lineno}: a residual is not lhs - (rhs)")
        out.append(ir.Equation(lhs=reader.expr(item.left), rhs=reader.expr(item.right)))
    return out


def solve_function(reader: Reader, fn: ast.FunctionDef) -> ir.SolveBlock | None:
    """``def f(a, b): <guesses>; def _residuals_x...; return solve_block(...)[0]``
    -> ``f(a, b) := find(x)`` inside a solve block."""
    last = fn.body[-1] if fn.body else None
    ret = last.value if isinstance(last, ast.Return) else None
    if isinstance(ret, ast.Subscript) and ast.unparse(ret.slice) == "0":
        ret = ret.value
    found = _solve_call(ret)
    if found is None:
        return None
    resid_name, unknowns = found
    guesses, resid = [], None
    for s in fn.body[:-1]:
        if isinstance(s, ast.FunctionDef) and s.name == resid_name:
            resid = s
        elif (isinstance(s, ast.Assign) and len(s.targets) == 1
              and isinstance(s.targets[0], ast.Name) and s.targets[0].id in unknowns):
            guesses.append(ir.Define(target=reader.expr(s.targets[0]),
                                     value=reader.expr(s.value)))
        else:
            raise Refused(f"line {s.lineno}: unexpected inside a solve-block function")
    if resid is None:
        raise Refused(f"line {fn.lineno}: no residual function")
    name = ir.Name(py=fn.name, original=mathcad_name(fn.name))
    reader.functions[fn.name] = name.original
    return ir.SolveBlock(guesses=guesses, constraints=residuals(reader, resid, unknowns),
                         unknowns=[reader.expr(ast.Name(id=u)) for u in unknowns],
                         targets=[name], params=[a.arg for a in fn.args.args])


def _shows_all(stmt: ast.stmt | None, names: list[ir.Name]) -> bool:
    """``print([a, b, c])``: codegen's echo of a multi-assignment."""
    return stmt is not None and ast.unparse(stmt) == (
        f"print([{', '.join(n.py for n in names)}])")


def read_python(text: str) -> list[ir.Region]:
    tree = ast.parse(text)
    reader = Reader(text)
    body = [s for s in tree.body if not isinstance(s, (ast.Import, ast.ImportFrom))]
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # docstring
    body = unguard(body)
    texts = [(line, paras) for line, paras in comment_blocks(text)
             if not all(p.startswith(_GUARD_NOTE) for p in paras)]
    regions: list[ir.Region] = []
    i = 0
    while i < len(body) or texts:
        if texts and (i >= len(body) or texts[0][0] < body[i].lineno):
            _line, paras = texts.pop(0)
            regions.append(ir.TextRegion(text="\n".join(paras)))
            continue
        stmt = body[i]
        if (plot := plot_block(reader, body, i)) is not None:
            region, i = plot
            regions.append(region)
        elif (built := index_build(reader, stmt)) is not None:
            nxt = reader.shown(body[i + 1]) if i + 1 < len(body) else None
            # A 1-D build echoes ``X[i]``; a 2-D one echoes the whole matrix.
            echo = (built.target.py if built.col_index is not None
                    else f"{built.target.py}[{built.index.py}]")
            if nxt and expr_text(nxt[0]) == echo:
                built.evaluate, built.display_unit = True, nxt[1]
                i += 1
            regions.append(built)
        elif is_elementwise_line(stmt):
            pass  # ``f = elementwise(f)``: Mathcad's vectorize arrow implies it
        elif (isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant)
                and stmt.value.value is None):
            pass  # ``X = None``: codegen's declaration before a difference equation
        elif (isinstance(stmt, ast.FunctionDef) and stmt.name.startswith("_residuals_")
                and i + 1 < len(body)):
            # The guesses came just before, and were read as plain definitions.
            nxt = body[i + 1]
            call = nxt.value if isinstance(nxt, ast.Assign) else None
            single = isinstance(call, ast.Subscript) and ast.unparse(call.slice) == "0"
            found = _solve_call(call.value if single else call)
            if found is None or found[0] != stmt.name:
                raise Refused(f"line {stmt.lineno}: a residual function with no solve_block")
            unknowns = found[1]
            guesses: list[ir.Define] = []
            while (regions and isinstance(regions[-1], ir.Define) and not regions[-1].params
                   and regions[-1].target.py in unknowns
                   and regions[-1].target.py not in [g.target.py for g in guesses]):
                guesses.insert(0, regions.pop())
            target_node = nxt.targets[0]
            names = target_node.elts if isinstance(target_node, ast.Tuple) else [target_node]
            block = ir.SolveBlock(guesses=guesses,
                                  constraints=residuals(reader, stmt, unknowns),
                                  unknowns=[reader.expr(ast.Name(id=u)) for u in unknowns],
                                  targets=[reader.expr(n) for n in names])
            i += 1
            after = body[i + 1] if i + 1 < len(body) else None
            shown = reader.shown(after) if after is not None and len(names) == 1 else None
            if shown and isinstance(shown[0], ir.Name) and shown[0].py == block.targets[0].py:
                block.evaluate, block.display_unit = True, shown[1]
                i += 1
            elif len(names) > 1 and _shows_all(after, block.targets):
                block.evaluate = True
                i += 1
            regions.append(block)
        elif (isinstance(stmt, ast.FunctionDef) and not stmt.name.startswith("_")
                and (solved := solve_function(reader, stmt)) is not None):
            regions.append(solved)
        elif isinstance(stmt, ast.FunctionDef) and stmt.name.startswith("_recur_"):
            nxt = body[i + 1] if i + 1 < len(body) else None
            regions.append(recurrence_def(reader, stmt, nxt))
            i += 1
        elif _is_step(stmt) or _vec_set(stmt) is not None:
            # A seed: ``X[0] := 30``, or several slots from one vector at once.
            run = [stmt]
            if _is_step(stmt):
                while i + 1 < len(body) and _vec_set(body[i + 1]) is not None:
                    i += 1
                    run.append(body[i])
            targets, value, values = recurrence_writes(reader, run)
            regions.append(ir.Recurrence(targets=targets, value=value, values=values))
        elif (multi := multi_assign(reader, stmt)) is not None:
            nxt = body[i + 1] if i + 1 < len(body) else None
            if _shows_all(nxt, multi.targets):
                multi.evaluate = True
                i += 1
            regions.append(multi)
        elif isinstance(stmt, ast.FunctionDef):
            name = stmt.name
            nxt = body[i + 1] if i + 1 < len(body) else None
            if (not stmt.args.args and name.startswith("_") and isinstance(nxt, ast.Assign)
                    and isinstance(nxt.targets[0], ast.Tuple)
                    and ast.unparse(nxt.value) == f"tuple({name}())"):
                # A program returning a vector, spread over several names.
                multi = ir.MultiAssign(targets=[reader.expr(e) for e in nxt.targets[0].elts],
                                       value=reader.program(stmt))
                i += 1
                after = body[i + 1] if i + 1 < len(body) else None
                if _shows_all(after, multi.targets):
                    multi.evaluate = True
                    i += 1
                regions.append(multi)
            elif (not stmt.args.args and name.startswith("_") and isinstance(nxt, ast.Assign)
                    and ast.unparse(nxt) == f"{name[1:]} = {name}()"):
                # A nullary helper: ``x := <program>`` for a plain variable.
                target = reader.expr(ast.Name(id=name[1:]))
                define = ir.Define(target=target, value=reader.program(stmt))
                i += 1
                shown = reader.shown(body[i + 1]) if i + 1 < len(body) else None
                if shown and isinstance(shown[0], ir.Name) and shown[0].py == target.py:
                    define.evaluate, define.display_unit = True, shown[1]
                    i += 1
                regions.append(define)
            else:
                target = ir.Name(py=name, original=mathcad_name(name))
                reader.functions[name] = target.original
                params = [a.arg for a in stmt.args.args]
                regions.append(ir.Define(target=target, value=reader.program(stmt),
                                         params=params))
        elif (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Lambda)):
            fn = stmt.value
            if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.defaults:
                raise Refused(f"line {stmt.lineno}: only plain positional parameters")
            name = stmt.targets[0].id
            target = ir.Name(py=name, original=mathcad_name(name))
            reader.functions[name] = target.original  # also for a recursive body
            regions.append(ir.Define(target=target, value=reader.expr(fn.body),
                                     params=[a.arg for a in fn.args.args]))
        elif (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)):
            target = reader.expr(stmt.targets[0])
            define = ir.Define(target=target, value=reader.expr(stmt.value))
            nxt = reader.shown(body[i + 1]) if i + 1 < len(body) else None
            if nxt and isinstance(nxt[0], ir.Name) and nxt[0].py == target.py:
                define.evaluate, define.display_unit = True, nxt[1]
                i += 1
            regions.append(define)
        elif (shown := reader.shown(stmt)) is not None:
            regions.append(ir.Evaluate(value=shown[0], display_unit=shown[1]))
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            # A bare call such as ``Seed(1)``: Mathcad runs it and shows nothing.
            regions.append(ir.Statement(value=reader.expr(stmt.value)))
        else:
            raise Refused(f"line {stmt.lineno}: {ast.unparse(stmt)[:60]!r} is not a "
                          "definition or an evaluation")
        i += 1
    return regions


# ---------------------------------------------------------------------------
# IR -> math50 (the stage-A writer, plus calls, roots and constants)
# ---------------------------------------------------------------------------


_LOGIC_TAGS = {"lt": "lessThan", "gt": "greaterThan", "le": "lessOrEqual",
               "ge": "greaterOrEqual", "eq": "equal", "ne": "notEqual",
               "and_": "and", "or_": "or"}


class Writer(mb._Writer):
    def __init__(self, ids, functions: dict[str, str] | None = None):
        super().__init__(ids)
        self.functions = functions or {}

    def unit(self, name):
        # ``label-is-contextual`` lets Prime pick the label itself, and where
        # the sheet also has a variable of the same name (``m``, ``s``) it
        # picks the variable. Prime's own files label a unit explicitly.
        return explicit(super().unit(name))

    def identifier(self, original, role):
        # The same for a built-in constant: ``R`` is the gas constant and
        # also a unit, and a contextual label leaves Prime unable to choose.
        xml = super().identifier(original, role)
        return explicit(xml) if role == "CONSTANT" else xml

    def binop(self, node):
        tag = _LOGIC_TAGS.get(node.op)
        if tag is None:
            return super().binop(node)
        prec = mb.BINARY_OPS[node.op][1]
        left = self.wrap(node.left, prec, parent_op=node.op)
        right = self.wrap(node.right, prec, tighter=True, parent_op=node.op)
        return f"<ml:apply><ml:{tag} />{left}{right}</ml:apply>", prec

    def emit(self, node):
        if isinstance(node, ir.Str):
            return f"<ml:str>{mb._escape(node.value)}</ml:str>", mb.ATOM_PREC
        if isinstance(node, ir.UnaryOp) and node.op == "not_":
            return self.apply("not", node.operand)
        if isinstance(node, ir.Program):
            return self.if_xml(node.branches, block=False), mb.ATOM_PREC
        if isinstance(node, ir.ProgramBlock):
            return self.block(node), mb.ATOM_PREC
        if isinstance(node, ir.Call) and node.role == "VARIABLE":
            name = ir.Name(py=node.func, original=self.functions.get(
                node.func, mathcad_name(node.func)))
            head = self.identifier(name.original, "VARIABLE")
            args = [self.emit(a)[0] for a in node.args]
            inner = args[0] if len(args) == 1 else f"<ml:sequence>{''.join(args)}</ml:sequence>"
            return f"<ml:apply>{head}{inner}</ml:apply>", mb.ATOM_PREC
        if (isinstance(node, ir.Call) and node.func == "element_of"
                and isinstance(node.args[1], ir.Str)):
            # The number set is a bare, unlabelled id: ℤ, ℝ, ℚ, ℂ, ℕ.
            num_set = f'<ml:id xml:space="preserve">{mb._escape(node.args[1].value)}</ml:id>'
            return (f"<ml:apply><ml:elementOf />{self.emit(node.args[0])[0]}{num_set}</ml:apply>",
                    mb.ATOM_PREC)
        if isinstance(node, ir.Number) and node.value.endswith("j"):
            return f'<ml:imag symbol="i">{mb._number(node.value[:-1])}</ml:imag>', mb.ATOM_PREC
        if isinstance(node, ir.Call) and node.func in _OPERATOR_CALLS:
            return self.apply(_OPERATOR_CALLS[node.func], *node.args)
        if isinstance(node, ir.Call):
            head = mb.ID_TEMPLATE.format(role="FUNCTION", body=mb._escape(node.func))
            args = [self.emit(a)[0] for a in node.args]
            inner = args[0] if len(args) == 1 else f"<ml:sequence>{''.join(args)}</ml:sequence>"
            return f"<ml:apply>{head}{inner}</ml:apply>", mb.ATOM_PREC
        if isinstance(node, ir.Root):
            degree = "<ml:placeholder />" if node.degree is None else self.emit(node.degree)[0]
            return (f"<ml:apply><ml:nthRoot />{degree}{self.emit(node.operand)[0]}</ml:apply>",
                    mb.ATOM_PREC)
        if isinstance(node, ir.MatrixLiteral):
            cells = "".join(self.emit(e)[0] for e in node.elements)
            return (f'<ml:matrix rows="{node.rows}" cols="{node.cols}">{cells}</ml:matrix>',
                    mb.ATOM_PREC)
        if isinstance(node, ir.Range):
            start, stop = self.emit(node.start)[0], self.emit(node.stop)[0]
            if node.step is None:
                return f"<ml:range>{start}{stop}</ml:range>", mb.ATOM_PREC
            # Mathcad states a step as the *second* value, ``a, a + s .. b``; the
            # parser turned that into ``s = next - a``, so undo it when it can.
            step = node.step
            if (isinstance(step, ir.BinOp) and step.op == "sub"
                    and expr_text(step.right) == expr_text(node.start)):
                nxt = step.left
            else:
                nxt = ir.BinOp(op="add", left=node.start, right=step)
            return (f"<ml:range><ml:sequence>{start}{self.emit(nxt)[0]}</ml:sequence>"
                    f"{stop}</ml:range>", mb.ATOM_PREC)
        if isinstance(node, ir.Index):
            return self.apply("indexer", node.base, node.index)
        if isinstance(node, ir.Index2D):
            seq = f"<ml:sequence>{self.emit(node.row)[0]}{self.emit(node.col)[0]}</ml:sequence>"
            return (f"<ml:apply><ml:indexer />{self.emit(node.base)[0]}{seq}</ml:apply>",
                    mb.ATOM_PREC)
        if isinstance(node, ir.MatCol):
            return self.apply("matcol", node.base, node.index)
        if isinstance(node, ir.Transpose):
            return self.apply("transpose", node.operand)
        if isinstance(node, ir.Vectorize):
            return self.apply("vectorize", node.operand)
        if isinstance(node, (ir.Summation, ir.Integral, ir.RangeSum, ir.Derivative)):
            tag = {ir.Summation: "summation", ir.Integral: "integral",
                   ir.RangeSum: "summation", ir.Derivative: "derivative"}[type(node)]
            func = node.func
            bound = "".join(self.identifier(mathcad_name(p), "VARIABLE") for p in func.params)
            parts = [f"<ml:lambda><ml:boundVars>{bound}</ml:boundVars>"
                     f"{self.emit(func.body)[0]}</ml:lambda>"]
            if isinstance(node, ir.Derivative):
                parts.append(f"<ml:degree>{self.emit(node.degree)[0]}</ml:degree>")
            elif isinstance(node, ir.RangeSum):
                parts.append("<ml:upperBound><ml:placeholder /></ml:upperBound>")
            else:
                parts.append(f"<ml:lowerBound>{self.emit(node.lower)[0]}</ml:lowerBound>"
                             f"<ml:upperBound>{self.emit(node.upper)[0]}</ml:upperBound>")
            # These operators extend to the right in Prime, so give them the
            # precedence of ``+``: an operand then gets the group it needs.
            return (f"<ml:apply><ml:{tag} />{''.join(parts)}</ml:apply>",
                    mb.BINARY_OPS["add"][1])
        if isinstance(node, ir.VectorSum):
            # A bare Σ: no bound variable, no bounds.
            return ("<ml:apply><ml:summation /><ml:lambda><ml:boundVars><ml:placeholder />"
                    f"</ml:boundVars>{self.emit(node.operand)[0]}</ml:lambda>"
                    "<ml:upperBound><ml:placeholder /></ml:upperBound></ml:apply>",
                    mb.ATOM_PREC)
        return super().emit(node)

    # -- programs ---------------------------------------------------------

    def if_xml(self, branches, *, block: bool) -> str:
        """``<ml:if>`` with ``<ml:elseif>``/``<ml:else>`` inside it.

        ``block`` says each branch body is a ProgramBlock (the statement form)
        rather than one value expression.
        """
        def body(value):
            inner = self.block_lines(value) if block else self.emit(value)[0]
            return f"<ml:program>{inner}</ml:program>"

        out = []
        for i, (test, value) in enumerate(branches):
            if test is None:
                out.append(f"<ml:else>{body(value)}</ml:else>")
                continue
            arm = (f"<ml:test>{self.emit(test)[0]}</ml:test>"
                   f"<ml:then>{body(value)}</ml:then>")
            out.append(arm if i == 0 else f"<ml:elseif>{arm}</ml:elseif>")
        return f"<ml:if>{''.join(out)}</ml:if>"

    def block(self, block: ir.ProgramBlock) -> str:
        return f"<ml:program>{self.block_lines(block)}</ml:program>"

    def block_lines(self, block: ir.ProgramBlock) -> str:
        stmts = block.statements
        if not stmts:
            return "<ml:placeholder />"
        return "".join(self.stmt(s, last=s is stmts[-1]) for s in stmts)

    def stmt(self, s: ir.Stmt, *, last: bool) -> str:
        if isinstance(s, ir.LocalAssign):
            return (f"<ml:localDefine>{self.emit(s.target)[0]}{self.emit(s.value)[0]}"
                    "</ml:localDefine>")
        if isinstance(s, ir.ForLoop):
            return (f"<ml:for>{self.emit(s.var)[0]}{self.emit(s.iterable)[0]}"
                    f"{self.block(s.body)}</ml:for>")
        if isinstance(s, ir.IfStmt):
            return self.if_xml(s.branches, block=True)
        if isinstance(s, ir.Return):
            # The last line of a block is Mathcad's implicit return; the parser
            # reads both that and an explicit <ml:return> as Return.
            value = self.emit(s.value)[0]
            return value if last else f"<ml:return>{value}</ml:return>"
        if isinstance(s, ir.ExprStmt):
            return self.emit(s.value)[0]
        if isinstance(s, ir.TryCatch):
            return f"<ml:tryCatch>{self.block(s.body)}{self.block(s.handler)}</ml:tryCatch>"
        raise mb.Unsupported(f"{type(s).__name__} statement")

    def apply(self, tag: str, *operands: ir.Expr) -> tuple[str, int]:
        inner = "".join(self.emit(o)[0] for o in operands)
        return f"<ml:apply><ml:{tag} />{inner}</ml:apply>", mb.ATOM_PREC


def explicit(xml: str) -> str:
    """Drop ``label-is-contextual``: the label stays what it says.

    Used for units and for the name a region defines. Left contextual, Prime
    relabels the target of ``m := 1 m`` (to ``*``) and the unit (to VARIABLE).
    """
    return xml.replace(' label-is-contextual="true"', "")


def override_xml(writer: Writer, unit: ir.Expr | None) -> str:
    inner = "<ml:placeholder />" if unit is None else writer.emit(unit)[0]
    return f"<ml:unitOverride>{inner}</ml:unitOverride>"


# What Prime writes inline for a text region; the real content lives in the
# XamlPackage the ``item-idref`` names.
FLOW_DOC = ('<FlowDocument FontFamily="Tahoma" FontStyle="Normal" FontWeight="Normal" '
            'FontSize="14.6666666666667" Foreground="#FF000000" Background="#00FFFFFF" '
            'TextAlignment="Left" xml:lang="en-us" Typography.Variants="Normal" '
            'xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" />')

_XAML_NS = "http://schemas.microsoft.com/winfx/2006/xaml/presentation"


def xaml_package(paragraphs: list[str]) -> bytes:
    """A FlowDocument XamlPackage: a zip in the zip, one ``Document.xaml``."""
    paras = "".join(
        f'<Paragraph><Run>{mb._escape(p)}</Run></Paragraph>' if p else "<Paragraph />"
        for p in paragraphs)
    doc = (f'<Section xmlns="{_XAML_NS}" xml:space="preserve" TextAlignment="Left" '
           'xml:lang="en-us" FontFamily="Tahoma" FontSize="14.6666666666667" '
           f'Foreground="#FF000000">{paras}</Section>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _XML + (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xaml" ContentType="application/vnd.ms-wpf.xaml+xml" />'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
            '</Types>'))
        zf.writestr("_rels/.rels", _XML + (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Type="http://schemas.microsoft.com/wpf/2005/10/xaml/entry" '
            'Target="/Xaml/Document.xaml" Id="R0" /></Relationships>'))
        zf.writestr("Xaml/Document.xaml", doc)
    return buf.getvalue()


# Text a region is this wide before it wraps, in px; about 7 px per character
# of 11 pt Tahoma.
TEXT_MIN_WIDTH, TEXT_MAX_WIDTH, CHAR_WIDTH = 200, 600, 7.5


def text_width(paragraphs: list[str]) -> float:
    longest = max((len(p) for p in paragraphs), default=0)
    return max(TEXT_MIN_WIDTH, min(TEXT_MAX_WIDTH, round(longest * CHAR_WIDTH)))


# Prime's own trace colours, in the order it gives them to new traces.
TRACE_COLORS = ["#00008B", "#8B0000", "#006400", "#8B008B", "#000000"]

_AXIS_GRID = ('<axisGrid><gridFrequency>{freq}</gridFrequency><gridLabels display="true" />'
              '<gridLines /><tickMarks display="true" /></axisGrid>')


def _equation(writer: Writer, expr: ir.Expr, unit: ir.Expr | None) -> str:
    unit_xml = "<ml:placeholder />" if unit is None else writer.emit(unit)[0]
    return (f"<plotEquation><math>{writer.emit(expr)[0]}</math>"
            f"<math>{unit_xml}</math></plotEquation>")


def _axis_equations(writer: Writer, pairs) -> str:
    """One equation per trace, or one shared by all when every trace agrees
    (how the parser pairs them: a single equation serves every trace)."""
    texts = {(expr_text(e), expr_text(u) if u is not None else "") for e, u in pairs}
    if len(texts) == 1:
        pairs = pairs[:1]
    return "".join(_equation(writer, e, u) for e, u in pairs)


def _limit(refs, value: float | None) -> tuple[str, str]:
    if value is None:
        return "<ml:placeholder />", ""
    return f"<ml:real>{value:g}</ml:real>", f' resultRef="{next(refs)}"'


def xy_plot_xml(region: ir.Plot, writer: Writer, refs) -> str:
    traces = "".join(
        f'<trace resultRef="{next(refs)}"><traceStyle color="#FF'
        f'{(t.color or TRACE_COLORS[n % len(TRACE_COLORS)]).lstrip("#").upper()}" '
        'symbol="none" line-weight="1" line-style="Solid">lines</traceStyle></trace>'
        for n, t in enumerate(region.traces))
    lo, hi = region.x_limits or (None, None)
    domains = {}
    for name in ("x", "y"):
        (start, sref), (end, eref) = ((_limit(refs, lo), _limit(refs, hi)) if name == "x"
                                      else (_limit(refs, None), _limit(refs, None)))
        domains[name] = (f'<xyDomain scale-type="linear" auto-scale="true">'
                         f"<startValue{sref}>{start}</startValue>"
                         f"<endValue{eref}>{end}</endValue></xyDomain>")
    x_eqs = _axis_equations(writer, [(t.x, t.x_unit) for t in region.traces])
    y_eqs = _axis_equations(writer, [(t.y, t.y_unit) for t in region.traces])

    def axis(tag, legend, eqs, domain):
        return (f'<{tag} rank="1" legend-position="{legend}" start="-1" end="1">'
                '<axisLine position="origin" positionticmark="0" legendWidth="0" />'
                + _AXIS_GRID.format(freq=11) +
                f"<axisLabel /><markers /><plotEquations>{eqs}</plotEquations>"
                f"{domain}</{tag}>")

    return ('<plot origin-positioning="true"><xyPlot><title /><legend />'
            f'<traces>{traces}</traces><graph-size width="{PLOT_SIZE}" height="{PLOT_SIZE}" />'
            "<axes>" + axis("xAxis", "PlotBoundaryBottom", x_eqs, domains["x"])
            + axis("yAxis", "PlotBoundaryRight", y_eqs, domains["y"])
            + "</axes></xyPlot></plot>")


def grid_plot_xml(region: ir.GridPlot, writer: Writer, refs) -> str:
    equation = _equation(writer, region.expr, region.z_unit)
    size = f'<graph-size width="{PLOT_SIZE}" height="{PLOT_SIZE}" />'
    if region.threed:
        def axis(tag, dom):
            return (f'<{tag} start="0" end="1" rank="1"><axisLine />'
                    + _AXIS_GRID.format(freq=5) +
                    f'<axisLabel /><{dom} scale-type="linear" allow-negative-values="true" '
                    f'auto-scale="true"><startValue /><endValue /></{dom}></{tag}>')
        return ('<plot><plot3D><traces><trace3D num-of-points="41" '
                f'resultRef="{next(refs)}"><traceStyle color="#FF000000" '
                'automaticStyle="true">surface</traceStyle></trace3D></traces>'
                f'{size}<axes>{axis("xAxis", "xyDomain")}{axis("yAxis", "xyDomain")}'
                f'{axis("zAxis", "zDomain")}</axes>'
                f"<plotEquations>{equation}</plotEquations></plot3D></plot>")

    def axis(tag, dom, extra):
        # Prime marks the whole region CorruptedRegion if the z axis line is
        # ``ticknumberlock`` like the other two (found by trying variants).
        line = ('position="origin" positionticmark="5"' if tag == "zAxis"
                else 'position="ticknumberlock" positionticmark="0"')
        return (f'<{tag} rank="1"{extra} start="0" end="1">'
                f'<axisLine {line} legendWidth="0" />'
                + _AXIS_GRID.format(freq=9 if tag == "zAxis" else 11) +
                f'<axisLabel /><markers /><{dom} scale-type="linear" auto-scale="true">'
                "<startValue><ml:placeholder /></startValue>"
                f"<endValue><ml:placeholder /></endValue></{dom}></{tag}>")
    return ('<plot background-type="white"><contourPlot><axes>'
            + axis("xAxis", "xyDomain", ' legend-position="PlotBoundaryBottom"')
            + axis("yAxis", "xyDomain", ' legend-position="PlotBoundaryLeft"')
            + axis("zAxis", "zDomain", "")
            + f'</axes><contour color="#FF000000" show-lables="false" resultRef="{next(refs)}" />'
            f"{size}{equation}</contourPlot></plot>")


PLOT_SIZE = 230.4
XY_REGION = (364.8, 326.4)


def solve_block_xml(region: ir.SolveBlock, rid: int, top: float, writer: Writer,
                    refs) -> str:
    """``<solveblock>``: guesses, constraints and the ``find`` line, each its
    own region with coordinates relative to the block."""
    subs, row = [], 0
    sub_id = itertools.count(1000 * (rid + 1))

    def sub(category: str, math: str) -> None:
        nonlocal row
        subs.append(f'<region region-id="{next(sub_id)}" top="{19.2 + row * ROW}" '
                    f'left="19.2" solve-block-category="{category}">'
                    f'<math resultRef="{next(refs)}">{math}</math></region>')
        row += 1.5

    for g in region.guesses:
        sub("guess-value", f"<ml:define>{explicit(writer.emit(g.target)[0])}"
                           f"{writer.emit(g.value)[0]}</ml:define>")
    for c in region.constraints:
        sub("constraint", writer.emit(ir.BinOp(op="eq", left=c.lhs, right=c.rhs))[0])

    unknowns = [writer.emit(u)[0] for u in region.unknowns]
    args = unknowns[0] if len(unknowns) == 1 else f"<ml:sequence>{''.join(unknowns)}</ml:sequence>"
    find = (f'<ml:apply><ml:id labels="KEYWORD" algorithm="" xml:space="preserve">'
            f'{region.command}</ml:id>{args}</ml:apply>')
    if region.params:
        name = writer.identifier(region.targets[0].original, "VARIABLE")
        bound = "".join(writer.identifier(mathcad_name(p), "VARIABLE") for p in region.params)
        target = f"<ml:function>{name}<ml:boundVars>{bound}</ml:boundVars></ml:function>"
    elif len(region.targets) == 1:
        target = writer.emit(region.targets[0])[0]
    else:
        cells = "".join(writer.emit(t)[0] for t in region.targets)
        target = f'<ml:matrix rows="{len(region.targets)}" cols="1">{cells}</ml:matrix>'
    if region.evaluate:
        find = f"<ml:eval>{find}{override_xml(writer, region.display_unit)}</ml:eval>"
    sub("solver", f"<ml:define>{explicit(target)}{find}</ml:define>")
    height = round(19.2 + row * ROW + 19.2, 4)
    return (f'<region region-id="{rid}" width="300" height="{height}" top="{top}" left="38.4">'
            f'<solveblock><regions>{"".join(subs)}</regions></solveblock></region>')


def solve_rows(region: ir.SolveBlock) -> float:
    return 1.5 * (len(region.guesses) + len(region.constraints) + 1) + 2


def region_xml(region: ir.Region, rid: int, top: float, writer: Writer, refs) -> str:
    if isinstance(region, ir.SolveBlock):
        return solve_block_xml(region, rid, top, writer, refs)
    if isinstance(region, ir.Plot):
        # Without a fixed size the region opens and calculates, but Prime
        # crashes laying it out for print (PlotGraphControl measures to
        # infinity). The size is Prime's own for a 230.4 px graph.
        return (f'<region region-id="{rid}" width="{XY_REGION[0]}" height="{XY_REGION[1]}" '
                f'top="{top}" left="38.4">'
                f"{xy_plot_xml(region, writer, refs)}</region>")
    if isinstance(region, ir.GridPlot):
        return (f'<region region-id="{rid}" top="{top}" left="38.4">'
                f"{grid_plot_xml(region, writer, refs)}</region>")
    if isinstance(region, (ir.Statement, ir.MultiAssign, ir.Recurrence)):
        if isinstance(region, ir.Statement):
            math = writer.emit(region.value)[0]
        else:
            if isinstance(region, ir.MultiAssign):
                n = len(region.targets)
                rows, cols = n, 1
                if region.matrix_target:
                    # The Python keeps only the count; assume a square matrix.
                    side = round(n ** 0.5)
                    if side * side != n:
                        raise Refused(f"cannot tell the shape of a {n}-name matrix target")
                    rows = cols = side
                cells = "".join(writer.emit(t)[0] for t in region.targets)
                target = explicit(f'<ml:matrix rows="{rows}" cols="{cols}">{cells}</ml:matrix>')
                value = writer.emit(region.value)[0]
            else:
                slots = [writer.emit(ir.Index(base=t.base, index=t.index) if t.col is None
                                     else ir.Index2D(base=t.base, row=t.index, col=t.col))[0]
                         for t in region.targets]
                target = explicit(slots[0] if len(slots) == 1 else
                                  f'<ml:matrix rows="{len(slots)}" cols="1">{"".join(slots)}</ml:matrix>')
                if region.values is not None:
                    value = (f'<ml:matrix rows="{len(region.values)}" cols="1">'
                             + "".join(writer.emit(v)[0] for v in region.values)
                             + "</ml:matrix>")
                else:
                    value = writer.emit(region.value)[0]
            if getattr(region, "evaluate", False):
                value = f"<ml:eval>{value}{override_xml(writer, None)}</ml:eval>"
            math = f"<ml:define>{target}{value}</ml:define>"
        return (f'<region region-id="{rid}" top="{top}" left="38.4">'
                f'<math resultRef="{next(refs)}">{math}</math></region>')
    if isinstance(region, ir.TextRegion):
        width = text_width(region.text.split("\n"))
        return (f'<region region-id="{rid}" width="{width}" top="{top}" left="38.4">'
                f'<text item-idref="Rtext{rid}">{FLOW_DOC}</text></region>')
    if isinstance(region, ir.IndexAssign):
        target = explicit(writer.emit(ir.Index(base=region.target, index=region.index))[0]
                  if region.col_index is None else
                  writer.emit(ir.Index2D(base=region.target, row=region.index,
                                         col=region.col_index))[0])
        value = writer.emit(region.value)[0]
        if region.evaluate:
            value = f"<ml:eval>{value}{override_xml(writer, region.display_unit)}</ml:eval>"
        math = f"<ml:define>{target}{value}</ml:define>"
        return (f'<region region-id="{rid}" top="{top}" left="38.4">'
                f'<math resultRef="{next(refs)}">{math}</math></region>')
    if isinstance(region, ir.Define) and region.params:
        name = writer.identifier(region.target.original, "VARIABLE")
        bound = "".join(writer.identifier(mathcad_name(p), "VARIABLE") for p in region.params)
        target = explicit(f"<ml:function>{name}<ml:boundVars>{bound}</ml:boundVars></ml:function>")
        math = f"<ml:define>{target}{writer.emit(region.value)[0]}</ml:define>"
    elif isinstance(region, ir.Define):
        target = explicit(writer.emit(region.target)[0])
        value = writer.emit(region.value)[0]
        if region.evaluate:
            value = f"<ml:eval>{value}{override_xml(writer, region.display_unit)}</ml:eval>"
        math = f"<ml:define>{target}{value}</ml:define>"
    else:
        value = writer.emit(region.value)[0]
        math = f"<ml:eval>{value}{override_xml(writer, region.display_unit)}</ml:eval>"
    return (f'<region region-id="{rid}" top="{top}" left="38.4">'
            f'<math resultRef="{next(refs)}">{math}</math></region>')


# ---------------------------------------------------------------------------
# The package
# ---------------------------------------------------------------------------

_NS = ('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
       'xmlns:ve="http://schemas.openxmlformats.org/markup-compatibility/2006" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
       'xmlns:ws="http://schemas.mathsoft.com/worksheet50" '
       'xmlns:ml="http://schemas.mathsoft.com/math50" '
       'xmlns:u="http://schemas.mathsoft.com/units10" '
       'xmlns:p="http://schemas.mathsoft.com/provenance10" '
       'xmlns="http://schemas.mathsoft.com/worksheet50"')

_XML = '<?xml version="1.0" encoding="utf-8"?>'
_CT = "application/vnd.openxmlformats-officedocument.mathprocessingml.mathcad"

PARTS = {
    "[Content_Types].xml": _XML + (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f'<Default Extension="xml" ContentType="{_CT}.main+xml" />'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
        '<Default Extension="XamlPackage" ContentType="application/zip" />'
        f'<Override PartName="/mathcad/settings/calculation.xml" ContentType="{_CT}.settings.calculation+xml" />'
        f'<Override PartName="/mathcad/result.xml" ContentType="{_CT}.result+xml" />'
        f'<Override PartName="/mathcad/integration.xml" ContentType="{_CT}.integration+xml" />'
        '</Types>'),
    "_rels/.rels": _XML + (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="/mathcad/worksheet.xml" Id="R0" /></Relationships>'),
    "mathcad/settings/calculation.xml": _XML + (
        '<calculation cache-worksheet="true" xmlns="http://schemas.ptc.com/mathcad/settings/calculation10">'
        '<builtInVariables array-origin="0" convergence-tolerance="0.001" constraint-tolerance="0.001" '
        'prn-col-width="8" prn-precision="4" random-seed="1" />'
        '<calculationBehavior automatic-recalculation="true" strings-use-origin="false" '
        'matrix-strict-singularity-check="false" exact-boolean="true" units-in-symbolics="false" '
        'constants-in-symbolics="false" symbolic-engine="axiom" bin-oct-hex-mode="false" />'
        '<units><customUnitSystem base-unit-system="si"><baseUnits /><derivedUnits /></customUnitSystem>'
        '<currentUnitSystem name="si" /></units></calculation>'),
    "mathcad/result.xml": _XML + (
        '<resultsList xmlns:ml="http://schemas.mathsoft.com/math50" '
        'xmlns:u="http://schemas.mathsoft.com/units10" xmlns="http://schemas.mathsoft.com/result10" />'),
    "mathcad/integration.xml": _XML + '<regions xmlns="http://schemas.ptc.com/integration10" />',
}

ROW = 38.4  # one grid row in Prime's default layout, in device-independent px


# Prime refuses to open a package without this part (found by removing parts
# one at a time from a working sheet). It holds styles only, so one copy from
# a Prime-saved sheet serves every generated one.
PRESENTATION = Path(__file__).with_name("mcdx_template") / "presentation.xml"


def rows(region: ir.Region) -> float:
    """Grid rows ``region`` takes, including the gap below it."""
    if isinstance(region, (ir.Plot, ir.GridPlot)):
        return PLOT_SIZE / ROW + 2.5
    if isinstance(region, ir.SolveBlock):
        return solve_rows(region)  # the graph, its axis labels and a gap
    if isinstance(region, ir.TextRegion):
        lines = sum(1 + len(p) * CHAR_WIDTH // TEXT_MAX_WIDTH
                    for p in region.text.split("\n"))
        return 0.5 + 0.5 * lines
    value = getattr(region, "value", None)
    return 0.75 + 0.75 * max(1.0, _lines(value)) if value is not None else 1.5


def _lines(node) -> float:
    """Rough height of an expression in text lines: a program stacks its
    lines, a matrix its rows. Prime sizes the region itself; this only has to
    keep the next region clear of it."""
    if isinstance(node, ir.ProgramBlock):
        return sum(_stmt_lines(s) for s in node.statements) or 1
    if isinstance(node, ir.Program):
        return sum(max(1.0, _lines(v)) for _t, v in node.branches) * 1.2
    if isinstance(node, ir.MatrixLiteral):
        return max(1.0, node.rows * 0.8)
    kids = ir.child_exprs(node) if isinstance(node, ir.Expr) else []
    return max([1.0, *(_lines(k) for k in kids)])


def _stmt_lines(s: ir.Stmt) -> float:
    if isinstance(s, ir.ForLoop):
        return 1 + _lines(s.body)
    if isinstance(s, ir.IfStmt):
        return sum(_lines(b) for _t, b in s.branches) * 1.2
    if isinstance(s, ir.TryCatch):
        return _lines(s.body) + _lines(s.handler) + 1
    return 1.0


def build(regions: list[ir.Region]) -> dict[str, str | bytes]:
    functions = {r.target.py: r.target.original for r in regions
                 if isinstance(r, ir.Define) and r.params}
    functions.update({r.targets[0].py: r.targets[0].original for r in regions
                      if isinstance(r, ir.SolveBlock) and r.params})
    writer = Writer({}, functions)
    body, top, rels = [], 2 * ROW, []
    parts: dict[str, str | bytes] = dict(PARTS)
    # resultRef numbers everything that has a result -- math, plot traces,
    # axis limits -- in one sequence, as Prime does.
    refs = itertools.count()
    for rid, region in enumerate(regions):
        if isinstance(region, ir.TextRegion):
            target = f"/mathcad/xaml/FlowDocument{rid}.XamlPackage"
            parts[target.lstrip("/")] = xaml_package(region.text.split("\n"))
            rels.append('<Relationship Type="http://schemas.openxmlformats.org/officeDocument/'
                        f'2006/relationships/flowDocument" Target="{target}" Id="Rtext{rid}" />')
        body.append(region_xml(region, rid, round(top, 4), writer, refs))
        top += rows(region) * ROW
    if rels:
        parts["mathcad/_rels/worksheet.xml.rels"] = _XML + (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels) + "</Relationships>")
    body = "".join(body)
    parts["mathcad/settings/presentation.xml"] = PRESENTATION.read_text(encoding="utf-8-sig")
    parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
        "</Types>",
        '<Override PartName="/mathcad/settings/presentation.xml" '
        f'ContentType="{_CT}.settings.presentation+xml" /></Types>')
    parts["mathcad/worksheet.xml"] = (f'<worksheet {_NS}><regions>{body}</regions></worksheet>')
    return parts


def write_mcdx(parts: dict[str, str | bytes], out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in parts.items():
            zf.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="py_to_mcdx", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        regions = read_python(args.file.read_text(encoding="utf-8"))
        parts = build(regions)
    except (Refused, mb.Unsupported, SyntaxError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_mcdx(parts, args.output)
    print(f"{len(regions)} regions -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
