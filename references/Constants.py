"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math

from mcad2py.const import c, g, e_c, h, hbar, k, m_u, N_A, R, R_inf, alpha, gamma, epsilon_0, mu_0, sigma, Phi_0
from mcad2py.runtime import disp
from mcad2py.units import ureg


# if symbols have not been defined as something else:

# constants:

print(math.e)

print(math.pi)

print(math.inf)

# physics:

print(c)

print(g)

# elementary charge:

print(disp((e_c), ureg.pC))

# planks const:

print(disp((h), 10**-34 * (ureg.kg * ureg.m**2 / ureg.s)))

# red planks

print(disp((hbar), 10**-34 * (ureg.kg * ureg.m**2 / ureg.s)))

# boltzmann

print(disp((k), 10**-23 * (ureg.kg * ureg.m**2 / (ureg.s**2 * ureg.K))))

# atomic mass unit

print(disp((m_u), 10**-27 * ureg.kg))

# Avo's number

print(N_A)

# gas const

print(R)

# Rydberg

print(R_inf)

# fine structure const

print(alpha)

# Euler const

print(gamma)

# vacuum:

print(epsilon_0)

print(mu_0)

# Stefan-boltzmann

print(sigma)

# Mag flux

print(Phi_0)
