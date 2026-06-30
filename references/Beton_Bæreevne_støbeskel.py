"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import sin, cos
ureg = pint.UnitRegistry()


# BÆREEVNE I STØBESKEL
# _

# Beregning af støbeskel i henhold til DS/EN 1992-1-1.

# Normalkraft i støbeskel (tryk pos) [kN]

N_Sd = 0

# Beton

# Mathcad ComboBoxControl: selected "C40" (options: C12, C16, C20, C25, C30, C35, C40, C45, C50).
f_ck = 40
f_ctk = 2.5

gamma_c = 1.60

gamma_ct = 1.87

# Forskydningskraft i støbeskel [kN]

V_Sd = 31.7

# Armering

# Mathcad ComboBoxControl: selected "Ribbestål B550" (options: Ribbestål B410, Ribbestål B500, Ribbestål B550).
f_yk = 550

gamma_s = 1.32

# Lasttype

# Mathcad ComboBoxControl: selected "Dynamisk last" (options: Statisk last, Dynamisk last).
k = 0.5

# Type

# Mathcad ComboBoxControl: selected "Ru" (options: Fortandet, Ru, Jævn, Glat).
c = 0.40
mu = 0.7

# Betonareal i støbeskel [mm2]

A_j = 500 * 1000

# Armeringsvinkel i støbeskel [°]

alpha = 90

# Armeringsarealet i støbeskel [mm2]

A_s = 6.67 * 113

# Revnefølsomt støbeskel

# Mathcad ComboBoxControl: selected "Ja" (options: Ja, Nej).
revne = 'Ja'

# Beregninger                                                                                                                                        _

# Regningsmæssige
# materialeparametre

f_cd = f_ck / gamma_c

f_ctd = f_ctk / gamma_ct

f_yd = f_yk / gamma_s

nu_v = 0.7 - f_ck / 200

alpha = alpha * ureg.deg

print(f_yd)

# Normalspænding og
# forskydningsspænding

tau_Sd = 1000 * V_Sd / A_j

sigma_nd = N_Sd * 10**3 / A_j

# Armeringsforholdet og
# kohæsionen

sigma_nd = sigma_nd if sigma_nd < 0.6 * f_cd else 0.6 * f_cd

rho = A_s / A_j

c = 0 if sigma_nd < 0 else 0 if rho <= (0.02 * f_cd - sigma_nd) / f_yd and revne == 'Ja' else c

# Støbeskellets bæreevne

tau_Rd = k * c * f_ctd + mu * (rho * f_yd * sin(alpha) + sigma_nd) + rho * f_yd * cos(alpha)

tau_Rd = tau_Rd if tau_Rd < 0.5 * nu_v * f_cd else 0.5 * nu_v * f_cd

Accept_tau = 'ok' if tau_Sd < tau_Rd else 'Utilstrækkeligt bæreevne'

# Resultater                                                                                                                                          __

# Bæreevne er:

print(tau_Rd)

# i forhold til belastningen:

print(tau_Sd)

# N/mm2

print(Accept_tau)
