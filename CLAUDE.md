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
- Mathcad's `·` is scalar, matrix *and* dot product; [shapes.py](mcad2py/shapes.py) decides which by
  inferring shapes across the whole sheet, and only rewrites to `matmul` when **both** operands are
  provably arrays (never under a vectorize arrow). Give a new array-returning builtin an entry in its
  `_CALL_KINDS` table.

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
[tests/test_rc_torsion.py](tests/test_rc_torsion.py) covers `references/RC_torsion.mcdx`
(torsion): the **range-indexed vector backbone** — it executes the whole sheet and checks the
`index_build` vectors (`T_Ed`/`A_sl`/`n_sl`/`s_t`/`k`/`accept`) against Mathcad's cached `1×1`
matrices, that `T_Ed` is 0-based and zero-filled (`[0, 400]`), and that the index variable `i` is an
integer array. Plus the supporting leaf features asserted on the generated source: the stepless range
`i := 1 .. n` (→ `arange(1, n, 1)`), `ceil`/`floor`/`round`, and an inline
`if(cond, "ok", "not ok!")` rendered as a ternary with string literals.
[tests/test_rc_interface.py](tests/test_rc_interface.py) covers
`references/RC_interface.mcdx` (joint shear capacity): the native `<ml:ComboBoxControl>`
row-selector — single- and multi-column picks (`[f_ck; f_ctk]`, `c`/`μ`) and the empty-values
name-as-string case (`crack := "No"`) — plus a `<ml:program>`-as-value becoming an inline ternary
(with `alsoif`/`and`) and a boolean `=` emitting `==` (not a SymPy `Eq`). Executes the whole sheet and
matches the cache for `f_yd`/`τ_Rd`/`τ_Sd`/`Accept`; `ν_v` is asserted at the live-`f_ck=40` value
`0.5` (the cache's `0.525` is a documented stale leftover, see the `ComboBoxControl` schema note).
[tests/test_3d_plots.py](tests/test_3d_plots.py) covers `references/3d_plots.mcdx`: the four ways a
`<contourPlot>`/`<plot3D>` equation can resolve to a grid — a function over two ranges (`f(x0, y0)`,
including the *composed* form from `biaxial_bending.mcdx`'s `sigma(epsilon(x0*mm, y0*mm))`, both
wrapped into `mesh_grid(lambda x, y: …, x, y)`), an `N×3` matrix as an `(x,y,z)` point list (scatter),
`CreateMesh(...)`, and an `N×M` matrix as an index-coordinate z-grid — executes the whole sheet, checks
`resolve_plot_grid`'s dispatch (`"grid"` vs `"scatter"`) and `matrix()`'s column-major reshape (and that
a leading `<ml:display>` metadata child isn't mistaken for a data element) against the sheet's own
values, and renders all 8 figures (matplotlib `Agg`, 2D + `mplot3d`). Plus a regression test that an
expression over only *one* range (not two) correctly stays an `UnsupportedRegion` rather than being
mishandled as a grid.
[tests/test_solve_block_and_double_integral.py](tests/test_solve_block_and_double_integral.py) covers
two `references/biaxial_bending.mcdx`-motivated runtime fixes *without* executing that sheet's slow,
not-reliably-convergent solve block: `double_integral` (what a nested nested-bounds-independent
`Integral` now emits instead of manually nested `integral()` calls) is checked against the equivalent
nested-`integral()` result and confirmed to fire in the sheet's generated source; and `solve_block`'s
fix for `fsolve` reporting `ier=1` ("converged") while parked on a point whose residual is nowhere near
zero (seen when the whole integration domain sits inside one flat branch of a piecewise model) is
reproduced with a fast synthetic residual, a mocked first `fsolve` call forcing the false-positive, and
a genuinely-stuck case asserting the honest "couldn't confirm convergence" warning (not a silently wrong
answer).
[tests/test_rc_col.py](tests/test_rc_col.py) covers `references/RC_col.mcdx` (a large biaxial column check) —
the **imperative-program engine** and its supporting features. It executes the whole sheet (all 7
multi-line programs, the `solve_strain(N,Mx,My) := find(e,kx,ky)` function-defining solve block, and the
12-loadcase `try`/`for`/`if`/`return` loop that builds vectors with `vec_set`) and matches the cached
`result.xml`: the coordinate builder's 12 rebar positions, the loadcase governing utilisations/indices
(`[UR_c_max=0.18899, i_c=7, UR_s_max=0.012134, i_s=0]`, `ERR=0`), and `solve_strain`'s cached strain
triple. Plus source assertions for the emitted constructs (`def _X_s_Y_s_n()` + `tuple(...)` destructure,
`for i in arange`, `vec_set`, `Neutral(e,kx,ky)`, `try`/`except`, 2-D `vec_set(Ans, (j, 0), …)`,
`def solve_strain(N, Mx, My)`), the data table (`Fz = col(...) * ureg.kN`; string columns clean), the
`augment`/`matmul`/`matcol`/`total` leaves, the TextBox status controls
(`print('<expr>', <expr>, '<message>')`), and that `A_smin = max(vector, scalar)` reduces to a **scalar**
(Mathcad `max` flattens). The **parametric plots** (section outline / rebar scatter / neutral-axis line,
both axes data vectors) are asserted too: the emitted direct-axis form (`plot_axis(matcol(Contour, 0),
ureg.mm)`, no `sample(lambda …)`) and a rendered check that the outline is a ±650 mm rectangle and the 12
rebars sit at ±583 mm (i.e. the `m`→`mm` override reduced). The numeric tests still strip plot blocks in
the exec purely for speed.
[tests/test_trig_hyperbolic.py](tests/test_trig_hyperbolic.py) covers `references/trig.mcdx` and
`references/hyperbolic.mcdx` — two **catalogue sheets** (one angle, then every member of the family
applied to it), so between them they pin the whole trig + hyperbolic group. Both run end-to-end and
every echoed region is matched to the cached `result.xml` by parsing the printed output in region
order. Plus: that the forward trig reads the angle *unit* (`sin(34 deg)` = 0.559) while the hyperbolic
and inverse functions reduce their argument to a pure number (`sinh(103.2 deg)` = `sinh(1.80118)` —
Mathcad angles are dimensionless); that inverse results are bare radians and `disp` **rescales** them
for a `deg` override (rather than dividing, which would read `0.593 1/degree`); that `disp` with no
override reduces `sin(θ)/θ` from `1/degree` to `0.9423` and is emitted for divisions *only*; the four
conventions that differ from Python/NumPy (`atan2`'s reversed arg order, `angle`'s `[0, 2π)` wrap,
`sinc` unnormalised vs `np.sinc`, and `acot`'s `(0, π)` branch — pinned by the sheet's cached
`acot(-2) = 2.67794`, the one argument sign where that convention differs from `atan(1/x)`, alongside
`atan(-6) = -1.40565` for the ordinary signed branch); and round-trip identities for all twelve
forward/inverse pairs.
[tests/test_matrices.py](tests/test_matrices.py) covers `references/matrices.mcdx` — a third **catalogue
sheet**, this one walking the whole **vector & matrix** family (shape, linear algebra, norms/conditions,
eigen/singular values, ordering, predicates) plus three worked examples (down-sampling, left/right
eigenvectors, PCA). It runs end-to-end and matches all 111 echoes against the cache — captured as
*objects* via a `print` shim in the exec namespace, since a sheet of matrices prints multi-line arrays
no line-based parse could reassemble. Beyond "the name resolves" it pins: **which `·` is a matrix
product** (`M·A`/`B·C`/`L_0ᵀ·A` → `matmul`, while `2·identity(4)`, `λ·R` and `M·kg` stay `*` — this needs
the sheet-wide shape pass, since `M` and `A` are plain names at the point of use); the **two-subscript
forms** (`matelem` reads, including on the 1-D arrays we store row/column vectors as; `index_build_2d`
writes over both ranges' outer product; the column-major `[a b; c d] := M` destructure); the two
bar operators (`|M|` = determinant vs. `|a_0|` = `abs`), row extraction and `×`; and `matrix(m, n, f)`
sharing its name with the literal builder. Eigen results are checked the only way they can be —
values as a **set** (LAPACK's order is Mathcad's for the symmetric cases, not for the general 6×6s or
`genvals`) and vectors by their **defining equation** (signs are arbitrary in any implementation), with
the PCA's cached principal components confirming the invariant end result.
[tests/test_areas.py](tests/test_areas.py) covers `references/collapsable-area.mcdx`: a **collapsible
area** (`<region><Area><regions>…`) is flattened away, so `y := 2·x` defined *inside* one converts and
runs like any other region and the `y + x =` below it matches the cache (`3`). Plus, on synthetic
worksheet XML, the two properties the fixture is too simple to show: areas **nest**, and their
children's `top`/`left` are **area-relative**, so each area is sorted within itself and spliced in at
its own position rather than sorted against the sheet.
[tests/test_implicit_plot_domain.py](tests/test_implicit_plot_domain.py) covers
`references/plotting-wo-var.mcdx`: an `<xyPlot>` of an **undefined** variable, for which Mathcad
invents the domain -10..10. Both traces are compared point-for-point against the cached
`<ml:Trace2dResult>` vectors, which pin the interval, the 499-point step, and that the interval
belongs to the *free variable* rather than the axis — the second trace plots `x/2` against `cos(x)`,
so it spans -5..5 while its `cos` still sees the full -10..10. Plus: that the invented variable stays
in a private `_domain_x` and doesn't leak into the module namespace, and — on synthetic worksheet XML
— the cases where a domain must *not* be invented (a parametric plot of two defined vectors, two free
names, an already-defined scalar or range) versus the ones where it must (a definition sitting *below*
the plot, out of scope; `π` in the expression, which is an identifier in the IR and would otherwise
count as a second free name). Plus that -10..10 is only the *default*: author-set x-axis limits
(`<xyDomain>`'s start/end values, as opposed to the auto-scaled `start`/`end` attributes) become the
sampled interval instead — pinned end-to-end by `incomplete_ifs.mcdx`'s -7..1.

[tests/test_incomplete_ifs.py](tests/test_incomplete_ifs.py) covers `references/incomplete_ifs.mcdx`:
a **blank line inside a program** (a bare `<ml:placeholder/>` body child) is ignored rather than parsed
as a statement — it used to emit `return None` mid-function and make every branch below it unreachable,
so the sheet's `σ_cI` piecewise curve returned `None` for its second branch instead of the cached
-30 MPa. It runs the sheet and matches the cache, asserts all six branches below the blank survive, and
— on synthetic program XML — pins the placements the fixture doesn't show (leading/trailing/inside a
`then`, where a trailing blank must *not* flip a one-line ternary into a `def`). Also documents the
divergence the sheet is named for: for an argument matching no branch, Mathcad caches an `engineError`
("This program has no return value") where we return `None`. Its **plot** covers what that means for a
trace: drawn over a domain running past the last branch, Mathcad caches a literal `NaN` per undefined
point and draws a gap, so `sample` fills `None` with a unit-carrying NaN (feeding `None` into
`plot_axis` used to raise). The trace is checked point-for-point against the cache including the NaN
mask, and the plot pins the other half of the implicit-domain rule — author-set x-axis limits (-7..1)
replace Mathcad's default -10..10.

[tests/test_mixed_plot_traces.py](tests/test_mixed_plot_traces.py) covers
`references/mixed_plot_traces.mcdx`: one plot carrying **both** a parametric trace (two data vectors)
and a function trace (`sin(t)` over a plotting range). Each kind worked alone, but mixed they didn't —
the plot's single domain was applied to every trace, so the parametric one became
`sample(lambda t: v, t)` and `plot_axis` raised on the nested array. Sampling is now decided per axis
expression, on whether it references the domain. The test asserts both traces against Mathcad's cached
`TraceType="Vector"` (3 points) and `"Range"` (101) — the differing lengths being exactly what one
shared domain can't express — plus `static_axis`'s vector/scalar split (a scalar is a *reference line*
and still spans the domain) and, on synthetic XML, that a purely parametric and a purely function plot
are both emitted unchanged.

[tests/test_auto_labels.py](tests/test_auto_labels.py) covers `labels="*"` — the **auto-labelled**
identifiers a worksheet Prime converted from a legacy `.xmcd` is full of (Mathcad 15's schema didn't
record whether a name was a unit, so the converter leaves it uncommitted). Purely synthetic XML, no
fixture. It pins that `*` is read as a unit *only* in slots that are a unit by definition (a display
override, a plot axis unit), including inside a compound `kN·m`, and that the three things that must
not move don't: a numeric scale override still divides, an explicit `labels="VARIABLE"` in a unit slot
stays a variable, and an auto-labelled name *outside* such a slot stays a variable (a converted sheet
auto-labels its loop index `i` — a name-based rule would emit `ureg.i`).

[tests/test_implied_index0_unit.py](tests/test_implied_index0_unit.py) covers
`references/implied_index0_unit.mcdx`: a program vector whose loop runs `i := 1 .. 10`, so Mathcad
auto-grows `z` and **zero-fills the untouched index 0**. Its cache is an `11×1` matrix carrying one
unit (metre) including the gap — `0` is `0` in any unit — where we left the gap a bare `0`, so the
array never fused out of `dtype=object`. Two compounding faults, both runtime-side (the emitted source
was already right): the unfused array is *dimensionless* to Pint, so a later `z / m` read `1/meter`
and the sheet it came from died with a `DimensionalityError` regions downstream of the mistake; and
`stack` returned `n×1` rather than the 1-D form column vectors use here, so the single-subscript echo
`z[0] =` read a one-row slice (`[0.0] / millimeter`) instead of the cached `0`. Both echoes are matched
to the cache, plus direct tests of `_consolidate`'s absorb-zero-only rule (a **nonzero** plain entry
mixed with dimensioned ones — RC_col's `[1; −l/2; −w/2]` — must still block fusing, as must
incompatible units), `vec_set`'s gap in 1-D and 2-D, and that `stack` keeps 2-D when a block is
genuinely wider.

[tests/test_stack_augment_lookup.py](tests/test_stack_augment_lookup.py) covers
`references/stack_augment_lookup.mcdx`: **row vs. column vectors** and the **table-search family**.
We emitted any literal with a dimension of 1 as `col(...)` (1-D), so a `1×3` header literal came back
a *column* and `stack(("A" "B" "C"), s)` wrote the labels down column 0 instead of across row 0 — every
later `matelem` then read a label where a number belonged. The sheet's cache states the distinction
itself: `match` on the `3×1` `V` returns the bare index `2`, on the `1×3` `R` the *pair* `[0; 2]` —
index pairs are what a matrix has. So `cols == 1` is the column vector (1-D) and `1×N` a genuine 2-D
matrix; `transpose` moves between the two (Mathcad's usual way of typing a column vector is a
transposed row literal `(a b c)ᵀ`, which must come back 1-D — NumPy's 1-D transpose is the identity, so
this can't lean on it). `augment` also had to stop flattening its arguments, so a *matrix* block keeps
its columns. All 15 echoes are matched to the cache, plus the labelled-table shapes
(header row / header column / both), `transpose`'s round trip, and `augment`/`stack` on matrix and
scalar blocks. The searches all return a **vector** even for one hit (the cache holds `1×1` matrices,
not scalars), scan a matrix **column-major** (`match(3, s)` → `[1;1]` before `[0;2]`), raise when the
value is absent, and compare mixed string/number cells without raising. Region 0's cached `4×1` is a
documented **stale leftover** (a plain define with nothing to echo, so Mathcad never refreshed it).

[tests/test_trace_source.py](tests/test_trace_source.py) covers `--trace-source`: with the flag
off (the default), output is byte-identical to a plain conversion — the regression guard that this
feature can't silently change anyone's existing output. With it on, `references/collapsable-area.mcdx`
pins that `ir.Region.source` (an `ir.SourceRef`) matches each region's XML `region-id` regardless of
the flag (it's always populated), that `to_python`/`to_notebook` prefix each statement/cell with
`# mcdx region <id>`, and — using a fixture with Greek/subscripted top-level names
(`references/RC_col.mcdx`) — that a renamed target's original Mathcad display name is appended
(`"σ_c" -> sigma_c`) while a plain ASCII target adds nothing extra. Plus a CLI check that
`--trace-source` reaches the output. `references/io.mcdx` (two Input-tagged definitions, two
Output-tagged regions, one of which is also a renamed `σ` -> `sigma`) covers reading
`mathcad/integration.xml`'s Input/Output tags: the id->`(io_kind, io_alias)` map matches the raw
XML, the alias is emitted (`# mcdx region 0, input alias "x"`), an alias and a renamed-name
annotation combine on one line when both apply, and a sheet with no Input/Output tags (the common
case — `collapsable-area.mcdx`'s `integration.xml` is a bare `<regions/>`) emits no alias text at
all.

[tools/strip_mcdx_metadata.py](tools/strip_mcdx_metadata.py) removes the authoring metadata a
`.mcdx` carries in parts you never see in Prime (`docProps/core.xml`'s `creator`/`lastModifiedBy`,
`docProps/app.xml`'s `Company`, and the printed header/footer). It rewrites only those parts —
`worksheet.xml` and `result.xml` stay **byte-identical**, so no cached value or test expectation
moves. Run it on any new fixture before committing; `--check` is the same scan as a report and is
wired into CI so a later worksheet can't quietly reintroduce a name.

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
