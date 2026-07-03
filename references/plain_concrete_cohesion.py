"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import sin, tan, cot, nth_root, disp
ureg = pint.UnitRegistry()


f_cd = 30 * ureg.MPa / 1.5
print(disp(f_cd, ureg.MPa))

beta = 120 * ureg.deg

# internal friction angle:

phi = 37 * ureg.deg

mu = tan(phi)
print(mu)

k = (1 + sin(phi)) / (1 - sin(phi))
print(k)

# internal cohesion:

c = f_cd / (2 * nth_root(k, 2))
print(disp(c, ureg.MPa))

v = 2 / nth_root(30, 2)
print(v)

c_eff = v * c
print(disp(c_eff, ureg.MPa))

f_eff = f_cd * v
print(disp(f_eff, ureg.MPa))

p = c_eff * cot(phi) * (tan(math.pi / 4 + phi / 2)**2 * math.exp((2 * beta - math.pi) * tan(phi)) - 1)
print(disp(p, ureg.MPa))

# Semi inifinte

p = c_eff * cot(phi) * (tan(math.pi / 4 + phi / 2)**2 * math.exp(math.pi * tan(phi)) - 1)
print(disp(p, ureg.MPa))
