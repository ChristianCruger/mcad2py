from sympy import solve, Symbol, Eq
import math
import pint
ureg = pint.UnitRegistry()

N = Symbol('N')
M = Symbol('M')
C = Symbol('C')
T = Symbol('T')
x_c = Symbol('x_c')
x_t = Symbol('x_t')

Eq(M, C * x_c - T * x_t)

Eq(N, C + T)
Eq(T, N - C)

print(solve(Eq(M, C * x_c - (N - C) * x_t) , C))


N = 115798 * ureg.kN
M = 23749 * ureg.kN * ureg.m

c = 71 * ureg.mm

w = 1.2 * ureg.m 

a_c =  500 * ureg.mm

x_t = w/2 - c
print(x_t)

x_c = w/2 - a_c/2
print(x_c)

C = (x_t * N + M) / (x_c + x_t)
print(C.to(ureg.kN))

T = N - C
print(T.to(ureg.kN))

# check:

print((C * x_c - T * x_t).to('kN*m'))