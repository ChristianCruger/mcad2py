# Mathcad function coverage — done vs. TODO

A working inventory of PTC Mathcad Prime's built-in **function catalog** measured against what
`mcad2py` currently converts. Use it to decide what to build next and to sanity-check whether a new
sample worksheet will hit an unsupported builtin.

- PTC groups its ~400–700 built-ins into ~25 categories (Functions ribbon → *All Functions*,
  "View by Category"). The official per-function reference lives at PTC's help portal
  (`support.ptc.com/help/mathcad/<rN.0>/en/PTC_Mathcad_Help/about_built-in_functions.html` — it
  blocks scripted fetches with a 403, so open it in a browser).
- **Source of truth for what we support:** every callable we emit is one of
  [`mapping.py`](../mcad2py/mapping.py)'s `FUNCTIONS` / `SYMBOLIC_COMMANDS` or a
  [`runtime.py`](../mcad2py/runtime.py) helper listed in `RUNTIME_IMPORTS`. Nothing is handled
  elsewhere — an unmapped builtin emits a bare `Call` and would `NameError` at runtime (or land in a
  `# TODO unsupported` region). This list is exhaustive as of this writing; regenerate it from those
  three tables when it drifts.

> Scope reminder: this repo targets **structural / civil-engineering** worksheets (concrete,
> sections, EN 1992). The priorities below reflect that — spline interpolation and the remaining
> solvers matter far more here than Bessel functions or wavelets.

---

## What we already support

### Functions emitted by name (`FUNCTIONS` + runtime helpers)

| Category | Supported | Notes |
|----------|-----------|-------|
| Trigonometry | `sin` `cos` `tan` `cot` `sec` `csc` `sinc`, `asin` `acos` `atan` `acot` `asec` `acsc`, `atan2` `angle` | all runtime helpers: forward ones are **angle-aware** (deg/rad via Pint), inverses return bare radians. `atan2(x, y)` reverses Python's arg order; `angle` wraps to `[0, 2π)`; `sinc` is the *unnormalised* `sin(z)/z` |
| Hyperbolic | `sinh` `cosh` `tanh` `coth` `sech` `csch` + all six inverses | argument reduced to a pure number first (Mathcad angles are dimensionless, so `sinh(103.2 deg)` = `sinh(1.80118)`) |
| Log & exponential | `exp`, `ln`, `log` (1- and 2-arg), `ln0`, `logspace` | `ln`/`log` return a **complex** value for a negative real argument (matching Mathcad — only `ln(0)` is a genuine domain error); `ln0` avoids that one case, returning `-1e307` at `x=0` |
| Powers & roots | `sqrt`, `nth_root`, `power` | dimension-aware: a dimensioned radicand keeps its unit, a dimensionless ratio is reduced first |
| Rounding / truncation | `ceil`, `floor`, `round` (→ `mround`) | dimensionless-aware; keep a unit if dimensioned |
| Min / max | `min` `max` (element-wise `np.minimum/maximum`), `mc_min` `mc_max` (flattening reductions) | Mathcad `max/min` flatten *all* args to a scalar; the element-wise form only appears under a vectorize arrow |
| Absolute value / size | `abs`, `length` (→ `len`) | |
| Interpolation | `linterp` | unit-aware, **extrapolates** past the knots (unlike `np.interp`); arg order reversed vs. numpy |
| Vector & matrix | `rows` `cols` `last` `length`, `identity` `diag` `augment` `stack` `submatrix` `matrix(m,n,f)`, `det` `tr` `lsolve` `geninv` `rank` `rref`, `norm` `norm1` `norm2` `norme` `normi`, `cond1` `cond2` `conde` `condi`, `eigenvals` `eigenvec` `eigenvecs` `genvals` `genvecs` `svds`, `sort` `reverse` `csort` `rsort`, `mean`, `IsArray` `IsScalar` | plus the operators: `\|x\|` (determinant *or* magnitude), row extraction, `×` cross product. Linear algebra runs on magnitudes; shape/ordering helpers keep units. Eigen ordering and eigenvector signs are LAPACK's — see [mcdx-schema-notes.md](mcdx-schema-notes.md) |

### Vector / matrix & reduction helpers (runtime)

`col` / `matrix` (literal builders, column-major, unit-fused or object-array), `augment` / `stack`
(side-by-side / stacked blocks, heterogeneous units OK), `transpose`, `matmul` (unit-aware `@`;
*which* `·` is a matrix product is decided by the sheet-wide shape pass in
[`shapes.py`](../mcad2py/shapes.py)), `matcol` / `matrow` (`A^<i>` column and row extract), `matelem`
(two-subscript element read, coping with a 1-D row/column vector), `vec_set` (growable program
vectors), `index_build` / `index_build_2d` (range-indexed `X[i] :=` and `X[i, j] :=`), `unpack`
(column-major flatten for `[a b; c d] := M`), `vec_set` again for difference equations (`ir.Recurrence`
emits a sequential loop where `index_build` would evaluate elements independently), `total` (sum a
vector), `summation` (indexed Σ),
`integral` / `double_integral` (scipy `quad`/`dblquad`), `arange` (inclusive unit-aware range),
`sample` / `plot_domain` / `plot_trace` / `mesh_grid` / `CreateMesh` / `resolve_plot_grid` (plot
sampling and axis padding),
`vectorize` /
`elementwise` (the arrow), `solve_block` (Given/Find via `fsolve`).

### Symbolic (`SYMBOLIC_COMMANDS` → SymPy)

`solve`, `simplify`, `factor`, `expand`. (The `→` arrow routes to SymPy; numeric `=` routes to
scipy/numeric Python.)

### Constants & language constructs (not "functions", for completeness)

Constants: the maths set (`π`/`pi`, `e`, `∞`, Euler-Mascheroni `γ`) and the **physics set** — `c`, `g`,
`e_c`, `h`, `ℏ`, `k`, `m_u`, `N_A`, `R`, `R_∞`, `α`, `ε_0`, `μ_0`, `σ`, `Φ_0` (`references/Constants.mcdx`).
The lookup is gated on Prime's `labels="CONSTANT"`, so a worksheet's own `c`/`g`/`k`/`R` is untouched.
Constructs already handled: `:=`/`=`, `≡` (global definition, hoisted), `!` (factorial), the
comparisons `< > ≤ ≥ = ≠`, the logic set `∧ ∨ ¬ ⊕`, number-set membership `∈` (`ℕ ℤ ℚ ℝ ℂ` —
`references/breaks-sets-logic.mcdx`), units (Pint), ranges, vector/matrix
literals & 0-based indexing, **imperative programs** (loops / `←` / `return` / `try`), inline & block
`if`, **difference equations** (seeded iteration — `guess[i+1] := f(guess[i])`, systems, and matrix
recurrences), numeric **solve blocks** (`find`), symbolic solve, **plots** (xy / contour / 3D),
**controls** (ComboBox, scriptable, TextBox status), data tables, `%` (both XML spellings), transpose.
(See
[mcdx-schema-notes.md](mcdx-schema-notes.md) for the XML→IR detail.)

---

## Category-by-category status

Legend: ✅ done · 🟡 partial · ⬜ not started · ⛔ out of scope (unlikely to ever matter for this repo)

| Category | Status | Have | Missing / notable gaps |
|----------|--------|------|------------------------|
| **Trigonometric** | ✅ | sin cos tan cot sec csc sinc, asin acos atan acot asec acsc, atan2 angle | — (`acot`'s `(0, π)` branch confirmed against a cached negative argument) |
| **Hyperbolic** | ✅ | sinh cosh tanh coth sech csch + all six inverses | — |
| **Log & exponential** | ✅ | exp ln log (1- and 2-arg) ln0 logspace | — (see `references/log-exp.mcdx`) |
| **Piecewise / conditional** | 🟡 | `if` (inline + block) | `sign`/`signum`, `Φ` Heaviside, `δ` Kronecker, `ε` Levi-Civita, `until` |
| **Truncation & round-off** | 🟡 | ceil floor round | `trunc`, `Ceil/Floor/Round/Trunc(x, y)` (round-to-multiple), `mantissa` |
| **Vector & matrix** | ✅ | the full list above (see `references/matrices.mcdx`), plus the table searches `match` `lookup` `vlookup` `hlookup` `vhlookup` (see `references/stack_augment_lookup.mcdx`) | — |
| **Solving & optimization** | 🟡 | `find` (numeric), `solve` (symbolic), `lsolve` (linear systems) | `root`, `polyroots`, `minerr`, `maximize` `minimize`, `Isolve` |
| **Interpolation & prediction** | 🟡 | `linterp` | `cspline`/`pspline`/`lspline` + `interp`, `bicubic`/`bilinear`, `predict`, `sinterp` |
| **Statistics** | ✅ | mean median mode gmean hmean, var Var stdev Stdev, skew kurt, percentile Rank histogram, corr cvar, Ftest Spear kendltau kendltau2 contingtbl | — (see `references/statistics.mcdx`). Lower-case `var`/`stdev` are the *population* forms, capitalised `Var`/`Stdev` the *sample* forms |
| **Probability distributions** | 🟡 | the `d/p/q/r` families for `norm`, `t` and `weibull` | the remaining families (`binom` `pois` `unif` `exp` `gamma` `beta` `F` `chisq` `lnorm` `logis` `geom` `hypergeom` …) — each is a four-line `scipy.stats` wrap following the same pattern |
| **Regression & smoothing** | 🟡 | `slope` `intercept` (least-squares line) | `line`, `regress` `loess`, `linfit` `genfit` `expfit` `logfit` `pwrfit` `sinfit`, `medsmooth` `ksmooth` `supsmooth` |
| **Complex numbers** | 🟡 | `abs` (`|z|`), the imaginary literal `i` (`<ml:imag>`), `ln`/`log` returning complex for a negative real argument | `Re` `Im` `arg` `csgn` `signum`, conjugate |
| **Number theory & combinatorics** | ⬜ | — | `mod` `gcd` `lcm` (engineering-relevant), `combin` `permut` `!` factorial, `isprime` `fibonacci` |
| **Special functions** | ⬜ | — | `erf` `erfc`, `Γ` `lgamma`, `Ψ` digamma, `β` beta, `fhyper` |
| **Bessel functions** | ⬜ | — | `J0/J1/Jn` `Y0/Y1/Yn` `I…` `K…` `Ai` `Bi` (rare here) |
| **Differential equations** | ⬜ | — | `odesolve`, `rkfixed` `Rkadapt` `Bulstoer` `Radau` `Stiffb/r`, `sbval` `bvalfit`, `relax` `multigrid` `numol` |
| **Fourier transforms** | ⬜ | — | `fft/ifft` `FFT/IFFT` `cfft/icfft` `dft` |
| **String functions** | ⬜ | — | `concat` `num2str` `str2num` `strlen` `substr` `search` `strfind` `error` (string *literals* already work) |
| **Sorting** | ✅ | `sort` `csort` `rsort` `reverse` (also listed under vector/matrix) | — (see also `references/sort.mcdx`) |
| **Graphing helpers** | 🟡 | `CreateMesh`, plot rendering (xy/contour/3D), QuickPlot (xy plot of an undefined variable → the invented -10..10 domain) | `CreateSpace`, `polyhedron` |
| **Finance** | ⛔ | — | `fv` `pv` `npv` `irr` `pmt` `rate` … (not engineering) |
| **Image processing** | ⛔ | — | out of scope |
| **File access / data I/O** | ⛔ | — | `READPRN` `WRITEPRN` `READEXCEL` `READFILE` … (a converter shouldn't touch the filesystem the way the sheet did) |
| **Signal / wavelets / measurement** | ⛔ | — | niche for this repo |
| **Design of experiments / misc** | ⛔ | — | niche |

---

## Prioritized TODO (for structural-engineering worksheets)

Ranked by expected payoff × frequency in the kind of sheets this repo converts, and roughly by effort.

1. **The remaining distribution families** — the `d/p/q/r` set for `binom`, `pois`, `exp`, `gamma`,
   `beta`, `F`, `chisq`, … now that `norm`/`t`/`weibull` have established the pattern (a four-line
   `scipy.stats` wrap each, plus one `mapping.py` row). *(The statistics batch that used to head this
   item is done — see `references/statistics.mcdx`.)*
2. **Cubic-spline interpolation** — `cspline`/`lspline`/`pspline` + `interp`, extending the existing
   `linterp`. Maps onto `scipy.interpolate`. Common for material curves.
3. **More solving** — `root` (scalar) and `polyroots`, then `minerr`/`maximize`/`minimize` (extend the
   `solve_block` machinery: `minerr` = least-squares residual, the optimizers = `scipy.optimize`).
4. **Complex-number accessors** — `Re`, `Im`, `arg`, conjugate. Trivial; occasionally needed. (The
   imaginary literal and complex-valued `ln`/`log` already work — see `references/log-exp.mcdx`.)
5. **`mod`, `gcd`, `lcm`** — trivial, high-completeness-per-line. *(The trig and hyperbolic families
   that used to head this item are done — see `references/trig.mcdx` / `references/hyperbolic.mcdx`.)*
6. **Special functions** — `erf`/`erfc`, `Γ` — thin `scipy.special` wraps; occasional.
7. **Differential equations** (`odesolve`, `rkfixed`, …) — a larger effort (a solve-block-like block
   construct over `scipy.integrate.solve_ivp`). Do only when a sample needs it.
8. **Fourier** (`fft`/`ifft`) — low priority for structural work; `scipy.fft` wraps if needed.

Explicitly **not** planned: finance, image processing, file I/O, wavelets/signal — out of scope for a
structural worksheet converter.

### Known behavioral gaps (already noted elsewhere, repeated here for the checklist)

- `find` solve blocks work; `minerr`/`maximize`/`minimize` do **not** yet.
- `ones` is **not** a Prime builtin — `RC_col.mcdx` defines its own, which is why the generated code
  calls one. Don't add it to `mapping.py`.
- A **row** vector (`1 × N`) is a matrix, a **column** vector (`N × 1`) a 1-D array; `transpose` moves
  between them. See the schema notes — conflating the two silently misplaces `stack`/`augment` headers.
- `TOL`/`CTOL` from `calculation.xml` aren't consumed — solve uses `fsolve` defaults.
- A *branching* program applied to an array still relies on `elementwise`/`sample`; a raw
  `np.vectorize(fn)` path for the general case isn't wired.
- Scriptable-control JScript is intentionally **not** transpiled (we surface the cached `RL` value).
- The four Numerical Recipes p-values (`Spear`'s `probd`, `kendltau`/`kendltau2`'s `prob`, `Ftest`'s
  `p`) match Mathcad only to ~1e-7: it uses NR's Chebyshev `erfcc`/continued-fraction `betai`, we use
  SciPy's exact `erfc`/`betainc`. Deliberate — see [test-coverage.md](test-coverage.md).
- `rnorm`/`rweibull`/`rt` are **random**, so no sheet built on them can reproduce its cached numbers.
