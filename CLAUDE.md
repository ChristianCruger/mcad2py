# CLAUDE.md

Guidance for working in this repo.

## What this is

`mathcad-converter` converts PTC **Mathcad Prime** worksheets (`.mcdx`) into runnable Python —
a **Jupyter notebook** (primary) or a `.py` script. Units are preserved with **Pint**. The end
goal includes a Claude skill (`.claude/skills/read-mathcad/`) so Claude can read `.mcdx` files.

A `.mcdx` is a zip of XML; the math is stored as an expression tree, so conversion walks that
tree into an IR and emits Python from it.

## Commands

```bash
pip install -e .                                    # install (deps: pint, nbformat; pytest for tests)
mcad2py convert file.mcdx                           # -> file.ipynb
mcad2py convert file.mcdx -f py -o -                # -> stdout as .py
python -m mathcad_converter.cli convert file.mcdx   # same, without console-script install
pytest                                              # run the suite
```

## Architecture — a pipeline with an IR in the middle

```
.mcdx ─load─▶ regions ─parse─▶ IR (our AST) ─emit─▶ .ipynb / .py
```

The **IR is the key design choice**: it decouples XML parsing from code generation, so a future
`.xmcd` (Mathcad 15) front-end or a SymPy backend can be added without touching the other half.
When adding features, respect this boundary — parsers produce IR, backends consume IR.

| File | Role |
|------|------|
| [loader.py](mathcad_converter/loader.py) | Unzip `.mcdx`; return `worksheet.xml`, `result.xml`, XAML text packages, rels map |
| [parser/namespaces.py](mathcad_converter/parser/namespaces.py) | Namespace constants; `localname()` strips `{ns}` — **match on local name, not full URI** (Prime bumps version numbers) |
| [parser/expressions.py](mathcad_converter/parser/expressions.py) | Recursive XML→IR walk; identifier reading (subscripts/Greek), `sanitize()` |
| [parser/regions.py](mathcad_converter/parser/regions.py) | Worksheet→ordered regions; **sort by (top, left)** for reading order |
| [ir.py](mathcad_converter/ir.py) | Backend-agnostic node dataclasses |
| [mapping.py](mathcad_converter/mapping.py) | Data tables: operators, builtins, constants, Greek, unit aliases |
| [runtime.py](mathcad_converter/runtime.py) | Angle-aware `sin/cos/tan/cot` imported by generated code |
| [emit/codegen.py](mathcad_converter/emit/codegen.py) | Precedence-aware expression printer; shared by both backends |
| [emit/notebook_backend.py](mathcad_converter/emit/notebook_backend.py) | IR→`.ipynb`; region→cell; bare last line echoes result |
| [emit/py_backend.py](mathcad_converter/emit/py_backend.py) | IR→`.py`; evaluations become `print(...)` |
| [convert.py](mathcad_converter/convert.py) | Orchestration: `convert_file` / `convert_worksheet` |

## Confirmed Prime schema (from `references/.../worksheet.xml`)

- Namespaces: `ws=worksheet50`, `ml=math50`, `u=units10`, `p=provenance10`.
- `<region top= left=>` → sort by position. `<math resultRef=N>` links to `result.xml`.
- `<ml:define>` = `:=`; `<ml:eval>` = inline `=`, carries `<ml:unitOverride>` (display unit, or
  `<ml:placeholder/>` = auto) → drives `.to(ureg.<unit>)`.
- `<ml:apply>`: first child is the operator (empty tag: `div mult plus minus pow scale nthRoot`)
  **or** an `<ml:id labels="FUNCTION">` (function call). `scale` = number×unit ("30 MPa").
  `nthRoot` with empty first child = √.
- `<ml:id labels="...">` roles: `VARIABLE`/`UNIT`/`FUNCTION`/`CONSTANT` — use them, don't guess.
- Subscripts: `f<pw:Subscript>cd</pw:Subscript>` → `f_cd`. Greek is literal unicode.
- Text regions: content is in `mathcad/xaml/FlowDocumentN.XamlPackage` (a nested zip),
  linked via `item-idref` → `worksheet.xml.rels`. See [text.py](mathcad_converter/text.py).

## Conventions

- Generated trig uses runtime helpers (`tan(phi)`), not `math.tan(phi.to('rad').magnitude)`.
- Display units come from `unitOverride`; emit `x.to(ureg.<unit>)` for the echo.
- Unknown/unsupported constructs emit a visible `# TODO unsupported: <note>` so output still
  loads — never silently drop a region.
- Add new builtins/units/constants to [mapping.py](mathcad_converter/mapping.py) (data, not code).

## Testing

[tests/test_convert.py](tests/test_convert.py) converts `references/plain_concrete_cohesion.mcdx`,
**executes** the generated Python, and asserts values match Mathcad's cached `result.xml`
(~14 sig figs). When adding a sample, prefer this execute-and-compare-to-`result.xml` style.

## Not yet supported (next targets)

Solve blocks (Given/Find), Mathcad programs, range variables, matrices, plots. Each currently
becomes a `# TODO unsupported` stub. Known gap: square roots emit `math.sqrt(x)` (fine for
dimensionless args); switch to `x ** 0.5` when a unit-bearing root appears so Pint handles units.

## Scope

Prime `.mcdx` only (`worksheet50`/`math50`). Legacy `.xmcd` (Mathcad 15, `math30`) is a future
front-end — add it as a new parser producing the same IR.
