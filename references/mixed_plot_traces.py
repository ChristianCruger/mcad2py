"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import sin, col, arange, sample, static_axis, plot_axis, plot_trace
ureg = pint.UnitRegistry()


v = col(1, 2, 3)

t = arange(0, 10, 0.1 - 0)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(static_axis(2 * v, t), None), plot_axis(static_axis(v, t), None)), label='2 * v', color='#00008B')
_ax.plot(*plot_trace(plot_axis(t, None), plot_axis(sample(lambda t: sin(t), t), None)), label='sin(t)', color='#000000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()
