"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import power, elementwise
ureg = pint.UnitRegistry()


epsilon_cu2 = -0.0035

# if/else test

epsilon_c2 = -0.002

f_ck = 30 * ureg.MPa

P1 = 0.25 * epsilon_c2

P2 = 0.50 * epsilon_c2

P3 = 0.75 * epsilon_c2

n = 2

# statements without all cases covered, still work, aslong as the none-working branch is not called.

def sigma_c(epsilon):
    if epsilon_cu2 <= epsilon < epsilon_c2:
        return -f_ck
    if epsilon_c2 <= epsilon < 0:
        return -f_ck * (1 - power(1 - epsilon / epsilon_c2, n))
sigma_c = elementwise(sigma_c)

print(sigma_c(P3))

print(sigma_c(-P3))

# blank lines in programs ignored:

def sigma_cI(epsilon):
    if epsilon <= epsilon_cu2:
        return -f_ck
    if epsilon_cu2 <= epsilon < epsilon_c2:
        return -f_ck
    if epsilon_c2 <= epsilon < P3:
        return -f_ck - (-f_ck - sigma_c(P3)) / (epsilon_c2 - P3) * (epsilon_c2 - epsilon)
    if P3 <= epsilon < P2:
        return sigma_c(P3) - (sigma_c(P3) - sigma_c(P2)) / (P3 - P2) * (P3 - epsilon)
    if P2 <= epsilon < P1:
        return sigma_c(P2) - (sigma_c(P2) - sigma_c(P1)) / (P2 - P1) * (P2 - epsilon)
    if P1 <= epsilon < 0:
        return sigma_c(P1) / P1 * epsilon
sigma_cI = elementwise(sigma_cI)

print(sigma_cI(-0.003))
