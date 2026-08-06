"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import cos, disp, power
ureg = pint.UnitRegistry()


# slab:

t = 200 * ureg.mm

E_c = 30 * ureg.GPa

# Soil stiffness

k = 5000 * (ureg.kPa / ureg.m)

# Analytical solution of beam on elastic foundation as per Hetenyi "Beams of elastic foundation" 11th print, 1979

lambda_ = power(3 * k / (E_c * t**3), 1 / 4)
print(disp(lambda_))

# char length:

print(lambda_**-1)

# shape functions:

D = lambda x: math.exp(-lambda_ * x) * cos(lambda_ * x)

# width of wall:

w = 300 * ureg.mm

# unit load:

q = 1 * (ureg.kN / ureg.m) / w

# [image: Image15.png]

# deflection under wall:

a = w / 2

b = w / 2

y = q / (2 * k) * (2 - D(a) - D(b))
print(disp(y, ureg.mm))

# Eq: line spring:

K = 1 * (ureg.kN / ureg.m) / y
print(disp(K, ureg.kN * ureg.m**-1 / ureg.m))
