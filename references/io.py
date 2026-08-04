"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import disp
ureg = pint.UnitRegistry()


x = 1 * ureg.m

y = 4 * ureg.m

F = 10 * ureg.MN

A = 2 * x * y

print(A)

sigma = F / A
print(disp(sigma, ureg.MPa))
