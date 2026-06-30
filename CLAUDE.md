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
```

The **IR is the key design choice**: it decouples XML parsing from code generation, so a future
`.xmcd` (Mathcad 15) front-end or a SymPy backend can be added without touching the other half.
When adding features, respect this boundary — parsers produce IR, backends consume IR.

| File | Role |
|------|------|
| [loader.py](mcad2py/loader.py) | Unzip `.mcdx`; return `worksheet.xml`, `result.xml`, XAML text packages, rels map |
| [parser/namespaces.py](mcad2py/parser/namespaces.py) | Namespace constants; `localname()` strips `{ns}` — **match on local name, not full URI** (Prime bumps version numbers) |
| [parser/expressions.py](mcad2py/parser/expressions.py) | Recursive XML→IR walk; identifier reading (subscripts/Greek), `sanitize()` |
| [parser/regions.py](mcad2py/parser/regions.py) | Worksheet→ordered regions; **sort by (top, left)** for reading order |
| [ir.py](mcad2py/ir.py) | Backend-agnostic node dataclasses |
| [mapping.py](mcad2py/mapping.py) | Data tables: operators, builtins, constants, Greek, unit aliases |
| [runtime.py](mcad2py/runtime.py) | Helpers imported by generated code: angle-aware `sin/cos/tan/cot`, `col`/`arange`/`vectorize`/`transpose`, `linterp` (unit-aware linear interp), `integral` (scipy `quad`), `summation`, `solve_block` (scipy `fsolve`), `sample`/`plot_axis` (matplotlib plots) |
| [emit/codegen.py](mcad2py/emit/codegen.py) | Precedence-aware expression printer; shared by both backends |
| [emit/notebook_backend.py](mcad2py/emit/notebook_backend.py) | IR→`.ipynb`; region→cell; bare last line echoes result |
| [emit/py_backend.py](mcad2py/emit/py_backend.py) | IR→`.py`; evaluations become `print(...)` |
| [convert.py](mcad2py/convert.py) | Orchestration: `convert_file` / `convert_worksheet` |

## Confirmed Prime schema (from `references/.../worksheet.xml`)

- Namespaces: `ws=worksheet50`, `ml=math50`, `u=units10`, `p=provenance10`.
- `<region top= left=>` → sort by position. `<math resultRef=N>` links to `result.xml`.
- `<ml:define>` = `:=`; `<ml:eval>` = inline `=`, carries `<ml:unitOverride>` (display unit, or
  `<ml:placeholder/>` = auto) → drives `.to(<unit-expr>)`. The override is parsed as a full
  expression, so a compound unit (`kN*m`, an `<ml:apply><ml:mult/>`) becomes `ureg.kN * ureg.m`.
- Function definition: `<ml:define>` whose first child is `<ml:function>` (a name + `<ml:boundVars>`)
  instead of `<ml:id>` → `f = lambda x, …: <body>` (`Define.params` is the bound-var list).
- `<ml:apply>`: first child is the operator (empty tag: `div mult plus minus pow scale nthRoot`)
  **or** an `<ml:id labels="FUNCTION">` (function call). `scale` = number×unit ("30 MPa").
  `nthRoot` with empty first child = √.
- `<ml:apply><ml:equal/> lhs rhs>` = a symbolic/boolean equation (not `:=`) → SymPy `Eq(lhs, rhs)`.
- `<ml:symEval>` = symbolic evaluation: an input expr, a `<ml:command><ml:sequence> name, args…>`
  (e.g. `solve, C`), and a cached `<ml:symResult>` → emits `name(expr, *args)` (`solve(Eq(...), C)`).
  Command keyword → SymPy callable lives in `SYMBOLIC_COMMANDS` in [mapping.py](mcad2py/mapping.py).
  Free identifiers used symbolically are auto-declared as `x = Symbol('x')` ahead of first use.
- `<ml:id labels="...">` roles: `VARIABLE`/`UNIT`/`FUNCTION`/`CONSTANT` — use them, don't guess.
- Multi-arg calls wrap their args in one `<ml:sequence>`: `f(a,b)` is `<apply><id>f</id><sequence>a b</sequence></apply>`
  → flatten the sequence into `Call.args`. Function-call names are `sanitize()`d so a Greek/subscripted
  callee (`σ_s`) matches its definition (`sigma_s`); ASCII builtins pass through unchanged for the lookup.
- `<ml:matrix rows= cols=>` = a vector/matrix literal (row-major) → `ir.MatrixLiteral`. A row/column
  vector emits the `col(...)` runtime helper, which builds a **1-D NumPy array** (plain numbers) or a
  **Pint `Quantity` array** (when elements carry units, built *in the elements' own registry* — never a
  globally imported `Quantity`, or you get cross-registry errors). `<apply><indexer/> base idx>` →
  `base[idx]` (Mathcad indices are 0-based here). General `rows×cols` matrices are still a TODO.
- `<apply><vectorize/> expr>` = the element-wise "arrow" → `vectorize(expr)`, a runtime **identity**
  pass-through. The real element-wise behaviour comes from vectors being NumPy/Pint arrays plus
  `min`/`max` → `np.minimum`/`np.maximum` (2-arg clamps that broadcast). The one case the identity
  can't fix — a *branching* program applied to an array — would need `np.vectorize(fn)`; not yet done.
- `<ml:if>` (with `<ml:test>`/`<ml:then>`/`<ml:elseif>`/`<ml:else>`, branch bodies wrapped in
  `<ml:program>`) = a Mathcad *block* program → `ir.Program` (branch list). A `Define` whose value is
  a `Program` **and has params** (`σ_c(e) := …`) emits a real `def` with `if/elif/else return`s (not
  a `lambda`) to preserve branching; a `Program` assigned to a plain variable (no params) emits an
  inline conditional-expression chain instead.
- Mathcad's **inline** `if(cond, then, else)` is a different construct: `<ml:apply>` with an
  `<ml:id labels="KEYWORD">if</ml:id>` head and a `<ml:sequence>` of the three args. It's parsed into
  the same `ir.Program` (branches `[(cond, then), (None, else)]`) so it renders as a ternary
  (`then if cond else else`) — *not* a call to a Python `if`.
- `<ml:str>` = a Mathcad string literal → `ir.Str` → a Python `str` (emitted via `repr`, so unicode
  like `"tværsnit overudnyttet"` survives). No units.
- `<ml:range>` = `start, next .. stop` → `arange(start, stop, step)` (step = `next - start`), a
  unit-aware, **inclusive** range runtime helper. Plain numbers → a NumPy array; unit-bearing bounds
  (`z_plot := -h/2, … .. h/2`) → a Pint array (steps over magnitudes in `start`'s unit, reattaches it).
  Two XML shapes: an explicit step wraps `start, next` in a `<ml:sequence>` (stop follows); a
  **stepless** range (`i := 1 .. n`) is just two bare children `start, stop` with no `<sequence>` →
  step defaults to 1.
- `<ml:apply><ml:integral/> <ml:lambda> <ml:lowerBound> <ml:upperBound>>` = a definite **numeric**
  integral (`∫…=`) → `integral(lambda z: <body>, lo, hi)`, a unit-aware `scipy.integrate.quad`
  wrapper (integrates magnitudes, reattaches `integrand_unit * var_unit`; assumes a consistent
  integrand unit across the interval, which Mathcad also requires). `<ml:summation/>` (same
  lambda + integer bounds) → `summation(lambda i: <body>, lo, hi)`, an **inclusive** plain Python
  sum (no scipy). `<ml:lambda>` (a `<ml:boundVars>` + body) → `ir.Lambda` → `lambda …: …`.
  **Rule (mirrors `solve`):** Mathcad's `=`/numeric forms route to scipy/numeric Python; the `→`
  symbolic arrow forms route to SymPy. A symbolic `∫…→` would be a SymPy `Integrate`, not handled yet.
- Comparison ops (`lessThan`/`greaterThan`/`lessOrEqual`/`greaterOrEqual`) live in `OPERATOR_TAGS`
  and emit `< > <= >=` (used in program tests).
- Subscripts: `f<pw:Subscript>cd</pw:Subscript>` → `f_cd`. Greek is literal unicode.
- Text regions: content is in `mathcad/xaml/FlowDocumentN.XamlPackage` (a nested zip),
  linked via `item-idref` → `worksheet.xml.rels`. See [text.py](mcad2py/text.py).
- Picture regions: `<picture><png item-idref=N>` → `item-idref` → rels → `mathcad/media/*`
  bytes (`McdxPackage.image`). MIME is sniffed from magic bytes (Mathcad mislabels extensions —
  its `.png` is often BMP). The notebook embeds it as a **stored `image/png` cell output** (plus
  re-runnable `Image(...)` source), converting non-web formats to PNG via Pillow — *not* a
  markdown `data:` URI, which VS Code/others sanitize or truncate. `.py` emits a comment.
- `<plot><xyPlot>` region → `ir.Plot` → a matplotlib figure. Each axis carries `<plotEquations>`
  (an expression `<math>` + a unit/scale `<math>`); traces pair the x/y equations by index, the
  single-equation axis being shared. The bare-`Name` axis is the **domain** (`e_plot`/`z_plot`);
  every non-domain trace expression is emitted as `sample(lambda <domain>: <expr>, <domain>)` so it's
  evaluated **element-wise** — this is how a *branching* program (`σ_c`'s `if`) gets applied across the
  array (the one case `vectorize()` couldn't cover). `plot_axis(data, unit)` applies Mathcad's
  value/unit axis scaling (`data / unit`; a placeholder unit → base SI units, e.g. `z_plot` in metres).
  Trace colors are `#AARRGGBB` → `#RRGGBB`. Emits `plt.show()`.
- `<solveblock>` region (numeric Given/Find) → `ir.SolveBlock`. Sub-regions carry
  `solve-block-category`: `guess-value` (a `Define` seeding an unknown), `constraint` (a numeric
  `<ml:equal>` → `ir.Equation`, emitted as a `lhs - rhs` residual — *not* a SymPy `Eq`), and
  `solver` (`[targets] := find(unknowns)`, the `find` id is `labels="KEYWORD"`). Emits guess
  assignments, a `def _residuals(_x)` returning the residual list, and `targets = solve_block(...)`.
  The `solve_block` runtime helper wraps `scipy.optimize.fsolve` and does all the Pint bookkeeping
  (unknowns solved as magnitudes in their guess units, residuals compared in base units, units
  restored on the result). Only `find` is wired; `minerr`/`maximize`/`minimize` are future.
  - The solver region may instead be a **function definition** — `f(a, b) := find(x)`, where the
    target is an `<ml:function>` header and a constraint depends on the bound vars. Then `SolveBlock.params`
    is the bound-var list, `targets` is just `[f]`, and the whole solve is emitted **inside** `def f(a, b):`
    so the constraints close over the parameters, returning the solved unknown(s). The `find(...)` value
    here is a bare `<ml:apply>` (not `<ml:eval>`-wrapped), so `_parse_solver` handles both. The residual
    helper is named from the unknowns (`_residuals_x`) in this form, vs. the targets otherwise.
- `<apply><percent/> x>` = Mathcad's `%` postfix → `x / 100` (a `BinOp` div; `80%` → `80 / 100`,
  `100%` → `100 / 100`). Dimensionless, so no Pint involved.
- `<apply><transpose/> m>` → `ir.Transpose` → `transpose(...)`, a unit-aware runtime helper. For the
  1-D vectors `col()` builds, transpose is effectively identity (NumPy treats a 1-D array's
  transpose as itself), which is all that feeding a transposed data column to `linterp` needs; a
  real 2-D matrix transposes normally. General 2-D matrices are still a TODO.
- `linterp` (Mathcad linear interpolation) is a **runtime helper**, not a `FUNCTIONS` entry, because
  it (a) reorders args — Mathcad `linterp(vx, vy, x)` vs `np.interp(x, xp, fp)` — and (b) is
  unit-aware and **extrapolates** linearly beyond the knots along the first/last segment (`np.interp`
  only clamps). It lives in `RUNTIME_IMPORTS` so a `Call` to it triggers its import.
- `<ml:ListBoxScriptableControl>` (and any `…ScriptableControl`) as a `Define` value → we **do not
  transpile its embedded JScript** (the `Script` attr, gzip+base64; arbitrarily complex). Instead we
  recover the control's **cached output value** from the `RL` attribute (base64 s-expression, e.g.
  `(op_matrix … (list (number 3:0x..) (number 0.13:0x..)))` → `col(3, 0.13)`), the same value
  downstream cells consume. `_decode_control_result` regex-parses the numbers/dims; the selection
  (`SelectedIndex` into `<ml:vals>`) and option list are written as a leading `#` comment via the new
  `Define.comment` field. (Worksheets with controls carry `mathcad/integration.xml` and a
  `msg-id="ScriptableWarning"`.)
- Echo display units (`echo_expr` → `_display`): a real unit override emits `x.to(<unit>)`, but a
  **pure numeric scale** (Mathcad showing a dimensionless result as e.g. `×10**-6`, with no `UnitRef`
  in the override) emits `x / (<scale>)` instead — `.to` only applies to a dimensioned quantity.
- Worksheet settings live in `mathcad/settings/calculation.xml`: `array-origin="0"` (confirms our
  0-based indexing), `convergence-tolerance` = Mathcad `TOL`, `constraint-tolerance` = `CTOL` (both
  per-file, default `0.001`). Not consumed yet — `TOL`/`CTOL` will drive `find`/`quad` tolerances
  when solve blocks land.

## Conventions

- Generated trig uses runtime helpers (`tan(phi)`), not `math.tan(phi.to('rad').magnitude)`.
- Display units come from `unitOverride`; emit `x.to(ureg.<unit>)` for the echo (or `x / (<scale>)`
  when the override is a pure numeric scale like `10**-6` — see `_display`).
- Unknown/unsupported constructs emit a visible `# TODO unsupported: <note>` so output still
  loads — never silently drop a region.
- Add new builtins/units/constants to [mapping.py](mcad2py/mapping.py) (data, not code).

## Testing

[tests/test_convert.py](tests/test_convert.py) converts `references/plain_concrete_cohesion.mcdx`,
**executes** the generated Python, and asserts values match Mathcad's cached `result.xml`
(~14 sig figs). When adding a sample, prefer this execute-and-compare-to-`result.xml` style.
[tests/test_symbolic.py](tests/test_symbolic.py) does the same for `references/NM_to_CT.mcdx` and
additionally checks the emitted `solve(...)` against Mathcad's cached `symResult` via SymPy.
[tests/test_vectors.py](tests/test_vectors.py) does the same for `references/Xsection_solver.mcdx`:
vectors/indexing vs cached matrices, the `σ_c` program's branches, element-wise `min`/`max` clamps,
the vectorized `F_s`, and `N_int`/`M_int` (concrete integral + steel summation) evaluated at the
cached solve point `e_1`/`k_1` against Mathcad's cached force/moment checks (rel_tol 1e-4 — `quad`
on the kinked integrand vs Mathcad's own quadrature at its 1e-3 solution differ ~1e-5), and the
`find` solve block recovering Mathcad's cached `e_1`/`k_1` via `fsolve`. The whole sheet now runs
end-to-end: the unit-bearing `z_plot` range and the neutral axis `x` are checked too, and both
`<xyPlot>` figures are rendered (matplotlib `Agg`) and their traces/labels asserted. Plus direct
unit tests of the `integral`/`summation` runtime helpers.
[tests/test_shrinkage.py](tests/test_shrinkage.py) covers `references/shrinkage.mcdx` (EN 1992
shrinkage): the `linterp`/`transpose` pair (`k_h` interpolates and extrapolates, cached `0.7`),
`percent` (`80%` → `0.8`), and the `ListBoxScriptableControl` recovering its cached `[3, 0.13]`
("Class S") output without transpiling the JScript. The whole sheet runs and matches the cache;
`ε_cd`/`ε_cs` use rel_tol 1e-4 because Pint's Julian year (365.25 d) differs from Mathcad's mean year.
[tests/test_solve_function.py](tests/test_solve_function.py) covers `references/solve_as_function.mcdx`:
a Given/Find block whose solver region is a *function definition* `f(a, b) := find(x)` (the constraint
`a·x²−b = cos(x)` closing over the params) — it asserts the emitted `def f(a, b):`, that `f(1, 3)`
recovers the cached root `1.6957…`, and that `f` is reusable with other arguments.
[tests/test_beton_vridning.py](tests/test_beton_vridning.py) covers the leaf features of
`references/Beton_Vridning.mcdx` (torsion): the stepless range `i := 1 .. n` (→ `arange(1, n, 1)`),
the `ceil`/`floor`/`round` builtins, and an inline `if(cond, "ok", "tværsnit overudnyttet")` rendered
as a ternary with string literals. It asserts the generated source, not execution — the whole sheet
needs the range-indexed vector backbone (see "Not yet supported") before an execute-vs-`result.xml`
test is possible.

**Reference files are test fixtures — don't edit them.** Tests compare generated output against each
`.mcdx`'s cached `result.xml`; changing a worksheet (e.g. a `phi` value) silently shifts every
dependent cached number and breaks the hardcoded expected values.

## Not yet supported (next targets)

**Range-indexed vector assignment** (the `Beton_Vridning.mcdx` backbone): a `Define` whose *target*
is an `<ml:indexer>` (`T_Ed[i] := 400`, `A_sl[i] := …`) with `i` a range — Mathcad loops `i` over the
range and **builds a vector** (0-based origin, so `i := 1 .. n` leaves index 0 defaulted). Currently
the indexer target is mis-read as a scalar name (`T_Edi`) and downstream `X[i]` reads dangle. The
stepless range, `ceil`, inline `if`, and string literals it also uses *are* done (see
[tests/test_beton_vridning.py](tests/test_beton_vridning.py)); the whole-sheet
execute-and-compare-to-`result.xml` test lands with this vector backbone.
General `rows×cols` matrices (vectors + transpose work). `find` solve blocks work;
`minerr`/`maximize`/`minimize` don't yet.
A *branching* program applied to an array still needs `np.vectorize(fn)` (the `vectorize()` identity
helper only covers arithmetic + `min`/`max`). Known gap: square roots emit `math.sqrt(x)` (fine for
dimensionless args); switch to `x ** 0.5` when a unit-bearing root appears so Pint handles units.
`TOL`/`CTOL` from `calculation.xml` aren't consumed yet (solve uses fsolve defaults).
Scriptable-control JScript is **intentionally** not transpiled — we surface the control's cached
output value (the `RL` attribute) instead, which is faithful as long as the worksheet was last saved
with the desired selection. A control with no cached `RL` falls back to a `# TODO unsupported` region.

Nice-to-have: an opt-in `--externalize-images` (or `--media-dir`) flag that writes picture
regions as sidecar files next to the output notebook and references them with a relative link,
instead of the default self-contained base64 embed. Only meaningful for file output (not `-o -`
stdout); keep embedding as the default since it stays portable. Wanted mainly to keep git diffs
clean when generated notebooks are committed.

## Scope

Prime `.mcdx` only (`worksheet50`/`math50`). Legacy `.xmcd` (Mathcad 15, `math30`) is a future
front-end — add it as a new parser producing the same IR.
