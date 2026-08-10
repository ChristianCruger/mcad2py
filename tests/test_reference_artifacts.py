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

Two things are normalised before comparing notebooks, both because they are not
reproducible rather than because they don't matter:

* **Cell ids.** `nbformat` mints a fresh random id for every cell on each run,
  so a byte comparison would fail on every notebook always -- and regenerating
  to satisfy it would churn ~500 lines of `RC_col.ipynb` to change three.
* **Embedded image payloads.** `Elastic_foundation_eq_line_spring.mcdx` carries
  a BMP, which the notebook backend re-encodes to PNG through Pillow (see
  `_as_raster`). Pillow's PNG bytes are not stable across platforms and
  versions -- the committed artifact was generated on Windows, CI runs Linux --
  so the base64 blob differs while the picture is identical. Comparing the
  bytes made this test fail on CI for an artifact that was perfectly current.
  The payload is compared as *pixels* instead, by
  `test_reference_notebook_images_are_pixel_identical`, which is the invariant
  that actually holds; here it is replaced with a marker so the surrounding
  cell structure is still compared exactly.

Everything else about the notebook, cell order and content included, is
compared exactly.

Not every worksheet ships both artifacts (`shrinkage.mcdx` has only a notebook),
so the parametrization walks the *committed files* rather than the worksheets.
`test_every_artifact_has_a_worksheet` covers the other direction: an artifact
whose `.mcdx` was renamed or removed would otherwise sit here unnoticed and
untested, since nothing else in the suite looks at these files at all.
"""

import base64
import io
import json
import re
from pathlib import Path

import pytest

from mcad2py.convert import convert_file

REFERENCES = Path(__file__).parent.parent / "references"
SCRIPTS = sorted(REFERENCES.glob("*.py"))
NOTEBOOKS = sorted(REFERENCES.glob("*.ipynb"))

REGENERATE = "regenerate with: mcad2py convert references/{stem}.mcdx{flag}"


def _worksheet(artifact: Path) -> Path:
    return artifact.with_suffix(".mcdx")


# A base64 blob, long enough that no ordinary emitted line can be mistaken for
# one (the shortest embedded image here is tens of kilobytes).
_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/]{256,}={0,2}")
_IMAGE_MARKER = "<image payload compared as pixels>"


def _normalised(notebook: str) -> dict:
    """A parsed notebook with the two irreproducible bits neutralised: every
    cell's random ``id``, and every embedded image payload (see module docs)."""
    parsed = json.loads(notebook)
    for cell in parsed["cells"]:
        cell.pop("id", None)
        cell["source"] = [_BASE64_BLOB.sub(_IMAGE_MARKER, line)
                          for line in cell["source"]]
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            for mime, payload in data.items():
                if isinstance(payload, str):
                    data[mime] = _BASE64_BLOB.sub(_IMAGE_MARKER, payload)
    return parsed


def _image_payloads(notebook: str) -> list[bytes]:
    """Every embedded image in a notebook, decoded, in cell order."""
    return [base64.b64decode(blob)
            for blob in _BASE64_BLOB.findall(notebook)]


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
    """Each committed `.ipynb` matches a fresh conversion -- cell ids and image
    payloads aside, both of which are irreproducible (see module docstring)."""
    fresh = convert_file(_worksheet(notebook), fmt="notebook")
    committed = notebook.read_text(encoding="utf-8")
    assert _normalised(committed) == _normalised(fresh), (
        f"{notebook.name} is stale -- "
        + REGENERATE.format(stem=notebook.stem, flag="")
    )


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=[p.stem for p in NOTEBOOKS])
def test_reference_notebook_images_are_pixel_identical(notebook):
    """The half of the notebook comparison that image bytes can't carry.

    A picture region reaches the notebook as base64. When the source is already
    a web raster (PNG/JPEG/GIF) those bytes are copied straight through and
    would compare fine; a BMP is re-encoded through Pillow, whose PNG output
    varies by platform and version, so the committed blob and a fresh one
    differ while showing the same picture. Decoding both and comparing pixels
    is the invariant that survives that -- and it still catches a *changed*
    image, which is the thing worth catching.
    """
    fresh = convert_file(_worksheet(notebook), fmt="notebook")
    committed = notebook.read_text(encoding="utf-8")

    committed_images = _image_payloads(committed)
    fresh_images = _image_payloads(fresh)
    assert len(committed_images) == len(fresh_images), (
        f"{notebook.name}: {len(committed_images)} embedded image(s), "
        f"fresh conversion has {len(fresh_images)}"
    )
    if not committed_images:
        pytest.skip("no embedded images in this notebook")

    from PIL import Image

    for index, (was, now) in enumerate(zip(committed_images, fresh_images)):
        if was == now:
            continue  # byte-identical: a pass-through raster, nothing to decode
        before, after = Image.open(io.BytesIO(was)), Image.open(io.BytesIO(now))
        assert (before.size, before.mode) == (after.size, after.mode), (
            f"{notebook.name} image {index}: {before.size}/{before.mode} "
            f"vs {after.size}/{after.mode}"
        )
        assert before.tobytes() == after.tobytes(), (
            f"{notebook.name} image {index} differs in pixel content -- "
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
