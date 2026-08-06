"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import matrix, arange, plot_axis, mesh_grid, CreateMesh, resolve_plot_grid
ureg = pint.UnitRegistry()


# Approach #1 - function of 2 ranges: (ranges cannot have units, function values can)

x0 = arange(-50, 50, -49 - -50)

y0 = arange(-50, 50, -49 - -50)

f = lambda x, y: (x**2 + y**2) * (1 * ureg.MPa)

# contour plot:

_X, _Y, _Z, _kind = resolve_plot_grid(mesh_grid(lambda x0, y0: f(x0, y0), x0, y0))
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, None)
_fig, _ax = plt.subplots()
if _kind == 'scatter':
    _cs = _ax.tricontourf(_Xs, _Ys, _Zs)
    _ax.tricontour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
else:
    _cs = _ax.contourf(_Xs, _Ys, _Zs)
    _ax.contour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
plt.colorbar(_cs, ax=_ax)
plt.show()

# 3d plot:

_X, _Y, _Z, _kind = resolve_plot_grid(mesh_grid(lambda x0, y0: f(x0, y0), x0, y0))
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, ureg.MPa)
_fig = plt.figure()
_ax = _fig.add_subplot(projection='3d')
if _kind == 'scatter':
    _ax.scatter(_Xs, _Ys, _Zs)
else:
    _ax.plot_surface(_Xs, _Ys, _Zs, cmap='viridis')
plt.show()

# approach #2 plot from 3xN matrix - x,y,z in seperate columns:

M = matrix(
    [1 * ureg.m, 1 * ureg.m, 3 * ureg.m],
    [2 * ureg.m, 1 * ureg.m, 4 * ureg.m],
    [3 * ureg.m, 1 * ureg.m, 5 * ureg.m],
    [4 * ureg.m, 1 * ureg.m, 6 * ureg.m],
    [5 * ureg.m, 2 * ureg.m, 1 * ureg.m],
    [6 * ureg.m, 2 * ureg.m, 2 * ureg.m],
    [7 * ureg.m, 2 * ureg.m, 4 * ureg.m],
    [8 * ureg.m, 2 * ureg.m, 6 * ureg.m],
    [9 * ureg.m, 3 * ureg.m, 7 * ureg.m],
    [10 * ureg.m, 3 * ureg.m, 8 * ureg.m],
)

# contour: (3xN matrix can have units, but must be the same for columns)

_X, _Y, _Z, _kind = resolve_plot_grid(M)
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, None)
_fig, _ax = plt.subplots()
if _kind == 'scatter':
    _cs = _ax.tricontourf(_Xs, _Ys, _Zs)
    _ax.tricontour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
else:
    _cs = _ax.contourf(_Xs, _Ys, _Zs)
    _ax.contour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
plt.colorbar(_cs, ax=_ax)
plt.show()

M2 = matrix(
    [1, 1, 3 * ureg.m],
    [2, 1, 4 * ureg.m],
    [3, 1, 5 * ureg.m],
    [4, 1, 6 * ureg.m],
    [5, 2, 1 * ureg.m],
    [6, 2, 2 * ureg.m],
    [7, 2, 4 * ureg.m],
    [8, 2, 6 * ureg.m],
    [9, 3, 7 * ureg.m],
    [10, 3, 8 * ureg.m],
)

# 3d (only z column can have units)

_X, _Y, _Z, _kind = resolve_plot_grid(M2)
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, None)
_fig = plt.figure()
_ax = _fig.add_subplot(projection='3d')
if _kind == 'scatter':
    _ax.scatter(_Xs, _Ys, _Zs)
else:
    _ax.plot_surface(_Xs, _Ys, _Zs, cmap='viridis')
plt.show()

# #3 from CreateMesh (i think this is what it does underthe hood for approach #1)

xlow = 0

xhigh = 10

ylow = 0

yhigh = 10

xdiv = 100

ydiv = 100

F = CreateMesh(f, xlow, xhigh, ylow, yhigh, xdiv, ydiv)
print(F)

_X, _Y, _Z, _kind = resolve_plot_grid(F)
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, None)
_fig, _ax = plt.subplots()
if _kind == 'scatter':
    _cs = _ax.tricontourf(_Xs, _Ys, _Zs)
    _ax.tricontour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
else:
    _cs = _ax.contourf(_Xs, _Ys, _Zs)
    _ax.contour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
plt.colorbar(_cs, ax=_ax)
plt.show()

_X, _Y, _Z, _kind = resolve_plot_grid(F)
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, None)
_fig = plt.figure()
_ax = _fig.add_subplot(projection='3d')
if _kind == 'scatter':
    _ax.scatter(_Xs, _Ys, _Zs)
else:
    _ax.plot_surface(_Xs, _Ys, _Zs, cmap='viridis')
plt.show()

# approach #4 from NxM matrix (indices as x/y coords)

# units supported if all the same (only applied to the z value)

A = matrix(
    [1, 1, 1, 1, 1],
    [1, 1, 2, 2, 2],
    [1, 2, 2, 2, 3],
    [2, 2, 3, 3, 3],
    [3, 3, 3, 4, 5],
) * ureg.m**2

# contour

_X, _Y, _Z, _kind = resolve_plot_grid(A)
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, ureg.m**2)
_fig, _ax = plt.subplots()
if _kind == 'scatter':
    _cs = _ax.tricontourf(_Xs, _Ys, _Zs)
    _ax.tricontour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
else:
    _cs = _ax.contourf(_Xs, _Ys, _Zs)
    _ax.contour(_Xs, _Ys, _Zs, colors='k', linewidths=0.5)
plt.colorbar(_cs, ax=_ax)
plt.show()

# 3D

_X, _Y, _Z, _kind = resolve_plot_grid(A)
_Xs, _Ys, _Zs = plot_axis(_X), plot_axis(_Y), plot_axis(_Z, None)
_fig = plt.figure()
_ax = _fig.add_subplot(projection='3d')
if _kind == 'scatter':
    _ax.scatter(_Xs, _Ys, _Zs)
else:
    _ax.plot_surface(_Xs, _Ys, _Zs, cmap='viridis')
plt.show()
