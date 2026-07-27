"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import sin, cos, tan, cot, sec, csc, sinc, asin, acos, atan, acot, asec, acsc, atan2, angle, disp
ureg = pint.UnitRegistry()


# trigonometric functions

theta = 34 * ureg.deg
print(theta)

A = sin(theta)
print(A)

D = cos(2 * theta)
print(D)

B = tan(theta)
print(B)

C = cot(theta)
print(C)

print(disp((atan(B)), ureg.deg))

print(acot(C))

print(asin(A))

print(disp((acos(D)), ureg.deg))

E = sec(theta)
print(E)

F = csc(theta)
print(F)

print(asec(E))

print(acsc(F))

print(disp((atan2(2, 1)), ureg.deg))

print(disp((angle(3, 1)), ureg.deg))

print(sinc(theta))

print(disp(sin(theta) / theta))

print(acot(-2))

print(atan(-6))
