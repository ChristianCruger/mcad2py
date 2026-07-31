"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import sin, cos
ureg = pint.UnitRegistry()


# Concrete interface shear check

# Concrete

# Mathcad ComboBoxControl: selected "C40" (options: C12, C16, C20, C25, C30, C35, C40, C45, C50).
f_ck = 40
f_ctk = 2.5

gamma_c = 1.60

# compression in section [kN]

N_Sd = 0

gamma_ct = 1.87

V_Sd = 31.7

# Shear in casting joint [kN]

# Rebar

# Mathcad ComboBoxControl: selected "B550" (options: B410, B500, B550).
f_yk = 550

gamma_s = 1.32

# Load type

# Mathcad ComboBoxControl: selected "Dynamic" (options: Static, Dynamic).
k = 0.5

# Type

# Mathcad ComboBoxControl: selected "Fortandet" (options: Fortandet, Ru, Jævn, Smooth).
c = 0.50
mu = 0.9

# Concrete interface area [mm2]

A_j = 500 * 1000

# Rebar angle [°]

alpha = 90

# Rebar crossing interface [mm2]

A_s = 6.67 * 113

# Cracking sensitive?

# Mathcad ComboBoxControl: selected "No" (options: Yes, No).
crack = 'No'

# Design strength

f_cd = f_ck / gamma_c

f_ctd = f_ctk / gamma_ct

f_yd = f_yk / gamma_s

nu_v = 0.7 - f_ck / 200

alpha = alpha * ureg.deg

print(f_yd)

# Design stress:

tau_Sd = 1000 * V_Sd / A_j

sigma_nd = N_Sd * 10**3 / A_j

# Reinforcement ratio and cohesion:

sigma_nd = sigma_nd if sigma_nd < 0.6 * f_cd else 0.6 * f_cd

rho = A_s / A_j

c = 0 if sigma_nd < 0 else 0 if rho <= (0.02 * f_cd - sigma_nd) / f_yd and crack == 'yes' else c

# Interface capacity:

tau_Rd = k * c * f_ctd + mu * (rho * f_yd * sin(alpha) + sigma_nd) + rho * f_yd * cos(alpha)

tau_Rd = tau_Rd if tau_Rd < 0.5 * nu_v * f_cd else 0.5 * nu_v * f_cd

Accept_tau = 'ok' if tau_Sd < tau_Rd else 'Not ok!'

print(tau_Rd)

# compared with demand:

print(tau_Sd)

# N/mm2

print(Accept_tau)
