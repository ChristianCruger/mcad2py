# CLAUDE.md

Guidance for working in this repo.

## What this is

`mcad2py` converts PTC **Mathcad Prime** worksheets (`.mcdx`) into runnable Python —
a **Jupyter notebook** (primary) or a `.py` script. Units are preserved with **Pint**. The end
goal includes a Claude skill (`.claude/skills/read-mathcad/`) so Claude can read `.mcdx` files.

A `.mcdx` is a zip of XML; the math is stored as an expression tree, so conversion walks that
tree into an IR and emits Python from it.

## Commands

```bash
pip install -e .                                    # install (deps: pint, nbformat, sympy, numpy, scipy, matplotlib, Pillow; pytest for tests)
mcad2py convert file.mcdx                           # -> file.ipynb
mcad2py convert file.mcdx -f py -o -                # -> stdout as .py
python -m mcad2py.cli convert file.mcdx   # same, without console-script install
pytest                                              # run the suite
```

## Architecture — a pipeline with an IR in the middle

```
.mcdx ─load─▶ regions ─parse─▶ IR (our AST) ─emit─▶ .ipynb / .py
                                    ▲
                              shape inference
```

The **IR is the key design choice**: it decouples XML parsing from code generation, so a future
`.xmcd` (Mathcad 15) front-end or a SymPy backend can be added without touching the other half.
When adding features, respect this boundary — parsers produce IR, backends consume IR.

| File | Role |
|------|------|
| [loader.py](mcad2py/loader.py) | Unzip `.mcdx`; return `worksheet.xml`, `result.xml`, XAML text packages, rels map |
| [parser/namespaces.py](mcad2py/parser/namespaces.py) | Namespace constants; `localname()` strips `{ns}` — **match on local name, not full URI** (Prime bumps version numbers) |
| [parser/expressions.py](mcad2py/parser/expressions.py) | Recursive XML→IR walk; identifier reading (subscripts/Greek), `sanitize()` |
| [parser/regions.py](mcad2py/parser/regions.py) | Worksheet→ordered regions; **sort by (top, left)** for reading order; collapsible `<Area>`s flattened away (their coords are area-relative) |
| [ir.py](mcad2py/ir.py) | Backend-agnostic node dataclasses |
| [shapes.py](mcad2py/shapes.py) | Post-parse IR pass: infers each name's shape across the sheet so Mathcad's one `·` splits into scalar `*` vs. `matmul` |
| [mapping.py](mcad2py/mapping.py) | Data tables: operators, builtins, constants, Greek, unit aliases |
| [runtime.py](mcad2py/runtime.py) | Helpers imported by generated code: the full angle-aware trig + hyperbolic families, the full vector/matrix family (`rows`/`identity`/`det`/`lsolve`/the norm & condition sets/the eigen set/`sort`…), `col`/`arange`/`index_build`/`vectorize`/`transpose`, `linterp` (unit-aware linear interp), `integral` (scipy `quad`), `summation`, `solve_block` (scipy `fsolve`), `sample`/`plot_domain`/`plot_axis` (matplotlib plots) |
| [emit/codegen.py](mcad2py/emit/codegen.py) | Precedence-aware expression printer; shared by both backends |
| [emit/notebook_backend.py](mcad2py/emit/notebook_backend.py) | IR→`.ipynb`; region→cell; bare last line echoes result |
| [emit/py_backend.py](mcad2py/emit/py_backend.py) | IR→`.py`; evaluations become `print(...)` |
| [convert.py](mcad2py/convert.py) | Orchestration: `convert_file` / `convert_worksheet` |

## Confirmed Prime schema

The full, detailed schema-to-IR mapping (namespaces, `<ml:define>`/`<ml:eval>`, operators, ranges,
vectors/matrices, programs/if, solve blocks, plots, controls, etc.) has moved to
[docs/mcdx-schema-notes.md](docs/mcdx-schema-notes.md) — read it before touching the parser or
adding support for a new XML construct.

## Conventions

- Generated trig uses runtime helpers (`tan(phi)`), not `math.tan(phi.to('rad').magnitude)`.
- Display units come from `unitOverride`; emit `x.to(ureg.<unit>)` for the echo (or `x / (<scale>)`
  when the override is a pure numeric scale like `10**-6` — see `_display`). With *no* override, an
  echo whose value contains a **division** is wrapped `disp(<expr>)` so a dimensionless-but-unreduced
  ratio (`mm²/m²`, `1/degree`) collapses the way Mathcad shows it.
- Unknown/unsupported constructs emit a visible `# TODO unsupported: <note>` so output still
  loads — never silently drop a region.
- `--trace-source` (opt-in, default off) annotates each generated statement with
  `# mcdx region <id>` — the originating `<region>`'s `region-id` in `worksheet.xml` — plus any
  renamed target's original Mathcad name (`# mcdx region 12, "σ_c" -> sigma_c`) and, if the region
  is tagged via Prime's Input/Output panel, its Application Automation alias from
  `mathcad/integration.xml` (`# mcdx region 0, input alias "x"`) — the literal name MathcadPy sets
  or reads the region by, which can differ from both the Mathcad and Python names (an un-named
  output defaults to e.g. `out`/`out_0`). This lets the `read-mathcad` skill trace a line of
  generated Python back to the source XML node (to edit it) or the name MathcadPy automation
  actually knows it by. `ir.Region.source` (an `ir.SourceRef`) is always populated during parsing
  regardless of the flag; only emission is gated. A `<spec-table>` column group shares one
  `region-id` (its per-column `resultRef` isn't captured). `integration.xml` is a sibling zip part
  to `worksheet.xml`, present (usually as a bare `<regions/>`) in every `.mcdx`.
- Add new builtins/units/constants to [mapping.py](mcad2py/mapping.py) (data, not code).
- Run [tools/strip_mcdx_metadata.py](tools/strip_mcdx_metadata.py) on any new fixture before
  committing: it removes the authoring metadata a `.mcdx` carries in parts you never see in Prime
  (`docProps/core.xml`'s `creator`/`lastModifiedBy`, `docProps/app.xml`'s `Company`, and the printed
  header/footer). It rewrites only those parts — `worksheet.xml` and `result.xml` stay
  **byte-identical**, so no cached value or test expectation moves. `--check` is the same scan as a
  report and is wired into CI so a later worksheet can't quietly reintroduce a name.
- Mathcad's `·` is scalar, matrix *and* dot product; [shapes.py](mcad2py/shapes.py) decides which by
  inferring shapes across the whole sheet, and only rewrites to `matmul` when **both** operands are
  provably arrays (never under a vectorize arrow). Give a new array-returning builtin an entry in its
  `_CALL_KINDS` table.

## Testing

Tests convert a `references/*.mcdx`, **execute** the generated Python, and assert that values match
Mathcad's cached `result.xml` (~14 sig figs). Prefer that execute-and-compare style when adding a sample.

Per-test detail — which fixture pins which feature, and the documented divergences (stale caches, LAPACK
eigenvalue ordering, Pint's Julian year) — lives in [docs/test-coverage.md](docs/test-coverage.md); read
the entry for a test before changing it, and add one when you add a fixture.

**Reference files are test fixtures — don't edit them.** Tests compare generated output against each
`.mcdx`'s cached `result.xml`; changing a worksheet (e.g. a `phi` value) silently shifts every
dependent cached number and breaks the hardcoded expected values.

## Not yet supported (next targets)

For a full **function-catalog coverage map** — every Mathcad function category vs. what we emit, plus a
prioritized TODO — see [docs/mathcad-function-coverage.md](docs/mathcad-function-coverage.md).

`find` solve blocks and `lsolve` work; `minerr`/`maximize`/`minimize`/`root`/`polyroots` don't yet.
`solve_block` (runtime) falls back
to a bounded random-restart search when `fsolve` reports success without actually reducing the
residual (a locally-flat/degenerate Jacobian, seen on `references/biaxial_bending.mcdx`'s double
integral) — capped at one retry so a bad case costs a few minutes, not tens; it prints a warning and
returns its best candidate if that still doesn't confirm convergence, rather than silently returning a
wrong answer.
Multi-line **imperative programs** (loops, local `←` assigns, `return`, `tryCatch`, program-built
vectors) are now supported (`ir.ProgramBlock` → a Python `def`; `X[i] :=` → `vec_set`); a single-arg
branching/clamp function is wrapped `elementwise` so the vectorize arrow applies it per element (see the
RC_col schema notes). Square roots now emit `nth_root(x, n)` (a *dimensioned* radicand keeps its unit; a
dimensionless one reduces first). Parametric xy plots (both axes are data vectors, e.g. a section
outline) now render correctly — a sampling domain is only inferred when an axis is a bare *range* (see
the schema note) — and an xy plot whose variable is never *defined* gets Mathcad's invented -10..10
domain (also a schema note). The **trig and hyperbolic families are complete** (including `sec`/`csc`/`sinc`,
`atan2`/`angle`, and all six inverse hyperbolics), with `acot`'s Maple/MuPAD `(0, π)` branch confirmed
against a cached negative argument (see the schema note). The **vector & matrix family is complete**,
the **table searches** (`match`/`lookup`/`vlookup`/`hlookup`/`vhlookup`) included — and with it come the
two-subscript read/write forms and the `·`-disambiguating shape pass. Two things there are *not*
byte-reproducible and shouldn't be treated as bugs: LAPACK's **eigenvalue ordering** differs from
Mathcad's for nonsymmetric matrices and for `genvals` (the multisets agree), and **eigenvector signs**
are arbitrary in any implementation.
`TOL`/`CTOL` from `calculation.xml` aren't consumed yet (solve uses fsolve defaults).
Scriptable-control JScript is **intentionally** not transpiled — we surface the control's cached
output value (the `RL` attribute) instead, which is faithful as long as the worksheet was last saved
with the desired selection. A control with no cached `RL` falls back to a `# TODO unsupported` region.

Nice-to-have: an opt-in `--externalize-images` (or `--media-dir`) flag that writes picture
regions as sidecar files next to the output notebook and references them with a relative link,
instead of the default self-contained base64 embed. Only meaningful for file output (not `-o -`
stdout); keep embedding as the default since it stays portable. Wanted mainly to keep git diffs
clean when generated notebooks are committed.

Nice-to-have: a **write path** into `mathcad/integration.xml` to tag a region as an Input/Output for
MathcadPy automation when the sheet's author never used Prime's Input/Output panel — i.e. `--trace-source`
reads these tags (see the Conventions bullet above), this would let Claude *add* one. Mechanically cheap:
append `<region region-id="N" ioTagType="Input"><inputAliases><alias>NAME</alias></inputAliases></region>`
to the part's `<regions>` (`Output`/`outputAliases` for the other direction) and rezip — confirmed via
`references/io.mcdx` that `integration.xml` carries no checksum and isn't even referenced via an OPC
relationship (Prime finds it by well-known path), so no other part needs to change. Two things a tool
should check before writing: the target region should be a plain literal `ir.Define` (a formula region
tagged Input would have automation overwrite the formula, not a value) and the new alias shouldn't collide
with an existing one in the file. Unverified: whether Prime's automation engine honors a hand-inserted tag
it didn't write itself, and whether it survives a later human re-save in Prime — no access to Prime/MathcadPy
here to confirm round-trip fidelity. Shape: a small `tools/tag_mcdx_input.py` (mirroring
`strip_mcdx_metadata.py`) doing the write, plus a skill layer that knows when to reach for it and applies
the two checks above — not folded into the converter itself, since this is a write path into a proprietary
format rather than `--trace-source`'s read-only annotation.

## Scope

Prime `.mcdx` only (`worksheet50`/`math50`). Legacy `.xmcd` (Mathcad 15, `math30`) is a future
front-end — add it as a new parser producing the same IR.
