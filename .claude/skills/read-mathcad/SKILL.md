---
name: read-mathcad
description: Read, understand, and change a PTC Mathcad Prime worksheet (.mcdx). Use whenever the user references, attaches, or asks about a .mcdx file — to see its definitions, equations, units, and computed values as Python, to set an input value in the worksheet itself, or to have Mathcad Prime recompute it.
---

# Reading a Mathcad worksheet

A `.mcdx` is a zipped XML worksheet that can't be read directly. This repo's
`mcad2py` turns it into readable Python (with Pint units), which is the
fastest way to understand a sheet's math.

## How to read a `.mcdx`

Convert it to a `.py` script and read that (it preserves region order, comments, units,
and inline-evaluation results):

```bash
python -m mcad2py.cli convert "<path/to/file.mcdx>" -o - -f py
```

This prints the script to stdout. Read it top-to-bottom: `:=` becomes assignment, Mathcad's
inline `=` becomes a `print(... .to(unit))`, text regions become `# comments`.

To produce a notebook the user can run instead:

```bash
python -m mcad2py.cli convert "<path/to/file.mcdx>"   # writes <file>.ipynb
```

## Interpreting the output

- `x = 30 * ureg.MPa / 1.5` — a definition with units (Pint `ureg`).
- `x.to(ureg.MPa)` / `print(x.to(ureg.MPa))` — Mathcad showed this result inline.
- `tan(phi)`, `sin(...)`, `cot(...)` — angle-aware helpers from
  `mcad2py.runtime` (accept `deg` or `rad`), matching Mathcad trig.
- `math.pi` is `π`; Greek/subscripted names are transliterated (`β`->`beta`, `f_cd`).
- `# TODO unsupported: ...` — a construct the converter doesn't translate yet
  (solve blocks, programs, plots, ranges, matrices). Note it; don't trust it as math.

## Tracing back to the original file

If you need to edit the worksheet itself (fix a bad formula, or set an input value via
MathcadPy) rather than just read it, convert with `--trace-source`:

```bash
python -m mcad2py.cli convert "<path/to/file.mcdx>" -o - -f py --trace-source
```

Each statement is prefixed with `# mcdx region <id>` — that id is the `region-id`
attribute on the matching `<region>` element in `mathcad/worksheet.xml` inside the
`.mcdx` zip (unzip the file to find it). If the Python name was renamed from Mathcad's
(Greek letters, subscripts), the same comment shows the original, e.g.
`# mcdx region 12, "σ_c" -> sigma_c` — that's the name MathcadPy or Prime's UI actually
knows the value by, not the sanitized Python identifier.

If the author tagged regions with Prime's **Input/Output** panel (for MathcadPy's
Application Automation), the comment also shows that region's automation **alias** —
`# mcdx region 0, input alias "x"` / `# mcdx region 4, output alias "out"`. This alias
is the literal name MathcadPy's Application Automation API sets/reads that region by —
it's assigned separately from the Mathcad variable name and can differ from it (an
un-named output defaults to something like `out`/`out_0`). Only regions the author
explicitly flagged carry this; most don't. Check MathcadPy's own docs for the exact call
to set/read a value by alias before using one.

## Changing an input value

Two tools in `tools/` turn the region id above into a write. Use them together —
editing alone leaves the sheet's cached results stale.

**Warning: never edit a file in `references/`.** Those are test fixtures. Changing one
shifts every cached number the test suite compares against. Copy it somewhere else first.

### 1. Set the value

```bash
python tools/set_mcdx_value.py "<file.mcdx>" --list                    # what is settable
python tools/set_mcdx_value.py "<file.mcdx>" --region 1 --value 45     # theta := 45 deg
python tools/set_mcdx_value.py "<file.mcdx>" --region 1 --value 45 --dry-run
```

It edits the file in place; `-o out.mcdx` writes a copy instead. `--unit rad` changes the
unit too, and `--unit ""` removes it; leave `--unit` off to keep the one that is there.

Only a **literal** definition can be set — `theta := 34 deg`, `n := 5`. The tool refuses a
formula, a matrix, a range or a function definition rather than overwrite the sheet's math.
Use `--list` (or `--trace-source`) to see which regions qualify.

### 1b. A number *inside* a formula

When the number you want is part of an expression — the `1.5` in `f_cd := 30 MPa / 1.5` —
`set_mcdx_value.py` refuses the region. Use `set_mcdx_literal.py` instead. It leaves the
expression tree alone and replaces one number in it.

```bash
python tools/set_mcdx_literal.py "<file.mcdx>" --region 0 --list --json
python tools/set_mcdx_literal.py "<file.mcdx>" --region 0 --index 1 --expect 1.5 --value 1.4
```

Always run `--list` first: it gives each number an `index`, its current value, its unit and
its **kind**. `--expect` is required and states the number you believe sits at that index —
a wrong index then stops the run instead of changing the wrong number. The tool converts the
region to Python before and after, and prints both lines, so you can check the edit landed
where you meant.

Three kinds are gated behind `--allow-kind`, because they change what the formula *means*
rather than what it is worth: `exponent` (a power, or a unit's `cm²`), `index` (a subscript)
and `display-scale` (a number in the unit override). Do not pass `--allow-kind` unless the
user asked for that specific change.

`--unit kPa` renames the unit of a scaled number such as `30 MPa`. It cannot add or remove a
unit inside a formula — that reshapes the tree, so do it in Prime.

Prefer `set_mcdx_value.py` whenever the region is a plain input. Reach for this tool only
when the number is inside an expression.

### 1c. A whole formula

To change the maths itself — add a factor, swap a term — use `set_mcdx_formula.py`. Write the new
formula as **the same Python the converter prints**, which is what you already read.

```bash
python tools/set_mcdx_formula.py "<file.mcdx>" --region 0 --list --json
python tools/set_mcdx_formula.py "<file.mcdx>" --region 0     --expect "30 * ureg.MPa / 1.5" --value "0.85 * 30 * ureg.MPa / 1.5"
```

Run `--list` first: it prints each region's current formula and marks the ones outside the writable
subset. `--expect` is required and states the formula you believe is there.

The subset is small on purpose: numbers, units, `+ - * / **`, negation, and **names the sheet
already uses**. A call (`tan(phi)`), a matrix, an index, or a new name is refused. The tool also
refuses a region it cannot reproduce byte for byte — one holding a `%` sign, a line break inside
the equation, or a redundant bracket — rather than restyle maths your edit does not touch.

Reach for the tools in this order: `set_mcdx_value.py` for a plain input, `set_mcdx_literal.py` for
one number inside a formula, and this one only when the *shape* of the formula changes.

### 2. Make Mathcad recompute

The converter never runs Mathcad, so after step 1 the sheet's own
`mathcad/result.xml` still holds the numbers computed for the **old** input. Do not read
that cache until it is refreshed.

```bash
python tools/recalc_mcdx.py "<file.mcdx>"              # in place
python tools/recalc_mcdx.py "<file.mcdx>" --visible    # watch the Prime window
```

This needs **Mathcad Prime installed on the machine** and `MathcadPy`
(`pip install -e ".[mathcad]"`), both Windows-only. If either is missing, say so — do not
try to fake the recomputed values. The generated Python is still a valid answer on its own:
it evaluates the new value for real, with units.

The tool waits for Prime's calculation to finish before it saves; a run takes a few seconds
on a small sheet. Raise `--timeout` for a sheet with a slow solve block.

### 3. Confirm

Convert again and run it, then compare against the refreshed cache. On `trig.mcdx` with
`theta` moved from 34° to 45°, all 19 values agreed to the last digit. Remember the cache
stores **base SI**, so `45 deg` reads back as `0.7853981633974483` rad — that is a match,
not a mismatch.

## Verifying numbers (optional)

To confirm computed values, run the generated script — it executes with real Pint units:

```bash
python -m mcad2py.cli convert "<file.mcdx>" -f py > /tmp/sheet.py && python /tmp/sheet.py
```

The original file's cached results live inside it at `mathcad/result.xml` (unzip the
`.mcdx`) if you need to compare against what Mathcad itself computed.
