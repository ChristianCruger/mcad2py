"""End-to-end tests against the reference worksheet.

The strongest check: convert the reference ``.mcdx``, execute the generated
Python, and confirm the computed values match Mathcad's own cached results
(from ``result.xml``).
"""

import math
from pathlib import Path

import nbformat
import pytest

from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.emit.notebook_backend import to_notebook
from mcad2py.loader import load_mcdx

REFERENCE = Path(__file__).parent.parent / "references" / "plain_concrete_cohesion.mcdx"

# Variable -> Mathcad's cached result magnitude (in the worksheet's display unit).
EXPECTED = {
    "f_cd": 20.0,
    "mu": 0.75355405010279419,
    "k": 4.0227912058161515,
    "c": 4.9858160805343159,      # MPa
    "v": 0.36514837167011072,
    "c_eff": 1.8205626232537591,  # MPa
    "f_eff": 7.3029674334022143,  # MPa
    "p": 101.27717357238693,      # MPa (last redefinition of p wins)
}


def _exec_generated() -> dict:
    src = convert_file(REFERENCE, fmt="py")
    namespace: dict = {}
    exec(compile(src, "<generated>", "exec"), namespace)  # noqa: S102
    return namespace


def test_generated_values_match_mathcad():
    ns = _exec_generated()
    for name, expected in EXPECTED.items():
        value = ns[name]
        magnitude = value.to("MPa").magnitude if hasattr(value, "to") else float(value)
        assert math.isclose(magnitude, expected, rel_tol=1e-9), (
            f"{name}: got {magnitude}, expected {expected}"
        )


def test_units_preserved():
    ns = _exec_generated()
    assert str(ns["f_cd"].to("MPa").units) == "megapascal"
    assert ns["mu"].__class__.__name__ != "Quantity"  # dimensionless -> plain float


def test_notebook_is_valid_and_interleaves_markdown():
    ws = convert_worksheet(load_mcdx(REFERENCE))
    nb = to_notebook(ws)
    nbformat.validate(nb)
    types = {c.cell_type for c in nb.cells}
    assert "code" in types and "markdown" in types
    # Text region content survives extraction from the XAML package.
    assert any("friction" in c.source for c in nb.cells if c.cell_type == "markdown")


def test_inline_eval_uses_display_unit():
    ws = convert_worksheet(load_mcdx(REFERENCE))
    nb = to_notebook(ws)
    f_cd_cell = next(c for c in nb.cells if c.source.startswith("f_cd ="))
    # define on first line, bare unit-converted echo on the last line (Mathcad "=")
    assert f_cd_cell.source.splitlines()[-1] == "f_cd.to(ureg.MPa)"


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        convert_file("does_not_exist.mcdx")
