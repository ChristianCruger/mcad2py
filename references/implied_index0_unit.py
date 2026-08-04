"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import disp, stack, arange, vec_set
ureg = pint.UnitRegistry()


h = 500 * ureg.mm

def _z():
    z = None
    for i in arange(1, 10, 1):
        z = vec_set(z, i, h / 2 - (2 * i - 1) * (h / 20))
    return stack(z)
z = _z()
print(disp(z))

print(disp((z[0]), ureg.mm))
