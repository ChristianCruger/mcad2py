"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint
from sympy import Eq, Symbol, solve

from mcad2py.runtime import disp
ureg = pint.UnitRegistry()


M = Symbol('M')
C = Symbol('C')
x_c = Symbol('x_c')
T = Symbol('T')
x_t = Symbol('x_t')
N = Symbol('N')

Eq(M, C * x_c - T * x_t)

Eq(N, C + T)

Eq(T, N - C)

print(solve(Eq(M, C * x_c - (N - C) * x_t), C))

N = 115798 * ureg.kN

M = 23749 * ureg.kN * ureg.m

c = 71 * ureg.mm

w = 1.2 * ureg.m

a_c = 500 * ureg.mm

x_t = w / 2 - c
print(x_t)

x_c = w / 2 - a_c / 2
print(disp(x_c, ureg.mm))

C = (x_t * N + M) / (x_t + x_c)
print(disp(C, ureg.kN))

T = N - C
print(disp(T, ureg.kN))

# check:

print(disp((C * x_c - T * x_t), ureg.kN * ureg.m))
