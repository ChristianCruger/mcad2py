"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import numpy as np
import pint

from mcad2py.runtime import ceil, disp, mc_min, mc_max, arange, index_build
ureg = pint.UnitRegistry()


# VRIDNING I BETONTVÆRSNIT
# _

# _

# Beregninger af vridning i betontværsnit i henhold til DS/EN 1992-1-1, afsnit 6.3.2.

# _

# Areal [mm2]

A = 2217000

# Styrke [MPa]       Partialk.

# Beton

f_ck = 45

gamma_c = 1.5 / 0.85

# Omkreds [mm]

u = 3501 + 2 * 250 + 1185 + 1380 + 1204
print(u)

# Armering

f_yk = 500

gamma_s = 1.15

# Antal bøjletværsnit

n_t = 1

# Antal snit

n = 1

i = arange(1, n, 1)

# Bøjlediameter  [mm]

phi_t = 16

# Betontrykvinkelen

cottheta = 2

# Vridningsmoment [kNm]

T_Ed = index_build(i, lambda i: 400)

# Dæklag [mm]

c = 75

AS1_unused = 150.49 * ureg.cm**2 - (136 * ureg.cm**2 + 62 * ureg.cm**2) / 2
print(disp(AS1_unused, ureg.mm**2))

# Diameter på længdearmering

phi = 32

# Beregninger                                                                                                                                          _

# Beregningsparametre

f_cd = f_ck / gamma_c

f_yd = f_yk / gamma_s

A_t = n_t * (math.pi / 4 * phi_t**2)
print(disp(A_t))

nu_t = 0.7 * (0.7 - f_ck / 200)

# Tværsnitsparamtre

t_ef = mc_max(A / u, 2 * (c + phi_t + phi / 2))

print(disp(t_ef / 2))

print(A)

print(u)

print(t_ef)

A_k = A - 387000

u_k = 3215 + 1061 + 1311 + 1084

print(A_k)

print(u_k)

# Bæreevne og bøjleafstand

T_Rdmax = 2 * nu_t * f_cd * t_ef * A_k * 10**-6 / (cottheta + 1 / cottheta)

A_sl = index_build(i, lambda i: T_Ed[i] * 10**6 * u_k / (2 * A_k * f_yd) * cottheta)

n_sl = index_build(i, lambda i: ceil(A_sl[i] / (math.pi / 4 * phi**2)))

s = index_build(i, lambda i: 2 * A_t * A_k * f_yd * cottheta / (T_Ed[i] * 10**6))

s_t = index_build(i, lambda i: mc_min(u / 8, s[i]))
print(disp(s_t[i]))

k = index_build(i, lambda i: T_Ed[i] / T_Rdmax)
print(disp(k[i]))

accept = index_build(i, lambda i: 'ok' if k[i] >= 0 else 'tværsnit overudnyttet')

# Resultater                                                                                                                                            _

# Nødvendig længde-     Ikke udnyttet skrå
# armering  [mm2]/antal       betonspænding         _

# Bæreevne [MPa]  Bøjleafstand [mm]_

print(T_Rdmax)

print(s_t[i])

print(A_sl[i])

print(n_sl[i])

print(1 - k[i])

print(accept[i])
