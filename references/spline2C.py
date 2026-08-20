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

# c1 = Spline2(x, y, 3, 0.1)
# print(c1)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# c2 = Spline2(x, y, 3, 0.2)
# print(c2)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# c3 = Spline2(x, y, 3, 0.3)
# print(c3)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# c4 = Spline2(x, y, 3, 0.4)
# print(c4)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# c5 = Spline2(x, y, 3, 0.5)
# print(c5)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# c6 = Spline2(x, y, 3, 0.6)
# print(c6)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# c7 = Spline2(x, y, 3, 0.7)
# print(c7)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# c8 = Spline2(x, y, 3, 0.8)
# print(c8)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it
