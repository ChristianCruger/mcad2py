"""Extract plain text from a Mathcad text region's FlowDocument XamlPackage.

A ``.XamlPackage`` is itself a zip containing ``Xaml/Document.xaml`` (a WPF
FlowDocument). We only need the readable text: the ``<Run>`` contents, with
``<Paragraph>`` boundaries becoming newlines.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from .parser.namespaces import localname


def extract_text(xaml_package: bytes) -> str:
    """Return the plain text of a FlowDocument XamlPackage (best effort)."""
    try:
        with zipfile.ZipFile(io.BytesIO(xaml_package)) as zf:
            doc_name = next(
                (n for n in zf.namelist() if n.lower().endswith("document.xaml")),
                None,
            )
            if doc_name is None:
                return ""
            doc_xml = zf.read(doc_name).decode("utf-8")
    except (zipfile.BadZipFile, KeyError):
        return ""

    root = ET.fromstring(doc_xml)
    paragraphs: list[str] = []
    for para in root.iter():
        if localname(para.tag) != "Paragraph":
            continue
        runs = [
            (run.text or "")
            for run in para.iter()
            if localname(run.tag) == "Run"
        ]
        line = "".join(runs).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)
