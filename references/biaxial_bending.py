"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import arange, double_integral, solve_block, sample, plot_axis, mesh_grid, resolve_plot_grid
ureg = pint.UnitRegistry()


W = 600 * ureg.mm

H = 800 * ureg.mm

epsilon_0 = 0

kappa_x = 1 * ureg.km**-1

kappa_y = 3 * ureg.km**-1

f_cd = 30 * ureg.MPa

E_c = 33 * ureg.GPa

f_ctd = 1 * ureg.MPa

n = 2

epsilon_c2 = -(2 / 1000)

def sigma(e):
    if e > f_ctd / E_c:
        return f_ctd
    elif e > 0:
        return E_c * e
    elif e > epsilon_c2:
        return -f_cd * (1 - (1 - e / epsilon_c2)**n)
    return -f_cd

e0 = arange(1.5 * epsilon_c2, -epsilon_c2, 1.49 * epsilon_c2 - 1.5 * epsilon_c2)

_fig, _ax = plt.subplots()
_ax.plot(plot_axis(e0, 10**-3), plot_axis(sample(lambda e0: sigma(e0), e0), ureg.MPa), label='sigma(e0)', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('e0 (10**-3)')
_ax.set_ylabel('(MPa)')
_ax.legend()
plt.show()

N = lambda epsilon, kappa_x, kappa_y: double_integral(lambda x, y: sigma(epsilon + kappa_x * x + kappa_y * y), -W / 2, W / 2, -H / 2, H / 2)

M_x = lambda epsilon, kappa_x, kappa_y: double_integral(lambda x, y: sigma(epsilon + kappa_x * x + kappa_y * y) * x, -W / 2, W / 2, -H / 2, H / 2)

M_y = lambda epsilon, kappa_x, kappa_y: double_integral(lambda x, y: sigma(epsilon + kappa_x * x + kappa_y * y) * y, -W / 2, W / 2, -H / 2, H / 2)

EA = H * W * E_c

EIx = E_c * (1 / 12) * W**3 * H

EIy = E_c * (1 / 12) * H**3 * W

N_Ed = 0 * ureg.kN

M_xEd = 0 * ureg.kN * ureg.m

M_yEd = 155 * ureg.kN * ureg.m

e = N_Ed / EA
kx = M_xEd / EIx
ky = M_yEd / EIy
def _residuals_epsilon_0_kappa_x_kappa_y(_x):
    e, kx, ky = _x
    return [
        N(e, kx, ky) - (N_Ed),
        M_x(e, kx, ky) - (M_xEd),
        M_y(e, kx, ky) - (M_yEd),
    ]
epsilon_0, kappa_x, kappa_y = solve_block(_residuals_epsilon_0_kappa_x_kappa_y, [e, kx, ky])

epsilon = lambda x, y: epsilon_0 + kappa_x * x + kappa_y * y

x0 = arange(-W / (2 * ureg.mm), W / (2 * ureg.mm), -0.495 * (W / ureg.mm) - -W / (2 * ureg.mm))

y0 = arange(-H / (2 * ureg.mm), H / (2 * ureg.mm), -0.495 * (H / ureg.mm) - -H / (2 * ureg.mm))

_X, _Y, _Z, _kind = resolve_plot_grid(mesh_grid(lambda x0, y0: sigma(epsilon(x0 * mm, y0 * mm)), x0, y0))
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, ureg.MPa)
_fig, _ax = plt.subplots()
if _kind == 'scatter':
    _cs = _ax.tricontourf(_Xs, _Ys, _Zs)
    _ax.tricontour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
else:
    _cs = _ax.contourf(_Xs, _Ys, _Zs)
    _ax.contour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
plt.colorbar(_cs, ax=_ax)
plt.show()
