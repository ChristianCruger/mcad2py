# Confirmed Prime schema (from `references/.../worksheet.xml`)

Detailed, confirmed notes on how PTC Mathcad Prime's `.mcdx` XML (`worksheet50`/`math50`) maps to
this project's IR ([mcad2py/ir.py](../mcad2py/ir.py)). Referenced from [CLAUDE.md](../CLAUDE.md) —
read this file when parsing a new schema construct or debugging a parser edge case.

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
  Command keyword → SymPy callable lives in `SYMBOLIC_COMMANDS` in [mapping.py](../mcad2py/mapping.py).
  Free identifiers used symbolically are auto-declared as `x = Symbol('x')` ahead of first use.
- `<ml:id labels="...">` roles: `VARIABLE`/`UNIT`/`FUNCTION`/`CONSTANT` — use them, don't guess.
- Multi-arg calls wrap their args in one `<ml:sequence>`: `f(a,b)` is `<apply><id>f</id><sequence>a b</sequence></apply>`
  → flatten the sequence into `Call.args`. Function-call names are `sanitize()`d so a Greek/subscripted
  callee (`σ_s`) matches its definition (`sigma_s`); ASCII builtins pass through unchanged for the lookup.
- `<ml:matrix rows= cols=>` = a vector/matrix literal → `ir.MatrixLiteral`. Its children are in
  **column-major** order (confirmed against Prime output: the first `rows` elements are column 0, the
  next `rows` are column 1, etc.) — verify against a known matrix before assuming otherwise if this
  ever looks wrong for a new sheet. A leading `<ml:display size="…">` child is a display-formatting
  hint, not a data element — skip it (`_parse_matrix` filters by tag). A row/column vector (`rows == 1`
  or `cols == 1`) emits the `col(...)` runtime helper, a **1-D NumPy array** (plain numbers) or **Pint
  `Quantity` array** (elements with units, built *in the elements' own registry* — never a globally
  imported `Quantity`, or you get cross-registry errors); a real `rows×cols` matrix emits `matrix(rows,
  cols, *elements)`, which reshapes the column-major elements with `order="F"` and handles units the
  same way as `col()` (Mathcad requires one consistent unit across the *whole* matrix, no per-column
  units). `<apply><indexer/> base idx>` → `base[idx]` (Mathcad indices are 0-based here).
- **Range-indexed vector assignment** — a `<ml:define>` whose *target* is an `<apply><indexer/> X i>`
  (not an `<ml:id>`) where `i` is a range variable (`i := 1 .. n`): `X[i] := expr` → `ir.IndexAssign`,
  emitted as `X = index_build(i, lambda i: <expr>)`. Mathcad iterates `i` over its range and builds
  the 0-based vector `X`, **zero-filling** any lower index never written (so `T_Ed[i] := 400` with
  `i := 1 .. 1` yields `[0, 400]`). The lambda's `i` is the *scalar* loop index, so the RHS — including
  `X[i]` reads of other vectors — uses the ordinary scalar codegen (`math.ceil`, the inline-`if`
  ternary, `np.minimum` all work on scalars); the outer `i` stays an **integer** range array (see
  `arange`) so the evaluation reads `X[i] =` fancy-index into 1-element vectors, matching Mathcad's
  cached `1×1` matrices. `index_build` (runtime) handles plain/Pint/string element types. An inline
  `=` after the assignment echoes `X[i]` (`IndexAssign.evaluate`/`display_unit` mirror `Define`).
- `arange` returns an **integer** array when start/stop/step are all integral (an index variable like
  `i := 1 .. n`), so it can index NumPy/Pint vectors directly; non-integral bounds stay float.
- `<apply><vectorize/> expr>` = the element-wise "arrow" → `vectorize(expr)`, a runtime **identity**
  pass-through. The real element-wise behaviour comes from vectors being NumPy/Pint arrays plus
  `min`/`max` → `np.minimum`/`np.maximum` (2-arg clamps that broadcast). The one case the identity
  can't fix — a *branching* program applied to an array — would need `np.vectorize(fn)`; not yet done.
- `<ml:if>` (with `<ml:test>`/`<ml:then>`/`<ml:elseif>`/`<ml:else>`, branch bodies wrapped in
  `<ml:program>`) = a Mathcad *block* program → `ir.Program` (branch list). A `Define` whose value is
  a `Program` **and has params** (`σ_c(e) := …`) emits a real `def` with `if/elif/else return`s (not
  a `lambda`) to preserve branching; a `Program` assigned to a plain variable (no params) emits an
  inline conditional-expression chain instead. `<ml:alsoif>` (Prime's "also if") is an `elif` — a
  sibling carrying its own `<ml:test>`/`<ml:then>`, handled like `<ml:elseif>`. A bare `<ml:program>`
  used directly as a value (`σ_nd := <program with if>`) is unwrapped to its single statement's
  expression.
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
- Comparison ops (`lessThan`/`greaterThan`/`lessOrEqual`/`greaterOrEqual`/`equal`) live in
  `OPERATOR_TAGS` and emit `< > <= >= ==`; boolean connectives `and`/`or` (in `OPERATOR_TAGS` as
  `and_`/`or_`) emit `and`/`or` (used in program tests, e.g. `rho <= x and revne == "Ja"`).
- `<ml:equal/>` is **context-dependent**: by default it parses as a `==` comparison (`BinOp` `eq`) for
  boolean use in tests/inline-`if`. In a genuinely *symbolic* region — a standalone equation, a
  `solve` input, or a solve-block constraint — it means an equation, so those three parsers route it
  through `_to_equation`, which lifts a top-level `eq` `BinOp` into an `ir.Equation` (SymPy `Eq`).
  (Don't make `equal` an `Equation` at parse time, or a boolean `=` in a non-symbolic sheet emits a
  bare `Eq(...)` with no SymPy imported → `NameError`.)
- Subscripts: `f<pw:Subscript>cd</pw:Subscript>` → `f_cd`. Greek is literal unicode.
- Text regions: content is in `mathcad/xaml/FlowDocumentN.XamlPackage` (a nested zip),
  linked via `item-idref` → `worksheet.xml.rels`. See [text.py](../mcad2py/text.py).
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
- `<plot><contourPlot>`/`<plot3D>` → `ir.GridPlot` (`threed` distinguishes them) → matplotlib
  `contourf`/`contour` or (3D) `plot_surface`/`scatter`. Unlike `<xyPlot>`, there's a single plot
  equation (`<contourPlot>` has one `<plotEquation>` directly inside it; `<plot3D>` wraps it in
  `<plotEquations>`), whose *value* resolves to the whole surface in one of three shapes a real
  Mathcad worksheet can produce — dispatched at runtime by `resolve_plot_grid`, not statically by the
  parser, since it only depends on the value's shape:
  1. **A function applied directly to two range variables** (`f(x0, y0)` where `x0`/`y0` were defined
     as `<ml:range>`s earlier in the sheet, not plain vectors) — Mathcad takes the ranges' **outer
     product** (a grid), not an elementwise zip, so this needs different codegen: the parser tracks
     which names were range-`Define`d (`range_names`, threaded through `_parse_region`/`_parse_plot`)
     and, if the plot equation is a 2-arg `Call` on two of them, sets `GridPlot.mesh_names = (func,
     x_name, y_name)` so codegen emits `mesh_grid(func, x, y)` (builds `np.meshgrid` + evaluates
     element-wise, like `sample` but 2-D) instead of calling `f(x0, y0)` directly (which would zip).
  2. **A bare matrix/mesh name** (e.g. `M`, `A`, or `F := CreateMesh(...)`) — emitted as-is;
     `resolve_plot_grid` inspects the runtime value: an already-built `Mesh` (from
     `mesh_grid`/`CreateMesh`) passes through; a matrix with **exactly 3 columns** is Mathcad's
     documented `(x, y, z)` point-list convention (irregular scatter data, `kind="scatter"` →
     `tricontourf`/bare 3D `scatter`); any other matrix is a z-value grid using the row/column
     **index** as the x/y coordinate (`kind="grid"`).
  3. **`CreateMesh(f, xlow, xhigh, ylow, yhigh, xdiv, ydiv)`** — a Mathcad builtin (not a `FUNCTIONS`
     mapping; it's a `RUNTIME_IMPORTS` entry like `linterp`, so a `Call` to it triggers its import).
     The runtime helper samples `f` over `np.linspace` grids (`xdiv`/`ydiv` are **divisions**, so
     `div + 1` points per axis) via the same `mesh_grid`, returning a `Mesh`.
  The second `<math>` in `<plotEquation>` is the z-axis unit override (or `<ml:placeholder/>` for
  "auto", same convention as `<xyPlot>`); x/y always use `plot_axis(..., None)` (auto base units) since
  neither plot type has a per-axis equation/unit the way `<xyPlot>` does.
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
  real 2-D matrix transposes normally.
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
- `<ml:ComboBoxControl>` as a `Define` value → `ir.ComboBoxAssign`. A **native** (non-scripted)
  row-selector: a `rows×cols` table (`<ml:ComboBoxValues>`, row-major; named by `<ml:ComboBoxRowNames>`)
  with a `SelectedRow` (0-based, per `array-origin`). The selected row's `cols` value(s) map onto the
  LHS target(s) — a single `<ml:id>` or a `<ml:matrix>` of ids (`[f_ck; f_ctk] := …`). A control with
  **no** `<ml:ComboBoxValues>` yields the selected row *name* as a string (a Ja/Nej flag → `revne := "Ja"`).
  Emits one `target = value` per column plus a `#` comment documenting the pick; `ComboBoxScaleFactors`
  (all placeholders in samples seen) are ignored. (`Beton_Bæreevne_støbeskel.mcdx`'s cached `result.xml`
  is internally **stale** — `ν_v`'s `0.525` implies an old C35 pick while `τ_Rd` reflects the live C40
  `SelectedRow=6`; we reproduce the live selection, which `τ_Rd`/`f_yd` corroborate.)
- Echo display units (`echo_expr` → `_display`): a real unit override emits `x.to(<unit>)`, but a
  **pure numeric scale** (Mathcad showing a dimensionless result as e.g. `×10**-6`, with no `UnitRef`
  in the override) emits `x / (<scale>)` instead — `.to` only applies to a dimensioned quantity.
- Worksheet settings live in `mathcad/settings/calculation.xml`: `array-origin="0"` (confirms our
  0-based indexing), `convergence-tolerance` = Mathcad `TOL`, `constraint-tolerance` = `CTOL` (both
  per-file, default `0.001`). Not consumed yet — `TOL`/`CTOL` will drive `find`/`quad` tolerances
  when solve blocks land.

## `LT91.mcdx` constructs (Stage 1 — leaf features)

- **Data table** = a `<region>` whose child is `<ml:spec-table>` holding one `<math><define>` per
  column (Mathcad names the resulting vectors by their column headers). `_parse_region` returns a
  **list** of `Define`s for it (and `parse_worksheet` flattens the list), so one region expands to N
  column regions — otherwise the whole table is silently dropped (only the region's first child is
  inspected). Each column is `<apply><scale/> <matrix col-vector> <unit-or-placeholder>`: a real unit
  (`Fz := col(…) * ureg.kN`) rides the normal `Quantity` path; a **placeholder** unit (a dimensionless
  or string column like `LS`) is stripped in `_parse_apply` so the value stands alone (else it emits
  `col(…) * None`). String columns become `col('ULS', …)` (an object array via `col()`).
- **`augment(a, b, …)`** = a `FUNCTION`-labelled call → runtime `augment` (in `RUNTIME_IMPORTS`).
  Stacks column vectors side by side into a matrix. Columns may carry **different** units (Mathcad
  allows a heterogeneous matrix here, e.g. `augment(ones(n), Xs_mm, Ys_mm)` mixing dimensionless and
  length columns), so the result is a NumPy **object array of per-element Pint scalars**; a later
  `matmul` propagates units column by column. `col()`/`matrix()` similarly fall back to an object
  array when their elements' units are incompatible (a mixed `[strain; curvature]` vector).
- **Bare `Σ`** = `<apply><summation/> <lambda>(boundVars=placeholder) <upperBound><placeholder/></apply>`
  — no index variable, no bounds. Means "sum every element of the (already-built) vector" → `ir.VectorSum`
  → runtime `total(v)` (unit-aware). Detected in `_parse_integral_like` by the lambda having **no
  params** (a real indexed sum always has an index var + integer bounds → `ir.Summation`).
- **Column extraction** `A^<i>` = `<apply><matcol/> <base> <index>` → `ir.MatCol` → runtime
  `matcol(m, i)` (the `i`-th column as a 1-D vector, unit-aware). Seen feeding plot equations
  (`Contour^<0>`/`Contour^<1>` as x/y outlines).
- **Matrix multiplication** uses the **same `<ml:mult>` tag** as scalar `*` (and as the element-wise
  product under a `vectorize` arrow) — Prime does not distinguish them in XML. Codegen emits a runtime
  `matmul(a, b)` (unit-aware `@`) only when **both operands are statically matrix-shaped**
  (`_is_matmul`): a `MatrixLiteral` with `rows>1 and cols>1`, an `augment(…)` call, a `Transpose` of
  one, or a nested matmul on the left; and an array-shaped right operand (matrix/vector literal,
  `matcol`, transpose, augment, matmul). A matrix times a *scalar*, and an element-wise vector product
  under `vectorize`, stay ordinary `*`. This is a heuristic (a matmul between two *named* matrix
  variables is not detected) but covers every product in `LT91`.
- **Multi-target destructuring** `[a; b; c] := <expr>` = a `<ml:matrix>` of ids as the define target
  with an ordinary value → `ir.MultiAssign` → `a, b, c = tuple(<expr>)` (unpack a returned vector).
  Guarded so a `<matrix>` target whose value is a native `…Control` still routes to the ComboBox path.
  (When the value is a multi-line program, the program-as-helper + destructure is Stage 2.)
- **`<ml:TextBoxScriptableControl>`** as a **standalone** region (`<math>` child, not a define value):
  a status widget with **no `RL` cache**. Its JScript isn't transpiled; instead the expression it
  carries in `PiggybackNode > inputControlInputField` — any expression, often a boolean (`λ < λlim`,
  `ERR = 0`) but possibly a plain variable the JScript inspects — becomes an `ir.StatusControl`, which
  emits `print("<expr>", <expr>, "<message>")`: the expression source, its live value, and the cached
  `<ml:vals>` message (`"All loadcases pass!"`, `"OK!"`), so the reader sees how the value drove the
  message. (Contrast `_parse_scriptable_control`, which recovers a define-*driving* control's cached
  `RL` value.)
## `LT91.mcdx` constructs (Stage 2 — imperative programs)

- **Multi-line program** (`<ml:program>` with statements) → a new statement IR (`ir.ProgramBlock` of
  `LocalAssign`/`ForLoop`/`IfStmt`/`Return`/`TryCatch`), distinct from the value-`Program` (piecewise
  ternary). `parse_expr` treats a program as imperative when it has a `localDefine`/`for`/`return`/
  `tryCatch` child (else it's a single value expression). Emitted as a Python **`def`**: a function
  (`Neutral(e,kx,ky) := …`) keeps its params; a plain variable (`As := …`) becomes a nullary helper
  `def _As(): …` bound with `As = _As()`; a multi-target `[Xs;Ys;n] := …` destructures
  `Xs, Ys, n = tuple(_Xs_Ys_n())`. Statement forms: `<ml:localDefine>` = `←` local assign,
  `<ml:for>` = `for v in arange(…)`, statement-`<ml:if>`/`then`/`elseif`/`else`, `<ml:return>`,
  `<ml:tryCatch>` = `try/except Exception`. A bare trailing expression is an implicit `return`.
- **Growable program vectors** — `X[i] := …` inside a program (Mathcad auto-grows/zero-fills) →
  `X = vec_set(X, i, v)` (codegen pre-declares `X = None`). `vec_set` grows an object array and
  **consolidates** it back to a fused Pint array once homogeneous (so downstream `kx * X` broadcasts).
  A `<ml:sequence>` index `Ans[j, 0]` = a 2-D element (`ir.Index2D`) → `vec_set(Ans, (j, 0), v)`.
- **`max`/`min` are reductions**, always: Mathcad flattens *all* arguments (scalars and vectors) and
  returns the single min/max — `mc_max`/`mc_min` (equivalent to `np.min`/`np.max` over the flattened
  args, unit-aware). There is no element-wise `np.minimum`/`np.maximum`; element-wise behaviour comes
  from the **vectorize arrow applying a function per element**. So `min(v)`/`max(v,s)`/`min(a,b,c)` all
  reduce to a scalar (fixes `A_smin = max(vectorize(0.1·N)/f_yd, 0.002·A_c)` → scalar).
- **`elementwise` wrapping** — a *single-argument* scalar function that the vectorize arrow applies per
  element is wrapped `f = elementwise(f)`: a branching program (`σ_c`) or a **two-argument** min/max
  *clamp* (`σ_s := min(f_yd, max(-f_yd, E_s·ε))`). It passes a scalar straight through and maps a
  vector per element (so a clamp applies per component instead of collapsing). A *single*-argument
  min/max is a reduction of its vector arg (`UR(ε) := min(ε)/ε_cu`), which `mc_min` already handles for
  either a scalar or a vector, so such a function is **not** wrapped (we can't know `ε`'s type at parse
  time, and the reduction is correct for both).
- **Dimensionless reduction for roots/powers** — Pint keeps a ratio of same-dimension quantities
  *unreduced* (`200 mm / d` = `mm/mm`, `ρ = A/(b·d)` = `mm²/mm²`); a `sqrt`/nth-root/fractional power of
  that would leave fractional `mm**0.5` unit noise (and floating-point `m**1e-16` residue that breaks a
  later `< 1` compare). So `√`/nthRoot → `nth_root(x, n)` and a *non-integer* `**` → `power(x, e)`, both
  reducing a dimensionless base first (a *dimensioned* radicand keeps its unit: `√(m²) = m`). Likewise
  `ceil`/`floor`/`round` are dimensionless-aware runtime helpers.
- **`disp(value, unit)`** replaces `value.to(unit)` for an inline `=` echo: it converts when
  dimensionally compatible, else divides (the residual-unit form Mathcad shows for a *loose* override,
  e.g. a `kN·m` moment displayed with a `kN` override), so a stray override can't crash the echo.
- **Data-table units** — a `<spec-table>` column with a real unit rides the normal `Quantity` path
  (`Fz := col(…) * ureg.kN`), preserving units; a mixed matrix keeps per-element units (object array)
  when a plain *nonzero* entry sits beside dimensioned ones (a strain matrix `[1, -l/2, -w/2]`), while
  a plain *zero* is absorbed into the prevailing unit (`[[w,0],[0,l]]`).
- **Parametric `<xyPlot>`s** — a plot has a *sampling domain* only when one axis is a bare **range**
  variable (`y = f(x)` over a range `x`, sampled element-wise with `sample(lambda x: …, x)`). When both
  axes are plain data vectors (`LT91`'s section outline, rebar scatter, neutral-axis line — e.g. x =
  `matcol(Contour, 0)`, y = `matcol(Contour, 1)`), there is no domain: each axis expression is emitted
  directly (`plot_axis(matcol(Contour, 0), ureg.mm)`) and the traces are plotted point-by-point.
  `_detect_domain` therefore only accepts a `Name` that is in `range_names`; a bare data-vector `Name`
  (`X_s`, built by an imperative program) is *not* mistaken for a domain. `plot_axis` also reduces a
  dimensionless-but-unreduced axis ratio (a section in `m` shown with an `mm` override → `m/mm`, which
  must collapse to `650`, not read as `0.65`).
- **Known limitation:** a solve block's guess/solution units stay unreduced, e.g. a strain shows as
  `kN/m²/GPa` rather than a plain number — correct value, verbose unit.
