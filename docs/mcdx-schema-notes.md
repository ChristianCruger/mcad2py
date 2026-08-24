# Confirmed Prime schema (from `references/.../worksheet.xml`)

Detailed, confirmed notes on how PTC Mathcad Prime's `.mcdx` XML (`worksheet50`/`math50`) maps to
this project's IR ([mcad2py/ir.py](../mcad2py/ir.py)). Referenced from [CLAUDE.md](../CLAUDE.md) —
read this file when parsing a new schema construct or debugging a parser edge case.

## Headers and footers (`header_footer.mcdx`)

Prime stores headers and footers in `mathcad/header.xml` and `mathcad/footer.xml`.
Each part has its own relationship file and relationship ID scope:
`mathcad/_rels/header.xml.rels` and `mathcad/_rels/footer.xml.rels`.
Text regions point to the usual `mathcad/xaml/*.XamlPackage` files.

Both parts use the worksheet region structure and can contain `<text>` and `<math>` regions.
Header math is presentation content. It does not define values used by the worksheet body.
The converter parses it into separate `Worksheet.header` and `Worksheet.footer` lists.
The backends emit it as `[display math]` comments, not executable code.

A dynamic page field is `<fieldText>` with a `<pageNumber>` child.
Its cached text, such as `Page 1 of 2`, describes Mathcad pages only.
The region parser omits this field. It keeps other `<fieldText>` values as text context.

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
  imported `Quantity`, or you get cross-registry errors); a real `rows×cols` matrix emits
  `matrix([row0…], [row1…], …)` — **one bracketed list per row**, so the literal reads as it looks in
  Prime and the shape is implied rather than passed. The emitter regroups the column-major `elements`
  into rows; the helper flattens them back column-major and reshapes with `order="F"`, and handles
  units the same way as `col()`. A literal wider than 88 characters is emitted **one row per line**
  (a lone row never wraps — nothing to line it up against); the newlines sit inside `matrix(`'s own
  parentheses, so the literal stays a single expression however it is nested, and `_reindent` gives
  the continuation lines the enclosing statement's indent (Mathcad requires one consistent unit across the *whole* matrix, no per-column
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
  A **zero-fill gap counts as homogeneous**: `0` is `0` in any unit, so a loop running `i = 1 .. n`
  still consolidates despite the bare `0` left at index 0 (Mathcad caches such a vector with one unit
  for the whole matrix — see `references/implied_index0_unit.mcdx`). Absorbing it matters far
  downstream: an unfused `dtype=object` vector is *dimensionless* to Pint, so a later `z / m` reads as
  `1/meter` and the sheet dies with a `DimensionalityError` regions away from the actual cause. The
  rule is **zero only** — a nonzero plain entry mixed with dimensioned ones is genuinely dimensionless
  (RC_col's `[1; −l/2; −w/2]` constant column) and must keep its own per-element type, exactly as
  `_build_array` treats a matrix literal.
- **A column vector is 1-D; a row vector is a matrix.** `<ml:matrix rows="N" cols="1">` → `col(…)`, a
  1-D array — a single subscript `z[0]` must read the *element*, where an `n × 1` shape would hand back
  a one-row slice (`[0.0]`). But `<ml:matrix rows="1" cols="N">` is a genuine `1 × N` and emits
  `matrix([…])` (a single row list). Mathcad says so itself: `match` on a `3 × 1` column returns a bare index, on a
  `1 × 3` row an index **pair** — and only a matrix has `(row, col)` positions. Collapsing both to 1-D
  loses the orientation `stack`/`augment` need, so a header literal `("A" "B" "C")` landed down
  column 0 instead of across row 0 (`references/stack_augment_lookup.mcdx`).
  `transpose` moves between the two forms, which it must do explicitly — NumPy's transpose of a 1-D
  array is itself, and Mathcad's usual way of *typing* a column vector is the transposed row literal
  `(a b c)ᵀ` (see `shrinkage.mcdx`, `RC_col.mcdx`), which has to come back 1-D.
- **`stack`/`augment` take blocks, not just vectors** — matrices join edge to edge (a scalar counts as
  `1 × 1`), which is how a labelled table is built: `stack(("A" "B" "C"), s)` captions the columns,
  `augment(("X" "Y" "Z")ᵀ, s)` the rows, and both together give the `vhlookup` shape.
- **Table search** — `match(z, A)` returns the positions of `z` in `A` (scalar indices for a vector,
  `(row, col)` pairs for a matrix), `lookup(z, A, B)` the elements of a parallel `B` at those
  positions, `vlookup(z, A, c)`/`hlookup(z, A, r)` search `A`'s first column/row and read out
  column `c`/row `r`, and `vhlookup(z_v, z_h, A)` reads the intersection. All five return a **vector**
  even for a single hit (Mathcad caches a `1 × 1` matrix, not a scalar); a matrix is scanned
  **column-major**; a value that isn't there is an error, not an empty result.
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
The runtime `matrix()` already existed as the emitter for `<ml:matrix>` literals, so it
distinguishes the two by the **trailing callable** argument — the literal form takes one list per row
(`matrix([1, 2], [3, 4])`), the builtin the `(m, n, f)` triple. Cached: `matrix(3, 3, f)` with
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

## Log/exponential catalogue and a redefined builtin (`log-exp.mcdx`)

- **The imaginary literal is `<ml:imag symbol="i">1</ml:imag>`**, a sibling of `<ml:real>` (not a child
  of it, and not wrapped in a `<ml:complex>` — that wrapper only appears in *cached results*, e.g.
  `result.xml`'s `ln(-3)`). The text is the magnitude; parsing it as `<magnitude>j` is already a valid
  Python complex literal, so `e^(i·π) + 1` (Euler's identity) needs no dedicated IR node.
- **`log`'s two-argument form is `<ml:sequence>` of the value and the base**, same shape as any other
  multi-arg call (`log(1000, 10)` → `<ml:apply><ml:id>log</ml:id><ml:sequence><ml:real>1000</ml:real>
  <ml:real>10</ml:real></ml:sequence></ml:apply>`) — nothing schema-special, but easy to miss if a
  builtin's Python mapping is a bare string (`"log": "math.log10"`) rather than a callable that can see
  `len(args)`.
- **Redefining a builtin changes the `labels` attribute at its later call sites.** `exp(x) := x + 2`
  followed by `exp(2)` gives the *call* an `<ml:id labels="VARIABLE" label-is-contextual="true">exp
  </ml:id>` head — not `labels="FUNCTION"` the way an un-shadowed builtin call ("log", "sort", …) gets.
  This is the same label an ordinary user-defined function call already carries (confirmed against
  `solve_as_function.mcdx`'s `f(1, 3)`), so `ir.Call.role` already captured the distinction — the bug
  was that [emit/codegen.py](../mcad2py/emit/codegen.py) mapped every `Call.func` through the builtin
  `FUNCTIONS` table unconditionally, ignoring `role`. The fix: skip that lookup whenever
  `role == "VARIABLE"` and call the (sanitized) name bare, everywhere the check happens — the
  expression printer itself, and the import-collection passes (`_used_runtime`/`_uses_numpy`) that scan
  for which runtime helpers a generated module needs.

## Difference equations — seeded iteration (`difference_eq.mcdx`)

- **The target is an indexer whose index is an *expression*, not a bare id.** That single detail is
  what separates a difference equation from the parallel `X[i] := …` build:

  ```xml
  <ml:define>
    <ml:apply><ml:indexer />
      <ml:id labels="*">guess</ml:id>
      <ml:apply><ml:plus /><ml:id labels="*">i</ml:id><ml:real>1</ml:real></ml:apply>
    </ml:apply>
    …the right-hand side, which reads guess[i]…
  </ml:define>
  ```

  A **constant** index (`guess[0] := 30`) is the *seed*; an index written in terms of a range variable
  (`guess[i+1]`, `Data[i+N]`, `V[i, k]`) is the *step*, and Mathcad runs it **sequentially** — each
  step reads the elements the steps before it wrote. `_parse_index_target` keeps requiring a bare
  `<ml:id>` index and still yields `ir.IndexAssign` (one `index_build` pass, elements independent);
  everything else now routes through `_parse_recurrence_targets` to `ir.Recurrence`
  ([parser/regions.py](../mcad2py/parser/regions.py)).
- **A *system* puts a `<ml:matrix>` of indexers on the left**, one row per equation, against a matching
  `<ml:matrix>` of right-hand sides — `[inf[τ+1]; sus[τ+1]; dec[τ+1]; rec[τ+1]] := […]`. Careful: a
  matrix of plain `<ml:id>`s on the left is the *destructuring* `ir.MultiAssign` instead, so the
  distinction is "is every entry an indexer". Mathcad updates a system **simultaneously**, which the
  emitted loop reproduces by staging the step in a tuple before writing any of it back — evaluating
  target by target would feed `sus[τ+1]`'s formula the `inf[τ+1]` the same step just produced.
- **A matrix recurrence writes two-subscript slots.** `V^<k> := A·V^<k-1>` is stored as three
  `V[i, k]` targets (an `<ml:indexer>` with a `<ml:sequence>` of two indices) against one vector-valued
  right-hand side, which is destructured across them. The `·` needs
  [shapes.py](../mcad2py/shapes.py) to have resolved it to a matrix product, so `annotate_products`
  visits a `Recurrence` with the driving index bound as a **scalar** and records each target base as a
  vector (or matrix, for the two-subscript form).
- **The driving range variable is only identifiable from the sheet.** The index carries the
  define-target label `labels="*"`, not `VARIABLE`, so the driver is found by intersecting the index's
  identifiers with the names defined as a `<ml:range>` above it — a whole-sheet pass
  (`_resolve_recurrences`), which also works out which base names a region is the first to write and
  so must create from nothing.
- **The loop variable must not leak.** The sheet keeps using `i` as a *range* below the recurrence
  (`i_range[i] := i`), so a bare `for i in i:` would leave it bound to the last scalar index. The
  emitted loop therefore lives inside a `def _recur_<names>(_idx, …)` that takes the vectors in and
  returns them, letting Python's own scoping keep the two apart.
- **`i := 0 .. N` writes N+1 elements, so the built vector outruns its index range.** With `N = 8`,
  `guess[i+1] :=` fills indices 1..9 and `guess` ends up 10 long against a 9-element `i`. Both the
  echo and the plot show this: `(guess[i])² - X =` caches **9** rows (the expression is evaluated over
  the range — plain NumPy fancy-indexing reproduces it, since `arange` returns an *integer* array),
  while the plot's cached trace pads the short axis, `[0,1,…,8,NaN]` against ten values. Hence
  `plot_trace` ([runtime.py](../mcad2py/runtime.py)), which NaN-pads a trace's two axes to a common
  length where matplotlib would reject the mismatch.
- **An inline `=` after a difference equation shows the slots it just wrote.** `Data[i+N] =` caches the
  5-element sub-vector, not all of `Data` — with the range variable still bound to its integer array,
  the echo is literally `Data[i + N]`.

## Statistics catalogue (`statistics.mcdx`)

- **Capitalisation is the estimator, not a style choice.** `var`/`stdev` are the *population* forms
  (divide by n) and `Var`/`Stdev` the *sample* forms (divide by n-1); the sheet computes each pair
  twice, once through the builtin and once from a hand-written Σ, which is how the mapping was
  confirmed. `skew`/`kurt` are the bias-corrected sample coefficients and `kurt` is *excess* kurtosis.
- **`percentile(A, p)` interpolates at position `p·(n+1)`** of the 1-based sorted sample — NumPy's
  `method="weibull"`. The cache settles it: the 90th percentile of `0 … 10` is **9.8**, not the 9 every
  "nearest rank" definition (and NumPy's default) gives.
- **`%` has *two* XML spellings, and this sheet uses the second.** `shrinkage.mcdx` writes it as a
  dedicated postfix operator, `<ml:apply><ml:percent /><ml:real>100</ml:real></ml:apply>` (parsed as
  `100 / 100`); here `50%` is instead an ordinary **scale apply**,
  `<ml:apply><ml:scale /><ml:real>50</ml:real><ml:id labels="FUNCTION">%</ml:id></ml:apply>` — the same
  shape as `50 mm`, treating `%` as the dimensionless unit worth 0.01 that Mathcad's unit system says
  it is, but labelled `FUNCTION` rather than `UNIT`. `%` can't be a Mathcad variable name, so
  `_parse_id` keys on the name itself and yields a `UnitRef`, mapped to Pint's `percent`. Both
  spellings have to be handled; neither subsumes the other.
- **Mathcad's own errors are cached, and a *tutorial* sheet may show them deliberately.** `mode(v)`
  refuses to guess: `no_duplicates` ("No value occurs more frequently than any others.") when nothing
  repeats and `multimodal` when the top frequency is shared, both stored as
  `<engineErrors><engineError><resource-string>` in place of the region's `<ml:result>`. Since the
  translation is faithful it raises too, which would abort the generated module — so `result.xml` is
  now read at parse time and such a region is emitted inside a `try`/`except` that prints Mathcad's own
  wording (`ir.Region.cached_error`). This retro-fixed `log-exp.mcdx`'s `ln(0)` and
  `incomplete_ifs.mcdx`'s uncovered program branch, both of which previously stopped their sheet dead.
- **The correlation set returns *all* the statistics its Numerical Recipes routine computes**, not just
  the coefficient: `Spear` → `(D, zd, probd, rs, probrs)` (NR `spear`), `kendltau` → `(τ, z, p)`
  (`kendl1`), `kendltau2` → the same three for a contingency table (`kendl2`), `contingtbl` →
  `(χ², df, p, Cramér's V, C)` (`cntab1`), and `Ftest` → `(F, p)`. The cached vector lengths are how
  each was identified. NR's `kendl2` walks the table's cells in **row-major** order and weights each
  pair by the product of the two counts — reproduced literally in
  [runtime.py](../mcad2py/runtime.py), since a vectorised rewrite would be harder to check against the
  original.
- **`Rank(v)` is 1-based ascending** — Mathcad's rank-transform, unrelated to `rank(M)` (matrix rank),
  which it differs from only by capitalisation.
- **`histogram(n, A)` returns an `n × 2` matrix** of bin midpoints and counts over `n` equal-width bins
  spanning the data. Column 0 keeps the sample's unit, so with dimensioned data the result is
  necessarily a mixed-unit (object) matrix; the sheet plots it as `matcol(H, 0)` against `matcol(H, 1)`.
- **The `r*` draws are random, by design.** `rnorm`/`rweibull`/`rt` produce a fresh sample every run,
  so every statistic below them in the sheet is unreproducible against the cache — see
  [test-coverage.md](test-coverage.md) for which regions that covers.

## Built-in constants (`Constants.mcdx`)

- **The `labels` attribute is the whole mechanism.** Prime's *Constants* label writes
  `<ml:id labels="CONSTANT">c</ml:id>`, and that is the only thing separating the speed of light from
  a worksheet variable called `c` (which every other fixture here spells `labels="VARIABLE"`). The
  sheet's own opening line says it out loud — "if symbols have not been defined as something else".
  So `mapping.CONSTANTS` may safely hold `c`, `g`, `k`, `R`, `e`, `σ`, `α`, `γ`: the lookup in
  [emit/codegen.py](../mcad2py/emit/codegen.py) is reached only for `role == "CONSTANT"`.
- **The key is the *display* name, subscript and all.** `read_identifier` joins a XAML
  `<pw:Subscript>` with an underscore, so the table is keyed `e_c`, `m_u`, `N_A`, `R_∞`, `ε_0`, `μ_0`,
  `Φ_0` — before `sanitize()` transliterates the Greek. `ℏ` (U+210F) arrives as a plain one-character
  id.
- **The cache states a dimensioned constant in base SI**, as a `<ml:unitedValue>` of a `<ml:real>` and
  a `<u:unitMonomial>` (`R` as `kg·m²·s⁻²·K⁻¹·mol⁻¹`) — the one exception being `Φ_0`, cached in
  `weber`. [const.py](../mcad2py/const.py) therefore defines each value in base units too (`h` as
  `kg·m²/s`, not `J·s`); see the next point for why that matters.
- **The values are *imported names*, not inlined numbers.** `mapping.CONSTANTS` maps each display name
  to a name in [const.py](../mcad2py/const.py) (`ℏ` → `hbar`, `R_∞` → `R_inf`), and the header emits
  `from mcad2py.const import c, …`, so a formula reads `m * c**2` rather than carrying 299792458 around.
  Two consequences worth knowing:
  * **They are pre-built Pint quantities, so there can only be one registry.** Pint refuses to combine
    quantities whose registries differ, so generated modules now take
    `from mcad2py.units import ureg` instead of constructing their own — which also lets two converted
    worksheets exchange values in one process.
  * **The import list is driven by the IR, not by scanning the emitted text** (which is how the runtime
    helpers are found). `c`, `g`, `k` and `R` are everyday variable names; a text scan would import
    Boltzmann's constant on the strength of a worksheet's own `k`. A CONSTANT-labelled `ir.Name` is
    unambiguous. A sheet that *does* define its own `k` shadows the import by plain assignment, which is
    close to Mathcad's own behaviour — the divergence is that Prime keeps the two apart by label even
    then, so a sheet using both spellings of one name would read the variable for both.
- **A display override can carry a numeric scale**, and it is *not* the pure-scale form `_display`
  already knew about. Mathcad shows Planck's constant as `10⁻³⁴ kg·m²/s`, which is a `<ml:scale>` (or
  `<ml:mult>`) of `10^-34` against a unit monomial — units *and* a factor, so `_has_unit` is true and
  the override goes to `disp(value, unit)`. Pint evaluates that override to a **Quantity** (magnitude
  `1e-34`) rather than a **Unit**, and `Quantity.to(<another Quantity>)` silently uses the argument's
  *units alone*: `h.to(10**-34 · kg·m²/s)` returns the unscaled `6.626e-34`, not Mathcad's `6.626`.
  `disp` now divides whenever the override's magnitude isn't 1, which is the faithful rendering and
  is what makes the base-unit table entries line up digit for digit.
- **`∞` is really 10³⁰⁷** — that is the number `result.xml` caches for it, and Mathcad's documented
  stand-in for infinity. We deliberately emit `math.inf` instead: it is the faithful reading of the
  symbol, and the only one that behaves as an integration limit or a comparison bound. The one
  divergence the fixture records.
- **`γ` is Euler-Mascheroni here**, not a variable named gamma; `σ` is Stefan-Boltzmann, not a stress;
  `k` is Boltzmann, not a stiffness. Again: the label, not the spelling.

## Equation breaks, number sets and logic (`breaks-sets-logic.mcdx`)

- **`<ml:globalDefine>` is `<ml:define>` with a different scope.** Mathcad's `≡` binds over the *whole*
  sheet — a region **above** it may use the name — which is its entire reason to exist. Structurally the
  element is identical to a define, so parsing reuses `_parse_define` and only sets
  `ir.Define.global_scope`; `_hoist_global_defines` then moves those regions to the top, the one way a
  linear Python module can honour sheet-wide scope. The partition is stable and leaves text regions
  alone, so the `≡`'s own heading is left behind — better than dragging unrelated prose up with it.
- **`split="true"` on an operator is a *display* attribute.** `<ml:plus split="true" />` is Mathcad
  wrapping a long formula onto the next line (`div` also carries `inline="true"` for the `/` form). It
  says nothing about the tree, so it is ignored — the fixture exists to pin that.
- **The right operand of `∈` is an `<ml:id>` with no `labels` attribute at all.** `ℤ`, `ℝ`, `ℚ`, `ℂ`,
  `ℕ` — every other id in the schema is VARIABLE/FUNCTION/UNIT/CONSTANT, so this is the one place the
  attribute is simply absent. Left as an `ir.Name` it would emit an undefined identifier; `_number_set`
  turns it into an `ir.Str` and it reaches `element_of` as a string.
- **`π ∈ ℚ` is a *symbolic* region — and that is not incidental.** No float can answer it (every float
  is a rational), which is why the sheet's own text says "Rational numbers has to be evaluated
  symbolically" and the region is an `<ml:symEval>` whose `<ml:command>` holds a bare
  `<ml:placeholder />` — a plain `→` with no keyword. `SYMBOLIC_COMMANDS[""] = "simplify"` covers that
  case; the answer itself comes from SymPy's `nsimplify`, which recovers the closed form a float came
  from (`3.14159…` → `π`, so `is_rational` is False). Mathcad's own `<ml:symResult>` caches `0`.
- **Every logical operator answers with the number 1 or 0.** `<ml:not>` maps to Python's `not` (which
  says exactly the same thing of a number, and `bool` is an `int`); `<ml:notEqual>` to `!=`;
  `<ml:factorial>` to `math.factorial`. `<ml:xor>` needs a helper — Python's `^` is *bitwise*, so
  `3 ⊕ 2` would come out 1 where Mathcad says 0.
- **`∧`/`∨` stay Python's `and`/`or`, with one known divergence.** They are almost always boolean
  connectives in a program test, where the two agree exactly. They differ when an operand is neither
  0 nor 1: Mathcad's `1 ∧ 3` is `1`, Python's is `3`. Rewriting them as helpers would churn every
  condition in every sheet to fix a case no worksheet here writes, so they are left alone.
- **A rendered `# TODO unsupported: …` cannot be wrapped in `print(...)`** — the closing parenthesis
  lands inside the comment and the whole generated module stops parsing, defeating the point of
  emitting a visible TODO instead of dropping the region. `print_lines`
  ([emit/codegen.py](../mcad2py/emit/codegen.py)) lifts the note onto its own line first. The notebook
  backend echoes as a bare last line and was never affected.

## `Σ` over a range variable (`<ml:summation>` with no bounds)

Prime writes three different things with the same `<ml:summation>` head, told apart by the lambda's
bound variables and the bounds:

| bound var | bounds | meaning | IR |
|---|---|---|---|
| named | `<lowerBound>` + `<upperBound>` | indexed sum `Σ_{i=a}^{b}` | `ir.Summation` → `summation(f, a, b)` |
| none | `<upperBound><placeholder/></upperBound>` | bare `Σ` over an already-built vector | `ir.VectorSum` → `total(v)` |
| named | `<upperBound><placeholder/></upperBound>`, no `<lowerBound>` at all | **range summation** — the index is a range variable defined elsewhere on the sheet, summed over every value in it | `ir.RangeSum` → `range_sum(i, lambda i: …)` |

The third form emits `range_sum(<var>, lambda <var>: <body>)`: the first argument reads the range
variable from the enclosing scope, and the lambda's parameter shadows it for the body — the same name
doing the same two jobs Mathcad gives it.

`references/range_sum.mcdx` puts all three forms over the same data and settles it: with
`i := 0..10` and `X[i] := mod(2i, 7)`, both the bare `Σ` and the range sum cache **33**, while the
indexed `Σ_{j=1}^{4}` caches 13. So an empty bound means the *whole* range variable — not an
unfinished slot, and not a zero-length sum. A second region, `Σ_i f(2i) = 1551`, pins that the body
sees each index value rather than the range as a whole.

## A note nested inside an expression

`ir.Placeholder` and `ir.Unsupported` render as `None` plus a `# …` comment. A comment swallows the
rest of its line, which is harmless when the note *is* the whole expression and fatal one level down —
`summation(f, None  # placeholder, None  # placeholder)` puts the closing parenthesis inside the
comment and the module stops parsing, the one outcome the "output still loads" convention exists to
prevent.

So a note node now renders as a bare `None` and pushes its text to a collector; the outermost
`expr_to_str` appends the collected notes once, at the end of the line. A top-level note comes out
byte-identical to before; a nested one becomes `foo(None, 2)  # TODO unsupported: apply/derivative`.
`print_lines` still lifts a trailing note onto its own line, unchanged.

## `seed.mcdx` — Mathcad's random number generator

`Seed(n)` restarts Mathcad's random stream. Reproducing that stream exactly is possible: Prime's
generator is the **Microsoft C runtime `rand()`**, and `Seed(n)` is `srand(n)`.

```
state = seed                                  # Seed(n) -> srand(n)
rand():  state = (state * 214013 + 2531011) mod 2**32
         return (state >> 16) & 0x7FFF        # 15 bits
runif:   u = (rand() * 32768 + rand()) / 2**30
rnorm:   Kinderman-Monahan ratio of uniforms --
             u = runif(); v = sqrt(8/e) * (runif() - 0.5); x = v / u
             accept when x**2 <= -4 * ln(u)
         and rnorm(m, mu, sigma) returns mu + sigma * x
```

Confirmed against every cached value in the fixture at **0.0 absolute error**: the 20-element
`runif`, the single `rnorm` draw, the four uniforms that follow it, and the 1000-element sample the
sheet's program builds. The constant is `sqrt(8/e)` exactly, **not** Numerical Recipes' rounded
`1.7156` (they differ at the fifth decimal, which the cached values resolve).

How the method was identified is worth recording, because the same trick cracked the rest of the
family. `Seed(1)`, then `rnorm(1,0,1)`, then `runif(4,0,1)` — the four trailing uniforms came back
as `U[4..7]` of the seeded stream, so one normal draw had consumed exactly **four** uniforms. That
count is the fingerprint: inverse-CDF would take one, Box-Muller two, sum-of-12 twelve. Four means two
ratio-of-uniforms attempts, the first rejected.

### The rest of the `r*` family

The sheet repeats that three-region block — `Seed(1)`, one draw, `runif(4,0,1)` — once per function.
Writing `U[k]` for the uniform stream after `Seed(1)`, the trailing four land at offset `k`, which is
the draw's consumption; the value then identifies the method uniquely. All of the following are exact
to the last bit against the cache.

| function | uniforms | how Prime draws it |
|---|---|---|
| `rexp(m, r)` | 1 | `-ln(u) / r` |
| `rweibull(m, s)` | 1 | `(-ln u) ** (1/s)` |
| `rlogis(m, l, s)` | 1 | `l + s * ln(u / (1 - u))` |
| `rcauchy(m, l, s)` | 1 | `l + s * tan(pi * (u - 1/2))` |
| `rgeom(m, q)` | 1 | `floor(ln(u) / ln(1 - q))` |
| `rbinom(m, n, q)` | 1 | inverse CDF, walking the mass function |
| `rpois(m, lam)` | k+1 | Knuth multiplication: multiply uniforms until the product drops below `exp(-lam)` |
| `rnbinom(m, n, q)` | 1 + k+1 | gamma-Poisson mixture: `Poisson(Gamma(n) * (1-q)/q)` |
| `rgamma(m, s)` | varies | see the shape split below |
| `rchisq(m, d)` | varies | `2 * Gamma(d/2)` |
| `rbeta(m, a, b)` | varies | `G(a) / (G(a) + G(b))` |
| `rF(m, d1, d2)` | 6 at (1,1) | `(chisq(d1)/d1) / (chisq(d2)/d2)` |

Every continuous inverse CDF above is on `u`, **not** `1 - u`. The two differ only in the stream, not
in the distribution, so a cached value is the only way to tell — and each of these five pins it.

**The gamma shape split.** Gamma shapes add, so Prime builds `Gamma(a)` from pieces it can draw
directly, and three separate blocks each pin one piece:

- whole part → that many exponentials (`rnbinom` and `rbeta` reach `a = 1`, one uniform);
- a remaining half → `z**2 / 2`, one normal (`rgamma(1, 0.5)`, four uniforms);
- any other fraction → **Johnk's ratio**, two uniforms per attempt plus one exponential
  (`rchisq(1, 0.5)` is `2 * Gamma(0.25)`, three uniforms).

No block mixes two pieces, so the *order* of the pieces is inferred rather than measured. Johnk's two
powers must be spelled differently to reproduce Prime's last two bits: `exp(log(u)/a)` for the first
and `**` for the second. `**` for both is off by 2 ulp, which the cached `rchisq` resolves.

Because integer `d` lands on the half arm, `chisq(1)` is exactly `z**2` — which is why `rF(1,1,1)` is
two normals and comes out as `(z1/z2)**2`.

**`rt` is not solved.** Its cached value is exactly `z1 / z2`, two normals and six uniforms, but the
block consumed **seven**. The seventh is drawn after the value is formed. One cached draw cannot say
whether it flips the sign or is discarded, and a wrong guess would silently negate half of all draws,
so `rt` stays on NumPy. One more block at a different seed would settle it: compute `z1/z2` from that
seed and see whether the cached `rt` keeps or flips the sign.

**`rhypergeom` is untested.** The sheet calls it as `rhypergeom(1, 0, 1, 1)` — zero white balls, so
the answer is a deterministic 0 and no uniform is drawn. It stays on NumPy.

**`rlnorm` has no block.** It is `exp(rnorm(...))`, which follows from `rnorm` rather than from a
cached number.

Three region/statement shapes appear here for the first time.

- **A bare call region.** `Seed(1)` on its own line is an `<ml:apply>` directly under `<math>` — no
  `<ml:define>`, no `<ml:eval>`. Mathcad runs it and displays nothing, so it becomes `ir.Statement`
  and emits a plain call. Wrapping it in `print` would invent output the sheet never shows. The same
  call *with* `=` (an `<ml:eval>`) is an ordinary evaluation and echoes.
- **A new worksheet starts at state 1**, the same place `Seed(1)` puts it. Typing `runif(4,0,1)` as
  the first region of a fresh sheet gives the same four numbers as `Seed(1)` then `runif(4,0,1)`, and
  `Seed(1)` as the first region of a fresh sheet echoes `1` — its previous state. So a worksheet that
  never calls `Seed` is reproducible too, and the module-level generator is constructed at 1.
- **`Seed(n)` returns the generator's *previous* 32-bit state**, not `n` and not a status code.
  Six consecutive `Seed` regions on the sheet make it unambiguous: after a `Seed(1)` the next
  `Seed(1)` echoes `1`, and after a `Seed(2)` the next echoes `2`, while a `Seed(1)` placed after a
  20-element `runif` run echoes that run's end state (`2617919885`). Running the LCG **backwards**
  from such an echo recovers where a block started, which is how the recalculation-order divergence
  below was found.
- **A bare call above the last line of a program body is a statement, not a return.** Mathcad's
  implicit return is a block's *final* line only. `Seed(1)` at the top of a `for` body previously
  became `return Seed(1)` and swallowed the two lines below it. `ir.ExprStmt` is that line.
- **`M^<i> := v` inside a program** writes a whole column. Prime writes it as an ordinary `matcol`
  target, so it reaches the IR as `ir.MatCol` (not an index node) and emits `col_set` — the column
  form of `vec_set`, sharing its growth, zero-fill and consolidation rules.

One more thing this sheet is the first to hit: it names a variable **`range`** (`range[n] := n`),
which shadows the Python builtin for every line below it. `sanitize()` now suffixes `_` on any name
that collides with a Python keyword or builtin. Two existing fixtures were already affected —
`probability.mcdx` was emitting both `range = …` and `int = …`.

### One divergence: Prime's recalculation order

Region 13 is the bare `Seed(1)`; region 14 draws `runif(20, 0, 1)` directly below it. Mathcad's cache
for region 14 does **not** start at state 1. Running the LCG backwards 40 steps from region 15's
echoed state gives 1365253, which is 5556 `rand()` calls past state 1 — exactly one `Seed(1)` plus
`rnorm(1000)`, i.e. one pass of the `Same` program *above* region 13. So Prime evaluated the bare
`Seed` region before the program rather than in reading order.

Generated code runs in reading order and therefore starts region 14 at state 1. This is Prime's
evaluation order, not a generator bug, and it is confined to those two regions: region 15 reseeds and
every block after it is exact. `tests/test_seed.py` pins the divergence rather than hiding it — it
asserts the two values differ, then reproduces Mathcad's by replaying the program pass first.

A useful side effect: 5556 rands for 1000 normals is itself a check on the Kinderman-Monahan
acceptance rate, and our `rnorm` lands on the same state to the bit.

The file is a **Prime 12** worksheet and still declares `worksheet50`/`math50`, like every other
fixture, so nothing in the parser needed a version check.

## Interpolation & prediction (`interpolation_prediction.mcdx`)

PTC's own tutorial sheet for the family. Three XML constructs it is the first fixture to reach, then
the algorithms the cache identified.

**The numeric derivative operator.** `<ml:apply><ml:derivative /><ml:lambda>…<ml:degree>`. The
lambda's single bound variable is the one differentiated against, and `<ml:degree>` holds the order —
an empty `<ml:placeholder />` there means first order, not "no derivative". Parsed to `ir.Derivative`
and emitted as `derivative(<lambda>, <var>, <degree>)`; the variable is in scope because the operator
only ever appears inside a definition of a function of it (`sd_p(x) := d²/dx² fitp(x)`). The runtime
helper is Ridders' method — a central difference at a shrinking step, Richardson-extrapolated — and it
divides `x`'s unit off the answer once per order.

**Σ over a range variable.** A `<ml:summation>` that *names* a bound variable but leaves both bounds
as empty placeholders is Mathcad's **range sum**: the index is a range variable already defined on the
sheet and the operator runs over every value in it. That is a third reading of the same element — the
existing two being the bounded sum (`ir.Summation`) and the bare `Σ` over a vector, which has *no*
bound variable (`ir.VectorSum`). Emitted as `range_sum(<index>, <lambda>)`, reading its limits off the
range itself so a step other than 1 sums the terms Mathcad shows. Without this the bounds emitted as
`None  # placeholder` and the trailing comment swallowed the closing parenthesis, so the module would
not even parse — the same hazard `print_lines` exists to avoid.

**A displayed equation whose names are already numbers.** A bare `<ml:apply><ml:equal />` region is
normally a symbolic step: its identifiers carry no `labels` attribute, and the converter declares them
as SymPy `Symbol`s. This sheet writes the linear-prediction recurrence `X[k] = c[0]·X[k-3] + …` out
beside the very data it applies to, so `X`, `c` and `k` all *do* have numeric values. Mathcad computes
nothing for the region either way, but evaluating it in Python indexes a real 7-element array with a
real range variable and raises. `ir.SymbolicEquation.display_only` marks the case (every free name
already defined above) and both backends emit it as a `# shown, not computed:` comment.

**The outlier family — `Grubbs`, `GrubbsClassic`, `ThreeSigma`, `trim`.** These sit beside the
least-squares spline in the same worksheet, but they are ordinary documented functions and nothing
about them had to be reverse-engineered. PTC publishes the returned matrices in full for one
195-point heatflow data set, across three example pages ("Outlier Detection", "Grubbs' Method for
Detecting Outliers", "Outlier Removal"), and those published numbers settle every choice:

* **`a` is a confidence, not a significance.** PTC's own example writes `Grubbs(y, 1 - α)`, so the
  significance level used inside is `1 - a`. The reference sheet's `GrubbsClassic(y, 0.55)` therefore
  tests at `α = 0.45`.
* **The test statistic uses the *population* standard deviation** — Mathcad's lowercase `stdev`,
  divide-by-n. This is pinned, not assumed: `Grubbs(y, 0.85)` publishes three rows (indices 3, 19,
  188), and the *sample* deviation puts row 188 at 3.3133 against a bound of 3.3191 and returns two.
* **The critical value** is the standard Grubbs bound, which the "Grubbs' Method" page spells out as a
  worksheet formula beside the call: `t := qt(α/(2N), N-2)` and
  `crit := (N-1)/√N · √(t²/(N-2+t²))`.
* **Each row is `(index, statistic, crit - statistic)`**, indices ascending. The third column is
  *negative* for a point that failed the test — the published `-0.207 / -0.312 / -0.003` at `a = 0.85`
  and `-0.102 / -0.207` at `a = 0.9` are reproduced exactly. `GrubbsClassic` returns one such row for
  the largest statistic whether or not it clears the bound (`[19 3.631 -0.389]` at `a = 0.8`);
  `ThreeSigma` returns two columns only, and falls back to the closest point when nothing exceeds 3.

`interpolation_prediction.mcdx` reaches exactly one arm of this — `matelem(GrubbsClassic(y, 0.55), 0, 0)`,
cached as `150`, which is the index of the largest statistic and would come out the same under either
deviation. **`references/grubbs.mcdx`** is the purpose-built sheet for the rest: 20 values with one
outlier, and 14 echoes covering every branch. It settles two readings no published page shows, and
the natural guess was wrong on both.

* **No function of this family ever returns an empty table.** `Grubbs(v, 0.999)`, where nothing
  clears the bound, caches as the one most extreme point with a **positive** third column — the same
  row `GrubbsClassic` gives. `ThreeSigma` documents that fall back; `Grubbs` shares it silently.
* **A matrix argument is one flat bag of values, and the position comes back nested.**
  `Grubbs(augment(x, v), 0.95)` on a 20×2 caches as a 1×3 whose first element is a nested 2×1 column
  `(0 0)ᵀ`, with statistic 2.52141319039385 — that is the extreme of all **40** elements measured
  against their common mean and deviation, not a per-column test. The nested column is what the
  documentation's "nested pairs of indices" means, and `A[0,0]` echoes it as a 2×1 matrix.

The pair is **`(row, col)`**, settled by the sheet's last two regions: `augment(x, v)` puts the
extreme at (0, 0), which reads the same either way round, so `Grubbs(augment(v, x), 0.95)` moves the
same point to row 0 of column 1 and caches `(0 1)ᵀ`. One detail is still **unconfirmed** — what order
*several* matrix candidates come back in. We emit column-major, which is Mathcad's own storage order
and matches the ascending order of the vector case.

The sheet also confirms that Prime **accepts a unit**: `GrubbsClassic(v·m, 0.95)` caches as plain
reals identical to the unitless call, since the statistic divides the unit out and an index never had
one. And it pins the critical value to full precision — the published pages print three decimals,
while the cached `-0.4049316586941907` confirms the `qt(α/(2N), N-2)` bound to fourteen digits.

`trim(v, vindex)` drops the rows `vindex` names, keeping the shape and unit of `v`; the indices are
relative to `ORIGIN`, i.e. 0-based here. The sheet trims both a vector and a two-column matrix.

**`Spline2` / `Binterp` / `DWS`, and `GrubbsClassic` / `trim`** are genuine Prime built-ins — the
worksheet has no include region and no add-in reference, and Prime labels them `FUNCTION` exactly like
`cspline`. `Spline2(x, y, n[, w][, level | knots])` returns one packed vector, and the sheet caches the
whole 79-element example (`b`, region 8), which pins the layout exactly:

| Slice | Meaning | Example |
|-------|---------|---------|
| `b[0]` | spline **order** (`n + 1`) | `4` |
| `b[1]` | knot **interval** count `m` | `34` |
| `b[2 : 3+m]` | the `m+1` knots, first = `min(x)`, last = `max(x)` | 309.4 … 1999.7 |
| `b[3+m : 6+2m]` | the `m+3` B-spline coefficients | 3726.71 … 749.31 |
| `b[6+2m:]` | four trailing statistics: `0`, the **Durbin-Watson statistic**, 0.99934, 0.44954 | — |

`i := 0 .. b[1]` / `knots[i] := b[i+2]` in the sheet confirms the knot slice, and `DWS(b)` echoing
`b[last(b) - 2]` confirms where the statistic sits.

**Everything except the knot placement is solved**, and exactly. The sheet's two `Spline2` calls
that pass an explicit knot vector (`SplineW`, `SplineNW`) are reproduced to the last bit:

* `Binterp(u, b)` is an ordinary **clamped B-spline evaluation** — knot vector
  `[k0]*(n+1) + interior + [ke]*(n+1)`, i.e. `scipy.interpolate.BSpline(t, b[3+m:6+2m], n)`. It returns
  **four** columns: the value and the first three derivatives. Matches the cached trace to 1.5e-11 on
  values near 6e4.
* Given knots, the coefficients are a **least-squares fit**, and `w` is a vector of **standard
  deviations**: the weight is `1/w²`. Weighting by `w`, `1/w`, `w²` or `√w` all miss.
* **Data points outside the knot range are dropped.** This is the detail that hides the rest: the
  sheet's `Knots := range` stops at 1982.96 while `x` reaches 1999.7, so five points fall outside.
  Keeping them moves every later check off by ~0.2% and makes the fit look wrong. Dropping them makes
  `DWS(SplineNW)` come out at 2.3915925499477533 against a cached 2.3915925499477493, and the whole
  `SplineW` trace match to 2.4e-10 out of 6e4.
* `DWS` is the plain **Durbin-Watson statistic** of the residuals — *weighted* residuals `r/w` when a
  `w` was given. Weighted: 2.32173216795681 against a cached 2.3217321679568084.
* The four trailing numbers are `[residual standard error, 0, DWS, ?, ?]`. The first is
  `sqrt(SSE/(N-p))` with `p` the coefficient count: 749.3112471272 against a cached 749.3112471272.
  The last two (0.999340554, 0.449535631) are still unidentified — neither is R² (0.99787) nor
  adjusted R² (0.99772).
* Argument reading, from the six cached calls: a **scalar** 4th argument is `level`; a **vector** 4th
  argument is the knots; with **five** arguments the 4th is `w` and the 5th is the knots. Passing an
  unsorted vector as the 4th (the sheet's `Spline2(x, y, n, w)`) is evidently rejected as a knot
  vector and the call falls back to the default adaptive fit — which is why
  `DWS(Spline2(x, y, n, w))` and `DWS(Spline2(x, y, n))` agree to all 17 digits.

**Only the knot *move* is unsolved** -- the step the loop below calls `<move them>`. The evidence
gathered on it is in the loop section further down.

**`Spline2` is therefore gated per call, not per name.** It is *not* in `mapping.UNIMPLEMENTED`;
`regions._spline2_needs_its_own_knots` decides one call at a time, because with an explicit knot
vector the function is exact. A call converts when the knot vector is **provable**:

* five arguments -- the last is positionally the knot slot, so a vector there settles it;
* a literal ascending vector (`k5 := (0 2 4 6 8 10)ᵀ`), folded straight out of the IR;
* a name the same sheet already passed in that fifth slot. `interpolation_prediction` writes
  `Spline2(x, y, n, w, Knots)` and then `Spline2(x, y, n, Knots)`, and the second converts on the
  strength of the first, without anyone having to evaluate the formula `Knots` was built from.

Everything else is suppressed: a **scalar** in the knot slot is `level` (whether written as `0.5` or
reached through a name), an **unsorted** literal is weights (the catalogue sheet's `w` is a column of
a measurement table), and anything **computed** cannot be told apart before the sheet runs. Emitting
one of those would put a `NotImplementedError` at import time, which is the single outcome the
suppression exists to prevent. `Binterp` and `DWS` need no gate: both only read a packed vector, so
they follow whatever their `Spline2` did, and the ordinary taint carries a suppressed one downstream.
Nothing is blocked by name any more — `GrubbsClassic` and `trim` are implemented (next section).
`references/spline2B.mcdx` converts with **no** TODO at all as a result.

Tested against the cached knots and rejected: uniform spacing; the data's quantiles (5 to 48 points
per interval, with the *fewest* points where the knots are *densest*); equidistributing arc length,
`Σ|Δy|`, `Σy·Δx`, `Σw`, `Σ1/w`, `√y`, `log x`; FITPACK (`splrep`) at the matching knot count, whose
first interior knot lands at 535 where Mathcad's is at 445.9; equal **SSE**, equal `Σ|residual|`,
equal residual sign-run count and equal local `Σ(Δresidual)²` per interval (spreads 0.45 to 0.78,
where "equal" means 0); and a 720-point scan of de Boor `NEWNOT` variants — the `|D⁴f|` estimate taken
from the jump of `D³f` over the average interval, over the two-interval span, raw, and as `|D³f|`
itself; exponents 1/5, 1/4, 1/3, 1/2; one to three redistribution passes per step; and knot counts
grown by 1, by 2, or in one jump from a 1-, 2-, 3-, 4- or 34-interval start. The best of those lands
35 units from Mathcad's knots at worst and 12.6 on average, against interval widths of about 25 — the
right neighbourhood, the wrong rule.

**The outer loop, on the other hand, is pinned** -- by `references/spline2.mcdx`, 13 points calling
`Spline2(x, y, 3)` at the default `level`, at 0.5 and at 0.001. All three echo the *identical* vector,
with knots `[0, 6, 12]`:

```
knots = [min(x), max(x)]                  # one interval
loop:
    fit least squares on knots
    d = Durbin-Watson statistic of the residuals
    if P(DW < d) > level:  stop
    m += 1
    knots = redistribute over m intervals   # the one unsolved step
```

Three things fall out of that sheet. **The search starts at one interval**: with a single interval the
fit is one cubic, so `|D³f|` is constant and any curvature-based redistribution returns uniform knots
-- which is exactly why the interior knot lands on 6.0 on visibly asymmetric data. **The stopping rule
is a Durbin-Watson p-value against `level`**: one interval gives `DW = 1.063`, `P(DW < d) = 0.00069`,
below every level the sheet tries, and two intervals give 0.79, above all of them -- so all three
calls stop in the same place, which is what the identical vectors prove. And **the rule reproduces the
big sheet's count**: run the same loop over the 536-row data and the first `m` with `P(DW < d) > 0.05`
is **34**, the cached number exactly (at `level = 0.001` it gives 30 against a cached 32, the gap
being the approximate redistribution).

The p-value is a Beta approximation on `[0, 4]` matched to the exact mean and variance of the
statistic under the null (`P = tr(MA)`, `Q = tr(MAMA)`, `M` the residual-maker of the B-spline design,
`A` the usual difference form with 1 in both corners). It lands within 3% of the number Mathcad stores
in the trailer -- 0.4561 against 0.4495 on the big sheet, 0.7925 against 0.7690 on the small one -- so
the fifth trailing statistic **is** this p-value, and only its exact convention is still open. The
exact (Imhof) distribution is no closer, so the difference is a modelling detail, not a quadrature one.

**The starting knot set is solved**, by `references/spline2A.mcdx` -- 45 points on `x` whose spacing
varies by a factor of four, with two kinks placed in the sparse half. Its three calls stop at 6, 4 and
3 intervals, and two of them return knots that are **uniform in the data index**, exactly:

```
knots[j] = interp(j * (len(x) - 1) / m,  0..len(x)-1,  x)      # equal points per interval
```

Zero difference on both -- and the interpolation between two data points is where the non-round
values come from (`0.834022` is `x[7] + (1/3)(x[8] - x[7])`). So Mathcad's first try at every interval
count puts an **equal number of data points** in each interval, not an equal width. The 13-point
sheet's `[0, 6, 12]` is the same rule on uniformly spaced data.

That makes the loop two-phase:

```
for m = 1, 2, 3, ...:
    knots = uniform in data index
    fit;  if p > level:  stop            # b and b3 stop here
    knots = <redistribute>               # the one step still unsolved
    fit;  if p > level:  stop            # b2 stops here
```

`spline2A`'s middle call is the one cached example of the second phase on small data: at four
intervals it drags the interior knots from `1.375 / 3.5 / 6.375` out to `3.538 / 6.926 / 8.908`,
towards the kinks. The three calls are mutually consistent with `stop when p > level` and a **default
`level` between 0.73 and 0.93** -- `level = 0.5` accepts the redistributed four-interval set at
p = 0.731 while the default rejects it and runs on to the uniform six-interval set at p = 0.930.
The big sheet's 34-interval answer and the 536-row `p = 0.9993` sit on the same rule.

Against that one cached example, a single redistribution step from the uniform-in-index fit was
scanned over `|D¹f|`, `|D²f|`, `|D³f|` and arc length, exponents 1/5 to 1, integrated in `x` and summed
over data points, plus residual-weighted variants, plus the equidistribution fixed point, plus a
Nelder-Mead free-knot search on both the sum of squares and the statistic itself. The best lands 0.58
out of an interval width of about 2. The target is **not** the least-squares optimum (its SSE is 27.18
against an attainable 22.06), so the second phase is neither a plain optimiser nor any plain
equidistribution tried so far.

**The last two trailing statistics are solved**, by `references/spline2B.mcdx` -- 31 points fitted on
five **explicit** knot vectors and at two degrees, so no placement rule is involved anywhere and every
echo is a clean (design, statistic, p-value) triple. They are the classical **bounds** of the
Durbin-Watson test. The statistic's exact null distribution depends on the design matrix, so Durbin
and Watson published two design-free bounds instead, both weighted sums of the eigenvalues of the
difference operator:

```
nu[j] = 2*(1 - cos(pi*j/n))            j = 1 .. n-1
upper = Beta_cdf(d/4)   fitted to the mean and variance of  nu[0 : n-p]
lower = Beta_cdf(d/4)   fitted to the mean and variance of  nu[p-1 : n-1]
```

Each bound is approximated by a Beta distribution on `[0, 4]` matched to its own mean and variance --
Durbin and Watson's own approximation, the one their published tables were built from. That
reproduces **both** numbers across all eleven cached fits to 3e-9, which is the Beta CDF's own
precision. The upper bound comes first, and it is the one the fit is judged by: it is the probability
of no positive residual autocorrelation, rising towards 1 as the spline stops leaving structure
behind. `Spline2` now returns the whole packed vector, with nothing left as `nan`.

That sheet also pins a hard limit: `Spline2(x, y, 4, …)` is the one region **Mathcad itself** will not
compute, returning an `order_too_big` engine error whose argument is 3. The family is capped at cubic.

**The loop is solved except for one step.** `references/spline2C.mcdx` fits the same 45 points at
eight values of `level`, and the interval counts come back sharply **non**-monotone -- 6, 6, 15, 15,
29, 5, 5, 7 -- which is what turned the loop from a guess into a rule:

```
for m = 1, 2, 3, ...:
    knots = uniform in data index
    fit;  if lower > level:  stop            # spline2A's level = 0.001 stops here
    knots = <move them>                      # THE ONE UNSOLVED STEP
    fit;  if lower > level:  stop            # every other cached adaptive fit stops here
```

`lower` is the **lower** Durbin-Watson bound, and the **default `level` is 0.05**. The moved sets
reach lower bounds of 0.034 (5 intervals), 0.203 (6), 0.065 (7), 0.461 (15) and 0.520 (29), and read
against the levels those explain every rung from 0.05 to 0.5: 0.05, 0.1 and 0.2 stop at 6 because
0.203 is the first value above them; 0.3 and 0.4 pass 6 and take 15; 0.5 needs 29. The move is a
separate step from adding a knot -- `level = 0.001` and the default both stop at **six** intervals,
one on the uniform set and one on the moved one. And the moved set is a function of the data and the
count alone: two levels that stop at the same count return byte-identical vectors.

The three highest levels (0.6, 0.7, 0.8) stop at 5, 5 and 7 intervals -- *fewer* than 0.5's 29 -- with
lower bounds far below their levels but **upper** bounds (0.768, 0.768, 0.972) that clear. So when the
loop cannot satisfy a level it falls back to the weaker half of the bounds test and to a count it had
already passed. The fallback is not reproduced.

**The move itself is still unsolved, and the search space is now well covered.** With five cached
moved sets on one dataset (5, 6, 7, 15 and 29 intervals) plus the 536-row sheet's 34, these were
scanned and rejected: equidistributing `|D¹f|`, `|D²f|` or `|D³f|` to any exponent from 0.05 to 1.5,
integrated in `x` or summed over data points, one to three passes, seeded from the uniform-in-index
fit at the same count *or* chained from the previous cached moved set (best mean error 0.6 of an
interval width, and the best exponent tends to 0, meaning the density is contributing nothing);
equidistributing the residuals as `r²`, `|r|`, `Σ(Δr)²`, `|r_i·r_{i+1}|` and `1 + r²`; uniform in `x`
and every blend of uniform-in-x with uniform-in-index; FITPACK's `splrep` at matching counts (its
knots sit *on* data points, Mathcad's do not); a free-knot Nelder-Mead search on both the sum of
squares and the statistic (the cached set is not the least-squares optimum -- 27.18 against an
attainable 22.06); and a fixed warp `W(j/m)` of the index, which the five sets do not collapse onto.

**The loop model above is wrong on one point, and three purpose-built sheets say how.**
`spline2D` / `spline2E` / `spline2F` fit one curve -- `f = exp(exp(x/2))`, 60 points, `x` uniform on
`[0, 10]`, no noise -- at 40 values of `level`. They are *experiments*, not fixtures: they were built
to expose the move, they sit in the git-ignored `references/_experiments/` so no test globs them,
and the numbers below are the whole result -- the sheets can be deleted without losing anything. Three things came out of them.

*The move repeats at a fixed interval count.* The pseudo-code above allows one move per count. In
fact several levels stop at the **same** count with **different** knots, so the loop moves, tests,
moves again. Four 3-interval sets and four 4-interval sets came back, which read as two chains:

```
m=3   3.3333 6.6667 -> 4.0223 7.2806 -> 4.8233 7.8291 -> 5.6032 8.3291
m=4   3.2393 6.1336 8.1752 -> 4.3195 7.2257 8.7123 -> 5.4260 8.0475 9.1324 -> 6.4652 8.7034 9.4549
```

*The move reads only the curve.* `spline2E` fits `f` and its exact mirror `g = exp(exp((10-x)/2))` at
twelve levels each. At every level `g`'s knots are `10 - reverse(f's knots)` to all cached digits. So
the rule carries no direction bias and no dependence on the data index -- which rules out anything
that walks the points in order, and anything seeded from a one-sided sweep.

*The level enters only as a stopping decision.* Levels 0.1, 0.2 and 0.3 return byte-identical knots,
as do 0.96 through 0.985. The level never reaches the placement arithmetic.

The search order is **not** "first configuration whose `lower` clears the level". Sorting all thirteen
cached configurations by `lower` gives an interval count of 3, 4, 3, 4, 4, 4, 5, 6, 8, 9 -- it drops
back to 3 -- and at the top end `lower` itself is non-monotone (8 intervals cache 0.998638, 9 cache
0.998135, and level 0.99 returns the 9). Ordering the same configurations by their **Durbin-Watson
statistic** and taking the first with `lower > level` reproduces 20 of the 24 rungs, including the
drop back to 3 intervals; the four it misses are all above `level = 0.8`, where two different
5-interval sets are reachable and which one comes back depends on the level. So the path through the
search is itself level-dependent, and a plain ordered scan will not model it.

Against those six move steps the following were tried and rejected, on top of everything in the
previous paragraph: equidistributing `|D³f|`, `|D³f|/h`, the **jump** of `D³f` across each knot (de
Boor's `NEWNOT`), `|D²f|` at midpoints, the RMS of `D²f` over each interval, and the mean residual --
each to 600 exponents from 0.02 to 3. The best fit is a de Boor jump equidistribution at an exponent
near 1/3, which lands **0.04 to 0.18** in `x` against interval widths of 2.5 -- seven times closer
than anything the noisy sheets gave, and still not a rule. The exponent that fits best is not shared:
the 3-interval steps want 0.46, the 4-interval steps want 0.34.

Two structural facts to build on, if this is picked up again. The sum of squares falls monotonically
along both chains (to 0.66 of its start over the 3-interval chain, 0.12 over the 4-interval one), so
the move is a descent step. But it is not gradient descent -- the cosine between the step and the
negative gradient runs 0.78 down to 0.33 -- and it is not converging on the free-knot optimum, which
for this curve is degenerate and sits far to the right of every cached set.

A practical note for building the next sheet: only **noise-free** data exercises the move at all. In
`spline2D` the three signals carrying pseudo-noise all ran straight to 30 intervals and were accepted
on the **uniform** set, with no move anywhere. The noise-free curve was the one that moved.

**One more side finding, now closed.** An earlier save of `spline2A` had cached a `y` that was our own
`rnorm` stream at offset 45 -- exactly one whole `rnorm(45, …)` call further on, because Prime had
drawn the vector twice across the saves. The sheet was re-saved and the stream now starts where it
should, so the fixture reproduces `y` element for element. Worth remembering as a diagnosis: a
worksheet whose random data will not reproduce is far more likely to have been recalculated than to
have caught a generator bug, and the offset says which.

**The algorithms, identified from the cache** (all exact, 0.0 error unless noted):

| Function | Method | How the cache identified it |
|----------|--------|------------------------------|
| `polyint` | Numerical Recipes `polint` (Neville) | `[value, error]`, error being the last correction added — the second cached element |
| `polycoeff` | NR `polcoe` | Lowest power first; agrees to 1e-11, the fit being ill-conditioned |
| `polyiter` | Rising order over the **first** k+1 points, stopping when two successive interpolations differ by < ε | Three cached calls: order 3 when allowed 5, order 2 and *not* converged when capped there — while `polyint`'s error estimate for that query is exactly 0 |
| `rationalint` | NR `ratint` (Bulirsch-Stoer) | Only plotted on the sheet, never echoed |
| `Thielecoeff` | Reciprocal differences, dividing by **1e-65** where the denominator is 0 | The degenerate example caches `1e65`, `-1e-65`, `-1e65`, `-4.2764235361e-50`; that last one is floating-point noise from the substitution and comes out to the last digit |
| `Thiele` | The continued fraction those coefficients define | The sheet writes `Q(a)` out by hand next to it |
| `predict` | Burg's maximum entropy (NR `memcof` + `predic`), each prediction fed back as data | The sheet writes the recurrence out term by term, with the coefficients cached: `memcof`'s `d[0]` weights the most recent sample, so Mathcad's display order is this vector reversed |
| `lspline` / `pspline` / `cspline` | Natural / parabolic-end / not-a-knot cubic spline | The cached second derivatives of the fits at the end knots: 0 for `lspline`, and `-0.0114488208` for `pspline` — which is exactly the y'' our tridiagonal solve puts at *both* of the first two knots, the parabolic condition |

Two cache readings worth keeping:

* **The whole returned vector carries the ordinates' unit.** `polyint(X, Y, U)` with `Y` in seconds
  caches as a `<unitedValue>` wrapping the 2×1 matrix — and so does `polyiter`, whose converged flag
  and order therefore arrive in seconds as well. Mathcad tags the result, not the elements.
* **`interp` extrapolates along the end piece.** `sd_p(vx[0])` — a second derivative taken *at* the
  first knot, so its finite difference reaches outside the data — caches the exact y'' of the end
  polynomial, which only happens if Mathcad continues that polynomial rather than clamping.
