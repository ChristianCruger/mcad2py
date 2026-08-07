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
| [units.py](mcad2py/units.py) | The one Pint registry generated modules and `const.py` share |
| [const.py](mcad2py/const.py) | Mathcad's built-in physical constants as importable Pint quantities |
| [runtime.py](mcad2py/runtime.py) | Helpers imported by generated code: the full angle-aware trig + hyperbolic families, the full vector/matrix family (`rows`/`identity`/`det`/`lsolve`/the norm & condition sets/the eigen set/`sort`…), the full statistics family (`median`/`mode`/`var`/`Var`/`percentile`/`histogram`/`corr`/`slope`/`Spear`… plus the `d`/`p`/`q`/`r` sets for `norm`/`t`/`weibull`), `col`/`arange`/`index_build`/`vec_set`/`vectorize`/`transpose`, `linterp` (unit-aware linear interp), `integral` (scipy `quad`), `summation`, `solve_block` (scipy `fsolve`), `sample`/`plot_domain`/`plot_axis`/`plot_trace` (matplotlib plots) |
| [emit/codegen.py](mcad2py/emit/codegen.py) | Precedence-aware expression printer; shared by both backends. `header_lines(ws, source)` reads the generated module's imports **off the rendered body** — hence both backends build the body first |
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
  ratio (`mm²/m²`, `1/degree`) collapses the way Mathcad shows it. An override that is a scale *and*
  units (`10**-34 * kg·m²/s`, how Mathcad shows Planck's constant) reaches `disp` as a Pint **Quantity**
  rather than a Unit, and `disp` divides by it — `Quantity.to(<Quantity>)` would quietly use the units
  alone and drop the factor.
- Mathcad's built-in constants (`mapping.CONSTANTS`) are keyed by *display* name and looked up only for
  an id Prime labelled `CONSTANT`. That gating is what lets names as ordinary as `c`, `g`, `k`, `R`, `e`,
  `σ` sit in the table without capturing a worksheet's own variables. The physics set maps to **names
  imported from [const.py](mcad2py/const.py)** (`ℏ` → `hbar`), so a formula reads `m * c**2`; the import
  list comes from the IR's CONSTANT-labelled names, never from scanning the emitted text. Values are
  defined in **base SI** (`h` as `kg·m²/s`, not `J·s`), matching how `result.xml` caches them and how a
  scaled override divides down. Because they are pre-built Pint quantities, every generated module takes
  the one shared registry from [units.py](mcad2py/units.py) — Pint refuses to combine quantities from two
  registries.
- Unknown/unsupported constructs emit a visible `# TODO unsupported: <note>` so output still
  loads — never silently drop a region. An echo is built through `print_lines`, which lifts such a note
  onto its own line: `print(None  # TODO …)` would close its parenthesis *inside* the comment and stop
  the module parsing, which is the one outcome the convention exists to prevent.
- Mathcad's `≡` (`<ml:globalDefine>`) binds over the **whole** sheet, so `_hoist_global_defines` moves
  those regions to the top before every other pass. It's the one construct that breaks reading order.
- A region **Mathcad itself** couldn't compute (`result.xml` holds an `<engineError>` — `mode(v)` with
  no repeated value, `ln(0)`, a program branch that returns nothing) is translated faithfully and then
  wrapped in a `try`/`except` that prints Mathcad's own wording, so one such region can't abort the
  generated module. `ir.Region.cached_error` carries the message; see the `statistics.mcdx` schema note.
- Mathcad's `X[i] := …` splits two ways. A **bare range variable** as the index is a parallel build
  (`ir.IndexAssign` → one `index_build` pass, elements independent). Anything else — a constant
  (`data[2] :=`), an offset (`guess[i+1] :=`), or a matrix of such slots — is a **difference equation**
  (`ir.Recurrence`), which Mathcad evaluates *sequentially* and which emits a loop inside a `def` so its
  index stays local to the recurrence.
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
- Add new builtins/units/constants to [mapping.py](mcad2py/mapping.py) (data, not code). A new
  **runtime helper** needs no registration at all: the generated module's imports are read off the
  emitted text (every public name defined in [runtime.py](mcad2py/runtime.py) is a candidate), so
  writing the helper and mapping the Mathcad name to it is the whole job. Anything the text doesn't
  reference isn't imported — [tests/test_generated_imports.py](tests/test_generated_imports.py) pins
  both directions across every fixture.
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
[tests/conftest.py](tests/conftest.py) holds the shared pieces — `run_sheet` (convert + exec, capturing
each `print` argument as an *object*), `flat` (column-major magnitudes, matching the cache's order), and
`cached_results`/`result_refs` (read `result.xml` instead of transcribing it, which is what makes an
82-region catalogue sheet testable). It also sets the headless `Agg` backend once.

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
The **statistics family is complete** (descriptive, regression, and the Numerical Recipes correlation
set — see `references/statistics.mcdx`); of the **probability distributions**, only `norm`/`t`/`weibull`
have their `d`/`p`/`q`/`r` sets, and the rest are a four-line `scipy.stats` wrap each. Two things there
are not byte-reproducible: anything downstream of the **random** `rnorm`/`rweibull`/`rt` draws, and the
four NR p-values, which use a Chebyshev `erfcc` we deliberately don't reproduce (SciPy's exact `erfc` is
the better number; they agree to ~1e-7).
**Difference equations** (seeded iteration) are supported in all three shapes — scalar, a simultaneous
system, and a matrix recurrence writing two-subscript slots (`references/difference_eq.mcdx`). Not
covered: a *self-referential* bare-index form (`X[i] := f(X[i-1])` with no offset on the target), which
still takes the parallel `index_build` path and would read a stale element.
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
