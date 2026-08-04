"""XML namespace constants for PTC Mathcad Prime worksheets.

Confirmed from a real Prime worksheet (`worksheet.xml`):

    xmlns:ws = http://schemas.mathsoft.com/worksheet50
    xmlns:ml = http://schemas.mathsoft.com/math50
    xmlns:u  = http://schemas.mathsoft.com/units10
    xmlns:p  = http://schemas.mathsoft.com/provenance10
    xmlns    = http://schemas.mathsoft.com/worksheet50   (default)

Rather than hard-code version numbers everywhere (Prime bumps them between
releases), the parser matches on the *local* tag name via :func:`localname`.
"""

WORKSHEET = "http://schemas.mathsoft.com/worksheet50"
MATH = "http://schemas.mathsoft.com/math50"
UNITS = "http://schemas.mathsoft.com/units10"
PROVENANCE = "http://schemas.mathsoft.com/provenance10"

# mathcad/integration.xml -- Application Automation (MathcadPy) Input/Output
# region tags. A sibling part to worksheet.xml, present (possibly empty) in
# every .mcdx Prime writes.
INTEGRATION = "http://schemas.ptc.com/integration10"

# XAML (used inside <text> regions and subscripted identifiers).
XAML = "http://schemas.microsoft.com/winfx/2006/xaml/presentation"


def localname(tag: str) -> str:
    """Strip the ``{namespace}`` prefix from an ElementTree tag.

    ``"{http://schemas.mathsoft.com/math50}apply"`` -> ``"apply"``
    """
    if tag and tag[0] == "{":
        return tag.split("}", 1)[1]
    return tag
