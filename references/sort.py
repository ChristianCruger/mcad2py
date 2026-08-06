"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import col, sort, reverse, csort, rsort, index_build_2d, arange
ureg = pint.UnitRegistry()


i = arange(0, 4, 1)

j = arange(0, 4, 1)

A = col(4, 3, 7, 1, 9, 6, 3, 5)

M = index_build_2d(i, j, lambda i, j: 19 - i * 4 - i**2 + i * j - 6 * j - 2 * j**2)
print(M)

print(sort(A))

print(csort(M, 4))

print(reverse(M))

print(rsort(M, 2))
