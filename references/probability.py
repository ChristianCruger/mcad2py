"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt

from mcad2py.runtime import mc_max, mc_min, disp, nth_root, ceil, floor, col, mean, stdev, histogram, dnorm, pnorm, qnorm, rnorm, dt, pt, qt, Re, cnorm, runif, dexp, pexp, qexp, rexp, dgamma, pgamma, qgamma, rgamma, dlogis, plogis, qlogis, rlogis, dcauchy, pcauchy, qcauchy, rcauchy, dgeom, pgeom, rgeom, dhypergeom, phypergeom, qhypergeom, rhypergeom, dbinom, pbinom, qbinom, rbinom, dnbinom, pnbinom, qnbinom, rnbinom, dbeta, pbeta, qbeta, rbeta, dchisq, pchisq, qchisq, rchisq, pF, qF, rF, dlnorm, plnorm, qlnorm, rlnorm, index_build, integral, summation, total, arange, sample, static_axis, plot_domain, plot_axis, plot_trace, vectorize
from mcad2py.units import ureg


# Probabilistic examples

# Example: Probability Density and Cumulative Probability Distribution

mu = 2

sigma = 1

_domain_x = plot_domain(-4.0, 6.0, 499)
_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: dnorm(x, mu, sigma), _domain_x), None)), label='dnorm(x, mu, sigma)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: pnorm(x, mu, sigma), _domain_x), None)), label='pnorm(x, mu, sigma)', color='#000000')
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: cnorm(x), _domain_x), None)), label='cnorm(x)', color='#FF0000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x')
_ax.set_ylabel('')
_ax.legend()
plt.show()

p = 0.5

q = qnorm(p, mu, sigma)
print(q)

print(integral(lambda x: x * dnorm(x, mu, sigma), -25, 25))

print(pnorm(q, mu, sigma))

i = arange(0, 1, 1)

range = index_build(i, lambda i: i)

x_75 = index_build(i, lambda i: qnorm(0.75, mu, sigma))

x_90 = index_build(i, lambda i: qnorm(0.90, mu, sigma))

x_95 = index_build(i, lambda i: qnorm(0.95, mu, sigma))

_domain_x = plot_domain(-4.0, 6.0, 499)
_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: dnorm(x, mu, sigma), _domain_x), None)), label='dnorm(x, mu, sigma)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: pnorm(x, mu, sigma), _domain_x), None)), label='pnorm(x, mu, sigma)', color='#000000')
_ax.plot(*plot_trace(plot_axis(static_axis(x_75, _domain_x), None), plot_axis(static_axis(range, _domain_x), None)), label='range', color='#FF0000')
_ax.plot(*plot_trace(plot_axis(static_axis(x_90, _domain_x), None), plot_axis(sample(lambda x: dnorm(x, mu, sigma), _domain_x), None)), label='dnorm(x, mu, sigma)', color='#008000')
_ax.plot(*plot_trace(plot_axis(static_axis(x_95, _domain_x), None), plot_axis(sample(lambda x: dnorm(x, mu, sigma), _domain_x), None)), label='dnorm(x, mu, sigma)', color='#0000FF')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Probability Distributions

# chi-squared

print(dchisq(5.5, 11))

# Use the dt function to calculate the probability density of variable t with 4 degrees of freedom, at -1.56:

print(dt(-1.56, 4))

# Cumulative Probability

print(1 - pnorm(1, 0, 1))

print(pchisq(5.6, 7))

print(pbinom(10, 15, 0.6))

print(qbinom(0.783, 15, 0.6))

print(rbinom(5, 7, 0.65))

print(dbeta(0.8, 3, 2))

print(1 - pbeta(0.8, 3, 2))

print(qbeta(0.8, 3, 2))

print(rbeta(5, 6, 0.75))

# Inverse Cumulative Probability

print(qnorm(0.95, 0, 1))

print(qt(0.99, 6))

# F-Distribution

print(qF(0.65, 4, 6))

print(pF(0.75, 5, 7))

print(qF(0.95, 9, 8))

print(rF(7, 2, 3))

# Example: Chi-Square Test for Goodness of Fit

Obs = col(12, 39, 17, 18, 9)

Exp = col(9.5, 42.75, 19, 14.25, 9.5)

print(total(Obs))

print(total(Exp))

nu = len(Obs) - 1
print(nu)

chi2 = total(vectorize((Obs - Exp)**2 / Exp))
print(disp(chi2))

alpha = 0.05

P = 1 - pchisq(chi2, nu)
print(P)

print(P >= alpha)

Χ2 = qchisq(1 - alpha, nu)
print(Χ2)

print(Χ2 > chi2)

# Accept the null hypothesis. There is evidence that the expected results fit the observations.

_domain_x = plot_domain(-10.0, 10.0, 499)
_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: dchisq(x, nu), _domain_x), None)), label='dchisq(x, nu)', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x')
_ax.set_ylabel('')
_ax.legend()
plt.show()

print(rchisq(9, 3))

# Example: T-Score of a Vector of Data

X = col(7.07, 7.1, 7, 7.01, 6.98, 7, 6.97, 7.03, 7.01, 7.08)

N = len(X)
print(N)

m_s = mean(X)
print(m_s)

s = stdev(X) * nth_root(N / (N - 1), 2)

SEM = s / nth_root(N, 2)
print(disp(SEM))

v = N - 1

alpha = 0.005

mu = 7

t = (m_s - mu) / SEM
print(disp(t))

P = 2 * (1 - pt(abs(t), v))
print(P)

print(P < alpha)

crit = abs(qt(alpha / 2, v))
print(disp(crit))

student = lambda x: Re(dt(x, v))

_domain_x = plot_domain(-10.0, 10.0, 499)
_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: student(x), _domain_x), None)), label='student(x)', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Z Score of a Vector of Data

X = col(5.791, 5.344, 7.328, 1.112, 5.926, 5.805, 3.704, 3.027, 6.763, 4.305, 4.274, 5.197, 5.937, 3.408, 4.713, 1.92, 5.98, 4.473, 2.148, 2.551, 5.437, 5.225, 4.719, 1.302, 2.126, 6.629, 6.416, 7.12, 7.176, 8.021, 4.718, 7.761, 3.397, 5.315, 4.933, 3.945, 6.342, 6.909, 1.84, 6.916, 4.762, 3.15, 2.114, 3.9, 6.79, 6.049, 7.472, 4.511, 4.945, 2.8, 3.977, 6.826, 6.485, 3.393, 2.191, 4.545, 6.16, 4.855, 3.657, 6.277, 6.526, 3.782, 5.502, 5.316, 4.743, 4.641, 3.235, 7.944, 4.461, 7.142, 8.27, 6.272, 4.052, 4.061, 3.504, 5.474, 6.291, 6.651, 4.932, 4.216, 5.586, 5.519, 5.595, 2.405, 7.436, 6.296, 4.007, 5.751, 4.864, 4.463, 4.962, 7.556, 5.735, 3.979, 5.241, 4.501, 6.467, 8.824, 7.4, 8.071)

N = len(X)
print(N)

m_s = mean(X)
print(m_s)

alpha = 0.01

sigma = 5

mu = 2

z = (m_s - mu) / (sigma / nth_root(N, 2))
print(disp(z))

P = 2 * (1 - pnorm(z, 0, 1))
print(P)

print(P >= alpha)

crit = abs(qnorm(alpha / 2, 0, 1))
print(disp(crit))

print(abs(z) < crit)

normal = lambda q: dnorm(q, 0, 1)

# Example: T-Test on Normal Means

data1 = col(22, 48, 88, 35, 7, 98, 57, 39, 76, 81)

data2 = col(55, 22, 67, 12, 45, 21, 67, 78, 83, 92)

n1 = len(data1)
print(n1)

n2 = len(data2)
print(n2)

m1 = mean(data1)
print(m1)

m2 = mean(data2)
print(m2)

s1 = stdev(data1) * nth_root(n1 / (n1 - 1), 2)
print(disp(s1))

s2 = stdev(data2) * nth_root(n2 / (n2 - 1), 2)
print(disp(s2))

nu = n1 + n2 - 2

s = nth_root(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / nu * (1 / n1 + 1 / n2), 2)
print(disp(s))

alpha = 0.01

t = (m1 - m2) / s
print(disp(t))

P = 2 * (1 - pt(abs(t), nu))
print(P)

print(P <= alpha)

crit = abs(qt(alpha / 2, nu))
print(disp(crit))

print(abs(t) > crit)

_domain_x = plot_domain(-4.0, 4.0, 499)
_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(_domain_x, None), plot_axis(sample(lambda x: dt(x, nu), _domain_x), None)), label='dt(x, nu)', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Generating Random Numbers

# Uniformly Distributed

n_set = 1 * 10**3

low = 0

high = 2

random_set = runif(n_set, low, high)

n_bins = 20

n = arange(0, n_bins, 1)

range = index_build(n, lambda n: n)

uniform = histogram(n_bins, random_set)

means = index_build(n, lambda n: n_set / n_bins)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(uniform, None)), label='range', color='#31ADC2')
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(means, None)), label='range', color='#ED1D2F')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Normally Distributed

mu = 0

sigma = 2

random_set = rnorm(n_set, mu, sigma)

lower = floor(mc_min(random_set))
print(lower)

upper = ceil(mc_max(random_set))
print(upper)

w = (upper - lower) / n_bins

x = index_build(n, lambda n: lower + w * n)

x = index_build(n, lambda n: lower + w * n)

int = x + 0.5 * w

F = index_build(n, lambda n: n_set * w * dnorm(int[n], mu, sigma))

normal = histogram(x, random_set)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(int, None), plot_axis(normal, None)), label='int', color='#662D91')
_ax.plot(*plot_trace(plot_axis(int, None), plot_axis(F, None)), label='int', color='#ED1D2F')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Exponentially Distributed

r = 0.5

random_set = rexp(n_set, r)

lower = floor(mc_min(random_set))
print(lower)

upper = ceil(mc_max(random_set))
print(upper)

w = (upper - lower) / n_bins

y = index_build(n, lambda n: lower + w * n)

y = index_build(n, lambda n: lower + w * n)

int = y + 0.5 * w

F = index_build(n, lambda n: n_set * w * dexp(int[n], r))

exponential = histogram(y, random_set)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(int, None), plot_axis(exponential, None)), label='int', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(int, None), plot_axis(F, None)), label='int', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Call functions pexp and qexp to calculate and plot the cumulative probability distribution for value x and the inverse cumulative probability distribution for value p, respectively.

Fp = index_build(n, lambda n: n_set * w * pexp(int[n], r))

Fq = index_build(n, lambda n: n_set * w * qexp(int[n] / 100, r))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(int, None), plot_axis(F, None)), label='int', color='#2E3192')
_ax.plot(*plot_trace(plot_axis(int, None), plot_axis(Fp, None)), label='int', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(int, None), plot_axis(Fq, None)), label='int', color='#068149')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Monte carlo

L = 1

S = 0.5

NSamples = 1 * 10**4

SSize = 100

i = arange(0, NSamples - 1, 1)

Means = index_build(i, lambda i: mean(rlogis(SSize, L, S)))

# Estimate the probability that the mean of a set of random numbers lies within interval [a, b].

width = 0.1

a = L - width

b = L + width

Success = summation(lambda i: a <= Means[i - 1] <= b, 1, NSamples)

Prob = Success / NSamples
print(disp(Prob))

# The probability depends on the number of data points in each sample and on the width of the interval.
# 5.Plot the plogis function to show the cumulative probability distribution of the logistic distribution. Use a horizontal marker to mark the probability level.

z = arange(0.5, 1.5, 0.6 - 0.5)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(static_axis(x, z), None), plot_axis(static_axis(plogis(x, L, S), z), None)), label='x', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(z, None), plot_axis(sample(lambda z: plogis(z, L, S), z), None)), label='plogis(z, L, S)', color='#068149')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

Lp = plogis(a, L, S)
print(Lp)

Up = plogis(b, L, S)
print(Up)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(z, None), plot_axis(sample(lambda z: plogis(z, L, S), z), None)), label='plogis(z, L, S)', color='#068149')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('z')
_ax.set_ylabel('')
_ax.legend()
plt.show()

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(static_axis(x, z), None), plot_axis(static_axis(dlogis(x, L, S), z), None)), label='x', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(z, None), plot_axis(sample(lambda z: dlogis(z, L, S), z), None)), label='dlogis(z, L, S)', color='#068149')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(z, None), plot_axis(sample(lambda z: dlogis(z, L, S), z), None)), label='dlogis(z, L, S)', color='#068149')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('z')
_ax.set_ylabel('')
_ax.legend()
plt.show()

print(qlogis(Prob, L, S))

# Example: Cauchy Distribution

f = lambda x, l, s: 1 / math.pi * (s / ((x - l)**2 + s**2))

l_0 = 0

l_1 = 2

l_2 = -2

s_0 = 1

s_1 = 1

s_2 = 1

height_0 = 1 / (math.pi * s_0)
print(disp(height_0))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(dcauchy(x, l_0, s_0), None)), label='x', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(dcauchy(x, l_1, s_0), None)), label='x', color='#068149')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(dcauchy(x, l_2, s_0), None)), label='x', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(pcauchy(x, l_0, s_0), None)), label='x', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(pcauchy(x, l_1, s_0), None)), label='x', color='#068149')
_ax.plot(*plot_trace(plot_axis(x, None), plot_axis(pcauchy(x, l_2, s_0), None)), label='x', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

l_0 = 0

l_1 = 2

l_2 = 4

s_0 = 1

s_1 = 4 * s_0

s_2 = 8 * s_0

x0 = arange(0, 1, 0.01 - 0)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(x0, None), plot_axis(sample(lambda x0: qcauchy(x0, l_0, s_0), x0), None)), label='qcauchy(x0, l_0, s_0)', color='#ED1D2F')
_ax.plot(*plot_trace(plot_axis(x0, None), plot_axis(sample(lambda x0: qcauchy(x0, l_1, s_0), x0), None)), label='qcauchy(x0, l_1, s_0)', color='#068149')
_ax.plot(*plot_trace(plot_axis(x0, None), plot_axis(sample(lambda x0: qcauchy(x0, l_2, s_0), x0), None)), label='qcauchy(x0, l_2, s_0)', color='#2E3192')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('x0')
_ax.set_ylabel('')
_ax.legend()
plt.show()

m = 50

n = arange(0, m - 1, 1)

R = rcauchy(m, l_0, s_0)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(n, None), plot_axis(sample(lambda n: R[n], n), None)), label='R[n]', color='#ED1D2F')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('n')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Gamma Distribution Functions

s = 3

x = col(7, 2, 6, 9, 11)

print(dgamma(x, s))

print(pgamma(x, s))

print(disp(qgamma(x / 100, s)))

m = 7

print(rgamma(m, s))

# Example: Geometric and Hypergeometric Distribution Functions

k = 3

q = 0.75

print(dgeom(k, q))

print(pgeom(k, q))

p = 0.85

print(pgeom(p, q))

m = 8

print(rgeom(m, q))

# Hypergeometric Distribution

a = 5

b = 4

m = 3

n = 6

print(dhypergeom(m, a, b, n))

print(phypergeom(m, a, b, n))

p = 0.85

print(qhypergeom(p, a, b, n))

print(rhypergeom(m, a, b, n))

# Example: Binomial and Negative Binomial Distributions

k = 2

n = 5

q = 0.75

print(dbinom(k, n, q))

print(pbinom(k, n, q))

p = 0.65

print(qbinom(p, n, q))

m = 3

print(rbinom(m, n, q))

# Negative Binomial Distributions

print(dnbinom(k, n, q))

print(pnbinom(k, n, q))

p = 0.65

print(qnbinom(p, n, q))

print(rnbinom(m, n, q))

q = col(0.1, 0.3, 0.5, 0.7, 0.9)

i = arange(0, len(q) - 1, 1)

P = pbinom(k, n, q)
print(P)

Pn = pnbinom(k, n, q)
print(Pn)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(i, None), plot_axis(sample(lambda i: P[i], i), None)), label='P[i]', color='#068149')
_ax.plot(*plot_trace(plot_axis(i, None), plot_axis(sample(lambda i: Pn[i], i), None)), label='Pn[i]', color='#ED1D2F')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('i')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Log Normal Distribution Functions

mu = 2

x = col(7, 3, 12, 9, 8)

sigma = 5

print(dlnorm(x, mu, sigma))

print(plnorm(x, mu, sigma))

p = 0.75

print(qlnorm(p, mu, sigma))

m = 8

print(rlnorm(m, mu, sigma))
