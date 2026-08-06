"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import col, matrix, augment, stack, match, lookup, vlookup, hlookup, vhlookup, index_build_2d, arange
ureg = pint.UnitRegistry()


i = arange(0, 2, 1)

V = col(1, 2, 3)

R = matrix([5, 6, 7])

j = arange(0, 2, 1)

s = index_build_2d(i, j, lambda i, j: 1 + i**2 * j + j)
print(s)

b = 50 + s
print(b)

S = stack(matrix(['A', 'B', 'C']), s)
print(S)

W = augment(col('X', 'Y', 'Z'), s)
print(W)

M = augment(col('Ø', 'X', 'Y', 'Z'), S)
print(M)

# loopkup and return indicies of matches:

print(match(3, V))

k = match(7, R)
print(k)

print(k[0])

ij = match(3, s)
print(ij)

print(ij[0])

print(ij[1])

# Lookup index of value in matrix 1 and return value at said index of matrix 2

print(lookup(3, s, b))

print(vlookup('Y', W, 1))

print(hlookup('C', S, 2))

print(vhlookup('X', 'C', M))
