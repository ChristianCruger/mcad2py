"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt

from mcad2py.runtime import mc_max, col_set, matcol, histogram, Seed, rnorm, rt, rweibull, runif, rexp, rgamma, rlogis, rcauchy, rgeom, rhypergeom, rbinom, rnbinom, rbeta, rchisq, rF, rpois, index_build, arange, plot_axis, plot_trace
from mcad2py.units import ureg


# Use functions Seed and rnorm in a short program to generate identical sets of normally distributed random numbers for three iterations by resetting the Seed value.

p = 1000

mu = 0

sigma = 2

def Same(p, mu, sigma):
    M = None
    for i in arange(0, 2, 1):
        Seed(1)
        nums = rnorm(p, mu, sigma)
        M = col_set(M, i, nums)
    return M

n_bins = 20

n = arange(0, n_bins, 1)

range_ = index_build(n, lambda n: n)

q = arange(0, p - 1, 1)

S1 = index_build(q, lambda q: matcol(Same(p, mu, sigma), 1)[q])
print(S1[q])

same = histogram(n_bins, S1)

print(mc_max(same))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(range_, None), plot_axis(same, None)), label='range_', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

Seed(1)

print(runif(20, 0, 1))

print(Seed(1))

print(rnorm(1, 0, 1))

print(runif(4, 0, 1))

# Seed return value seems to be the value of the previous rng seed?

print(Seed(1))

print(Seed(1))

print(Seed(1))

print(Seed(2))

print(Seed(2))

# Different random functions:

print(Seed(1))

print(rF(1, 1, 1))

print(runif(4, 0, 1))

print(Seed(1))

print(rgeom(1, 0.5))

print(runif(4, 0, 1))

print(Seed(1))

print(rgamma(1, 0.5))

print(runif(4, 0, 1))

print(Seed(1))

print(rhypergeom(1, 0, 1, 1))

print(runif(4, 0, 1))

print(Seed(1))

print(rbeta(1, 1, 1))

print(runif(4, 0, 1))

print(Seed(1))

print(rcauchy(1, 0, 1))

print(runif(4, 0, 1))

print(Seed(1))

print(rbinom(1, 1, 0.5))

print(runif(4, 0, 1))

print(Seed(1))

print(rexp(1, 0.5))

print(runif(4, 0, 1))

print(Seed(1))

print(rchisq(1, 0.5))

print(runif(4, 0, 1))

print(Seed(1))

print(rlogis(1, 0, 1))

print(runif(4, 0, 1))

print(Seed(1))

print(rnbinom(1, 1, 0.5))

print(runif(4, 0, 1))

print(Seed(1))

print(rpois(1, 1))

print(runif(4, 0, 1))

print(Seed(1))

print(rt(1, 1))

print(runif(4, 0, 1))

print(Seed(1))

print(rweibull(1, 1))

print(runif(4, 0, 1))
