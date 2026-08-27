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

[tests/test_probability.py](../tests/test_probability.py) covers `references/probability.mcdx`, PTC's own
probability tutorial and the fixture that completes the distribution catalogue `statistics.mcdx` started:
uniform, exponential, gamma, logistic, Cauchy, geometric, hypergeometric, binomial, negative binomial,
beta, chi-squared, F, log-normal and Poisson, each with its full `d`/`p`/`q`/`r` set, plus the Mathcad-15
`cnorm` alias (`pnorm(x, 0, 1)`) and `Re` (needed because the sheet wraps a Student-t density
`Re(dt(x, v))` defensively). **99 evaluated regions**, 80 matching the cache to 1e-9 (SciPy's `ppf`/`cdf`
round-trips aren't quite the ~1e-12 the closed-form families hit).

The Poisson and Weibull blocks were added to the sheet after the rest, and they pin something none of
the earlier blocks did: **Mathcad maps a distribution function over a vector with no vectorize arrow.**
`dweibull(x, s)` over a column of five measurements, or `dpois(k, λ)` over a column of counts, is an
ordinary worksheet line that reaches the runtime as a single call with an array `x`. The
`norm`/`t`/`weibull` helpers predated that and wrapped their result in `float()`, which raises on
exactly this call — they now return SciPy's result like every later family, and
`test_distributions_apply_element_wise_to_a_vector` checks the array call against the scalar one it has
to agree with. (Re-saving the sheet in Prime also renumbered every `region-id` and inserted an `rt(m, ν)`
echo mid-sheet, shifting the tail of the test's index-based `RANDOM` set by one; the cached values of
every pre-existing *deterministic* echo were verified unchanged across that re-save.)

Two things the sheet exposed that weren't bugs in the distributions themselves:

* `histogram` has a **second call shape**. `statistics.mcdx` only exercises `histogram(n, A)` (an `n × 2`
  midpoint/count matrix); this sheet also calls `histogram(intvls, A)` with an explicit boundary vector,
  which returns just the `len(intvls) - 1` counts — both are real Mathcad overloads, disambiguated on
  whether the first argument is scalar or array-like.
* **`plot_trace`'s NaN-pad only handled 1-D traces.** The "Uniformly Distributed" plot draws a 21-point
  `range` (`n := 0 .. n_bins`, a genuine Mathcad range — the upper bound is inclusive, so 20 bins gives 21
  points) against `histogram`'s 20-row output; Mathcad plots the mismatch by NaN-padding the shorter trace
  (same behaviour `difference_eq.mcdx` pins for 1-D), but here the shorter side is a 2-column matrix, and
  padding used to concatenate a flat NaN block that only matched a 1-D shape. Fixed to pad along axis 0
  using the trailing dimensions of whichever array is shorter.

Three further **unit-safety** cases the fixture itself doesn't reach, pinned by direct tests because a
worksheet plausibly would:

* **`histogram(intvls, A)` converts the boundaries into the data's unit** before binning
  (`test_histogram_converts_boundaries_into_the_data_unit`). Comparing raw magnitudes put `mm` edges
  against `m` data straight into the first bin — a wrong count with no error, the worst failure mode
  here. An *incompatible* unit now raises Pint's `DimensionalityError` rather than returning a
  plausible-looking number.
* **`Re` is unit-aware** (`test_Re_keeps_a_unit_and_takes_the_real_part`). Mathcad takes `Re` of a
  dimensioned complex value (a complex impedance, a complex modulus) as readily as of a plain number, and
  `np.real` has no implementation for a Pint quantity — it raises instead of reaching the magnitude. The
  sheet only calls it on a dimensionless Student-t density, so nothing else catches this.
* **Every distribution parameter is dimensionless-reduced** (`test_distribution_parameters_accept_an_unreduced_ratio`).
  A worksheet routinely feeds these a ratio Pint still carries as `mm/mm`; a bare `float()` would read the
  unreduced magnitude. The `r*` draws take their parameters through `_num`/`_count` for that reason. The
  `d`/`p`/`q` wrappers deliberately return SciPy's own result rather than coercing to `float`, so a vector
  of `x` evaluates element-wise — which is also why only the `r*` names are registered in
  [shapes.py](../mcad2py/shapes.py)'s `_CALL_KINDS` (they always return a vector; their siblings follow
  their argument's shape, and `histogram`'s shape depends on which overload was called).

One **documented divergence**, the same shape as `statistics.mcdx`'s: every `r*` draw, and anything
computed from one downstream (a random histogram's `lower`/`upper` bin edges, a Monte Carlo `Prob`
estimate and the `qlogis` built from it), is a fresh sample each run and cannot reproduce a cached number
— 19 of the 99 echoes (the test's `RANDOM` set). They still execute, so the code path is covered; the
`d`/`p`/`q` inverse relationships are checked directly instead (`test_distributions_are_mutually_consistent`).

[tests/test_constants.py](../tests/test_constants.py) covers `references/Constants.mcdx`, which
evaluates Prime's whole built-in **Constants** label with nothing defined on the sheet: the maths trio
(`e`/`π`/`∞`), Euler-Mascheroni `γ`, and the physics set (`c`, `g`, `e_c`, `h`, `ℏ`, `k`, `m_u`, `N_A`,
`R`, `R_∞`, `α`, `ε_0`, `μ_0`, `σ`, `Φ_0`). All 19 echoes are read out of `result.xml` by `resultRef`
rather than transcribed, and 18 match to 1e-12. What the sheet pinned down: the lookup is **label-gated**
— Prime writes `<ml:id labels="CONSTANT">`, which is the only thing distinguishing the speed of light
from a worksheet's own `c`, so names as ordinary as `c`/`g`/`k`/`R`/`σ` can live in `mapping.CONSTANTS`
safely; the cache states a dimensioned constant in **base SI**, so `mcad2py/const.py` defines it that
way and the test compares `to_base_units().magnitude`. The values are **imported names**
(`from mcad2py.const import c, g, …`), not inlined numbers, so a formula reads `m * c**2`; because they
are pre-built Pint quantities, generated modules now share one registry
(`from mcad2py.units import ureg`) instead of each building their own. The import list is chosen from
the **IR** rather than by scanning the emitted text — `c`/`g`/`k`/`R` are everyday variable names, and
`test_only_the_constants_a_sheet_labels_are_imported` pins that a sheet with its own `k` imports
nothing. It also turned up a **real bug in `disp`**: a display override
that carries a numeric scale (`h` shown as `10⁻³⁴ kg·m²/s`) evaluates to a Pint *Quantity*, and
`Quantity.to(<Quantity>)` silently uses the argument's units and drops the `10⁻³⁴` — every such echo was
off by the scale factor. `disp` now divides when the override's magnitude isn't 1.

One **documented divergence**: Mathcad's `∞` is 10³⁰⁷ and that is what the cache holds, while we emit
`math.inf` — the faithful reading of the symbol, and the only one that works as an integration limit or
a comparison bound. That echo is asserted to be an infinity instead (`test_infinity_is_a_real_infinity`,
which also pins the cached 1e307 so the difference stays visible).


[tests/test_breaks_sets_logic.py](../tests/test_breaks_sets_logic.py) covers
`references/breaks-sets-logic.mcdx`, a small catalogue of four corners that are all about *notation*
rather than numerics: `≡` global definitions, equation breaks, number sets, and the logic operators.
All 24 echoes are read from `result.xml` by `resultRef`; 23 are numeric and match, and the 24th is the
symbolic one below. What the sheet pinned down: `<ml:globalDefine>` is structurally a define but binds
over the **whole** sheet, so those regions are hoisted to the top (`ir.Define.global_scope`) — the only
way a linear module can honour sheet-wide scope; `split="true"` on an operator is Mathcad wrapping a
long formula in its *display* and means nothing to the tree; the right operand of `∈` is an `<ml:id>`
with **no `labels` attribute at all** (unique in the schema) and travels to `element_of` as a string;
and `⊕` needs a runtime helper because Python's `^` is bitwise, so `3 ⊕ 2` would answer 1 where Mathcad
says 0. `¬` and `≠` do map straight onto Python's `not` and `!=`.

`π ∈ ℚ` is the one that earns its place: no float can answer it, since every float *is* a rational.
Mathcad refuses too — the sheet's own text says "Rational numbers has to be evaluated symbolically" —
and writes the region as an `<ml:symEval>` whose command is a bare `<ml:placeholder />`, a plain `→`
with no keyword. That empty command now maps to SymPy's `simplify`, and `element_of`'s `ℚ` branch
answers from the closed form `nsimplify` recovers (`3.14159…` → `π`), matching Mathcad's cached
`<symResult>` of 0. Its caveat is inherent to the question and documented on the helper: a float that
merely approximates π reads as irrational.

Two things this fixture fixed beyond itself: comparisons and connectives are checked *numerically*
because Mathcad answers 1/0 where Python gives `True`/`False` (the same value — `bool` is an `int`),
and a rendered `# TODO unsupported: …` can no longer be wrapped in `print(...)`, where the closing
parenthesis used to land inside the comment and stop the whole module parsing — exactly what emitting
a visible TODO instead of dropping the region exists to prevent (`print_lines`).


## `tests/test_header_footer.py` — `references/header_footer.mcdx`

Pins the separate `header.xml` and `footer.xml` package parts and their relationship maps.
The fixture has three header text regions, four header math regions, and one footer text region.
It also has a dynamic page number field.

The tests require both backends to emit the useful content as non-executable comments.
Header math carries a `[display math]` label and does not define worksheet values.
The page field is omitted, and `--no-header-footer` removes all context from both formats.

The label belongs to math alone — a separate test pins that a note and a plot go unlabelled, since
`[display math] TODO unsupported: …` would claim the note was an equation.

The page field is dropped a paragraph at a time, not a region at a time: two synthetic footers pin
that a project name beside the page number survives, and that a `<pageNumber>` with no `template`
still takes its region with it. `_field_pattern` is tested on a German template, because the match
is built from the template rather than from the English words.

A header is decoration, so two tests pin that it can never cost you the worksheet: a parse that
raises becomes one `ir.UnsupportedRegion` note, and a module carrying that note still compiles.

This is the one fixture [tools/strip_mcdx_metadata.py](../tools/strip_mcdx_metadata.py) must not
strip: the tool empties `header.xml`/`footer.xml` by default, which would delete everything these
tests read. It is named in that tool's `_KEEP_HEADER_FOOTER`, so both the strip and the `--check`
CI guard skip those two parts for it — and only those two. Its `docProps` fields are blanked like
any other sheet's, so the header text here (`John Smith`, `Mcad test`) is invented on purpose.


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

One read is excused: a region **Mathcad itself** couldn't compute may name something that is
undefined for exactly the reason Mathcad reported — `header_footer.mcdx` reads an `X` that only its
*header* defines, and Mathcad errors on it too. The excuse is keyed to the
`# Mathcad reports an error here:` comment `guard_cached_error` writes above the `try`, not to
`try`/`except Exception` in general: any other guarded block is still checked, or a genuinely missing
import could hide inside one. A unit test pins both halves of that.

[tests/test_reference_artifacts.py](../tests/test_reference_artifacts.py) is the other fixture-wide
guard: every committed `references/*.py` and `*.ipynb` must equal a fresh conversion of its worksheet.
These are generated artifacts kept in git so a reader can see a sheet's output without running
anything — but nothing *consumed* them (the rest of the suite converts each `.mcdx` fresh and executes
that), so they drifted through several header changes unnoticed and were still emitting
`ureg = pint.UnitRegistry()` long after generated modules moved onto the shared registry in
`units.py`. Refreshing them was a one-liner; the value of this test is that the commit which *changes
codegen* is the one that fails, instead of a reader hitting a stale artifact months later.

Two things are normalised before comparing notebooks, both because they are irreproducible rather than
unimportant. Cell **ids** are stripped — `nbformat` mints a fresh random id per cell on every run, so a
byte comparison would fail on every notebook always, and regenerating to satisfy it would churn ~500
lines of `RC_col.ipynb` to change three. And **embedded image payloads** are replaced with a marker:
`Elastic_foundation_eq_line_spring.mcdx` carries a BMP (the only non-web raster in the fixtures), which
the notebook backend re-encodes to PNG through Pillow, whose bytes are not stable across platforms or
versions. That one is a **documented divergence** worth knowing about — it was found the hard way, as a
CI failure on an artifact that was perfectly current: the committed notebook was generated on Windows
and CI runs Linux, so the base64 blob differed while the picture was identical. The payload is compared
as *pixels* instead (`test_reference_notebook_images_are_pixel_identical`, which decodes both sides and
compares size, mode and `tobytes()`), so a genuinely changed image is still caught. Everything else,
cell order and content included, is compared exactly. The `.py` artifacts need none of this — that
backend emits a `# [image: …]` comment rather than embedding the data.

The parametrization walks the *committed artifacts* rather
than the worksheets, because not every sheet ships both (`shrinkage.mcdx` has only a notebook) —
`test_every_artifact_has_a_worksheet` covers the reverse, since an artifact whose `.mcdx` was renamed
would otherwise sit here with no test running against it at all.

## `tests/test_seed.py` — `references/seed.mcdx`

Pins Mathcad's own random number generator, which mcad2py now reproduces exactly, and the `r*`
distribution family built on top of it. See the `seed.mcdx` entry in
[mcdx-schema-notes.md](mcdx-schema-notes.md) for the algorithms and for how each was identified.

The comparisons here use exact equality — not a tolerance, deliberately. These helpers are
bit-for-bit Mathcad, so any drift at all is a real change and should fail.

Echoes are paired with regions by **`region-id`**, not by position. The sheet is a long catalogue of
near-identical three-region blocks and it keeps growing, so a positional index would break on every
edit; the `blocks` fixture counts `print(` in each region's rendered lines to do the alignment.

| Test | Pins |
|------|------|
| `test_generated_source_shape` | The three constructs this fixture is first to reach: a bare `Seed(1)` region that must not print, a bare call in a program body that must not become a return, and `M^<i> :=` as a `col_set`. Plus `range` renamed to `range_`. |
| `test_seed_returns_the_previous_state` | Six consecutive `Seed` regions: `Seed(n) =` echoes the state left behind, not `n` and not a status code |
| `test_rnorm_matches_mathcad` | One normal draw, and that the four uniforms after it are `U[4..7]` — the stream continuing, not restarting |
| `test_distribution_draw_and_its_stream_position` | 13 `r*` functions, each as a `Seed(1)` / draw / `runif(4,0,1)` block. The trailing uniforms are the stricter half: they pin **consumption**, so a helper cannot return the right number off the wrong uniforms |
| `test_rt_matches_mathcad` | `xfail(strict)` — the one unsolved member. Marked strict so it fails loudly if `rt` is ever cracked and the mark left behind |
| `test_first_runif_block_diverges_by_mathcad_recalculation_order` | The one non-exact block, asserted as a divergence rather than hidden: reading order vs. Prime's own evaluation order |
| `test_program_reseeds_each_pass` | The sheet's point: three passes of `Seed(1)` + `rnorm` give three identical columns, and that column is Mathcad's |
| `test_histogram_of_the_repeated_set` | `hist` over the seeded sample |

**What the worksheet does not reach.** Every `r*` block draws **one** value at **one** parameter set,
so the array call, a dimensioned parameter, and every gamma shape split other than the single piece
each block happened to use are all untested by the table above. The direct unit tests below the
fixture ones cover: `Seed` on a Pint quantity and on an *unreduced* ratio (`7000 mm / 1 m`, where a
bare `float()` would read 7000); a distribution parameter arriving the same two ways; `m > 1` drawing
off one shared stream rather than restarting it; the gamma shape split at a whole shape, a half shape
and a mixed 2.5; `rbinom` at `n = 20` (one uniform, not 20 Bernoulli trials) and across its whole
support; `rlnorm` against `rnorm`, since the sheet has no `rlnorm` block; and the location/scale arms
of `rcauchy` and `rlogis`, which the sheet only calls at 0 and 1.

**Still on NumPy:** `rt` and `rhypergeom`. `rt`'s cached value is exactly `z1/z2`, six uniforms, but
the block consumed seven — the seventh is unexplained, and guessing would silently negate half of all
draws. `rhypergeom`'s only block is degenerate (zero white balls, no uniform drawn). Both are
repeatable run to run because `Seed` reseeds NumPy too, but neither is Mathcad's number, and a sheet
that calls either desynchronises the stream for everything after it.

A sheet that never calls `Seed` **is** reproducible: Prime opens a new worksheet at state 1, the same
as `Seed(1)`. `test_a_fresh_worksheet_starts_at_state_one` pins that the module-level generator starts
there too.

## `tests/test_interpolation.py` — `references/interpolation_prediction.mcdx`

PTC's own "Interpolation and Prediction" tutorial. 28 evaluated regions covering the three cubic
splines and `interp`, the polynomial set (`polyint` / `polyiter` / `polycoeff`), the rational and
Thiele continued-fraction interpolants, and `predict`. Echoes are paired with regions by `region-id`
via the shared `cached_results` / `result_refs` helpers, as in `test_statistics.py`.

What the sheet pinned that no reading of the documentation would have given:

| Test | Pins |
|------|------|
| `test_sheet_matches_cached_results` | All 27 computable echoes against `result.xml` |
| `test_polyiter_stops_on_the_change_not_the_error_estimate` | The convergence rule. The same data and query converge at **order 3** when allowed 5, and report failure at **order 2** when capped there — and `polyint`'s error estimate for that query is exactly 0. So `polyiter` compares two *successive interpolations*, not the error estimate, and it takes the data points **in the order given**, not nearest-first |
| `test_thielecoeff_substitutes_a_tiny_denominator_for_zero` | Mathcad divides by **1e-65** where a reciprocal difference is infinite. The sheet's degenerate example caches `1e65`, `-1e-65`, `-1e65` and then `-4.2764235361e-50` — that last one is pure floating-point noise from the substitution, and reproducing the substitution reproduces it to the last digit |
| `test_predict_matches_the_sheets_hand_written_recurrence` | `predict` is Burg's maximum-entropy method (NR `memcof` + `predic`). The sheet writes the predictor out term by term beside the builtin call, which is what identified the method and the coefficient order (`memcof`'s `d[0]` weights the *most recent* sample; Mathcad displays them oldest-first) |
| `test_predict_refuses_to_use_every_data_point` | `m >= rows(v)` is an `<engineError>` in Mathcad, wording included |
| `test_polyint_family_carries_the_ordinates_unit` | Mathcad tags the **whole** returned vector with `vy`'s unit — `polyiter`'s converged flag and order arrive in seconds too. Cached as a `<unitedValue>` wrapping the matrix, so this is the cache's own reading |
| `test_the_three_splines_differ_only_at_the_ends` | `lspline` = natural (y'' = 0), `pspline` = parabolic ends (y'' constant over the end piece), `cspline` = not-a-knot |
| `test_unimplemented_builtins_do_not_break_the_module` | The adaptive-knot `Spline2` calls degrade to comments and the rest of the sheet still runs — including `GrubbsClassic` and `trim`, which sit in the same section |

**Documented divergences.**

*Only `Spline2`'s adaptive knot placement is missing.* `Spline2`, `Binterp` and `DWS` (with the
`GrubbsClassic` / `trim` outlier pair) drive the sheet's first 15 echoes. Everything there is
implemented and exact except the calls where Mathcad would place its own knots: they are neither
uniform nor quantiles of the data, and PTC documents no rule. Guessing one would return plausible
wrong numbers from a green-looking sheet, which is the failure this repo's conventions exist to
prevent, so those calls — and only those — convert to visible `# TODO unsupported region` comments.
Nothing is blocked by *name*: see `tests/test_least_squares_spline.py` for the per-call gate and
`tests/test_outliers.py` for the outlier pair.

*The second derivative at an interior knot* — `sd_p(vx[1])` and `sd_p(vx[last-1])`, taken with the
numeric derivative operator — agrees to ~1e-3 and ~1e-5, not 1e-14. A spline's third derivative jumps
at a knot, so any finite difference straddling one is wrong in its last digits; Mathcad's own two
values for what is provably the *same* number (a parabolic end piece has constant y'') disagree at the
7th digit. The values at the **ends**, where the end piece continues smoothly and Mathcad extrapolates
along it, match to 1e-13 — that is the real check on the spline coefficients, and it is exact enough to
confirm the end conditions above.

*`polycoeff`* agrees to 1e-11 rather than 1e-14: a 5th-degree fit over x ≈ 300…333 has a leading
coefficient of 1.8e4 against a trailing one of 2.4e-6, and the cancellation between them is the whole
computation.

**What the worksheet does not reach.** Every interpolator on the sheet is called on dimensionless data
except the `polyint`/`polyiter` block, and no spline there is ever asked for a *dimensioned* query
point or handed a query in a different unit from its knots. The direct unit tests below the fixture
ones cover: a query in mm against knots in m (through `linterp`, `interp` and `polyint` alike, plus a
tolerance in ms against ordinates in s); `interp` over a whole **vector** of query points, which is
how the sheet's plots call it but which no echo checks; the three splines' end conditions read off
their coefficients; `rationalint` on a pole and on an exact hit; a `Thielecoeff` → `Thiele` round trip;
the derivative operator on a **dimensioned** argument (m/s² differentiated twice against s); and
`range_sum` over a stepped range and over a unit-bearing summand.

## `tests/test_least_squares_spline.py` — `references/interpolation_prediction.mcdx`

`Spline2` / `Binterp` / `DWS`, the **reproducible half** of Mathcad's least-squares B-spline family.
The knot *placement* is still Mathcad's own undocumented rule, so the names stay in
`mapping.UNIMPLEMENTED` and the sheet's regions still convert to visible comments; this module tests
the runtime helpers directly. A call that has to place its own knots raises rather than fitting a
plausible wrong curve, and `test_placing_its_own_knots_raises_rather_than_guessing` pins that for all
three shapes Mathcad also declines (no fourth argument, a scalar `level`, and an unsorted vector).

The sheet never echoes `SplineW` or `SplineNW`, so the anchors are indirect and worth naming:

| Anchor | What it pins |
|--------|--------------|
| `DWS(SplineNW)` = 2.3915925499477493 | an **unweighted** fit on a given knot vector |
| `DWS(SplineW)` = 2.3217321679568084 | `w` is a **standard deviation** — the weight is `1/w²`, and `DWS` runs on the *weighted* residuals |
| the cached plot trace of `Binterp(range, SplineW)` | `Binterp`'s four rows (value + three derivatives) at 101 points — the only direct check of it that exists |
| the cached 79-element `b` | the packed layout, and that a refit on Mathcad's own knots returns Mathcad's own coefficients |

**The detail that hides the rest: `Spline2` drops data outside the knot range.** The sheet's
`Knots := range` stops at 1982.96 while `x` reaches 1999.7, so five of the 536 points fall out.
Keeping them shifts every number here by about 0.2% — close enough to read as a rounding difference,
which is why `test_points_outside_the_knot_range_are_dropped` asserts it rather than leaving it to be
caught downstream.

**One documented divergence.** `Binterp`'s **third** derivative is not compared against the cached
trace. It is piecewise constant, the trace samples it exactly *at* the knots, and Mathcad picks the
left or the right interval there inconsistently — its own values repeat at samples 1, 4, 8, 16, 32, 64
and 100, a bisection artifact in Mathcad's interval search. Pinning against it would encode that bug.
`test_the_third_derivative_differentiates_mathcads_own_second` checks it at interval *midpoints*
against the difference quotient of Mathcad's cached second derivative instead.

**What the worksheet does not reach.** Every `Spline2` call on the sheet is dimensionless, so
`test_a_query_is_converted_into_the_abscissae_unit` builds a fit in metres and queries it in
millimetres, and checks that the derivative rows come back in `kg/m`, `kg/m²`, `kg/m³` — the four rows
cannot share one unit, which is why `Binterp` returns an object array in that case. The two
unidentified trailing statistics come back `nan` rather than a guess, pinned by its own test.

### `references/spline2.mcdx` (in the same module)

13 points, calling `Spline2(x, y, 3)` at the default `level`, at 0.5 and at 0.001. Its value is that
all three echoes are **identical** — knots `[0, 6, 12]`, the midpoint exactly, on data that is not
symmetric. Three tests pin what that proves:

* `test_a_small_sheet_reproduces_its_whole_packed_vector` — every element to 4e-15, on data with
  nothing in common with the 536-row sheet.
* `test_the_level_argument_changes_nothing_on_the_small_sheet` — the stopping rule is a
  Durbin-Watson p-value against `level`. One interval gives p = 0.00069, below every level tried; two
  gives 0.79, above all of them. So all three calls stop in the same place.
* `test_the_small_sheets_knots_are_uniform` — the search **starts at one interval**. With one
  interval the fit is a single cubic, `|D³f|` is constant, and any curvature-based redistribution
  returns uniform knots, which is why the interior knot is exactly 6.0.

The sheet deliberately cannot discriminate between knot-placement rules — its `x` is uniform and it
stops before the redistribution step ever runs. It settles the loop around that step instead.

### `references/spline2A.mcdx` (in the same module)

45 points on **non-uniformly spaced** `x` — its spacing varies by a factor of four — with two kinks
placed deliberately in the sparse half, so that a placement rule which equidistributes in `x` and one
that equidistributes over data points cannot agree. Three calls at the default `level`, at 0.5 and at
0.001 return 6, 4 and 3 intervals.

* `test_the_starting_knots_are_uniform_in_data_index` — the headline. Two of the three cached knot
  vectors are `interp(j·(len(x)-1)/m, 0..len(x)-1, x)` **exactly**, zero difference. Mathcad's first
  try at every interval count puts an equal number of *data points* in each interval, not an equal
  width, and interpolates the knot between the two neighbouring points (which is where values like
  0.834022 come from).
* `test_a_stricter_level_can_return_a_redistributed_knot_set` — the `level = 0.5` call does **not**
  return that set. It is the one cached example of the second phase on small data, and the rule
  behind it is the last unsolved piece.
* `test_every_cached_vector_is_reproduced_from_its_own_knots` — given the knots, all three vectors
  come back to 1e-12, at three different interval counts.

**A documented divergence.** The sheet does `Seed(1)` then `nz := rnorm(45, 0, 0.85)`, so executing
the generated module gives a different `y` from the cached one. The cached values are our stream at
offset **45** — exactly one whole `rnorm(45, …)` call further on — so Prime drew the vector twice
across the saves that produced the file.
`test_the_sheets_noise_is_our_random_stream_one_call_later` pins that offset, which says the generator
is right and the worksheet state is what moved.

### `references/spline2B.mcdx` (in the same module)

31 points fitted on five **explicit** knot vectors (2, 4, 5, 8 and 10 intervals) and at two degrees.
No placement rule is involved anywhere, so each echo is a clean (design, statistic, p-value) triple —
which is what identified the last two trailing statistics.

* `test_the_whole_packed_vector_matches_element_for_element` — knots, coefficients, residual standard
  error, statistic **and both p-values**, to 3e-9 across six fits. That is the Beta CDF's own
  precision, not a modelling gap. The degree-2 call is the only non-cubic fit in any fixture, and it
  is what shows the coefficient count is `m + degree`, not `m + 3`.
* `test_a_higher_degree_is_refused_the_way_mathcad_refuses_it` — the sheet's seventh call,
  `Spline2(x, y, 4, k5)`, is the one region **Mathcad itself** will not compute: an `order_too_big`
  engine error whose argument is 3. The family is capped at cubic, and `Spline2` raises to match.

The two statistics are the classical **bounds** of the Durbin-Watson test — the statistic's exact null
distribution depends on the design matrix, so Durbin and Watson published two design-free bounds
instead. Mathcad stores the upper first (the probability of no positive autocorrelation, which is what
the fit is judged by) then the lower.

### `references/spline2C.mcdx` (in the same module)

The same 45 points as `spline2A`, fitted at eight values of `level`. Its worth is that the interval
counts come back sharply **non**-monotone — 6, 6, 15, 15, 29, 5, 5, 7 — which is what turned the
knot-count loop from a guess into a rule.

* `test_the_moved_knot_set_does_not_depend_on_level` — two levels that stop at the same count return
  byte-identical vectors, so the moved set is a function of the data and the count alone. `level`
  chooses when to stop, never where the knots go.
* `test_the_loop_accepts_the_first_fit_whose_lower_bound_beats_level` — the rungs from 0.1 to 0.5 form
  a ladder: each cached fit clears its own level, and no smaller cached count does.
* `test_the_level_0_001_rung_is_predicted_from_scratch` — the one cached adaptive fit reproduced end
  to end with no unsolved step, count and knots included, by sweeping interval counts and taking the
  first whose lower bound clears 0.001.
* `test_the_three_highest_levels_are_accepted_on_the_upper_bound` — 0.6, 0.7 and 0.8 stop at *fewer*
  intervals than 0.5 does, on upper bounds rather than lower ones. That fallback is not reproduced;
  the test records the evidence rather than a rule.

`test_every_rung_is_reproduced_from_its_own_knots` covers all eight, at counts from 5 to 29 — the last
leaving only 13 residual degrees of freedom.

### The per-call `Spline2` gate (in the same module)

`Spline2` is suppressed per *call*, not per name — with an explicit knot vector it is exact, so
blocking the name would throw away work that is finished. Two tests pin the split:

* `test_a_sheet_of_explicit_knot_calls_converts_completely` — `spline2B` has **no TODO left in it**
  and its numbers match the cache, the degree-4 region included (which converts as a guarded region,
  the way any cached engine error does). Its `x` and `y` come back exactly too, since they are built
  from `Seed`/`rnorm`.
* `test_the_gate_keeps_the_adaptive_calls_out` — `interpolation_prediction` has both kinds.
  `Spline2(x, y, n, w, Knots)` and `Spline2(x, y, n, Knots)` convert, the second only because the
  first named `Knots` in the unambiguous fifth slot. `Spline2(x, y, n)`, `Spline2(x, y, n, w)`,
  `Spline2(…, 0.5)` and `Spline2(x, y, n, w, level)` all stay comments — an unsorted column, no
  fourth argument, and a significance sitting in the knot slot.

**A suppressed region shows its own would-be code.**
`test_a_suppressed_region_shows_the_python_it_would_have_been` (in `tests/test_interpolation.py`)
holds every `# TODO unsupported region:` line to having the commented-out Python directly above it.
That is what makes the taint chain readable: `# b = Spline2(x, y, n, w)` above the first note, and
then a run of `needs b, left undefined above` that a reader can trace back to that one line. Multi-line
regions are commented whole — the sheet's plots name the very variables their notes list as missing.

## `tests/test_outliers.py` — `references/grubbs.mcdx` and PTC's published matrices

`references/interpolation_prediction.mcdx` reaches exactly one arm of Mathcad's outlier family:
`GrubbsClassic(y, 0.55)` on a plain unitless column, read for its index alone (cached as `150`). That
one call would come out the same under several wrong readings, so this module pins the rest two ways:
against PTC's worked examples, which publish the returned matrices in full for one 195-point heatflow
data set, and against `references/grubbs.mcdx`, a 20-value sheet built to reach every branch. See the
schema note for where each number comes from.

| Test | What it pins |
|------|--------------|
| `test_grubbs_reproduces_the_published_matrix` | `Grubbs(y, 0.85)` → the three rows `3 3.526 -0.207 / 19 3.631 -0.312 / 188 3.322 -0.003`. This is the test that identifies the **population** standard deviation: the sample form drops row 188 |
| `test_a_tighter_confidence_returns_fewer_rows` | `a = 0.9` → two rows, and the third column moves with the bound rather than the data. Confirms `a` is a *confidence*, so the significance is `1 - a` |
| `test_grubbs_falls_back_to_the_closest_point` | With nothing past the bound `Grubbs` returns the one most extreme point, third column **positive** — the same row `GrubbsClassic` gives. An empty table was the natural guess and the cache says it is wrong |
| `test_grubbs_classic_returns_the_extreme_point_outlier_or_not` | `[19 3.631 -0.389]` at `a = 0.8`, and a **positive** third column at `a = 0.98` — the documented "not an outlier, but the point most likely to be one" |
| `test_three_sigma_returns_index_and_statistic_only` | Two columns, no bound to subtract |
| `test_three_sigma_falls_back_to_the_closest_point` | The one place the family invents a row, and Mathcad documents it |
| `test_the_statistic_is_dimensionless_for_dimensioned_data` | `|x - mean| / stdev` cancels the unit, so a column of metres gives a bare matrix — indexing it must not hand a sheet a stray unit |
| `test_trim_drops_the_named_rows_of_a_matrix_and_keeps_the_unit` | The "Outlier Removal" example's two-column `augment(x, y)`: 195 rows in, 192 out, unit intact |
| `test_trim_takes_a_single_index` | The reference sheet passes one scalar, not a vector; a vector keeps its 1-D shape |
| `test_trim_reduces_a_dimensionless_index` | An index still carried as `mm/m` reduces before rounding — reading the raw magnitude would drop row 2000 and trim nothing |
| `test_a_matrix_is_one_flat_bag_with_nested_index_pairs` | A matrix is judged as a single sample of **all** its elements, and the position comes back as a nested 2×1 `(row, col)` column |

### `references/grubbs.mcdx` (in the same module)

Built for this family alone: 20 values with one outlier at index 19, a clean twin `u`, and 16 echoes.

| Test | What it pins |
|------|--------------|
| `test_the_sheet_converts_with_no_todo` | Nothing in it is suppressed |
| `test_every_echo_matches_the_cache` | All 16 echoes to ~1e-11. This is what pins the critical value to **fourteen** digits — the published pages print three |
| `test_the_sheet_pins_the_fallback_and_the_nested_pair` | The two readings no page shows, named rather than buried in the sweep: `Grubbs(v, 0.999)` returns the closest point, and `Grubbs(M, 0.95)` returns a nested `(row, col)` column |
| `test_a_unit_on_the_data_leaves_the_table_bare` | Prime accepts `GrubbsClassic(v·m, 0.95)` and caches plain reals, identical to the unitless call |
| `test_the_nested_pair_is_row_then_column` | `Grubbs(augment(x, v), …)` puts its extreme at (0, 0), which reads the same either way round. `Grubbs(augment(v, x), …)` moves the same point to row 0 of column **1** and caches `(0 1)ᵀ` — so the pair is `(row, col)` |

**Still unconfirmed.** One candidate cannot show what order **several** matrix candidates come back
in. We emit column-major — Mathcad's own storage order, and the order the vector case is confirmed to
use.

## `tests/test_range_sum.py` — `references/range_sum.mcdx`

Mathcad writes three different sums with one `<ml:summation>` head, told apart by the lambda's bound
variable and the bounds. The sheet puts one of each over the same data, so confusing two of them
shows up as a wrong number rather than as a parse failure.

| Test | Pins |
|------|------|
| `test_generated_source_shape` | Each `Σ` reaches a different helper — `total`, `range_sum`, `summation` |
| `test_the_indexed_vector_matches` | `X[i] := mod(2i, 7)` over `i := 0..10` |
| `test_a_bare_sigma_totals_the_vector` | The bare `Σ` over an already-built vector |
| `test_a_range_sum_covers_the_whole_range_variable` | The point of the sheet: `Σ_i X[i]` with no bounds is 33, the same as `total(X)` — an empty bound is the whole range variable, not an unfinished slot |
| `test_an_indexed_sum_still_honours_its_bounds` | `Σ_{j=1}^{4} X[j]` is 13, so the bounded form did not quietly become a range sum |
| `test_an_indexed_sum_over_a_function` | The bounded form over `f(j)` |
| `test_a_range_sum_over_an_expression_in_the_index` | `Σ_i f(2i) = 1551`, so the body sees each index value, not the range as a whole |
| three parser-shape tests | That each XML shape is *told apart* in the first place. A value check cannot do this alone: `total` and `range_sum` agree on this data by design |

**What the worksheet does not reach.** It sums dimensionless integers over a dimensionless range and
calls `mod` only on non-negative values. Direct unit tests below the fixture ones cover a dimensioned
domain, a dimensioned result, `mod`'s sign rule (C's `fmod`, not Python's `%`), `mod` with a divisor
in a *different* unit (`2.5 m` against `300 mm`), `mod` on an unreduced `mm/m` ratio, and `mod`
applied element-wise to a vector.

`mod`'s sign rule is PTC's documented one, not a cached number. One negative `mod` region on the
sheet would upgrade it.

## `tests/test_emit_notes.py` — no fixture

A `# TODO`/`# placeholder` note is a comment, so it swallows the rest of its line. Harmless when the
note *is* the whole expression, fatal one level down: `summation(f, None  # placeholder, None  #
placeholder)` puts the closing parenthesis inside the comment and the module stops parsing — the one
outcome the "output still loads" convention exists to prevent.

These build the IR by hand: a nested placeholder, a nested unsupported node, two notes in one
expression, a top-level note (which must stay byte-identical to before the fix), and that the
collector does not leak between expressions. No fixture, because the worksheet that surfaced it calls
several functions it never defines and cannot be executed.

## `tests/test_set_mcdx_value.py` — `references/trig.mcdx` (copied to `tmp_path`)

The write path (`tools/set_mcdx_value.py`). The fixture is copied first: the tool edits in place,
and a `references/*.mcdx` is read-only for the rest of the suite.

| Test | Pins |
|------|------|
| `test_sets_the_number_and_keeps_the_unit` | `theta := 34 deg` -> `45 deg`; the unit survives an edit that names only the number |
| `test_only_worksheet_xml_changes` | Every other zip part comes through byte-identical — `result.xml` above all, so a stale cache stays visibly stale rather than being half-rewritten |
| `test_edit_is_minimal` | Exactly two characters differ in `worksheet.xml`. A re-serialized part would pass a value check and still perturb the file |
| `test_generated_python_carries_the_new_value` | End-to-end: the edited sheet converts and runs, `sin(45 deg)` = 0.7071… . Goes back through the parser the rest of the suite trusts, rather than asserting on XML |
| `test_unit_can_be_replaced` / `_removed_and_added` | `--unit rad`, `--unit ""`, and re-adding one — the `<ml:apply><ml:scale/>` wrapper is built and unbuilt correctly |
| `test_negative_value_wraps_in_neg` | A negative value becomes `<ml:apply><ml:neg />…`, not a `-` inside `<ml:real>`. No fixture has a negative literal define, so this is the only cover for that arm |
| `test_output_leaves_the_input_alone` | `-o` writes a copy and does not touch the source |
| `test_refuses` (3 cases) | A formula (`A := sin(theta)`), a text region, and a missing region id each raise `Refused`. This is the point of the tool: overwriting a formula with a number would silently delete the sheet's maths |
| `test_refuses_a_bad_number` | A non-numeric `--value` is caught before anything is written |
| `test_refuses_a_compound_unit_rename` | `kN/m` has no single name to replace, so `--unit` declines instead of guessing; the number alone is still settable. Uses `Elastic_foundation_eq_line_spring.mcdx`, the only fixture with a compound-unit literal |
| `test_listing_matches_the_generated_python` | `--list` on `RC_col.mcdx` (28 inputs) offers only real numbers |
| `test_listing_never_offers_a_formula` | Across `matrices`/`3d_plots`/`difference_eq`, nothing listed re-classifies as a formula |

**What these do not reach.** `tools/recalc_mcdx.py` has **no test** — it needs Mathcad Prime and
Windows COM, so it cannot run in CI. It was verified by hand on 2026-08-21 against Prime 12.0.0.1:
`trig.mcdx` with `theta` at 45° recomputed to a cache matching the generated Python's 19 values
exactly, and at 60° in 6.6 s. If you change its wait loop, re-run that check by hand — a wrong loop
fails by writing *stale* numbers, which no value comparison against the same file can detect.

## `tests/test_set_mcdx_literal.py` — `references/plain_concrete_cohesion.mcdx` (copied to `tmp_path`)

`tools/set_mcdx_literal.py` writes one number *inside* a formula, where `set_mcdx_value.py`
refuses the region whole. The fixture's region 0 is the smallest useful case:
`f_cd := 30 MPa / 1.5` holds two numbers of two different kinds. The tool is built for an
**agent**, so most of what is pinned here is the machinery that makes a wrong index fail
loudly instead of writing a plausible wrong number.

| Test | Pins |
|------|------|
| `test_lists_every_number_with_its_role` | The ordinals an agent will use: `[0] 30 MPa value`, `[1] 1.5 factor`. Document order of the `<ml:real>` nodes is the addressing scheme, so it is pinned explicitly |
| `test_sets_the_number_inside_the_formula` | The before/after report is the region rendered back to Python — `f_cd = 30 * ureg.MPa / 1.5` -> `/ 1.4`. This is the tool's own verification, run before it writes |
| `test_only_worksheet_xml_changes` | Every other zip part comes through byte-identical, `result.xml` above all |
| `test_edit_is_minimal` | Exactly one character differs. The expression tree is untouched, which is the whole premise |
| `test_executed_python_carries_the_new_number` | End-to-end: `30 MPa / 1.25` runs to 24 MPa. Goes back through the parser rather than asserting on XML |
| `test_expect_must_match` / `_be_a_number` | `--expect` is the guard that makes a stale index safe; a mismatch refuses before anything is written |
| `test_index_out_of_range` | The count and the valid range are named in the error, so an agent can recover without guessing |
| `test_accepts_a_negative_value` | Prime writes a negative straight into `<ml:real>` (every measurement matrix in `statistics.mcdx` does), unlike a top-level literal define, which `set_mcdx_value.py` wraps in `<ml:neg/>`. No wrapper is built here |
| `test_renames_the_unit_of_a_scaled_number` / `test_unit_needs_a_scaled_number` | `--unit` reaches only the `<ml:scale/>` form, where one unit belongs to one number. In `a / m` the unit belongs to the division |
| `test_output_leaves_the_input_alone` | `-o` writes a copy and does not touch the source |
| `test_classifies_and_gates_the_risky_kinds` (4 cases) | An `exponent` (`cm²` in `RC_torsion` r26, a power in `shrinkage` r9), an `index` (`matrices` r17) and a `display-scale` (inside `<ml:unitOverride>`) are each classified and each refused without `--allow-kind`. These change what the formula *means*, and an accidental edit there produces a plausible wrong answer rather than an error |
| `test_matrix_cells_are_editable` | `statistics.mcdx` r54's 50-cell measurement matrix lists as ordinary editable values, negatives included |
| `test_every_listed_number_reads_back` | Across `RC_col`/`matrices`/`statistics`, setting a listed number to itself is a byte-level no-op. That is what proves each ordinal addresses the span it claims to — the failure this test caught was `.87` being normalised to `0.87` |

**What these do not reach.** The `<ml:real>`-count guard (the tool refuses a region whose
element count and text count disagree, e.g. an empty `<ml:real/>`) has no fixture — no
worksheet here writes one. Prime's own re-layout of a widened region is likewise untested in
CI: it was confirmed by hand that a math region's `actualWidth` is recomputed by Prime and is
not something an editor must maintain.

## tests/test_mcdx_backend.py

Covers `mcad2py/emit/mcdx_backend.py`, the first thing in the package that *writes* worksheet
math (IR -> `math50` XML). Nothing here needs Mathcad: every input is XML Prime itself wrote.

| Test | What it pins |
|------|------|
| `test_every_supported_expression_survives_a_round_trip` (per sheet) | Parse -> emit -> parse gives the **identical IR** for every `<ml:apply>` in every fixture. The IR nodes are dataclasses, so `==` compares the whole tree |
| `test_the_sweep_reaches_real_worksheet_math` | The floor (>1000 expressions) under the sweep above, which would also pass by skipping everything |
| `test_re_emission_matches_primes_own_bytes` (per sheet) | Stronger than the round trip: the emitted XML equals Prime's, modulo the positional `label-is-contextual`, an omitted `labels="VARIABLE"`, and cosmetic `<ml:parens>`. The two constructs the IR does not carry (`<ml:percent/>`, `split=`/`inline=`) are skipped by name — see the schema note |
| `test_most_expressions_re_emit_byte_for_byte` | Over 80% are identical byte for byte, parentheses included (996 of 1124 at the time of writing) |
| `test_writes_a_quantity_the_way_prime_does` | The `<ml:apply><ml:scale/>` shape, spelled out |
| `test_a_subscripted_name_becomes_a_xaml_span` | The synthesised form, for a name the sheet has never used |
| `test_harvested_ids_keep_a_names_own_encoding` | Prime writes `m_s` two ways and the parser reads both the same, so a rewrite reuses the sheet's own `<ml:id>` bytes rather than restyling a name |
| `test_harvest_gives_up_rather_than_guess` / `test_every_sheet_yields_an_id_map` | The positional pairing of text matches to ElementTree nodes holds on every fixture; a disagreement drops the whole map instead of pairing a name with another name's XML |
| `test_parentheses_are_restored_where_prime_shows_them` (6 cases) | The parenthesising rule, including both associativity directions (`a - (b - c)`, `(a**b)**c`) |
| `test_refuses_a_literal_prime_would_not_write` (5 cases) | `2j`, `1e-05`, `0x10`, `""`, `1.2.3` — a complex literal has its own `<ml:imag>`, and a rendered float is not a form Prime writes |
| `test_refuses_a_node_outside_the_subset` / `test_refuses_a_name_mathcad_cannot_display` | The subset is a whitelist. Emitting a half-understood construct into a proprietary format is worse than refusing |
| `test_emitted_xml_splices_into_a_worksheet_and_converts` | The end-to-end proof, against Prime's own root element: re-emitting region 0 of `plain_concrete_cohesion.mcdx` reproduces the worksheet **byte for byte**, and the generated Python is unchanged. This is what pins the module's one standing assumption — that the `ml:` prefix it writes is the prefix `worksheet.xml` binds |
| `test_a_changed_expression_reaches_the_generated_python` | The same splice with an operand added: `f_cd = 0.85 * (30 * ureg.MPa / 1.5)`. The write path in miniature, minus the zip surgery and the guards a tool will add |

**What these do not reach.** No Mathcad Prime, so nothing here proves Prime *opens* a rewritten
sheet — only that our own parser reads it back identically. The byte-for-byte result on region 0
is the strongest available evidence short of Prime itself. The subset is stage A (numbers, units,
`+ - * / **`, negation, names); calls, matrices, indices, ranges and programs all raise
`Unsupported` and are skipped by the sweeps.

## tests/test_python_expr.py

Covers `mcad2py/parser/python_expr.py`, the write path's front end (Python source -> IR). Stage A
proved IR -> XML against Prime's bytes; this is the mirror proof on the other half.

| Test | What it pins |
|------|------|
| `test_generated_python_reads_back_to_the_same_ir` (per sheet) | Print every writable expression in every fixture with the ordinary code generator, read the text back, and require the **identical IR**. The round trip an agent actually performs — read the sheet as Python, type Python back |
| `test_the_sweep_is_almost_total` | 1112 of 1113 exact. The one refusal is `power(z, i)`, whose `z` is bound by an enclosing lambda and so is not a name the *sheet* defines; a lambda body is out of the write path's reach anyway |
| `test_reads_the_subset` (7 cases) | `.87` keeps its leading dot, `-3` folds into one `<ml:real>` rather than a `<ml:neg/>` wrapper, `30 * ureg.MPa` becomes a `Quantity`, and `power(a, b)` reads back as a power (what codegen prints for a fractional exponent) |
| `test_a_number_keeps_the_text_it_was_typed_as` | `repr(float(...))` would rewrite bytes for no gain, and setting a number to what it already was must be a no-op |
| `test_refuses_what_it_cannot_write` (6 cases) | A call, an index, a boolean, `%`, a string, a syntax error. The subset is a whitelist on both halves of the write path |
| `test_refuses_a_name_the_sheet_does_not_use` / `test_a_unit_must_also_be_one_the_sheet_uses` | `sanitize()` has no inverse, so a name is resolved through the sheet's own symbol table or not at all |
| `test_reconcile_keeps_a_scale_a_scale` | `30 * ureg.MPa` prints the same whether the sheet wrote `<ml:scale/>` or `<ml:mult/>`; the sheet's form is kept in both directions |
| `test_reconcile_only_keeps_what_still_matches` | Changing one operand leaves the other branch as the sheet's own node — asserted by identity, not equality |
| `test_reconcile_gives_up_on_a_different_shape` | A genuinely different formula is taken as written |
| `test_symbol_table_keys_are_the_generated_python` | The table's key is literally what the code generator printed, including for transliterated Greek names |

## tests/test_set_mcdx_formula.py

Covers `tools/set_mcdx_formula.py`, the fourth write tool and the only one that changes the maths.

| Test | What it pins |
|------|------|
| `test_reads_the_formula_in_a_region` / `test_the_span_is_the_value_only` | The replaced span is the *value* subtree: inside `<ml:eval>`, past any wrapping `<ml:parens>`, never the `<ml:define>`. The target name, the unit override and the result format keep their own bytes |
| `test_replaces_the_formula` | The before/after report is the region rendered back to Python, the tool's own verification run before it writes |
| `test_executed_python_carries_the_new_formula` | End-to-end: `f_cd` moves from 20 MPa to 17 MPa through the real parser and Pint |
| `test_can_bring_in_another_name_from_the_sheet` | A formula may grow a term; the result still runs (21 MPa) |
| `test_only_worksheet_xml_changes` / `test_everything_outside_the_formula_is_untouched` | Every other zip part is byte-identical, and so is every byte of `worksheet.xml` outside the value span |
| `test_expect_must_match` / `test_expect_ignores_only_whitespace` | `--expect` is the guard that makes a stale read safe; spacing is not worth a refusal |
| `test_refuses_what_it_cannot_write` (3 cases) | A call, an unknown name, a syntax error — refused while still text |
| `test_refuses_a_region_that_is_not_a_formula` / `test_refuses_an_unknown_region` | A text note and a missing region id both name the problem |
| `test_writing_a_formula_back_unchanged_is_a_no_op` (5 sheets) | **The strongest property available without Mathcad.** Every accepted region goes out through the code generator, back through the front end and out through the XML backend, and must land on the bytes Prime wrote |
| `test_the_no_op_sweep_reaches_most_writable_regions` | The floor: 331 regions across every fixture pass that round trip end to end |
| `test_refuses_a_region_it_cannot_reproduce` | `shrinkage.mcdx` region 9 holds `RH / 100%`, which would come back as `100/100`. The guard is generic — re-emit what is already there and compare — so it also catches the `split=` line-break hints and an author's redundant bracket |

**What these do not reach.** No Mathcad Prime, so nothing proves Prime *opens* a rewritten sheet;
the byte-for-byte no-op sweep is the strongest evidence short of Prime itself. The writable subset
is numbers, units, `+ - * / **`, negation and names the sheet already uses — no calls, matrices,
indices, ranges or programs, and no *new* Mathcad identifier.
