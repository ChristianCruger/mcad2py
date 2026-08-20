"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import col, index_build, arange
from mcad2py.units import ureg


i = arange(1, 12, 1)

x = index_build(i, lambda i: i)

print(len(x))

y = col(3, 2.5, 2, 1.5, 1.5, 2, 4, 6, 10, 14, 18, 22, 26)

print(len(y))

# b = Spline2(x, y, 3)
# print(b)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# b2 = Spline2(x, y, 3, 0.5)
# print(b2)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it

# b3 = Spline2(x, y, 3, 0.001)
# print(b3)
# TODO unsupported region: Spline2 would have to place its own knots here, and Mathcad's rule for that is not reproduced -- pass an explicit knot vector to convert it
