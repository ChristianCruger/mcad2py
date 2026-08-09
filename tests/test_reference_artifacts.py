"""The committed `references/*.py` and `*.ipynb` match what the converter emits.

These files are generated artifacts kept in git so a reader can see the output
for a worksheet without running anything -- but nothing consumed them, so
nothing noticed when they went stale. The rest of the suite converts each
`.mcdx` *fresh* and executes that (see `conftest.run_sheet`); the committed
copies were never read, and they silently drifted through several header
changes until they still carried `ureg = pint.UnitRegistry()` long after
generated modules had moved onto the one shared registry in `units.py`.

Regenerating them is a one-liner (`mcad2py convert <sheet>.mcdx -f py`); the
point of this module is that the *commit which changes codegen* is the one that
fails, rather than a reader hitting a stale artifact months later.

Notebooks are compared with their cell **ids stripped**. `nbformat` mints a
fresh random id for every cell on each run, so a byte comparison would fail on
every notebook always -- and regenerating to satisfy it would churn ~500 lines
of `RC_col.ipynb` to change three. Everything else about the notebook, cell
order and content included, is compared exactly.

Not every worksheet ships both artifacts (`shrinkage.mcdx` has only a notebook),
so the parametrization walks the *committed files* rather than the worksheets.
`test_every_artifact_has_a_worksheet` covers the other direction: an artifact
whose `.mcdx` was renamed or removed would otherwise sit here unnoticed and
untested, since nothing else in the suite looks at these files at all.
"""

import json
from pathlib import Path

import pytest

from mcad2py.convert import convert_file

REFERENCES = Path(__file__).parent.parent / "references"
SCRIPTS = sorted(REFERENCES.glob("*.py"))
NOTEBOOKS = sorted(REFERENCES.glob("*.ipynb"))

REGENERATE = "regenerate with: mcad2py convert references/{stem}.mcdx{flag}"


def _worksheet(artifact: Path) -> Path:
    return artifact.with_suffix(".mcdx")


def _without_cell_ids(notebook: str) -> dict:
    """A parsed notebook with every cell's random ``id`` dropped."""
    parsed = json.loads(notebook)
    for cell in parsed["cells"]:
        cell.pop("id", None)
    return parsed


@pytest.mark.parametrize("script", SCRIPTS, ids=[p.stem for p in SCRIPTS])
def test_reference_script_matches_a_fresh_conversion(script):
    """Each committed `.py` is what `convert_file(..., fmt="py")` emits today."""
    fresh = convert_file(_worksheet(script), fmt="py")
    # newline="" would compare the platform's line endings, which git rewrites.
    committed = script.read_text(encoding="utf-8")
    assert committed.splitlines() == fresh.splitlines(), (
        f"{script.name} is stale -- "
        + REGENERATE.format(stem=script.stem, flag=" -f py")
    )


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=[p.stem for p in NOTEBOOKS])
def test_reference_notebook_matches_a_fresh_conversion(notebook):
    """Each committed `.ipynb` matches a fresh conversion, cell ids aside."""
    fresh = convert_file(_worksheet(notebook), fmt="notebook")
    committed = notebook.read_text(encoding="utf-8")
    assert _without_cell_ids(committed) == _without_cell_ids(fresh), (
        f"{notebook.name} is stale -- "
        + REGENERATE.format(stem=notebook.stem, flag="")
    )


@pytest.mark.parametrize("artifact", SCRIPTS + NOTEBOOKS,
                         ids=[p.name for p in SCRIPTS + NOTEBOOKS])
def test_every_artifact_has_a_worksheet(artifact):
    """No orphaned artifact: a renamed or deleted `.mcdx` leaves one behind,
    and since nothing else in the suite reads these files it would never be
    caught -- the two tests above simply wouldn't run for it."""
    assert _worksheet(artifact).exists(), (
        f"{artifact.name} has no matching .mcdx -- delete it, or restore the sheet"
    )
