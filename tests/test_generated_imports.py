"""The generated module's imports agree with the code beneath them.

This is the invariant that replaced a hand-maintained mirror. `header_lines`
used to *predict* which runtime helpers the emitted text would name by walking
the IR, with the prediction spread across a `found.add(...)` scan and a separate
ordering list. Forgetting either half produced a module that raised `NameError`
on import -- and nothing noticed until somebody converted that particular sheet.

Now the header is read off the rendered body, so the two agree by construction.
These tests check that across *every* reference worksheet at once, in both
directions, which is exactly the check the old design couldn't support.

The audit when this landed found seven dead imports the predictor had been
emitting for years: `import numpy as np` in four sheets whose `min`/`max` are
reductions (they emit `mc_min`/`mc_max`, never `np.minimum`), and `sample` in
three whose only plots are *parametric* (both axes are data vectors, so no
`sample(lambda ...)` is ever written).
"""

import ast
import builtins
import re
from pathlib import Path

import pytest

from mcad2py.convert import convert_file
from mcad2py.emit.codegen import _identifiers, _runtime_exports

REFERENCES = sorted((Path(__file__).parent.parent / "references").glob("*.mcdx"))
IDS = [p.stem for p in REFERENCES]


def _split(source: str) -> tuple[set[str], str]:
    """``(names the runtime import line brings in, the rest of the module)``."""
    imported: set[str] = set()
    body: list[str] = []
    for line in source.splitlines():
        match = re.fullmatch(r"from mcad2py\.runtime import (.*)", line)
        if match:
            imported = {n.strip() for n in match.group(1).split(",")}
        else:
            body.append(line)
    return imported, "\n".join(body)


def _unresolved(source: str) -> set[str]:
    """Names the module reads but never binds or imports -- i.e. would `NameError`.

    Deliberately built with `ast` rather than the emitter's own tokenizer, so
    this is an *independent* check: the tests below that compare the import line
    against `_identifiers` would agree with a wrong answer, because they call
    the same function `header_lines` does. Scoping is approximated by pooling
    every binding in the module, which is sound here -- generated code never
    shadows a name in an inner scope while relying on an outer one of the same
    name being absent.
    """
    tree = ast.parse(source)
    bound = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.Import):
            bound.update(a.asname or a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            bound.update(a.asname or a.name for a in node.names)
    return {
        n.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound
    }


@pytest.fixture(scope="module", params=REFERENCES, ids=IDS)
def sheet(request) -> tuple[set[str], str, str]:
    source = convert_file(request.param, fmt="py")
    return (*_split(source), source)


def test_generated_module_resolves_every_name(sheet):
    """The `NameError`-on-import direction -- the one that used to bite.

    Checked against the parsed module rather than against the emitter's own
    scan, so a bug in that scan can't hide here.
    """
    *_, source = sheet
    assert _unresolved(source) == set()


def test_every_import_is_used(sheet):
    """No dead imports: a name brought in from the runtime is named below.

    Together with the two backends' reordering (body rendered first, header
    built from it), this also pins that they hand `header_lines` the *whole*
    body -- a region rendered after the header was built would show up here as
    a missing import rather than as a silently broken sheet.
    """
    imported, body, _ = sheet
    assert imported - _identifiers(body) == set()


def test_numpy_is_imported_exactly_when_referenced(sheet):
    """`np` is subject to the same rule; it isn't a runtime helper, so it needs
    its own check. Four sheets used to import it without ever writing `np.`."""
    _, body, source = sheet
    assert ("import numpy as np" in source) == ("np" in _identifiers(body))


def test_runtime_exports_excludes_imported_modules():
    """The registry is "public things *defined in* runtime.py" -- the modules
    runtime itself imports (`np`, `math`, `cmath`) must not leak in, or every
    generated sheet would try to import `math` from the runtime."""
    exports = set(_runtime_exports())
    assert {"np", "math", "cmath", "NamedTuple"} & exports == set()
    # ...while the helpers themselves are all there, across every family.
    assert {"sin", "matmul", "percentile", "solve_block", "plot_trace"} <= exports


def test_identifiers_ignores_comments_and_strings():
    """Tokenizing rather than pattern-matching: a helper's name mentioned in a
    `# TODO unsupported` comment or a string literal must not pull in an import."""
    assert _identifiers("# TODO unsupported: sort\nx = 1") == {"x"}
    assert _identifiers("label = 'mean of the sample'") == {"label"}
    assert _identifiers("y = sort(v)") == {"y", "sort", "v"}


def test_identifiers_falls_back_when_source_is_unparseable():
    """Unparseable output is a bug elsewhere, but the converter still has to
    produce a file -- an over-broad import list beats a crashed conversion."""
    assert "sort" in _identifiers("y = sort(v")  # unbalanced: tokenize gives up
