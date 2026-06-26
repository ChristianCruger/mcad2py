---
name: read-mathcad
description: Read and understand a PTC Mathcad Prime worksheet (.mcdx). Use whenever the user references, attaches, or asks about a .mcdx file — to see its definitions, equations, units, and computed values as Python.
---

# Reading a Mathcad worksheet

A `.mcdx` is a zipped XML worksheet that can't be read directly. This repo's
`mathcad-converter` turns it into readable Python (with Pint units), which is the
fastest way to understand a sheet's math.

## How to read a `.mcdx`

Convert it to a `.py` script and read that (it preserves region order, comments, units,
and inline-evaluation results):

```bash
python -m mathcad_converter.cli convert "<path/to/file.mcdx>" -o - -f py
```

This prints the script to stdout. Read it top-to-bottom: `:=` becomes assignment, Mathcad's
inline `=` becomes a `print(... .to(unit))`, text regions become `# comments`.

To produce a notebook the user can run instead:

```bash
python -m mathcad_converter.cli convert "<path/to/file.mcdx>"   # writes <file>.ipynb
```

## Interpreting the output

- `x = 30 * ureg.MPa / 1.5` — a definition with units (Pint `ureg`).
- `x.to(ureg.MPa)` / `print(x.to(ureg.MPa))` — Mathcad showed this result inline.
- `tan(phi)`, `sin(...)`, `cot(...)` — angle-aware helpers from
  `mathcad_converter.runtime` (accept `deg` or `rad`), matching Mathcad trig.
- `math.pi` is `π`; Greek/subscripted names are transliterated (`β`->`beta`, `f_cd`).
- `# TODO unsupported: ...` — a construct the converter doesn't translate yet
  (solve blocks, programs, plots, ranges, matrices). Note it; don't trust it as math.

## Verifying numbers (optional)

To confirm computed values, run the generated script — it executes with real Pint units:

```bash
python -m mathcad_converter.cli convert "<file.mcdx>" -f py > /tmp/sheet.py && python /tmp/sheet.py
```

The original file's cached results live inside it at `mathcad/result.xml` (unzip the
`.mcdx`) if you need to compare against what Mathcad itself computed.
