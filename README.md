# mcad2py

Convert PTC **Mathcad Prime** worksheets (`.mcdx`) into runnable Python — either a
**Jupyter notebook** (one region per cell, results echoed inline like Mathcad's `=`) or a
plain `.py` script. Units are preserved with [Pint](https://pint.readthedocs.io/).

A `.mcdx` file is a zip archive of XML; the math is stored as an expression tree, so the
conversion walks that tree into an intermediate representation and emits Python from it.

## Install

```bash
pip install -e .
```

Dependencies: `pint`, `nbformat` (and `pytest` for the tests).

## Usage

```bash
# Jupyter notebook (default)
mcad2py convert worksheet.mcdx                 # -> worksheet.ipynb
mcad2py convert worksheet.mcdx -o out.ipynb

# Plain Python script
mcad2py convert worksheet.mcdx -f py           # -> worksheet.py
mcad2py convert worksheet.mcdx -o - -f py      # to stdout
```

Or from Python:

```python
from mcad2py import convert_file
print(convert_file("worksheet.mcdx", fmt="py"))
```

### Example

A Mathcad region `f_cd := 30 MPa / 1.5 =` (displayed in MPa) becomes, in a notebook cell:

```python
f_cd = 30 * ureg.MPa / 1.5
f_cd.to(ureg.MPa)        # the bare last line echoes "20 megapascal", like Mathcad's "="
```

Mathcad trig handles angle units automatically; generated code matches this via small
angle-aware helpers (`from mcad2py.runtime import sin, cos, tan, cot`), so
`tan(phi)` works whether `phi` is in `deg` or `rad`.

## What's supported

- `:=` definitions and inline `=` evaluations (with display-unit overrides)
- Arithmetic (`+ - * / ^`), unit scaling (`30 MPa`), roots, parentheses
- Built-in functions (`sin`, `cos`, `tan`, `cot`, `exp`, `ln`, `log`, `sqrt`, ...)
- Constants (`π`, `e`), Greek/subscripted identifiers (`f_cd`, `β`, `ϕ` -> `f_cd`, `beta`, `phi`)
- Text/comment regions -> markdown cells / comments

Unsupported constructs (solve blocks, programs, plots, ranges, matrices) are emitted as
clearly marked `# TODO unsupported` stubs so output still loads; these are the next targets.

## Tests

```bash
pytest
```

The suite converts the reference worksheet in `references/`, executes the generated code, and
checks the computed values against Mathcad's own cached results in the file's `result.xml`.

## Scope

Targets Mathcad **Prime** (`.mcdx`, `worksheet50`/`math50` schema). Legacy Mathcad 15
(`.xmcd`) is a future target — the parser is structured behind an intermediate representation
so a second front-end can be added without changing the code generators.
