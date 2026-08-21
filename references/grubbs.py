"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.runtime import col, matrix, transpose, augment, stack, matelem, Grubbs, GrubbsClassic, ThreeSigma, trim, index_build, arange
from mcad2py.units import ureg


v1 = matrix([12.1, 11.8, 12.4, 12.0, 11.9, 12.3, 12.2, 11.7, 12.5, 12.1])

v2 = matrix([11.95, 12.05, 12.35, 11.85, 12.15, 12.25, 11.75, 12.45, 12.6, 13.3])

v = stack(transpose(v1), transpose(v2))
print(v)

u2 = matrix([11.95, 12.05, 12.35, 11.85, 12.15, 12.25, 11.75, 12.45, 12.6, 12.0])

u = stack(transpose(v1), transpose(u2))
print(u)

i = arange(0, 19, 1)

x = index_build(i, lambda i: i)

print(Grubbs(v, 0.95))

print(Grubbs(v, 0.999))

print(GrubbsClassic(v, 0.95))

print(GrubbsClassic(v, 0.999))

print(ThreeSigma(v))

print(ThreeSigma(u))

vindex = col(3, 19)

print(trim(v, vindex))

M = augment(x, v)
print(M)

print(trim(M, vindex))

A = Grubbs(M, 0.95)
print(A)

print(matelem(A, 0, 0))

B = GrubbsClassic(v * ureg.m, 0.95)
print(B)

C = Grubbs(augment(v, x), 0.95)
print(C)

print(matelem(C, 0, 0))
