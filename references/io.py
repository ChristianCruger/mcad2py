"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import disp
from mcad2py.units import ureg


x = 1 * ureg.m

y = 4 * ureg.m

F = 10 * ureg.MN

A = 2 * x * y

print(A)

sigma = F / A
print(disp(sigma, ureg.MPa))
