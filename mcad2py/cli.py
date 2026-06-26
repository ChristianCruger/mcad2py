"""Command-line interface: ``mcad2py convert file.mcdx -o out.ipynb``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .convert import convert_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcad2py",
        description="Convert PTC Mathcad Prime (.mcdx) worksheets to Python / Jupyter.",
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
    except (FileNotFoundError, ValueError) as exc:
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
