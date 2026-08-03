# Confirmed Prime schema (from `references/.../worksheet.xml`)

Detailed, confirmed notes on how PTC Mathcad Prime's `.mcdx` XML (`worksheet50`/`math50`) maps to
this project's IR ([mcad2py/ir.py](../mcad2py/ir.py)). Referenced from [CLAUDE.md](../CLAUDE.md) —
read this file when parsing a new schema construct or debugging a parser edge case.

- Namespaces: `ws=worksheet50`, `ml=math50`, `u=units10`, `p=provenance10`.
- `<region top= left=>` → sort by position. `<math resultRef=N>` links to `result.xml`.
- `<region><Area><regions>…` = a **collapsible area** (a container region, not math) — flattened away;
  see [Collapsible areas](#collapsible-areas-collapsable-areamcdx).
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
  like `"tværsnit overudnyttet"` survives — worksheets are routinely written in the engineer's
  own language). No units.
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
  `and_`/`or_`) emit `and`/`or` (used in program tests, e.g. `rho <= x and crack == "Yes"`).
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
  **no** `<ml:ComboBoxValues>` yields the selected row *name* as a string (a Yes/No flag → `crack := "No"`).
  Emits one `target = value` per column plus a `#` comment documenting the pick; `ComboBoxScaleFactors`
  (all placeholders in samples seen) are ignored. (`RC_interface.mcdx`'s cached `result.xml`
  is internally **stale** — `ν_v`'s `0.525` implies an old C35 pick while `τ_Rd` reflects the live C40
  `SelectedRow=6`; we reproduce the live selection, which `τ_Rd`/`f_yd` corroborate.)
- Echo display units (`echo_expr` → `_display`): a real unit override emits `x.to(<unit>)`, but a
  **pure numeric scale** (Mathcad showing a dimensionless result as e.g. `×10**-6`, with no `UnitRef`
  in the override) emits `x / (<scale>)` instead — `.to` only applies to a dimensioned quantity.
- Worksheet settings live in `mathcad/settings/calculation.xml`: `array-origin="0"` (confirms our
  0-based indexing), `convergence-tolerance` = Mathcad `TOL`, `constraint-tolerance` = `CTOL` (both
  per-file, default `0.001`). Not consumed yet — `TOL`/`CTOL` will drive `find`/`quad` tolerances
  when solve blocks land.

## `RC_col.mcdx` constructs (Stage 1 — leaf features)

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
  variables is not detected) but covers every product in `RC_col`.
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
## `RC_col.mcdx` constructs (Stage 2 — imperative programs)

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
  Two further cases (see the trig/hyperbolic section below): a **plain number with an angle override**
  is rescaled as radians rather than divided, and `disp(value)` with **no** override reduces a
  dimensionless-but-unreduced quantity.
- **Data-table units** — a `<spec-table>` column with a real unit rides the normal `Quantity` path
  (`Fz := col(…) * ureg.kN`), preserving units; a mixed matrix keeps per-element units (object array)
  when a plain *nonzero* entry sits beside dimensioned ones (a strain matrix `[1, -l/2, -w/2]`), while
  a plain *zero* is absorbed into the prevailing unit (`[[w,0],[0,l]]`).
- **Parametric `<xyPlot>`s** — a plot has a *sampling domain* only when one axis is a bare **range**
  variable (`y = f(x)` over a range `x`, sampled element-wise with `sample(lambda x: …, x)`). When both
  axes are plain data vectors (`RC_col`'s section outline, rebar scatter, neutral-axis line — e.g. x =
  `matcol(Contour, 0)`, y = `matcol(Contour, 1)`), there is no domain: each axis expression is emitted
  directly (`plot_axis(matcol(Contour, 0), ureg.mm)`) and the traces are plotted point-by-point.
  `_detect_domain` therefore only accepts a `Name` that is in `range_names`; a bare data-vector `Name`
  (`X_s`, built by an imperative program) is *not* mistaken for a domain. `plot_axis` also reduces a
  dimensionless-but-unreduced axis ratio (a section in `m` shown with an `mm` override → `m/mm`, which
  must collapse to `650`, not read as `0.65`).
- **Known limitation:** a solve block's guess/solution units stay unreduced, e.g. a strain shows as
  `kN/m²/GPa` rather than a plain number — correct value, verbose unit. (An *echoed* ratio no longer
  has this problem — see the automatic-display note below.)

## `trig.mcdx` / `hyperbolic.mcdx` constructs (the two function families)

Both sheets are catalogues: one angle, then every member of the family applied to it. No new XML
constructs — the parser already handled them — but they pin down several **semantics**:

- **Angles are dimensionless in Mathcad.** `deg` is a plain π/180 scale, not a distinct dimension.
  So `sinh(103.2 deg)` means `sinh(1.80118)`, and `atan(x) = … deg` displays a bare radian result in
  degrees. The runtime's `_radians` coercion therefore serves *both* jobs: converting an angle
  argument for the forward trig functions, and reducing any pure-number argument (an angle, or an
  unreduced Pint ratio like `mm/mm`) to a float for the hyperbolic/inverse ones.
- **Inverse trig/hyperbolic return bare floats of radians**, matching what Mathcad stores. The
  display override is applied by `disp`, which special-cases a value with no `.to()` and an *angle*
  unit (`_ANGLE_UNITS`): it rescales via `Quantity(value, "radian").to(unit)`. Without that case it
  would fall through to `value / ureg.deg` and report `0.593 1/degree` instead of `34 deg`.
- **Automatic display reduces a ratio.** With an *empty* (placeholder) override Mathcad shows the
  reduced number, but Pint leaves `sin(θ)/θ` as `0.0164 1/degree` and `ρ = A/(b·d)` as
  `783.98 mm²/m²`. So an echo whose value contains a **division** is wrapped `disp(<expr>)` (one-arg
  form → `_reduce_dimensionless`); other echoes stay bare, keeping generated cells readable. This is
  what makes `RC_col`'s `ε_yd`, `ρ`, `n_0` and the `UR_vc` utilisation vector match the cache — they
  were previously displayed ~1000× off, with the residual unit as the only hint.
- **Conventions that differ from Python/NumPy** — worth checking against, not guessing:
  `atan2(x, y)` takes its arguments in the **opposite** order to `math.atan2(y, x)`; `angle(x, y)` is
  the same thing wrapped to `[0, 2π)`; `sinc(z)` is the **unnormalised** `sin(z)/z` (`np.sinc` is
  `sin(πz)/(πz)`); `asec`/`acsc` are `acos(1/x)`/`asin(1/x)`; and `acot` is `π/2 - atan(x)`, the
  `(0, π)` branch (the Maple/MuPAD convention, *not* Mathematica's `atan(1/x)`).
- **`acot`'s negative branch is confirmed**, not inferred: the sheet caches `acot(-2) = 2.67794`
  (= `π/2 - atan(-2)`), ruling out `atan(1/x)`, which would give `-0.46365`. The two conventions agree
  for positive arguments, so this is the only case that distinguishes them. `atan(-6) = -1.40565` is
  cached alongside it, confirming `atan` keeps the ordinary signed `(-π/2, π/2)` branch.
- **`sec` arrives without a `labels` attribute** (`<ml:id xml:space="preserve">sec</ml:id>`, no
  `labels="FUNCTION"`), presumably because the name collides with the `sec`/second unit. It resolves
  anyway: `_parse_apply` takes the first child of `<ml:apply>` as the callable regardless of label.
- **Multi-argument builtins** wrap their arguments in `<ml:sequence>` (`atan2`, `angle`) — already
  handled by the generic apply path.

## `matrices.mcdx` constructs (the vector & matrix family)

A catalogue of Mathcad's whole "Vector and Matrix" function category plus its bar/row/cross
operators, followed by three worked examples (down-sampling, left/right eigenvectors, PCA).

### New `<ml:apply>` heads

- `<ml:absval>` and `<ml:determinant>` are **two different operators that both render as `|x|`**
  (Prime's ribbon offers them separately). `absval` is the elementwise absolute value → plain
  `abs(x)`. `determinant` is the determinant of a matrix — but Mathcad also accepts a *vector* there,
  where it means the Euclidean magnitude, so it emits the runtime `determinant(x)`, which dispatches
  on the operand's shape (2-D → `np.linalg.det`, 1-D → 2-norm, scalar → `abs`). The sheet caches
  both: `|M| = 12` (a determinant) and `|A| = 5.4772 = √30` (a magnitude).
- `<ml:matrow> base index>` = the row-extraction operator, the sibling of `<ml:matcol>` (`A^<i>`) →
  `matrow(M, i)`. Mathcad's cache shows a `1×4` result; we return a 1-D array, as we do for every
  row/column vector.
- `<ml:crossProduct> a b>` = the `×` operator → `cross(a, b)` (unit-aware: the result carries
  `unit_a · unit_b`).

### Two-subscript forms

- **Reads.** `<apply><indexer/> base <sequence>i j>` (already parsed into `ir.Index2D`) now emits
  `matelem(base, i, j)` rather than `base[i, j]`. A Mathcad row *or* column vector is stored here as a
  1-D array, which NumPy will not accept two subscripts for — and the sheet does exactly that
  (`A[1, 0]` on a 4×1, `B[0, 2]` on a 1×4). `matelem` takes whichever subscript is non-zero in that
  case, and indexes straight through for a genuine 2-D matrix.
- **Writes.** A `<ml:define>` whose target is `<apply><indexer/> X <sequence>i j>` with *both*
  indices range variables is the matrix form of `ir.IndexAssign` (`col_index` set) →
  `X = index_build_2d(i, j, lambda i, j: <expr>)`. Mathcad takes the two ranges' **outer product**
  (as it does for a contour plot's two ranges), not a zip. The inline `=` echoes the whole matrix,
  where the one-subscript form echoes the sub-vector `X[i]`.
- **Destructuring a whole matrix.** `[a1 b1 …; …] := M·kg` is an `ir.MultiAssign` whose target
  `<ml:matrix>` has `rows > 1` *and* `cols > 1`. The target ids are listed **column-major**, exactly
  like `<ml:matrix>`'s own elements, so the value is flattened the same way first:
  `a1, b1, … = tuple(unpack(M * ureg.kg))`. (The sheet confirms the order: `v := [a_0; b_0; c_0]` is
  documented as "column 0 of M", and `DET`'s cofactor expansion uses `a_0, a_1, a_2` as row 0.)

### Which `·` is a matrix product — `mcad2py/shapes.py`

Mathcad writes scalar multiplication, matrix multiplication and the dot product all as `·`, and the
XML records no shapes. Deciding between them needs to know how each *name* was defined earlier in the
sheet, so it runs as a pass over the parsed worksheet (`annotate_products`, called at the end of
`parse_worksheet`): it walks the regions in order tracking `name -> scalar/vector/matrix/unknown` and
rewrites every `BinOp("mul", …)` whose **both** operands are array-shaped into `Call("matmul", …)`.

- Anything not *provably* an array stays a plain `*`, so the inference only has to be right about
  what it knows. `2·identity(4)`, `λ_0·R_0` and `M·kg` all keep `*`.
- Nothing under a **vectorize arrow** is rewritten — the arrow is precisely how Mathcad asks for the
  element-wise product (`vectorize(F_ci(…) * Y_c)` in `RC_col.mcdx` must stay `*`).
- Names bound in a smaller scope (a function's params, a program's locals, a lambda's bound var) are
  masked to `unknown` there, so a product inside one is only rewritten when the operands are
  structurally array-shaped on their own (a matrix literal, `augment(...)`, a transpose).
- A **row × column** product is a matmul too: `B·C` with `B` a `1×4` and `C` a `4×1` caches as the
  scalar `112`, which is what `@` on two 1-D arrays gives.

### `matrix(m, n, f)` — a builtin sharing its name with the literal builder

Prime's `matrix` builtin fills an `m×n` matrix from a function of the (0-based) row and column index.
The runtime `matrix()` already existed as the emitter for `<ml:matrix>` literals, so it now
distinguishes the two by the single **callable** argument. Cached: `matrix(3, 3, f)` with
`f(x, y) = x² − y` gives columns `[0,1,4] [-1,0,3] [-2,-1,2]`.

### Eigen results: what LAPACK reproduces

Mathcad is using LAPACK too, so `eigenvals`/`eigenvecs`/`genvals` reproduce its cached values to
full double precision — and, for the symmetric matrices, in Mathcad's own order. What is *not*
reproducible:

- **Ordering.** For the sheet's general (nonsymmetric) 6×6s and for `genvals`, Mathcad's order and
  NumPy/SciPy's differ (the multisets are equal). Mathcad does not sort — the sheet itself calls
  `reverse(sort(eigenvals(S1)))` when it wants a sorted spectrum.
- **Eigenvector sign.** Arbitrary in any implementation; the sheet's `eigenvecs(M)` and the PCA
  transform matrix `T` differ from the cache by a column sign (and `D2 = D·T` with them). Invariants
  do match: `S2`'s diagonal reproduces the cached principal components exactly.
- **Normalisation differs between the two eigenvector builtins**: `eigenvecs` columns are unit
  length (as SciPy returns them), while `genvecs` columns are scaled so their largest-magnitude
  component is `1` — confirmed against the cached `genvecs(M, N, "L")`, whose first column starts
  with a literal `1`.

### `arange` and a fractional endpoint

`j := 0 .. (length(v) − 1)/28` stops at `7.142857` yet takes only integer values, and is then used as
an index (`u[j] := v[n·j]`). So `arange` returns an **integer** array whenever the *start and step*
are whole — the endpoint need not be. (It previously required all three, and produced a float array
here, which NumPy refuses as an index.)

## Collapsible areas (`collapsable-area.mcdx`)

A Prime **area** is a container region — one whose only child is `<Area>`, holding its own `<regions>`
list — that the user can fold shut in the worksheet:

```xml
<region region-id="2" top="96" left="0"><Area><regions>
  <region region-id="3" top="19.2" left="19.2"><text item-idref="R3f6…"/></region>
  <region region-id="4" top="38.4" left="19.2"><math resultRef="1"><ml:define>…</ml:define></math></region>
</regions></Area></region>
```

Collapsing is **purely presentational** — Mathcad still evaluates everything inside, and downstream
regions depend on those definitions — so `_ordered_regions` ([parser/regions.py](../mcad2py/parser/regions.py))
splices an area's contents into the region stream at the area's own position and converts them as
though the area weren't there. Points worth knowing:

- Nested `top`/`left` are **area-relative** (`19.2`, `38.4` above, versus the area's own `96`), so each
  area is sorted *within itself* and inserted as a block. Sorting every region globally would scatter
  area contents to the top of the sheet.
- Areas nest, so the flattening recurses.
- `<Area>` is in the **worksheet** namespace (no `ml:` prefix) and is capitalized, unlike its siblings —
  match on the local name, as everywhere else.
- No collapsed/locked state is recorded in the fixture's `<Area>` (it has no attributes at all). Since
  we flatten regardless, any such attribute is irrelevant to conversion.
- Before this, a region containing an `<Area>` matched none of `_parse_region`'s cases and returned
  `None` — the whole area was silently dropped, definitions included, and dependent regions downstream
  emitted references to names that were never defined.

## Plotting without a plotting variable (`plotting-wo-var.mcdx`)

An `<xyPlot>` needs **no** `x := -10, -9.96 .. 10` above it. Writing `sin(x)` on the y axis against
`x` on the x axis is enough: Mathcad notices `x` is undefined and invents a domain for it. Nothing in
the XML says so — the `<plotEquation>`s are ordinary `<ml:id>`/`<ml:apply>` trees, and the
`<xAxis start="-10" end="10">` attributes are just the *drawn* window (the union of the traces'
extents). The interval is read off the cached `<ml:Trace2dResult>` instead:

```xml
<ml:Trace2dResult TraceType="Parametric">
  <ml:RangeInfo Min="-10" Max="10" />          <!-- trace 1: x on the x axis -->
  <ml:Data><ml:RangePoints><ml:DataVectors … VectorLength="499">[-10,-9.9598…,10]</…>
```

- **-10..10 in 499 points** (a step of 20/498). The `<trace>` element's own `num-of-points="500"` is
  *not* the vector length — the cached data holds 499. `plot_domain()` ([runtime.py](../mcad2py/runtime.py))
  reproduces it as `np.linspace(-10, 10, 499)`.
- **The interval belongs to the free variable, not to the axis.** The fixture's second trace puts
  `x/2` on the x axis against `cos(x)`; its cached `RangeInfo` is `Min="-5" Max="5"` and its y values
  are `cos(x)` for `x` over the *full* -10..10 (checked against `cos(x/2)`, which they are not). So
  the axis expression is just another function sampled over the domain — exactly like the y axis.
- **-10..10 is the default, not the rule.** Setting the x-axis limits makes Mathcad sample the free
  variable over *those* instead (still 499 points). The limits live in the axis's
  `<xyDomain><startValue>/<endValue>` as full `<math>` expressions with their own `resultRef`s;
  while the axis auto-scales they are `<ml:placeholder/>`. The `start`/`end` **attributes** are not
  the setting — they hold the drawn window either way, computed from the data when auto-scaling, so
  reading them back would be circular (`plotting-wo-var.mcdx`'s second trace draws -5..5 from a full
  -10..10). `_parse_axis_limits` ([parser/regions.py](../mcad2py/parser/regions.py)) therefore reads
  the `<xyDomain>` values and only when both are plain numbers (`incomplete_ifs.mcdx`: -7..1,
  confirmed by its cached 499-point trace running -7..1). A limit that is an arbitrary expression
  falls back to the default — no sample pins what Mathcad does there.
- **Inference** is a post-parse pass, `_infer_implicit_plot_domains`
  ([parser/regions.py](../mcad2py/parser/regions.py)), because it needs to know which names the sheet
  ever defines. Walking the regions in order, a `Plot` with no range-typed domain whose axis
  expressions reference **exactly one** variable not bound above it takes that variable as its domain
  and gets `implicit_domain = (-10, 10, 499)`. Order matters: Mathcad reads top-to-bottom, so a
  definition *below* the plot doesn't reach it. Zero free names is a parametric plot (two data
  vectors, see the `RC_col` note) and two is not a function plot — both are left alone. `π`/`e` are
  skipped: they're still bare identifiers in the IR (codegen is what maps them to `math.pi`/`math.e`),
  so `sin(π·x)` would otherwise look like two free variables.
- **The invented variable is scoped to the plot.** Codegen puts the array in `_domain_<name>` rather
  than `<name>`, since Mathcad conjures it for the one plot — leaking it would let a region below
  silently resolve a name that has no value in the worksheet.
- The legend names the **y** expression whenever the domain is implicit. The usual rule ("whichever
  axis isn't the domain") doesn't decide the `x/2` vs `cos(x)` trace, where *neither* axis is the bare
  variable.

## Mixed trace kinds on one plot (`mixed_plot_traces.mcdx`)

An `<xyPlot>`'s traces need not all be the same kind. A **parametric** trace has data vectors on
both axes (a section outline); a **function** trace has the plotting range on one axis and a
function of it on the other. Mathcad records which is which in the cached result — `TraceType`
is `"Vector"` vs `"Range"` — and, decisively, **their lengths differ**: the fixture caches a
3-point `Vector` trace beside a 101-point `Range` one.

Nothing in `<plotEquations>` marks the difference; both are ordinary expression `<math>`s. So the
kind has to be inferred, per trace, from whether the axis expression **references the plotting
variable**. `_detect_domain` finds one domain for the whole plot (the first bare-`Name` axis that is
a range), which is right for the plot but wrong per trace: applying it everywhere emitted
`sample(lambda t: v, t)` for the parametric trace, evaluating a constant vector once per domain point
into a nested object array that `plot_axis` can't flatten.

`_plot_axis_call` ([emit/codegen.py](../mcad2py/emit/codegen.py)) now samples only expressions that
actually mention the domain. A domain-independent expression is emitted through `static_axis`, which
settles the one case codegen can't: a **vector** is a parametric trace and keeps its own length,
while a **scalar** is a reference line and is broadcast across the domain (which is what `sample`
incidentally did for it before — the only part of the old behaviour worth keeping).

## Auto-labelled identifiers (`labels="*"`) — worksheets converted from `.xmcd`

An `<ml:id>` normally declares its role: `labels="UNIT"`, `"VARIABLE"`, `"FUNCTION"`, `"CONSTANT"`.
A worksheet **Prime converted from a legacy Mathcad 15 `.xmcd`** carries `labels="*"` on a large
share of them instead — Mathcad 15's `math30` schema didn't record the distinction, so the converter
leaves the name uncommitted and resolves it from context at evaluation time. One real converted sheet:
1522 `VARIABLE`, 134 `UNIT`, **125 `*`**, 81 `FUNCTION`, 8 `CONSTANT`.

`_parse_id` maps only `labels="UNIT"` to `ir.UnitRef`, so an auto-labelled `MPa` became a plain
`Name` and the echo emitted `x / (MPa)` — a `NameError` against a name nothing defines — instead of
`disp(x, ureg.MPa)`.

**Resolve by slot, never by name.** In the same sheet, the 114 auto-labelled ids inside
`<ml:unitOverride>` are all units (`mm`, `MPa`, `kN`, `GPa`, `m`) while the 11 outside it are all the
loop index `i` — auto-labelled at its *use* even though the enclosing `<ml:for>` declares it
`labels="VARIABLE"`. So a name-based rule ("is it a known unit?") would turn `i` into `ureg.i`, and
would break any sheet with a variable called `m`. `as_units()`
([parser/expressions.py](../mcad2py/parser/expressions.py)) instead reinterprets `*` **only** in slots
that are a unit by definition — the display override and a plot axis's/`plot3D`'s unit `<math>` —
recursing through compound units (`kN·m` is a `<mult>` of two ids). An explicit `labels="VARIABLE"`
there is left alone: a variable used as a display scale is legal and already divides correctly.

Not yet handled: an auto-labelled unit in a *value* expression (`f_ck := 30 MPa` written with `*`).
The converted sheet inspected labels those `UNIT`, so no sample forces the issue; resolving it would
need the sheet-wide defined-name set to tell a unit from a variable that shadows one.

## Blank lines and uncovered cases in programs (`incomplete_ifs.mcdx`)

- **A blank line in a program is a bare `<ml:placeholder/>`** child of `<ml:program>` — the same tag
  as an empty slot anywhere else, with no marker distinguishing "empty line" from "empty operand":

  ```xml
  <ml:program>
    <ml:if>…</ml:if>
    <ml:placeholder />   <!-- a blank line the author left in the middle -->
    <ml:if>…</ml:if>
  ```

  Mathcad ignores it, so `_program_lines()` ([parser/expressions.py](../mcad2py/parser/expressions.py))
  filters it out before anything else looks at the body. This **must not** be parsed as a statement:
  a bare expression line is an *implicit return*, so a blank one emitted `return None` mid-function and
  made every branch below it unreachable. Filtering happens *before* the "more than one line" test that
  decides value-`Program` (ternary) vs. imperative `ProgramBlock` (`def`) too, so a lone trailing blank
  can't flip a one-line `σ := if …` into a function definition. Blanks are stripped in the same way
  inside a `<ml:then>`/`<ml:else>` body, where the first line is the branch's value.
- **A program need not cover every case.** Mathcad accepts `if`-chains with no `else`; the sheet only
  errors if an argument actually reaches the end — `This program has no return value. You must account
  for all cases when using conditional statements in a Mathcad program.`, cached as an
  `<engineErrors><engineError>` in place of that region's `<ml:result>`. Our `def` just falls off the
  end and returns `None`, so the *reachable* calls (the point of such a sheet) match Mathcad and only
  the erroring one diverges. Worth knowing when reading a cached `result.xml`: a region with no result
  isn't necessarily one Mathcad didn't evaluate.
- **Plotting one draws a gap, not an error.** Where such a program has no branch, the cached trace
  holds a literal **`NaN`** (`[…,-0.3162650602409639,NaN,NaN,…]` — note `json.loads` won't parse that
  vector, though `float()` will). So `sample` ([runtime.py](../mcad2py/runtime.py)) maps a `None`
  sample to NaN, and matplotlib breaks the line exactly where Mathcad does. The NaN takes the
  **unit** of the points that are defined, without which the column stays a mixed `object` array and
  `plot_axis`'s `data / unit` raises. Only `None` is filled — a point that *raises* is left to
  propagate, since swallowing exceptions here would turn a conversion bug into a silently empty plot.
