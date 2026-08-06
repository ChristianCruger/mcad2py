"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import col, matrix, transpose, vec_set, matmul, matcol, index_build, arange, plot_axis, plot_trace
ureg = pint.UnitRegistry()


# Example: Seeded Iteration and Difference Equation

X = 700

guess = vec_set(None, 0, 30)

N = 8

i = arange(0, N, 1)

def _recur_guess(_idx, guess):
    for i in _idx:
        guess = vec_set(guess, i + 1, (guess[i] + X / guess[i]) * (1 / 2))
    return guess

guess = _recur_guess(i, guess)

print(guess)

print(guess[i]**2 - X)

i_range = index_build(i, lambda i: i)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(i_range, None), plot_axis(guess, None)), label='i_range', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Systems of Difference Equations

# Define seed values for the simultaneous iteration.

inf = vec_set(None, 0, 50)
sus = vec_set(None, 0, 2.2 * 10**4)
dec = vec_set(None, 0, 0)
rec = vec_set(None, 0, 0)

# Define the system of difference equations.

tau = arange(0, 20, 1)

tau_range = index_build(tau, lambda tau: tau)

def _recur_inf_sus_dec_rec(_idx, inf, sus, dec, rec):
    for tau in _idx:
        _step = (1 * 10**-4 * sus[tau] * inf[tau], sus[tau] - 1 * 10**-4 * sus[tau] * inf[tau], dec[tau] + 0.55 * inf[tau], rec[tau] + 0.45 * inf[tau])
        inf = vec_set(inf, tau + 1, _step[0])
        sus = vec_set(sus, tau + 1, _step[1])
        dec = vec_set(dec, tau + 1, _step[2])
        rec = vec_set(rec, tau + 1, _step[3])
    return inf, sus, dec, rec

inf, sus, dec, rec = _recur_inf_sus_dec_rec(tau, inf, sus, dec, rec)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(tau_range, None), plot_axis(inf, None)), label='tau_range', color='#00008B')
_ax.plot(*plot_trace(plot_axis(tau_range, None), plot_axis(sus, None)), label='tau_range', color='#0000FF')
_ax.plot(*plot_trace(plot_axis(tau_range, None), plot_axis(dec, None)), label='tau_range', color='#008000')
_ax.plot(*plot_trace(plot_axis(tau_range, None), plot_axis(rec, None)), label='tau_range', color='#FFA500')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Matrix Difference Equations

v_0 = col(10, 25, 15)

A = matrix([0.5, 0, 0.2], [0.25, 0.9, 0.1], [0.25, 0.1, 0.7])

# Define the iteration process.

k = arange(1, 8, 1)

k_range = index_build(k, lambda k: k)

_step = tuple(v_0)
V = vec_set(None, (0, 0), _step[0])
V = vec_set(V, (1, 0), _step[1])
V = vec_set(V, (2, 0), _step[2])

def _recur_V(_idx, V):
    for k in _idx:
        _step = tuple(matmul(A, matcol(V, k - 1)))
        V = vec_set(V, (0, k), _step[0])
        V = vec_set(V, (1, k), _step[1])
        V = vec_set(V, (2, k), _step[2])
    return V

V = _recur_V(k, V)

# Calculate the final state of the vector.

print(matcol(V, 8))

# The matrix V contains the history of the process:

print(transpose(V))
