"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import power, ln, log, ln0, logspace
ureg = pint.UnitRegistry()


# base 10 log (default)

# natural log

print(log(1000))

print(ln(20.086))

print(log(1000, 10))

print(log(256, 2))

# ln(0) doesnt work. ln0(0) does!

print(math.e**3)

# Mathcad reports an error here: This function is undefined at one or more points. You may be dividing by zero.
try:
    print(ln(0))
except Exception as _err:
    print('error:', _err)

print(math.exp(3))

print(ln0(0))

print(ln(-3))

print(power(math.e, math.pi * 1j) + 1)

print(logspace(1, 1000, 4))

# you can overwrite functions!!

exp = lambda x: x + 2

log = lambda x: x**2

print(exp(2))

print(log(2))
