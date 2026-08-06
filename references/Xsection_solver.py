"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import elementwise, mc_max, mc_min, disp, col, integral, summation, solve_block, arange, sample, plot_axis, plot_trace, vectorize
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

phi = 1

E_c = 30 * ureg.GPa

epsilon_c2 = -0.0020

# Stress-strain function

def sigma_c(e):
    if e < epsilon_c2:
        return -f_cd
    elif e < 0:
        return -f_cd * (1 - (1 - e / epsilon_c2)**2)
    return 0 * ureg.MPa
sigma_c = elementwise(sigma_c)

# Plot:

e_plot = arange(-0.0035, 0.001, -0.00345 - -0.0035)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(e_plot, 10**-3), plot_axis(sample(lambda e_plot: sigma_c(e_plot / (1 + phi)), e_plot), ureg.MPa)), label='sigma_c(e_plot / (1 + phi))', color='#000000')
_ax.plot(*plot_trace(plot_axis(e_plot, 10**-3), plot_axis(sample(lambda e_plot: sigma_c(e_plot), e_plot), ureg.MPa)), label='sigma_c(e_plot)', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('e_plot (10**-3)')
_ax.set_ylabel('(MPa)')
_ax.legend()
plt.show()

# Steel

# Array of each layer

cov = 75 * ureg.mm

Ø = col(0, 25) * ureg.mm

z_s = col(h / 2 - cov - Ø[0] * 0.5, -(h / 2) + cov + Ø[1] * 0.5)
print(disp(z_s))

s = col(150, 150) * ureg.mm

n = len(Ø)
print(n)

A_s = vectorize(Ø**2 * (math.pi / 4 * (w / s)))
print(disp(A_s, ureg.mm**2))

f_yk = 500 * ureg.MPa

f_yd = f_yk / gamma_s
print(disp(f_yd, ureg.MPa))

E_s = 200 * ureg.GPa

# steel stress-strain relation:

sigma_s = lambda e: mc_max(mc_min(E_s * e, f_yd), -f_yd)
sigma_s = elementwise(sigma_s)

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

e = N_ext / EA_g
k = M_ext / EI_g
def _residuals_e_1_k_1(_x):
    e, k = _x
    return [
        N_int(e, k) - (N_ext),
        M_int(e, k) - (M_ext),
    ]
e_1, k_1 = solve_block(_residuals_e_1_k_1, [e, k])

# check:

print(disp((N_int(e_1, k_1)), ureg.kN))

print(disp((M_int(e_1, k_1)), ureg.kN * ureg.m))

# Plot:

z_plot = arange(-h / 2, h / 2, -h / 2 + 1 * ureg.mm - -h / 2)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(sample(lambda z_plot: sigma(z_plot, e_1, k_1), z_plot), ureg.MPa), plot_axis(z_plot, None)), label='sigma(z_plot, e_1, k_1)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(sample(lambda z_plot: epsilon(z_plot, e_1, k_1), z_plot), 10**-3), plot_axis(z_plot, None)), label='epsilon(z_plot, e_1, k_1)', color='#000000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('(MPa)')
_ax.set_ylabel('z_plot')
_ax.legend()
plt.show()

# neutral axis:

x = h / 2 + e_1 / k_1
print(disp(x, ureg.mm))

# Stress in steel:

print(disp((vectorize(sigma_s(epsilon(z_s, e_1, k_1)))), ureg.MPa))
