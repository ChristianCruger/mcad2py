"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import sin, disp, col, Seed, rnorm, Spline2, index_build, arange
from mcad2py.units import ureg


N = 30

i = arange(0, N, 1)

x = index_build(i, lambda i: i / 3)
print(disp(x[i]))

q = lambda t: 5 + sin(t / 2)

print(Seed(2))

nz = rnorm(N + 1, 0, 0.4)
print(nz)

y = index_build(i, lambda i: q(x[i]) + nz[i])
print(y[i])

k2 = col(0, 5, 10)

k4 = col(0, 2.5, 5, 7.5, 10)

k5 = col(0, 2, 4, 6, 8, 10)

k8 = col(0, 1.25, 2.5, 3.75, 5, 6.25, 7.5, 8.75, 10)

k10 = col(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

s2 = Spline2(x, y, 3, k2)
print(s2)

s4 = Spline2(x, y, 3, k4)
print(s4)

s5 = Spline2(x, y, 3, k5)
print(s5)

s8 = Spline2(x, y, 3, k8)
print(s8)

s10 = Spline2(x, y, 3, k10)
print(s10)

sq = Spline2(x, y, 2, k5)
print(sq)

# Mathcad reports an error here: The value of one of the arguments is too large.
try:
    sf = Spline2(x, y, 4, k5)
    print(sf)
except Exception as _err:
    print('error:', _err)
