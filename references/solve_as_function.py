"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import pint

from mcad2py.runtime import cos, solve_block
ureg = pint.UnitRegistry()


def f(a, b):
    x = 3
    def _residuals_x(_x):
        x, = _x
        return [
            a * x**2 - b - (cos(x)),
        ]
    return solve_block(_residuals_x, [x])[0]

G = f(1, 3)
print(G)

a = 1

b = 3

print(cos(G))

print(a * G**2 - b)
