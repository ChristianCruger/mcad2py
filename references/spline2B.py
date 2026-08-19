"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import sin, disp, col, Seed, rnorm, index_build, arange
from mcad2py.units import ureg


N = 30

i = arange(0, N, 1)

x = index_build(i, lambda i: i / 3)
print(disp(x[i]))

q = lambda t: 5 + sin(t / 2)

Seed(2)

nz = rnorm(N + 1, 0, 0.4)

y = index_build(i, lambda i: q(x[i]) + nz[i])
print(y[i])

k2 = col(0, 5, 10)

k4 = col(0, 2.5, 5, 7.5, 10)

k5 = col(0, 2, 4, 6, 8, 10)

k8 = col(0, 1.25, 2.5, 3.75, 5, 6.25, 7.5, 8.75, 10)

k10 = col(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here

# TODO unsupported region: Spline2 -- least-squares B-spline with adaptive knot placement; Mathcad's knot-choosing rule is undocumented and not reproducible here
