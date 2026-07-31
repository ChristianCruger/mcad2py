#!/usr/bin/env python3
"""Strip authoring metadata from Mathcad Prime ``.mcdx`` worksheets.

A ``.mcdx`` is a zip, and Prime stores who wrote a sheet -- and when, and on
whose machine -- in parts you never see in the application:

* ``docProps/core.xml``  -- ``dc:creator``, ``cp:lastModifiedBy``, timestamps,
  ``dc:title``/``dc:subject``/``dc:description``, ``cp:category``, keywords;
* ``docProps/app.xml``   -- ``Company``, ``Manager``, ``Template``;
* ``mathcad/header.xml`` / ``footer.xml`` -- the printed page header and footer,
  which typically carry a project number, a date and a company name.

Anyone who unzips the file can read all of it. This rewrites those parts in
place while leaving ``worksheet.xml`` and ``result.xml`` **byte-identical**, so
the maths, the cached results and therefore every test expectation are
untouched. It is metadata surgery, not a re-save.

    python tools/strip_mcdx_metadata.py references/*.mcdx
    python tools/strip_mcdx_metadata.py --check references/*.mcdx   # report only
    python tools/strip_mcdx_metadata.py --author "A. Engineer" sheet.mcdx

``--check`` exits non-zero if anything identifying is left, which makes it
usable as a pre-commit or CI guard.

Note this does *not* touch the sheet's visible content: text regions, variable
names and comments are yours to review. It also cannot rewrite what is already
in git history -- run it before committing a worksheet, not after.
"""

from __future__ import annotations

import argparse
import os
import re

import sys
import tempfile
import zipfile
from pathlib import Path

# Parts rewritten wholesale, and the replacement content.
_CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:creator>{author}</dc:creator><cp:lastModifiedBy>{author}</cp:lastModifiedBy></cp:coreProperties>"""

# docProps/app.xml is optional and Prime tolerates it being minimal.
_APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>PTC Mathcad Prime</Application></Properties>"""

# Header/footer: keep the part (Prime expects it) but empty its text.
_EMPTY_TEXT = re.compile(r">[^<>]+<")

# Fields worth reporting on in --check, by part.
_SENSITIVE = {
    "docProps/core.xml": ("creator", "lastModifiedBy", "title", "subject",
                          "description", "keywords", "category"),
    "docProps/app.xml": ("Company", "Manager", "Template"),
}


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def inspect(path: Path) -> list[str]:
    """Identifying values still present in ``path``, as ``part: field=value``."""
    import xml.etree.ElementTree as ET

    findings: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        for part, fields in _SENSITIVE.items():
            if part not in names:
                continue
            root = ET.fromstring(zf.read(part).decode("utf-8", "replace"))
            for elem in root.iter():
                value = (elem.text or "").strip()
                if value and _localname(elem.tag) in fields:
                    findings.append(f"{part}: {_localname(elem.tag)}={value!r}")
        for part in ("mathcad/header.xml", "mathcad/footer.xml"):
            if part not in names:
                continue
            root = ET.fromstring(zf.read(part).decode("utf-8", "replace"))
            text = " ".join(t.strip() for t in root.itertext() if t.strip())
            if text:
                findings.append(f"{part}: {text[:60]!r}")
    return findings


def strip(path: Path, author: str = "") -> bool:
    """Rewrite ``path``'s metadata parts in place. True if anything changed.

    The archive is rebuilt into a temporary file and moved over the original
    only on success, so an interrupted run can't leave a half-written
    worksheet behind.
    """
    with zipfile.ZipFile(path) as zf:
        entries = [(item, zf.read(item.filename)) for item in zf.infolist()]

    changed = False
    rewritten: list[tuple[zipfile.ZipInfo, bytes]] = []
    for item, data in entries:
        name = item.filename
        if name == "docProps/core.xml":
            new = _CORE_XML.format(author=author).encode("utf-8")
        elif name == "docProps/app.xml":
            new = _APP_XML.encode("utf-8")
        elif name in ("mathcad/header.xml", "mathcad/footer.xml"):
            # Blank the text runs but keep the element structure intact.
            new = _EMPTY_TEXT.sub("><", data.decode("utf-8", "replace")).encode("utf-8")
        else:
            new = data
        changed = changed or new != data
        rewritten.append((item, new))

    if not changed:
        return False

    # mkstemp hands back an *open* descriptor; close it before writing through
    # ZipFile, or the later move fails on Windows (a file open in this process
    # still counts as in use).
    fd, tmp_name = tempfile.mkstemp(suffix=".mcdx", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            for item, data in rewritten:
                # Reset the per-entry timestamp too -- it is its own small leak
                # of when (and in what order) the sheet was worked on.
                info = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                out.writestr(info, data)
        # os.replace, not shutil.move: it overwrites atomically on every
        # platform. shutil.move tries os.rename first, which on Windows refuses
        # an existing destination, and then falls back to copy-then-delete --
        # which is neither atomic nor safe if the worksheet happens to be open
        # in Mathcad at that moment.
        os.replace(tmp, path)
    except PermissionError as exc:
        tmp.unlink(missing_ok=True)
        raise PermissionError(
            f"{path}: could not be replaced ({exc}). Close it in Mathcad Prime "
            "and run again -- the original is untouched."
        ) from exc
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="strip_mcdx_metadata",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="+", type=Path, help=".mcdx files to process")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report identifying metadata without modifying anything; "
        "exit 1 if any is found",
    )
    parser.add_argument(
        "--author",
        default="",
        help="value for creator/lastModifiedBy (default: empty)",
    )
    args = parser.parse_args(argv)

    found_any = False
    for path in args.files:
        if not path.exists():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2
        if args.check:
            findings = inspect(path)
            found_any = found_any or bool(findings)
            if findings:
                print(f"{path.name}:")
                for line in findings:
                    print(f"    {line}")
            else:
                print(f"{path.name}: clean")
        else:
            before = inspect(path)
            strip(path, author=args.author)
            after = inspect(path)
            status = "clean" if not after else f"still has {len(after)} field(s)"
            print(f"{path.name}: stripped {len(before)} field(s) -> {status}")
            found_any = found_any or bool(after)

    return 1 if (args.check and found_any) else 0


if __name__ == "__main__":
    raise SystemExit(main())
