"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import sinh, cosh, tanh, coth, sech, csch, asinh, acosh, atanh, acoth, asech, acsch, disp
from mcad2py.units import ureg


# Hyperbolic

theta = 103.2 * ureg.deg
print(theta)

A = sinh(theta)
print(A)

B = cosh(theta)
print(B)

C = tanh(theta)
print(C)

D = coth(theta)
print(D)

print(disp((asinh(A)), ureg.deg))

print(acosh(B))

print(atanh(C))

print(acoth(D))

S = sech(2 * theta)
print(S)

print(asech(S))

T = csch(theta / 2)
print(disp(T))

print(acsch(T))
