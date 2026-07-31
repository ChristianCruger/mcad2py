"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import sin, cos, sample, plot_domain, plot_axis
ureg = pint.UnitRegistry()


# plot without defined plotting variable

_domain_x = plot_domain(-10.0, 10.0, 499)
_fig, _ax = plt.subplots()
_ax.plot(plot_axis(_domain_x, None), plot_axis(sample(lambda x: sin(x), _domain_x), None), label='sin(x)', color='#00008B')
_ax.plot(plot_axis(sample(lambda x: x / 2, _domain_x), None), plot_axis(sample(lambda x: cos(x), _domain_x), None), label='cos(x)', color='#000000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x')
_ax.set_ylabel('')
_ax.legend()
plt.show()
