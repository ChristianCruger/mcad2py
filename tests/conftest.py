"""Shared helpers for the reference-worksheet tests.

The house style (see CLAUDE.md) is: convert a ``references/*.mcdx``, **execute**
the generated Python, and assert the values against Mathcad's cached
``result.xml``. That shape was copied by hand into most test modules; the pieces
of it that were genuinely identical live here.

Not everything fits, and that is fine. ``test_vectors.py`` slices the generated
source four different ways (stopping before the solve block, before the checks,
…) and ``test_rc_col.py`` strips plot blocks for speed -- those harnesses are
doing different work, and folding them in would hide why.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import matplotlib
import numpy as np
import pytest

# Headless: several reference sheets end in a plot, and rendering must not try
# to open a window. Set once here rather than in each module that needs it.
matplotlib.use("Agg")

from mcad2py.convert import convert_file  # noqa: E402 -- after matplotlib.use
from mcad2py.runtime import _consolidate  # noqa: E402

REFERENCES = Path(__file__).parent.parent / "references"


def reference(name: str) -> Path:
    """The path to a fixture worksheet, with or without the ``.mcdx`` suffix."""
    return REFERENCES / (name if name.endswith(".mcdx") else f"{name}.mcdx")


def run_sheet(path: Path | str) -> tuple[str, dict, list]:
    """Convert, execute, and return ``(source, namespace, echoed values)``.

    Echoes are captured as **objects**, not text: a sheet of matrices prints
    multi-line arrays that no line-based parse could put back together. Binding
    ``print`` in the module globals shadows the builtin for the generated code
    only, which is why the value arrives intact.
    """
    source = convert_file(path, fmt="py")
    echoed: list = []
    namespace: dict = {
        "print": lambda *a: echoed.append(a[0] if len(a) == 1 else a)
    }
    exec(compile(source, "<generated>", "exec"), namespace)  # noqa: S102
    return source, namespace, echoed


def flat(value) -> np.ndarray:
    """A 1-D **column-major** view of a value's magnitudes.

    Column-major because that is the order Mathcad's cached ``<ml:matrix>``
    lists its elements in, so a flattened result lines up with the cache
    element for element. A heterogeneous (object) array -- one built by
    ``augment``/``vec_set`` from per-element quantities -- is fused first.
    """
    if isinstance(value, np.ndarray) and value.dtype == object:
        value = _consolidate(value)
    arr = np.asarray(getattr(value, "magnitude", value))
    if arr.dtype == object:
        arr = arr.astype(float)
    return arr.reshape(-1, order="F") if arr.ndim > 1 else np.atleast_1d(arr)


def cached_results(path: Path | str) -> dict[str, list[float]]:
    """``result-id`` -> that region's cached numbers, flattened column-major.

    Reading the cache instead of transcribing it keeps a wide catalogue sheet
    testable: ``statistics.mcdx`` has 82 evaluated regions, and hand-copying 82
    expectations would be both unreadable and a fresh source of error. Regions
    Mathcad itself could not compute hold an ``<engineError>`` rather than a
    result, so they are simply absent here.

    A value carrying units is cached as ``<unitedValue>`` -- a number plus a
    ``<u:unitMonomial>``. Only the **number** is returned; Mathcad states it in
    base SI, so the caller compares against ``.to_base_units().magnitude``.
    """
    root = _part(path, "mathcad/result.xml")
    out: dict[str, list[float]] = {}
    for data in root:
        result = data.find("./{*}result")
        node = next(iter(result), None) if result is not None else None
        if node is not None and _local(node.tag) == "unitedValue":
            node = next((c for c in node if _local(c.tag) in ("real", "matrix")), None)
        if node is None:
            continue
        if _local(node.tag) == "matrix":
            out[data.get("result-id")] = [
                float(c.text) for c in node if _local(c.tag) == "real"
            ]
        elif _local(node.tag) == "real":
            out[data.get("result-id")] = [float(node.text)]
    return out


def result_refs(path: Path | str) -> dict[int, str]:
    """``region-id`` -> the ``resultRef`` its ``<math>`` child points at.

    Pairs an IR region (whose ``source.region_id`` is the ``region-id``) with
    its entry in :func:`cached_results`.
    """
    root = _part(path, "mathcad/worksheet.xml")
    refs: dict[int, str] = {}
    for region in root.iter():
        if _local(region.tag) != "region" or region.get("region-id") is None:
            continue
        math_elem = next((c for c in region if _local(c.tag) == "math"), None)
        if math_elem is not None and math_elem.get("resultRef"):
            refs[int(region.get("region-id"))] = math_elem.get("resultRef")
    return refs


def _part(path: Path | str, name: str) -> ET.Element:
    return ET.fromstring(zipfile.ZipFile(path).read(name).decode("utf-8"))


def _local(tag: str) -> str:
    """The local name of a namespaced tag (Prime bumps the namespace version)."""
    return tag.rsplit("}", 1)[-1]


@pytest.fixture
def sheet_runner():
    """``run_sheet`` as a fixture, for tests that prefer injection over import."""
    return run_sheet
