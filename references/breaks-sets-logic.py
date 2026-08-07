"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
from sympy import simplify

from mcad2py.runtime import disp, xor, element_of
from mcad2py.units import ureg


G = 10

# constant def, cannot be reassigned

# factorial

print(math.factorial(3))

A = 1 * ureg.m

B = 5 * ureg.m

# equation breaks

print(A**2 + B**2)

print(B - A)

print(A * B)

print(disp(B / A))

# Number sets

print(element_of(3, 'ℤ'))

print(element_of(3.1, 'ℤ'))

print(element_of(3.1, 'ℝ'))

print(element_of(1 + 2j, 'ℂ'))

# Rational numbers has to be evaluated symbolically:

print(simplify(element_of(math.pi, 'ℚ')))

# logic

# XOR:

print(xor(1, 1))

print(xor(0, 1))

# neq:

print(A != B)

# gt, ge, lt, le:

print(B > A)

print(B >= A)

print(B <= 5 * ureg.m)

print(B <= A)

# and:

print(1 and 1)

# or:

print(1 or 0)

# not:

print(not 0)

print(not 3)

print(not 1)

print(not -1)

# eq:

print(3 == 3)
