#!/usr/bin/env python3
"""Make Mathcad Prime recompute a ``.mcdx`` and refresh its cached results.

``mcad2py`` reads a worksheet; it never runs Mathcad. After
``tools/set_mcdx_value.py`` changes an input, the sheet's own cache
(``mathcad/result.xml``) still holds the numbers Prime computed for the *old*
value. This drives Prime itself through Application Automation to recompute
and save, so the cache matches the worksheet again.

    python tools/set_mcdx_value.py sheet.mcdx --region 1 --value 45
    python tools/recalc_mcdx.py sheet.mcdx

    python tools/recalc_mcdx.py sheet.mcdx -o recalculated.mcdx
    python tools/recalc_mcdx.py sheet.mcdx --visible --timeout 300

**Requires Mathcad Prime installed on this machine**, plus the ``MathcadPy``
package (``pip install -e ".[mathcad]"``). Both are Windows-only, which is why
they are not dependencies of ``mcad2py`` itself.

Prime's ``Synchronize()`` is **asynchronous** -- it returns immediately and the
calculation engine keeps working. Saving straight after it writes a
``result.xml`` whose entries still say ``calculation-status="Pending"`` and
whose numbers are the stale ones. So this saves, inspects the saved cache, and
repeats until it settles -- a check of the real output rather than a guess at
how long to wait.

"Settled" means two consecutive saves whose ``result.xml`` is byte-identical
*and* holds no ``Pending`` entry. Absence of ``Pending`` alone is not enough:
an edited-but-not-recalculated worksheet reads as fully ``Synchronized``
already (``set_mcdx_value.py`` rewrites the maths, not the cache), so a save
that lands before the engine starts would look finished while every number in
it is stale.

Prime is left running if it was already running when this started; only a
Prime that this tool launched is closed again.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

_RESULTS = "mathcad/result.xml"
_STATUS = re.compile(r'calculation-status="(\w+)"')


class RecalcError(Exception):
    """Prime could not be driven to a synchronized state."""


def _cache(path: Path) -> bytes:
    """The raw ``result.xml`` of ``path`` (empty if the part is absent)."""
    with zipfile.ZipFile(path) as zf:
        if _RESULTS not in zf.namelist():
            return b""
        return zf.read(_RESULTS)


def pending_count(path: Path) -> int:
    """Cached results in ``path`` that Prime has not finished computing."""
    text = _cache(path).decode("utf-8", "replace")
    return sum(1 for status in _STATUS.findall(text) if status != "Synchronized")


def recalculate(path: Path, out: Path, timeout: float = 120.0,
                visible: bool = False, poll: float = 3.0) -> float:
    """Open ``path`` in Prime, recompute, save to ``out``. Returns seconds taken.

    Raises ``RecalcError`` if the cache still holds unfinished results when
    ``timeout`` expires -- the partly-computed file is *not* moved over ``out``
    in that case.
    """
    try:
        from MathcadPy import Mathcad
    except ImportError as exc:  # pragma: no cover - depends on the machine
        raise RecalcError(
            "MathcadPy is not installed. It needs Mathcad Prime on this machine "
            'and Windows: pip install -e ".[mathcad]"') from exc

    started = time.monotonic()
    # A temp file inside the destination directory, so the final move is a
    # rename on the same volume and never a half-written destination.
    fd, tmp_name = tempfile.mkstemp(suffix=".mcdx", dir=out.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    # save_as refuses to overwrite in some Prime builds; hand it a free name.
    tmp.unlink(missing_ok=True)

    mathcad = Mathcad(visible=visible)
    # Dispatch attaches to a Prime that is already running. Closing that one
    # would take the user's other open worksheets with it.
    ours = not mathcad.worksheet_names()
    worksheet = None
    try:
        worksheet = mathcad.open(path.resolve())
        worksheet.calculate()
        deadline = started + timeout
        previous: bytes | None = None
        while True:
            worksheet.save_as(tmp)
            current = _cache(tmp)
            pending = pending_count(tmp)
            if pending == 0 and current == previous:
                break
            previous = current
            if time.monotonic() >= deadline:
                reason = (f"{pending} result(s) still marked Pending"
                          if pending else "the results were still changing")
                raise RecalcError(
                    f"{path.name}: {reason} after {timeout:g}s. The worksheet may "
                    "hold a slow solve block, or Prime may be showing a dialog. "
                    "Raise --timeout, or run with --visible to watch. Nothing was "
                    "written.")
            time.sleep(poll)
    finally:
        try:
            if worksheet is not None:
                worksheet.close(save_option="Discard")
            if ours:
                mathcad.quit()
        except Exception:  # pragma: no cover - COM teardown is best effort
            pass

    try:
        os.replace(tmp, out)
    except OSError:
        shutil.move(str(tmp), str(out))  # different volume
    finally:
        tmp.unlink(missing_ok=True)
    return time.monotonic() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="recalc_mcdx",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", type=Path, help="the .mcdx worksheet")
    parser.add_argument("-o", "--output", type=Path,
                        help="write here instead of updating the file in place")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="seconds to wait for the calculation (default: 120)")
    parser.add_argument("--visible", action="store_true",
                        help="show the Prime window while it calculates")
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"error: no such file: {args.file}", file=sys.stderr)
        return 2

    out = (args.output or args.file).resolve()
    try:
        elapsed = recalculate(args.file, out, timeout=args.timeout,
                              visible=args.visible)
    except RecalcError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"recalculated in {elapsed:.1f}s -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
