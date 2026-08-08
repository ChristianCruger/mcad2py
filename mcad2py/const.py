"""Mathcad's built-in physical constants, as importable Pint quantities.

Generated code names these rather than inlining their values, so a formula reads
the way the worksheet does::

    E = m * c**2                              # not m * (299792458 * ureg.m / ureg.s)**2

They behave like Mathcad's constants do: in scope from the top of the sheet, and
shadowed the moment the worksheet defines a variable of the same name -- which
is simply Python assignment, since the import sits in the module header. (Prime
keeps the two apart by *label* even then; a sheet that defines its own ``c`` and
still refers to the constant ``c`` below it is the one case where that
divergence shows. No fixture does.)

Values are the CODATA/SI numbers Prime itself caches, in **base SI units** --
which is how ``result.xml`` states them, and what makes a scaled display
override (``10⁻³⁴ kg·m²/s``) divide down to exactly Mathcad's number.

The Mathcad display name for each is in :data:`mcad2py.mapping.CONSTANTS`, which
is what maps ``ℏ`` to ``hbar`` and ``R_∞`` to ``R_inf``.
"""

from __future__ import annotations

from .units import ureg

#: Speed of light in vacuum.
c = 299792458 * ureg.m / ureg.s
#: Standard acceleration of gravity.
g = 9.80665 * ureg.m / ureg.s**2
#: Elementary charge (Mathcad spells it ``e_c``, to leave ``e`` to Euler).
e_c = 1.602176634e-19 * ureg.coulomb
#: Planck constant.
h = 6.62607015e-34 * ureg.kg * ureg.m**2 / ureg.s
#: Reduced Planck constant, Mathcad's ``ℏ``. Prime carries the rounded
#: 1.054571817e-34 rather than h/(2π), and the cache is held to it.
hbar = 1.054571817e-34 * ureg.kg * ureg.m**2 / ureg.s
#: Boltzmann constant.
k = 1.380649e-23 * ureg.kg * ureg.m**2 / (ureg.s**2 * ureg.K)
#: Atomic mass unit.
m_u = 1.66053906892e-27 * ureg.kg
#: Avogadro constant.
N_A = 6.02214076e23 / ureg.mol
#: Molar gas constant.
R = 8.314462618 * ureg.kg * ureg.m**2 / (ureg.s**2 * ureg.K * ureg.mol)
#: Rydberg constant, Mathcad's ``R_∞``.
R_inf = 10973731.56816 / ureg.m
#: Fine-structure constant (dimensionless).
alpha = 0.0072973525643
#: Euler-Mascheroni constant, Mathcad's ``γ`` (dimensionless).
gamma = 0.5772156649015329
#: Vacuum electric permittivity.
epsilon_0 = 8.8541878188e-12 * ureg.A**2 * ureg.s**4 / (ureg.kg * ureg.m**3)
#: Vacuum magnetic permeability.
mu_0 = 1.25663706127e-6 * ureg.kg * ureg.m / (ureg.s**2 * ureg.A**2)
#: Stefan-Boltzmann constant.
sigma = 5.670374419e-8 * ureg.kg / (ureg.s**3 * ureg.K**4)
#: Magnetic flux quantum.
Phi_0 = 2.067833848e-15 * ureg.weber
