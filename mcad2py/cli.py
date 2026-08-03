"""Command-line interface: ``mcad2py convert file.mcdx -o out.ipynb``."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from .convert import convert_file

__version__ = version("mcad2py")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcad2py",
        description="Convert PTC Mathcad Prime (.mcdx) worksheets to Python / Jupyter.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    conv = sub.add_parser("convert", help="convert a .mcdx file")
    conv.add_argument("input", type=Path, help="path to the .mcdx file")
    conv.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output file; '-' for stdout. Default: input with .ipynb/.py suffix.",
    )
    conv.add_argument(
        "-f",
        "--format",
        choices=["notebook", "py"],
        help="output format (default: inferred from -o suffix, else notebook).",
    )

    args = parser.parse_args(argv)
    if args.command == "convert":
        return _run_convert(args)
    parser.error("unknown command")
    return 2


def _run_convert(args: argparse.Namespace) -> int:
    fmt = args.format or _infer_format(args.output)
    try:
        result = convert_file(args.input, fmt=fmt)
    except (OSError, ValueError) as exc:
        # The loader raises these with user-facing messages (missing file, not a
        # zip, no worksheet.xml), so print the message rather than a traceback.
        # OSError (which FileNotFoundError subclasses) also covers the read
        # failures underneath -- a permission problem, a dead network drive --
        # which are equally not the user's bug to debug.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output is None:
        suffix = ".ipynb" if fmt == "notebook" else ".py"
        out_path = args.input.with_suffix(suffix)
    elif str(args.output) == "-":
        sys.stdout.write(result)
        return 0
    else:
        out_path = args.output

    out_path.write_text(result, encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


def _infer_format(output: Path | None) -> str:
    if output is not None and output.suffix == ".py":
        return "py"
    return "notebook"


if __name__ == "__main__":
    raise SystemExit(main())
