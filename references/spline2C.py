"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import elementwise, disp, Seed, rnorm, index_build, arange
from mcad2py.units import ureg


N = 44

i = arange(0, N, 1)

x = index_build(i, lambda i: 4 * (i / N) + 6 * (i / N)**2)
print(disp(x[i]))

def q(t):
    if t <= 5:
        return 1 + 0.2 * t
    elif t <= 8:
        return 2 + (t - 5)**2
    return 11 - 1.5 * (t - 8)
q = elementwise(q)

print(Seed(1))

nz = rnorm(N + 1, 0, 0.85)
print(nz)

y = index_build(i, lambda i: q(x[i]) + nz[i])
print(y[i])

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here
