"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import numpy as np
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import sin, augment, nth_root, disp, mc_min, mc_max, rows, cols, last, identity, diag, submatrix, matrix, det, determinant, tr, lsolve, geninv, rank, rref, cross, norm, norm1, norm2, norme, normi, cond1, cond2, conde, condi, eigenvals, eigenvec, eigenvecs, genvals, genvecs, svds, sort, reverse, mean, IsArray, IsScalar, matrow, matelem, matmul, col, arange, index_build, index_build_2d, vectorize, transpose, matcol, total, unpack, sample, plot_axis
ureg = pint.UnitRegistry()


# Matrix functions - not complete yet!

A = col(1, 2, 3, 4)

M = matrix(4, 4, 3, 2, 1, 0, 2, 3, 2, 1, 1, 2, 3, 2, 0, 1, 2, 3)

B = col(1, 1, 2, 2)

C = matmul(M, A)
print(C)

print(matmul(B, C))

print(diag(M))

# index of last (considers whether mathcad is set to index zero or 1)

print(last(A))

print(len(A))

MM = M + 2 * identity(4)
print(MM)

# Assemble matrix from vectors:

AA = augment(A, A, A)
print(AA)

print(cols(A))

print(rows(A))

col0 = matcol(M, 0)
print(col0)

row1 = matrow(M, 1)
print(row1)

elemM13 = matelem(M, 1, 3)
print(elemM13)

elemA1 = A[1]
print(elemA1)

elemB2 = matelem(B, 0, 2)
print(elemB2)

print(matelem(A, 1, 0))

# determinant:

D = det(M)
print(D)

# Max/min element of matrix/vector:

print(mc_min(M))

print(mc_max(M))

# sum of diagonal:

print(tr(MM))

print(total(diag(MM)))

# generate matrix with function:

f = lambda x, y: x**2 - y

M2 = matrix(3, 3, f)
print(M2)

# eigenvals:

e = eigenvals(M)
print(e)

print(eigenvec(M, e[0]))

print(eigenvecs(M))

# linear solve:

x = lsolve(M, A)
print(x)

print(matmul(M, x))

print(norm(x))

# submatrix

m = submatrix(MM, 2, 3, 2, 3)
print(m)

# transpose

print(transpose(A))

print(transpose(M))

# norm:

print(determinant(A))

print(determinant(M))

# elementwise:

print(vectorize(M + 10))

# Matrix normalizations and conditions

# L1:

print(norm1(M))

print(cond1(M))

# L2:

print(norm2(M))

print(cond2(M))

# euclidean:

print(norme(M))

print(conde(M))

# infinity:

print(normi(M))

print(condi(M))

# cross product

a = col(0, 1, 1)

b = col(1, 2, 1)

c = cross(a, b)
print(c)

# generalizes (psuedo) inverse matrix

Mi = geninv(M)
print(Mi)

print(matmul(Mi, A))

# rank of M:

print(rank(M))

# row-reduced echelon form:

print(rref(M))

# definitions from elements:

a1, b1, c1, d1, a2, b2, c2, d2, a3, b3, c3, d3, a4, b4, c4, d4 = tuple(unpack(M * ureg.kg))

print(b2)

print(d3)

# example: down sampling

T0 = 2 * ureg.s

fs = 16 * ureg.Hz

i = arange(0, 200, 1)

ti = index_build(i, lambda i: i / fs)
print(disp(ti[i]))

v = index_build(i, lambda i: sin(2 * math.pi * ti[i] / T0))
print(disp(v[i]))

print(len(v))

n = 28

j = arange(0, (len(v) - 1) / 28, 1)
print(disp(j))

u = index_build(j, lambda j: v[n * j])
print(u[j])

range1 = index_build(i, lambda i: i)
print(range1[i])

range2 = index_build(j, lambda j: j * n)
print(range2[j])

_fig, _ax = plt.subplots()
_ax.plot(plot_axis(range2, None), plot_axis(u, None), label='range2', color='#000000')
_ax.plot(plot_axis(range1, None), plot_axis(v, None), label='range1', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Example: Finding the Left and Right Eigenvector

A = matrix(2, 2, 3, 3, 2, -2)

V = eigenvals(A)
print(V)

lambda__0 = V[0]
print(lambda__0)

lambda__1 = V[1]
print(lambda__1)

# right (default):

R = eigenvecs(A, 'R')
print(R)

R_0 = matcol(R, 0)
print(R_0)

R_1 = matcol(R, 1)
print(R_1)

print(matmul(A, R_0))

print(lambda__0 * R_0)

print(matmul(A, R_1))

print(lambda__1 * R_1)

# Left:

L = eigenvecs(A, 'L')
print(L)

L_0 = matcol(L, 0)
print(L_0)

L_1 = matcol(L, 1)
print(L_1)

print(matmul(transpose(L_0), A))

print(lambda__0 * transpose(L_0))

print(matmul(transpose(L_1), A))

print(lambda__1 * transpose(L_1))

# Example: Covariance and Principal Component Analysis

D = matrix(26, 3, 7.5, 5.5, 7.5, 5.5, 5.5, 5.5, 5.5, 7.5, 7.5, 4.5, 5.0, 7.0, 5.0, 4.5, 5.0, 5.5, 4.5, 5.0, 5.0, 7.5, 5.0, 6.5, 7.5, 7.5, 5.0, 6.5, 12.0, 8.5, 12.0, 8.5, 9.0, 8.5, 8.5, 12.0, 12.0, 7.5, 8.0, 11.0, 8.5, 7.5, 8.0, 9.0, 7.5, 8.0, 8.0, 11.5, 8.5, 10.5, 12.0, 12.0, 8.0, 10.0, 5.5, 4.0, 5.5, 4.0, 4.5, 3.5, 4.0, 5.0, 5.5, 4.0, 4.0, 4.5, 4.0, 4.0, 3.5, 3.5, 3.5, 4.5, 4.0, 5.0, 4.0, 4.5, 5.5, 5.0, 4.0, 4.0)

# Each row of D represents one observation, each column a measured characteristic.

# Calculate the covariance matrix of the sample.

i = arange(0, rows(D) - 1, 1)
print(i)

j = arange(0, cols(D) - 1, 1)
print(j)

X = index_build_2d(i, j, lambda i, j: matelem(D, i, j) - mean(matcol(D, j)))
print(X)

S1 = matmul(transpose(X), X) / (rows(D) - 1)
print(disp(S1))

# Compute and sort the eigenvalues.

V = reverse(sort(eigenvals(S1)))
print(V)

# Compute the transform matrix.

x = index_build(j, lambda j: eigenvec(S1, V[j]))
print(x[j])

T = augment(x[0], x[1], x[2])
print(T)

# Transform the original data.

D2 = matmul(D, T)
print(D2)

# Calculate the covariance matrix of the transformed data.

i = arange(0, rows(D2) - 1, 1)
print(i)

j = arange(0, cols(D2) - 1, 1)
print(j)

X = index_build_2d(i, j, lambda i, j: matelem(D2, i, j) - mean(matcol(D2, j)))
print(X)

S2 = matmul(transpose(X), X) / (rows(D2) - 1)
print(disp(S2))

# The principal components of the data are the diagonal elements of matrix S2.

alpha = 3.456

print(IsScalar(S2))

print(IsArray(S2))

print(IsScalar(alpha))

print(IsArray(alpha))

# Example: Using genvals and genvecs Functions

M = matrix(6, 6, 7.5, 5.5, 7.5, 5.5, 5.5, 5.5, 12, 8.5, 12, 8.5, 9, 8.5, 5.5, 4, 5.5, 4, 4.5, 3.5, 5.5, 7.5, 7.5, 4.5, 5, 7, 8.5, 12, 12, 7.5, 8, 11, 4, 5, 5.5, 4, 4, 4.5)

N = matrix(6, 6, 9, 5.5, 7.5, 5.5, 9.5, 3, 13, 9, 12, 8.5, 3, 4.5, 6.5, 4, 6, 6, 4.5, 3.5, 6.5, 7.5, 7.5, 5, 3, 7, 9.5, 10, 12, 7.5, 2.5, 11, 5, 5, 5.5, 4, 4, 5)

print(eigenvals(M))

print(eigenvals(N))

print(genvals(M, N))

print(genvecs(M, N, 'L'))

# Example: Matrix Norm and Determinant Functions

M = matrix(3, 3, 1, 9, 3, 0, 5, 4, 7, 8, 2)

a_0, b_0, c_0, a_1, b_1, c_1, a_2, b_2, c_2 = tuple(unpack(M))

# Use the norm1 function to find the L1 norm of matrix M

print(norm1(M))

# Alternatively, find the L1 norm by calculating the maximum of the absolute column sums of M.

ACS_0 = abs(a_0) + abs(b_0) + abs(c_0)
print(ACS_0)

ACS_1 = abs(a_1) + abs(b_1) + abs(c_1)
print(ACS_1)

ACS_2 = abs(a_2) + abs(b_2) + abs(c_2)
print(ACS_2)

N_L1 = mc_max(ACS_0, ACS_1, ACS_2)
print(N_L1)

# Use the norm2 function to find the L2 norm of matrix M.

print(norm2(M))

# Alternatively, use the svds function to find the largest absolute singular value of matrix M.

print(svds(M))

# The svds function returns a vector of sorted singular values, so the top value is the largest singular value of matrix M.

# Use the norme function to find the Euclidean norm of matrix M.

print(norme(M))

# Alternatively, manually calculate the square root of the sum of the absolute squares of matrix M.

N_e = nth_root(abs(a_0)**2 + abs(a_1)**2 + abs(a_2)**2 + abs(b_0)**2 + abs(b_1)**2 + abs(b_2)**2 + abs(c_0)**2 + abs(c_1)**2 + abs(c_2)**2, 2)
print(N_e)

# Use the normi function to find the Infinity norm of matrix M.

print(normi(M))

# Alternatively, use the max function to manually calculate the maximum of the absolute row sums of matrix M.

ARS_0 = abs(a_0) + abs(a_1) + abs(a_2)
print(ARS_0)

ARS_1 = abs(b_0) + abs(b_1) + abs(b_2)
print(ARS_1)

ARS_2 = abs(c_0) + abs(c_1) + abs(c_2)
print(ARS_2)

N_i = mc_max(ARS_0, ARS_1, ARS_2)
print(N_i)

# Use the det function to find the determinant of matrix M.

print(det(M))

DET = a_0 * (b_1 * c_2 - b_2 * c_1) - a_1 * (b_0 * c_2 - b_2 * c_0) + a_2 * (b_0 * c_1 - b_1 * c_0)
print(DET)

# Use the norm function to find the norm of a vector containing the elements of column 0 of matrix M.

v = col(a_0, b_0, c_0)
print(v)

print(norm(v))

# Alternatively, manually calculate the norm of vector v.

N = nth_root(a_0**2 + b_0**2 + c_0**2, 2)
print(N)
