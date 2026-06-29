"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import numpy as np
import pint

from mcad2py.runtime import col, vectorize, integral, summation
ureg = pint.UnitRegistry()


# Cross section

h = 500 * ureg.mm

w = 1000 * ureg.mm

gamma_c = 1.0

gamma_s = 1.0

# Concrete properties:

f_cd = 45 * ureg.MPa / gamma_c

f_ctm = 2.9 * ureg.MPa

# creep factor:

phi = 0

E_c = 30 * ureg.GPa

epsilon_c2 = -0.0020

# Stress-strain function

def sigma_c(e):
    if e < epsilon_c2:
        return -f_cd
    elif e < 0:
        return -f_cd * (1 - (1 - e / epsilon_c2)**2)
    return 0 * ureg.MPa

# Plot:

e_plot = np.arange(-0.0035, (0.001) + (-0.00345 - -0.0035), -0.00345 - -0.0035)

# Steel

# Array of each layer

cov = 75 * ureg.mm

Ø = col(0, 25) * ureg.mm

z_s = col(h / 2 - cov - Ø[0] * 0.5, -(h / 2) + cov + Ø[1] * 0.5)
print(z_s)

s = col(150, 150) * ureg.mm

n = len(Ø)
print(n)

A_s = vectorize(Ø**2 * (math.pi / 4 * (w / s)))
print(A_s.to(ureg.mm**2))

f_yk = 500 * ureg.MPa

f_yd = f_yk / gamma_s
print(f_yd.to(ureg.MPa))

E_s = 200 * ureg.GPa

# steel stress-strain relation:

sigma_s = lambda e: np.maximum(np.minimum(E_s * e, f_yd), -f_yd)

# Strain function incl creep

epsilon = lambda z, e, k: (e + k * z) / (1 + phi)

# Stress function

sigma = lambda z, e, k: sigma_c(epsilon(z, e, k))

# Rebar force vector:

F_s = lambda e, k: vectorize(A_s * sigma_s(epsilon(z_s, e, k)))

# Internal forces:

N_int = lambda e, k: w * integral(lambda z: sigma(z, e, k), -h / 2, h / 2) + summation(lambda i: F_s(e, k)[i], 0, n - 1)

M_int = lambda e, k: w * integral(lambda z: sigma(z, e, k) * z, -h / 2, h / 2) + summation(lambda i: F_s(e, k)[i] * z_s[i], 0, n - 1)

# Gross section stiffness:

EA_g = w * h * E_c

EI_g = E_c * (1 / 12) * h**3 * w

# External forces

N_ext = -500 * ureg.kN

M_ext = -530 * ureg.kN * ureg.m

# Solve to find strain distribution matchin external forces:

# TODO unsupported region: solve block (Given/Find)

# check:

print((N_int(e_1, k_1)).to(ureg.kN))

print((M_int(e_1, k_1)).to(ureg.kN * ureg.m))

# Plot:

z_plot = np.arange(-h / 2, (h / 2) + (-h / 2 + 1 * ureg.mm - -h / 2), -h / 2 + 1 * ureg.mm - -h / 2)

# neutral axis:

x = h / 2 + e_1 / k_1
print(x.to(ureg.mm))

# Stress in steel:

print((vectorize(sigma_s(epsilon(z_s, e_1, k_1)))).to(ureg.MPa))
