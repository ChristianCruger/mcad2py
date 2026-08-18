"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import mod, index_build, summation, total, range_sum, arange
from mcad2py.units import ureg


i = arange(0, 10, 1)

X = index_build(i, lambda i: mod(2 * i, 7))
print(X[i])

print(total(X))

A = range_sum(i, lambda i: X[i])
print(A)

print(summation(lambda j: X[j], 1, 4))

f = lambda x: x**2 + 1

print(summation(lambda j: f(j), 1, 4))

print(range_sum(i, lambda i: f(2 * i)))
