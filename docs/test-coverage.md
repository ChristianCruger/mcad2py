# Test coverage — which fixture pins which feature

Per-test detail for the suite: what each `references/*.mcdx` fixture exercises, why it was added,
and the documented divergences from Mathcad it records. Referenced from [CLAUDE.md](../CLAUDE.md) —
read the entry for a test before changing it, and add one here when you add a fixture.

The house style is in CLAUDE.md's Testing section: convert the sheet, **execute** the generated
Python, and assert against Mathcad's cached `result.xml`.

[tests/test_convert.py](../tests/test_convert.py) converts `references/plain_concrete_cohesion.mcdx`,
**executes** the generated Python, and asserts values match Mathcad's cached `result.xml`
(~14 sig figs). When adding a sample, prefer this execute-and-compare-to-`result.xml` style.

[tests/test_symbolic.py](../tests/test_symbolic.py) does the same for `references/NM_to_CT.mcdx` and
additionally checks the emitted `solve(...)` against Mathcad's cached `symResult` via SymPy.

[tests/test_vectors.py](../tests/test_vectors.py) does the same for `references/Xsection_solver.mcdx`:
vectors/indexing vs cached matrices, the `σ_c` program's branches, element-wise `min`/`max` clamps,
the vectorized `F_s`, and `N_int`/`M_int` (concrete integral + steel summation) evaluated at the
cached solve point `e_1`/`k_1` against Mathcad's cached force/moment checks (rel_tol 1e-4 — `quad`
on the kinked integrand vs Mathcad's own quadrature at its 1e-3 solution differ ~1e-5), and the
`find` solve block recovering Mathcad's cached `e_1`/`k_1` via `fsolve`. The whole sheet now runs
end-to-end: the unit-bearing `z_plot` range and the neutral axis `x` are checked too, and both
`<xyPlot>` figures are rendered (matplotlib `Agg`) and their traces/labels asserted. Plus direct
unit tests of the `integral`/`summation` runtime helpers.

[tests/test_shrinkage.py](../tests/test_shrinkage.py) covers `references/shrinkage.mcdx` (EN 1992
shrinkage): the `linterp`/`transpose` pair (`k_h` interpolates and extrapolates, cached `0.7`),
`percent` (`80%` → `0.8`), and the `ListBoxScriptableControl` recovering its cached `[3, 0.13]`
("Class S") output without transpiling the JScript. The whole sheet runs and matches the cache;
`ε_cd`/`ε_cs` use rel_tol 1e-4 because Pint's Julian year (365.25 d) differs from Mathcad's mean year.

[tests/test_solve_function.py](../tests/test_solve_function.py) covers `references/solve_as_function.mcdx`:
a Given/Find block whose solver region is a *function definition* `f(a, b) := find(x)` (the constraint
`a·x²−b = cos(x)` closing over the params) — it asserts the emitted `def f(a, b):`, that `f(1, 3)`
recovers the cached root `1.6957…`, and that `f` is reusable with other arguments.

[tests/test_rc_torsion.py](../tests/test_rc_torsion.py) covers `references/RC_torsion.mcdx`
(torsion): the **range-indexed vector backbone** — it executes the whole sheet and checks the
`index_build` vectors (`T_Ed`/`A_sl`/`n_sl`/`s_t`/`k`/`accept`) against Mathcad's cached `1×1`
matrices, that `T_Ed` is 0-based and zero-filled (`[0, 400]`), and that the index variable `i` is an
integer array. Plus the supporting leaf features asserted on the generated source: the stepless range
`i := 1 .. n` (→ `arange(1, n, 1)`), `ceil`/`floor`/`round`, and an inline
`if(cond, "ok", "not ok!")` rendered as a ternary with string literals.

[tests/test_rc_interface.py](../tests/test_rc_interface.py) covers
`references/RC_interface.mcdx` (joint shear capacity): the native `<ml:ComboBoxControl>`
row-selector — single- and multi-column picks (`[f_ck; f_ctk]`, `c`/`μ`) and the empty-values
name-as-string case (`crack := "No"`) — plus a `<ml:program>`-as-value becoming an inline ternary
(with `alsoif`/`and`) and a boolean `=` emitting `==` (not a SymPy `Eq`). Executes the whole sheet and
matches the cache for `f_yd`/`τ_Rd`/`τ_Sd`/`Accept`; `ν_v` is asserted at the live-`f_ck=40` value
`0.5` (the cache's `0.525` is a documented stale leftover, see the `ComboBoxControl` schema note).

[tests/test_3d_plots.py](../tests/test_3d_plots.py) covers `references/3d_plots.mcdx`: the four ways a
`<contourPlot>`/`<plot3D>` equation can resolve to a grid — a function over two ranges (`f(x0, y0)`,
including the *composed* form from `biaxial_bending.mcdx`'s `sigma(epsilon(x0*mm, y0*mm))`, both
wrapped into `mesh_grid(lambda x, y: …, x, y)`), an `N×3` matrix as an `(x,y,z)` point list (scatter),
`CreateMesh(...)`, and an `N×M` matrix as an index-coordinate z-grid — executes the whole sheet, checks
`resolve_plot_grid`'s dispatch (`"grid"` vs `"scatter"`) and `matrix()`'s row-per-list literal form and
column-major reshape (and that
a leading `<ml:display>` metadata child isn't mistaken for a data element) against the sheet's own
values, and renders all 8 figures (matplotlib `Agg`, 2D + `mplot3d`). Plus a regression test that an
expression over only *one* range (not two) correctly stays an `UnsupportedRegion` rather than being
mishandled as a grid.

[tests/test_solve_block_and_double_integral.py](../tests/test_solve_block_and_double_integral.py) covers
two `references/biaxial_bending.mcdx`-motivated runtime fixes *without* executing that sheet's slow,
not-reliably-convergent solve block: `double_integral` (what a nested nested-bounds-independent
`Integral` now emits instead of manually nested `integral()` calls) is checked against the equivalent
nested-`integral()` result and confirmed to fire in the sheet's generated source; and `solve_block`'s
fix for `fsolve` reporting `ier=1` ("converged") while parked on a point whose residual is nowhere near
zero (seen when the whole integration domain sits inside one flat branch of a piecewise model) is
reproduced with a fast synthetic residual, a mocked first `fsolve` call forcing the false-positive, and
a genuinely-stuck case asserting the honest "couldn't confirm convergence" warning (not a silently wrong
answer).

[tests/test_rc_col.py](../tests/test_rc_col.py) covers `references/RC_col.mcdx` (a large biaxial column check) —
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

[tests/test_trig_hyperbolic.py](../tests/test_trig_hyperbolic.py) covers `references/trig.mcdx` and
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

[tests/test_matrices.py](../tests/test_matrices.py) covers `references/matrices.mcdx` — a third **catalogue
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

[tests/test_areas.py](../tests/test_areas.py) covers `references/collapsable-area.mcdx`: a **collapsible
area** (`<region><Area><regions>…`) is flattened away, so `y := 2·x` defined *inside* one converts and
runs like any other region and the `y + x =` below it matches the cache (`3`). Plus, on synthetic
worksheet XML, the two properties the fixture is too simple to show: areas **nest**, and their
children's `top`/`left` are **area-relative**, so each area is sorted within itself and spliced in at
its own position rather than sorted against the sheet.

[tests/test_implicit_plot_domain.py](../tests/test_implicit_plot_domain.py) covers
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

[tests/test_incomplete_ifs.py](../tests/test_incomplete_ifs.py) covers `references/incomplete_ifs.mcdx`:
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

[tests/test_mixed_plot_traces.py](../tests/test_mixed_plot_traces.py) covers
`references/mixed_plot_traces.mcdx`: one plot carrying **both** a parametric trace (two data vectors)
and a function trace (`sin(t)` over a plotting range). Each kind worked alone, but mixed they didn't —
the plot's single domain was applied to every trace, so the parametric one became
`sample(lambda t: v, t)` and `plot_axis` raised on the nested array. Sampling is now decided per axis
expression, on whether it references the domain. The test asserts both traces against Mathcad's cached
`TraceType="Vector"` (3 points) and `"Range"` (101) — the differing lengths being exactly what one
shared domain can't express — plus `static_axis`'s vector/scalar split (a scalar is a *reference line*
and still spans the domain) and, on synthetic XML, that a purely parametric and a purely function plot
are both emitted unchanged.

[tests/test_auto_labels.py](../tests/test_auto_labels.py) covers `labels="*"` — the **auto-labelled**
identifiers a worksheet Prime converted from a legacy `.xmcd` is full of (Mathcad 15's schema didn't
record whether a name was a unit, so the converter leaves it uncommitted). Purely synthetic XML, no
fixture. It pins that `*` is read as a unit *only* in slots that are a unit by definition (a display
override, a plot axis unit), including inside a compound `kN·m`, and that the three things that must
not move don't: a numeric scale override still divides, an explicit `labels="VARIABLE"` in a unit slot
stays a variable, and an auto-labelled name *outside* such a slot stays a variable (a converted sheet
auto-labels its loop index `i` — a name-based rule would emit `ureg.i`).

[tests/test_implied_index0_unit.py](../tests/test_implied_index0_unit.py) covers
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

[tests/test_stack_augment_lookup.py](../tests/test_stack_augment_lookup.py) covers
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

[tests/test_trace_source.py](../tests/test_trace_source.py) covers `--trace-source`: with the flag
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

[tests/test_sort.py](../tests/test_sort.py) covers `references/sort.mcdx`: a small catalogue sheet for
the ordering family (`sort`/`csort`/`reverse`/`rsort`), all of which already had runtime support from
`matrices.mcdx`. It runs the whole sheet end-to-end and matches Mathcad's cache — mainly a regression
guard that the *sheet* converts cleanly, not new runtime behavior. (`csort(M, 4)`, `reverse(M)` and
`rsort(M, 2)` all happen to produce the same matrix here because `M`'s columns are individually
monotonic — a property of this particular `M`, not a bug; each is still checked against its own cached
value.)

[tests/test_log_exp.py](../tests/test_log_exp.py) covers `references/log-exp.mcdx`, which surfaced several
real gaps in the log/exp family: `log(x, b)`'s explicit-base 2-arg form was silently passed as a second
argument to `math.log10` (which doesn't take one) — `log`/`ln` are now a runtime helper pair instead of
bare `math.log10`/`math.log`, and also return a **complex** value for a negative real argument
(`ln(-3) = ln(3) + iπ`, matching Mathcad) rather than raising, since only `ln(0)` is a genuine Mathcad
domain error (cached as an `engineError`) — which the runtime `ln` still raises on. That cached error is
now what tells the converter to wrap the region in a `try`/`except` (see `test_statistics.py` below), so
the sheet runs as a single `exec()` like every other reference and the guarded region echoes the caught
exception in place of a value. Also new: `ln0` (Mathcad's domain-error-avoiding natural log, returning `-1e307`
at `x = 0` instead of raising); the `<ml:imag symbol="i">` literal (previously unparsed), needed for
`e^(i·π) + 1` (Euler's identity, checked as "close to zero" rather than pinned to Mathcad's own
float-noise residual); `logspace(x1, x2, n)` (points log-spaced between two *values*, unlike
`numpy.logspace`'s exponent bounds); and — the sheet's last two lines redefine `exp`/`log` as plain
functions (`exp(x) := x + 2`) and then call them — a call site whose name was redefined is codegen's cue
to skip the builtin table entirely and call the name bare, since Mathcad marks such a call
`labels="VARIABLE"` (the same label an ordinary user-defined function call gets), not `FUNCTION`; this
was previously ignored, so a call to a redefined builtin silently kept calling the original.

[tests/test_difference_eq.py](../tests/test_difference_eq.py) covers `references/difference_eq.mcdx`, a
sheet of **seeded iterations** — Mathcad's way of writing a recurrence, where a seed pins one element and
the equation assigns into a slot whose index is *offset* from the driving range variable
(`guess[i+1] := (guess[i] + X/guess[i])/2`, Newton's `sqrt(700)`). Until now the parser only understood
`X[i] :=` with a bare range variable as the index (`ir.IndexAssign`, one parallel `index_build` pass);
the offset makes each step depend on the last, so the whole family routes to the new `ir.Recurrence` and
emits a sequential loop. The three shapes are each pinned: the scalar recurrence above, a **system** (an
SIR epidemic model whose four vectors read the previous step, so the step is staged in a tuple before
anything is written back — computing them one at a time would feed `sus[τ+1]`'s formula the `inf[τ+1]`
the same step just produced), and a **matrix** recurrence `V^<k> := A·V^<k-1>` writing two-subscript
slots to build a Markov chain's history column by column (which also needs the shape pass to have
resolved that `·` to `matmul`). Two supporting behaviours share the sheet: the loop variable stays
**function-local** (the recurrence is emitted as a `def`, because the sheet keeps using `i` as a range
just below it — a bare `for i in i:` would leave it bound to the last scalar index), and a plot whose two
axes end up different lengths is NaN-padded (`guess` is 10 long against a 9-element index range;
Mathcad's own cached trace reads `[0,1,…,8,NaN]` against ten values). All four echoes and all four cached
plot traces match to ~1e-12, plus two invariants that don't depend on the cache at all — the SIR
population is conserved and the Markov columns keep their initial total.

[tests/test_statistics.py](../tests/test_statistics.py) covers `references/statistics.mcdx`, PTC's own
statistics tutorial and the widest single catalogue sheet in the suite: **82 evaluated regions** over
descriptive statistics, regression, hypothesis tests, the normal/Student-t/Weibull distributions, and the
Numerical-Recipes correlation set. Rather than transcribe 82 expectations, the test reads the fixture's
`result.xml` and pairs each echoing region with its `resultRef`, so the comparison stays exhaustive; 64
echoes match to 1e-12. What the sheet pinned down: capitalisation is the *estimator* (`var`/`stdev`
divide by n, `Var`/`Stdev` by n-1 — the sheet computes each pair twice, once through the builtin and once
from a hand-written Σ, which is how the mapping was confirmed); `percentile(A, p)` interpolates at
position `p·(n+1)` of the 1-based sorted sample, so the 90th percentile of `0 … 10` is 9.8 and not the 9
NumPy's default gives; `%` is a dimensionless unit here rather than `shrinkage.mcdx`'s `<ml:percent/>`
operator; `Rank` is a 1-based ascending rank transform (unrelated to `rank(M)`, the matrix rank it
differs from only by capitalisation); `histogram(n, A)` is an `n × 2` matrix of bin midpoints and counts;
and `data[2] := 1.2·data[2]` is a constant-index `ir.Recurrence` updating one element in place, which is
why every mean below it moves from 75.4 to 77.24. The sheet also **demonstrates Mathcad's own errors**:
`mode` refuses to guess, once for data with no repeat and once for multimodal data, both cached as
`<engineError>`. Reading those at parse time and emitting the region guarded (`ir.Region.cached_error`)
is what lets the sheet run to the end — and retro-fixed `log-exp.mcdx` and `incomplete_ifs.mcdx`, which
had the same problem.

Two **documented divergences** there, neither a bug:

* **Random draws can't match a cache.** `rnorm`/`rweibull`/`rt` produce a fresh sample every run, so the
  16 echoes fed by them (listed in the test's `RANDOM` set: `rt(7, ν)`, and the mean/`Var`/`Stdev`/`var`/
  `stdev`/`kurt`/`skew` of the two 2000-point distributions) are executed for coverage but compared only
  on shape. The estimator *relationships* they exist to demonstrate are checked directly instead.
* **The Numerical Recipes p-values agree to ~1e-7, not ~1e-14.** `Spear`'s `probd`, `kendltau`'s and
  `kendltau2`'s `prob`, and `Ftest`'s `p` are the four values Mathcad computes with NR's Chebyshev
  `erfcc` (accurate to ~1.2e-7) and continued-fraction `betai`; we use SciPy's exact `erfc`/`betainc`,
  which is the more accurate of the two. Reproducing the approximation to be bit-compatible would trade
  correctness for a matching digit, so the test loosens the tolerance on those four indices only
  (`APPROXIMATE`) and everything else stays at 1e-12.

[tests/test_generated_imports.py](../tests/test_generated_imports.py) is not tied to one fixture: it
runs over **every** `references/*.mcdx` and asserts that a generated module's imports and its body
agree, in both directions. That invariant is new. `header_lines` used to *predict* which runtime
helpers the emitted text would name by walking the IR, with the prediction split between a
`found.add(...)` scan and a separate ordering list — miss either half and the module raised
`NameError` on import, invisible until someone converted that particular sheet. The header is now
read off the rendered body, so the two agree by construction and this file guards it.

The "would it `NameError`" direction is checked by parsing the module with `ast` and looking for names
it reads but never binds — deliberately a *different* implementation from the emitter's own tokenizer,
so a bug in that tokenizer can't hide behind a test that calls it. The audit when this landed found
seven dead imports the old predictor had been emitting: `import numpy as np` in four sheets whose
`min`/`max` are reductions (they emit `mc_min`/`mc_max`, so no bare `np.` is ever written), and
`sample` in three whose only plots are parametric (both axes data vectors, so no `sample(lambda …)`).
Nothing was found *missing*, which is the reassuring half of the result.
