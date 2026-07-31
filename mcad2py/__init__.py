"""Convert PTC Mathcad Prime (.mcdx) worksheets to Python / Jupyter notebooks."""

from importlib.metadata import PackageNotFoundError, version as _version

from .convert import convert_file, convert_worksheet

try:
    # Read the installed distribution's metadata rather than keeping a second
    # copy of the number here: pyproject.toml stays the single source of truth,
    # so the two can't drift (and a release that stamps the version only has to
    # touch one file).
    __version__ = _version("mcad2py")
except PackageNotFoundError:  # imported from a source tree, not installed
    __version__ = "0.0.0.dev0"

__all__ = ["convert_file", "convert_worksheet", "__version__"]
