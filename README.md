# mcad2py

Convert PTC **Mathcad Prime** worksheets (`.mcdx`) into runnable Python — either a
**Jupyter notebook** (one region per cell, results echoed inline like Mathcad's `=`) or a
plain `.py` script. Units are preserved with [Pint](https://pint.readthedocs.io/).

A `.mcdx` file is a zip archive of XML; the math is stored as an expression tree, so the
conversion walks that tree into an intermediate representation and emits Python from it.

## Install

```bash
pip install mcad2py
```

Or from a clone, for development:

```bash
git clone https://github.com/ChristianCruger/mcad2py
cd mcad2py
pip install -e ".[dev]"
```

Requires Python 3.10+. Dependencies: `pint`, `nbformat`, `sympy`, `numpy`, `scipy`,
`matplotlib`, `Pillow`.

## Usage

```bash
# Jupyter notebook (default)
mcad2py convert worksheet.mcdx                 # -> worksheet.ipynb
mcad2py convert worksheet.mcdx -o out.ipynb

# Plain Python script
mcad2py convert worksheet.mcdx -f py           # -> worksheet.py
mcad2py convert worksheet.mcdx -o - -f py      # to stdout
```

Or from Python:

```python
from mcad2py import convert_file
print(convert_file("worksheet.mcdx", fmt="py"))
```

### Example

A Mathcad region `f_cd := 30 MPa / 1.5 =` (displayed in MPa) becomes, in a notebook cell:

```python
f_cd = 30 * ureg.MPa / 1.5
f_cd.to(ureg.MPa)        # the bare last line echoes "20 megapascal", like Mathcad's "="
```

Mathcad trig handles angle units automatically; generated code matches this via small
angle-aware helpers (`from mcad2py.runtime import sin, cos, tan, cot`), so
`tan(phi)` works whether `phi` is in `deg` or `rad`.

## What's supported

- `:=` definitions and inline `=` evaluations, with display-unit overrides
- Arithmetic, unit scaling (`30 MPa`), roots, `%`, comparisons and boolean connectives
- Constants (`π`, `e`, `∞`), Greek/subscripted identifiers (`f_cd`, `β`, `ϕ` → `f_cd`, `beta`, `phi`)
- **Vectors and matrices** — literals, 0-based indexing (including the two-subscript form),
  ranges, range-built vectors and matrices, and the full built-in family: `rows`/`cols`/`identity`/
  `augment`/`submatrix`, `det`/`lsolve`/`geninv`/`rank`/`rref`, the norm and condition sets, the
  eigen and singular-value set, `sort`/`reverse`. Mathcad's one `·` is resolved into a scalar,
  matrix or dot product by inferring shapes across the whole sheet.
- **Functions** — the complete trigonometric and hyperbolic families (angle-aware), logs,
  powers and roots, rounding, `min`/`max`, `linterp`
- **Programs** — inline and block `if`, plus multi-line imperative programs (loops, local `←`
  assignments, `return`, `try`) emitted as real Python `def`s
- **Solve blocks** — numeric Given/Find (via `scipy.optimize`), including a block that *defines a
  function*; symbolic `solve`/`simplify`/`factor`/`expand` via SymPy
- **Integrals and sums** — definite and double integrals (`scipy.integrate`), indexed Σ
- **Plots** — x-y (function and parametric), contour and 3D, rendered with matplotlib
- **Controls and tables** — ComboBox row selectors, data tables, scriptable controls (via their
  cached value), text/comment regions → markdown cells
- Images embedded from picture regions

Anything not yet handled is emitted as a clearly marked `# TODO unsupported` stub rather than
dropped, so the output always loads. See
[docs/mathcad-function-coverage.md](docs/mathcad-function-coverage.md) for the full
category-by-category map and what's next.

## Tests

The suite lives in the git repository (it is not part of the published package, since each test
converts and **executes** a real `.mcdx` fixture from `references/`):

```bash
git clone https://github.com/ChristianCruger/mcad2py
cd mcad2py
pip install -e ".[dev]"
pytest
```

Every test converts a reference worksheet, runs the generated code, and checks the computed
values against Mathcad's own cached results in that file's `result.xml`.

## Scope

Targets Mathcad **Prime** (`.mcdx`, `worksheet50`/`math50` schema). Legacy Mathcad 15
(`.xmcd`) is a future target — the parser is structured behind an intermediate representation
so a second front-end can be added without changing the code generators.

## License

MIT — see [LICENSE](LICENSE).
