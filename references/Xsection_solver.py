"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

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
        return -f_cd * (1 - (1 - e / epsilon_c2) ** 2)
    else:
        return 0 * ureg.MPa

# Plot:
def fl_range(start, stop, step):
    """helper function to generate a range of floats."""
    while start < stop:
        yield start
        start += step


e_plot = fl_range(-0.0035, 0.001, (-0.00345 - (-0.0035)))



## Actual plot here!! - maybe we add matplotlib? 


# Steel

# Array of each layer

cov = 75 * ureg.mm

Ø = [0, 25]* ureg.mm

## this doesnt seem to work with the units??
z_s = [h/2 - cov - Ø[0] * 0.5, h/2 - cov - Ø[1] * 0.5]
print(z_s)

s = [150, 150] * ureg.mm

n = len(Ø)
print(n)

A_s = Ø**2 * math.pi / 4 * w / s
print(A_s.to(ureg.mm**2))

f_yk = 500 * ureg.MPa

f_yd = f_yk / gamma_s
print(f_yd.to(ureg.MPa))

E_s = 200 * ureg.GPa

# steel stress-strain relation:

sigma_s = lambda e: max(min( E_s * e, f_yd), -f_yd)

# Strain function incl creep

epsilon = lambda z, e, k: (e + k * z) / (1 + phi)

# Stress function

sigma = lambda z, e, k: sigma_c(epsilon(z, e, k))

# Rebar force vector:

F_s = lambda e, k: A_s * sigma_s(epsilon(z_s, e, k))

# # Internal forces:

# N_int = lambda e, k: w * None  # TODO unsupported: apply/integral + None  # TODO unsupported: apply/summation

# M_int = lambda e, k: w * None  # TODO unsupported: apply/integral + None  # TODO unsupported: apply/summation

# # Gross section stiffness:

# EA_g = w * h * E_c

# EI_g = E_c * (1 / 12) * h**3 * w

# # External forces

# N_ext = -500 * ureg.kN

# M_ext = -530 * ureg.kN * ureg.m

# # Solve to find strain distribution matchin external forces:

# # check:

# print((N_int(None  # TODO unsupported: sequence)).to(ureg.kN))

# print((M_int(None  # TODO unsupported: sequence)).to(ureg.kN * ureg.m))

# # Plot:

# z_plot = None  # TODO unsupported: range

# # neutral axis:

# x = h / 2 + e_1 / k_1
# print(x.to(ureg.mm))

# # Stress in steel:

# print((None  # TODO unsupported: apply/vectorize).to(ureg.MPa))
