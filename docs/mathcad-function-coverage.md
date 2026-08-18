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
| **Probability distributions** | ✅ | the `d/p/q/r` families for `norm` `t` `weibull` `unif` `exp` `gamma` `beta` `F` `chisq` `lnorm` `logis` `cauchy` `geom` `hypergeom` `binom` `nbinom` `pois`, plus `cnorm` (Mathcad-15's `pnorm(x,0,1)` alias). All apply element-wise to a vector argument | the remaining niche families, finance-adjacent (see `references/probability.mcdx`) |
| **Regression & smoothing** | 🟡 | `slope` `intercept` (least-squares line) | `line`, `regress` `loess`, `linfit` `genfit` `expfit` `logfit` `pwrfit` `sinfit`, `medsmooth` `ksmooth` `supsmooth` |
| **Complex numbers** | 🟡 | `abs` (`|z|`), the imaginary literal `i` (`<ml:imag>`), `ln`/`log` returning complex for a negative real argument, `Re` | `Im` `arg` `csgn` `signum`, conjugate |
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

## New in Mathcad Prime 12 (r12.0, April 2026)

Prime 12's release notes group the changes as **Application**, **Engine** and **Usability**
enhancements. Only some of it reaches a converter; the table below is the triage. PTC's help portal
(`support.ptc.com/help/mathcad/r12.0/en/PTC_Mathcad_Help/whatsNewMathcadPrime.html`) blocks scripted
fetches with a 403, so the detail here comes from PTC's release blog, the PTC Community release post
and third-party write-ups — **signatures and XML spellings are unverified**; confirm against a real
r12 worksheet before mapping anything.

| Prime 12 item | Group | Relevance | Status here |
|---------------|-------|-----------|-------------|
| **Function-analysis class** — `isContinuous`, `discontPoints`, `localExtrema` / `globalExtrema`, `localMinima` / `globalMinima`, `localMaxima` / `globalMaxima` | Engine | ⬜ new builtins. Symbolic: PTC says to evaluate them with `→`, so they belong with `SYMBOLIC_COMMANDS` and SymPy (`continuous_domain`, `singularities`, `solve(diff(f))`), not with the numeric path | not mapped |
| **Expression-type class** — `hasVariables`, `getVariables` | Engine | ⬜ new builtins, also symbolic (`expr.free_symbols`). Cheap to add | not mapped |
| **MultiStart** for solver functions | Engine | 🟡 a global-search option on `find` / `minerr` / `maximize` / `minimize`. Our `solve_block` already does a bounded random-restart search when `fsolve` converges without reducing the residual — the same idea. A sheet that sets MultiStart carries an extra flag we would have to read and honour | flag not parsed |
| **Optimized / non-optimized solver options** | Engine | 🟡 same shape: a per-solve-block setting in the XML | flag not parsed |
| **King Rule** for definite integrals (symbolic) | Engine | ⛔ symbolic-engine internals. Changes which closed forms Prime prints, not the worksheet XML | no action |
| **Calculus-operator improvements** — more cases for `limit`, range-summation, indefinite integral | Engine | ⬜ the *operators* are what matters: we emit `summation` and `integral`, but an indefinite integral and a `limit` operator have no IR node yet | limit and indefinite integral unsupported |
| **2D native plot** titles, axis titles, gridlines, legend | Application | 🟡 formatting attributes on an xy plot region. We render the traces; a legend and a title are a small `matplotlib` addition once the attributes are read | attributes not parsed |
| Header / footer customization, hide solve-block labels | Usability | ⛔ document presentation | no action |
| Find and replace identifiers with subscripts | Usability | ⛔ authoring only | no action |
| Performance work; back end moved from .NET Framework to .NET | — | ⛔ runtime only | no action |

Open question for the schema: whether r12 bumps the `worksheet50` / `math50` namespace version.
[`parser/namespaces.py`](../mcad2py/parser/namespaces.py) matches on **local name**, so a bump alone
should not break parsing — but nothing here has been tested against an r12 file, and there is no r12
fixture in [`references/`](../references/).

---

## Prioritized TODO (for structural-engineering worksheets)

Ranked by expected payoff × frequency in the kind of sheets this repo converts, and roughly by effort.

1. **Cubic-spline interpolation** — `cspline`/`lspline`/`pspline` + `interp`, extending the existing
   `linterp`. Maps onto `scipy.interpolate`. Common for material curves. *(The distribution-family batch
   that used to head this item is done — see `references/probability.mcdx`; only out-of-scope niche
   families remain.)*
2. **More solving** — `root` (scalar) and `polyroots`, then `minerr`/`maximize`/`minimize` (extend the
   `solve_block` machinery: `minerr` = least-squares residual, the optimizers = `scipy.optimize`).
3. **Complex-number accessors** — `Im`, `arg`, conjugate. Trivial; occasionally needed. (The imaginary
   literal, complex-valued `ln`/`log`, and `Re` already work — see `references/log-exp.mcdx` and
   `references/probability.mcdx`.)
4. **`mod`, `gcd`, `lcm`** — trivial, high-completeness-per-line. *(The trig and hyperbolic families
   that used to head this item are done — see `references/trig.mcdx` / `references/hyperbolic.mcdx`.)*
5. **Special functions** — `erf`/`erfc`, `Γ` — thin `scipy.special` wraps; occasional.
6. **Differential equations** (`odesolve`, `rkfixed`, …) — a larger effort (a solve-block-like block
   construct over `scipy.integrate.solve_ivp`). Do only when a sample needs it.
7. **Fourier** (`fft`/`ifft`) — low priority for structural work; `scipy.fft` wraps if needed.
8. **Prime 12 symbolic classes** — `hasVariables` / `getVariables`, then the function-analysis set
   (`isContinuous`, `discontPoints`, `localExtrema`…). Thin SymPy wraps on the existing `→` path, but
   worth only what a real r12 worksheet needs — see the Prime 12 section above. Do the two
   expression-type functions first; they are a few lines each.

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
- `Seed`, `runif` and `rnorm` reproduce Mathcad's stream **exactly** (the MS C runtime `rand()`, plus
  Kinderman-Monahan for the normal — see the `seed.mcdx` note in
  [mcdx-schema-notes.md](mcdx-schema-notes.md)). The other 15 `r*` functions (`rweibull`, `rt`,
  `rbinom`, …) still draw from NumPy: repeatable run-to-run, since `Seed` reseeds NumPy too, but not
  Mathcad's numbers, so a sheet built on one cannot reproduce its cached values. Each is crackable the
  same way `rnorm` was — seed, draw one value, then `runif(4,0,1)` to count the uniforms it consumed.
