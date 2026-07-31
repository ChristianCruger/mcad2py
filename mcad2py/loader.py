"""Load a Mathcad Prime ``.mcdx`` file (a ZIP / OPC package).

A ``.mcdx`` is a zip archive. The interesting parts:

    mathcad/worksheet.xml   -> regions (the math + text layout)
    mathcad/result.xml      -> cached numeric results (used for verification)
    mathcad/xaml/*.XamlPackage -> text-region content (nested zips)
    mathcad/media/*         -> embedded images (picture regions)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class McdxPackage:
    """The raw bytes/text we care about from an unzipped ``.mcdx``."""

    worksheet_xml: str
    result_xml: str | None = None
    xaml_packages: dict[str, bytes] = field(default_factory=dict)
    # Basename -> bytes for embedded images (``mathcad/media/*``).
    media: dict[str, bytes] = field(default_factory=dict)
    # Relationship id (region's ``item-idref``) -> target basename.
    rels: dict[str, str] = field(default_factory=dict)

    @property
    def has_results(self) -> bool:
        return bool(self.result_xml)

    def text_package(self, idref: str) -> bytes | None:
        """The XamlPackage bytes for a text region's ``item-idref``."""
        basename = self.rels.get(idref)
        if basename is None:
            return None
        return self.xaml_packages.get(basename)

    def image(self, idref: str) -> tuple[str, bytes] | None:
        """The (basename, bytes) for a picture region's ``item-idref``."""
        basename = self.rels.get(idref)
        if basename is None:
            return None
        data = self.media.get(basename)
        return (basename, data) if data is not None else None


def load_mcdx(path: str | Path) -> McdxPackage:
    """Open a ``.mcdx`` file and return its key parts.

    Raises ``FileNotFoundError`` if the path doesn't exist and ``ValueError``
    if it isn't a readable Prime worksheet -- either not a zip at all (a
    corrupt download, or a legacy ``.xmcd``, which is a different format) or a
    zip without ``mathcad/worksheet.xml``. Both carry a message meant to be
    shown to a user as-is; the CLI prints them without a traceback.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no such file: {path}")

    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ValueError(
            f"{path}: not a readable .mcdx file ({exc}). A Mathcad Prime "
            "worksheet is a zip archive; a Mathcad 15 .xmcd file is not one "
            "and is not supported yet."
        ) from exc

    with zf:
        names = set(zf.namelist())

        worksheet_name = _find(names, "mathcad/worksheet.xml")
        if worksheet_name is None:
            raise ValueError(
                f"{path}: no mathcad/worksheet.xml found; is this a Mathcad Prime file?"
            )
        worksheet_xml = zf.read(worksheet_name).decode("utf-8")

        result_name = _find(names, "mathcad/result.xml")
        result_xml = zf.read(result_name).decode("utf-8") if result_name else None

        xaml_packages = {
            name.rsplit("/", 1)[-1]: zf.read(name)
            for name in names
            if name.lower().endswith(".xamlpackage")
        }

        media = {
            name.rsplit("/", 1)[-1]: zf.read(name)
            for name in names
            if name.lower().endswith(_IMAGE_EXTS)
        }

        rels_name = _find(names, "mathcad/_rels/worksheet.xml.rels")
        rels = _parse_rels(zf.read(rels_name).decode("utf-8")) if rels_name else {}

    return McdxPackage(
        worksheet_xml=worksheet_xml,
        result_xml=result_xml,
        xaml_packages=xaml_packages,
        media=media,
        rels=rels,
    )


_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg")


def _parse_rels(xml: str) -> dict[str, str]:
    """Map each relationship Id to the basename of its target file."""
    rels: dict[str, str] = {}
    for rel in ET.fromstring(xml):
        rel_id = rel.get("Id")
        target = rel.get("Target")
        if rel_id and target:
            rels[rel_id] = target.replace("\\", "/").rsplit("/", 1)[-1]
    return rels


def _find(names: set[str], target: str) -> str | None:
    """Locate an archive member case-insensitively, tolerating path separators."""
    target_norm = target.lower().replace("\\", "/")
    for name in names:
        if name.lower().replace("\\", "/") == target_norm:
            return name
    return None
