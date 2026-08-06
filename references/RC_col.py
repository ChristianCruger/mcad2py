"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import elementwise, mc_max, mc_min, disp, nth_root, power, mround, col, matrix, transpose, vec_set, augment, matmul, matcol, matelem, total, solve_block, arange, plot_axis, plot_trace, vectorize
ureg = pint.UnitRegistry()


# Example: Biaxial bending verification of RC column

# Column dimensions

w_c = 1.3 * ureg.m

l_c = 1.3 * ureg.m

# Foundation thickness:

t = 1.0 * ureg.m

Contour = 1 / 2 * matmul(matrix(5, 2, -1, -1, 1, 1, -1, -1, 1, 1, -1, -1), matrix(2, 2, w_c, 0, 0, l_c))

# Foundation level:

FUK = 16.5 * ureg.m

# Cover layer

cov = 45 * ureg.mm

z = 19.42 * ureg.m

# Top of column:

h_c = z - (FUK + t)
print(h_c)

# Height of column:

# Concrete properties:

f_ck = 35 * ureg.MPa

f_cd = f_ck / 1.5
print(disp(f_cd, ureg.MPa))

E_c = 30 * ureg.GPa

# Strain limits

epsilon_c2 = -2 * 10**-3

epsilon_cu = -3.5 * 10**-3

# Steel properties:

f_yk = 500 * ureg.MPa

f_yd = f_yk / 1.15

E_s = 200 * ureg.GPa

alpha = E_s / E_c
print(disp(alpha))

# Strain limits

epsilon_yd = f_yd / E_s
print(disp(epsilon_yd))

epsilon_ud = 9 / 100

# Stress-strain functions:

def sigma_c(e):
    if e > 0:
        return 0 * ureg.MPa
    elif e > epsilon_c2:
        return -f_cd * (1 - (1 - e / epsilon_c2)**2)
    return -f_cd
sigma_c = elementwise(sigma_c)

sigma_s = lambda e: mc_min(f_yd, mc_max(-f_yd, E_s * e))
sigma_s = elementwise(sigma_s)

# Stirrup:

ø_w = 12 * ureg.mm

s_w = 400 * ureg.mm

# Vertical reinforcement:

ø = 20 * ureg.mm

# Target spacing (used to calcualte number of bars)

s_x = 300 * ureg.mm

s_y = 300 * ureg.mm

n_s = col(mround(l_c / s_x), mround(w_c / s_y), mround(l_c / s_x), mround(w_c / s_y)) - 2
print(disp(n_s))

stirrup = Contour + matrix(5, 2, cov + ø_w / 2, cov + ø_w / 2, -cov - ø_w / 2, -cov - ø_w / 2, cov + ø_w / 2, cov + ø_w / 2, -cov - ø_w / 2, -cov - ø_w / 2, cov + ø_w / 2, cov + ø_w / 2)
print(disp(stirrup))

s = vectorize(col(l_c - 2 * cov - 2 * ø_w, w_c - 2 * cov - 2 * ø_w, l_c - 2 * cov - 2 * ø_w, w_c - 2 * cov - 2 * ø_w) * (1 / (n_s + 1)))
print(disp(s, ureg.mm))

def _X_s_Y_s_n():
    X = None
    Y = None
    j = 0
    for i in arange(0, n_s[0], 1):
        X = vec_set(X, j, -l_c / 2 + cov + ø_w + ø / 2 + i * s[0])
        Y = vec_set(Y, j, w_c / 2 - cov - ø_w - ø / 2)
        j = j + 1
    for i in arange(0, n_s[1], 1):
        X = vec_set(X, j, l_c / 2 - cov - ø_w - ø / 2)
        Y = vec_set(Y, j, w_c / 2 - cov - ø_w - s[1] * i - ø / 2)
        j = j + 1
    for i in arange(0, n_s[2], 1):
        X = vec_set(X, j, l_c / 2 - cov - ø_w - s[2] * i - ø / 2)
        Y = vec_set(Y, j, -w_c / 2 + cov + ø_w + ø / 2)
        j = j + 1
    for i in arange(0, n_s[3], 1):
        X = vec_set(X, j, -l_c / 2 + cov + ø_w + ø / 2)
        Y = vec_set(Y, j, -w_c / 2 + cov + ø_w + s[3] * i + ø / 2)
        j = j + 1
    return col(X, Y, j)
X_s, Y_s, n = tuple(_X_s_Y_s_n())

# Actual spacing on each face:

print(disp((s), ureg.mm))

# Total number of vertical bars:

print(n)

# Area:

A_c = w_c * l_c
print(A_c)

def _A_s():
    A = None
    for i in arange(0, n - 1, 1):
        A = vec_set(A, i, ø**2 * (math.pi / 4))
    return A
A_s = _A_s()

# Moment of inertia:

Iy = 1 / 12 * w_c * l_c**3

Ix = 1 / 12 * w_c**3 * l_c

# The cross section is divided into 10x10 fibers to solve the biaxial problem

# Division:

n_x = 10

n_y = 10

# Size of each fiber:

dy = w_c / n_y
print(disp(dy, ureg.mm))

dx = l_c / n_x
print(disp(dx, ureg.mm))

A_ci = dx * dy
print(A_ci)

def _X_c_Y_c():
    Y = None
    X = None
    for i in arange(0, n_x - 1, 1):
        for j in arange(0, n_y - 1, 1):
            Y = vec_set(Y, i + j * n_x, -w_c / 2 + (j + 0.5) * dy)
            X = vec_set(X, i + j * n_x, -l_c / 2 + (i + 0.5) * dx)
    return col(X, Y)
X_c, Y_c = tuple(_X_c_Y_c())

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(matcol(Contour, 0), ureg.mm), plot_axis(matcol(Contour, 1), ureg.mm)), label='matcol(Contour, 0)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(matcol(stirrup, 0), ureg.mm), plot_axis(matcol(stirrup, 1), ureg.mm)), label='matcol(stirrup, 0)', color='#932329')
_ax.plot(*plot_trace(plot_axis(X_s, ureg.mm), plot_axis(Y_s, ureg.mm)), label='X_s', color='#932329')
_ax.plot(*plot_trace(plot_axis(X_c, ureg.mm), plot_axis(Y_c, ureg.mm)), label='X_c', color='#A1A3A6')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('(mm)')
_ax.set_ylabel('(mm)')
_ax.legend()
plt.show()

# Center of each sub-division fiber shown as grey marker:

# Forces

LS = col('ULS', 'ULS', 'ULS', 'ULS', 'ALS', 'ALS', 'ULS', 'ULS', 'ULS', 'ULS', 'ULS', 'ULS')

ID = col('Col1', 'Col1', 'Col1', 'Col1', 'Col1', 'Col1', 'Col1', 'Col1', 'Col1', 'Col1', 'Col1', 'Col1')

Side = col('North', 'South', 'North', 'South', 'North', 'South', 'North', 'South', 'North', 'South', 'North', 'South')

Case = col('Phase1', 'Phase1', 'Phase1', 'Phase1', 'Phase1', 'Phase1', 'Phase2', 'Phase2', 'Phase3', 'Phase3', 'Phase3', 'Phase3')

WindDir = col('NorthToSouth', 'NorthToSouth', 'SouthToNorth', 'SouthToNorth', '-', '-', '-', '-', 'NorthToSouth', 'NorthToSouth', 'SouthToNorth', 'SouthToNorth')

Fz = col(1819, 1853, 1850, 1822, 2669, 3036, 8041, 8333, 3945, 4847, 4762, 4030) * ureg.kN

Fy = col(637, 637, 637, 637, 0, 0, 226, 226, 256, 256, 256, 256) * ureg.kN

Fx = col(0, 0, 0, 0, 0, 0, 776, 805, 0, 0, 0, 0) * ureg.kN

# Weight of column:

G_c = w_c * l_c * h_c * (25 * (ureg.kN / ureg.m**3))
print(disp(G_c, ureg.kN))

# Second order effects and imperfections

# Effective height (Assumption based on cantilever with elastic rotation stiffness)

l_0 = h_c * 3

# Slenderness:

I_c = mc_min(Ix, Iy)

i = nth_root(I_c / A_c, 2)
print(disp(i))

lambda_ = l_0 / i
print(disp(lambda_))

# Limiting Slenderness:

A = 0.7

B = 1.1

C = 0.7

n_0 = mc_max(Fz) / (A_c * f_cd)
print(disp(n_0))

lambda__lim = 20 * A * B * C / nth_root(n_0, 2)
print(disp(lambda__lim))

print('lambda_ < lambda__lim', lambda_ < lambda__lim, 'Effects can be neglected!')

# Imperfections:

theta_0 = 1 / 200

alpha_m = 1

alpha_h = mc_min(2 / nth_root(h_c * (1 / ureg.m), 2), 1)
print(disp(alpha_h))

theta_i = theta_0 * alpha_h * alpha_m
print(theta_i)

e_i = theta_i * l_0 / 2
print(disp(e_i, ureg.mm))

# Placement tolerance for temporary bearings (assumption):

e_tol = 50 * ureg.mm

# 3.2 Design forces at base

# Normal force incl self weight:

# Bending moment incl imperfections and tolerance

N = -Fz - G_c
print(disp(N, ureg.kN))

M_x = Fy * h_c - (e_i + e_tol) * N
print(disp(M_x, ureg.kN))

M_y = Fx * h_c - (e_i + e_tol) * N
print(disp(M_y, ureg.kN))

# Shear force:

V_x = Fx

V_y = Fy

# 4 Biaxial problem

# Forces in each bar and concrete fiber as a function of strain and section curvature:

F_si = lambda e, kx, ky: vectorize(A_s * sigma_s(e + kx * X_s + ky * Y_s))

F_ci = lambda e, kx, ky: vectorize(A_ci * sigma_c(e + kx * X_c + ky * Y_c))

# Internal forces in section for given strain parameters:

N_int = lambda e, kx, ky: total(F_ci(e, kx, ky)) + total(F_si(e, kx, ky))

M_x_int = lambda e, kx, ky: total(vectorize(F_ci(e, kx, ky) * Y_c)) + total(vectorize(F_si(e, kx, ky) * Y_s))

M_y_int = lambda e, kx, ky: total(vectorize(F_ci(e, kx, ky) * X_c)) + total(vectorize(F_si(e, kx, ky) * X_s))

# Solve equilibrium to find strain profile:

def solve_strain(N, Mx, My):
    e = N / (A_c * E_c)
    kx = My / (Iy * E_c)
    ky = Mx / (Ix * E_c)
    def _residuals_e_kx_ky(_x):
        e, kx, ky = _x
        return [
            N_int(e, kx, ky) - (N),
            M_x_int(e, kx, ky) - (-Mx),
            M_y_int(e, kx, ky) - (-My),
        ]
    return solve_block(_residuals_e_kx_ky, [e, kx, ky])

def ones(n):
    A = None
    for i in arange(0, n - 1, 1):
        A = vec_set(A, i, 1)
    return A
ones = elementwise(ones)

# Concrete corner strains:

epsilon_c = lambda e, kx, ky: matmul(matrix(4, 3, 1, 1, 1, 1, -l_c / 2, -l_c / 2, l_c / 2, l_c / 2, -w_c / 2, w_c / 2, -w_c / 2, w_c / 2), col(e, kx, ky))

# Rebar strain:

epsilon_s = lambda e, kx, ky: matmul(augment(ones(n), X_s, Y_s), col(e, kx, ky))

# Utilization functions:

UR_c = lambda epsilon_c: mc_min(epsilon_c) / epsilon_cu

UR_s = lambda epsilon_s: mc_max(epsilon_s) / epsilon_ud

# 4.1 Loop through all load cases

# All load cases are looped through - the equilibrium strain profile is calculated and saved in the E matrix, and the resulting utilizations are found.The load cases with maximum tensile and compressive utlizations are saved and shown below

def _UR_c_max_i_c_UR_s_max_i_s_ERR_E():
    E = None
    i_c = -1
    UR_c_max = 0
    i_s = -1
    UR_s_max = 0
    for j in arange(0, len(Case) - 1, 1):
        try:
            e = solve_strain(N[j], M_x[j], M_y[j])
            E = vec_set(E, j, e)
            ec = epsilon_c(e[0], e[1], e[2])
            es = epsilon_s(e[0], e[1], e[2])
            UR_ci = UR_c(ec)
            UR_si = UR_s(es)
            if UR_ci > UR_c_max:
                UR_c_max = UR_ci
                i_c = j
            if UR_si > UR_s_max:
                UR_s_max = UR_si
                i_s = j
        except Exception:
            return transpose(matrix(1, 6, 9.99, j, 9.99, j, 1, E))
    return transpose(matrix(1, 6, UR_c_max, i_c, UR_s_max, i_s, 0, E))
UR_c_max, i_c, UR_s_max, i_s, ERR, E = tuple(_UR_c_max_i_c_UR_s_max_i_s_ERR_E())
print([UR_c_max, i_c, UR_s_max, i_s, ERR, E])

print('ERR == 0', ERR == 0, 'Solved without errors')

print('mc_max(UR_c_max, UR_s_max) < 1', mc_max(UR_c_max, UR_s_max) < 1, 'All loadcases pass!')

# 4.2 Critical load cases

# 4.2.1 Maximum compression case:

# neural axis (found by solving strain = 0 on each boundary)

# Critical case nr:

j = i_c
print(j)

def Neutral(e, kx, ky):
    Ans = None
    y = -e / ky + l_c / 2 * (kx / ky)
    j = 0
    if y >= -w_c / 2 and y <= w_c / 2:
        Ans = vec_set(Ans, (j, 0), -l_c / 2)
        Ans = vec_set(Ans, (j, 1), y)
        j = j + 1
    y = -e / ky - l_c / 2 * (kx / ky)
    if y > -w_c / 2 and y < w_c / 2:
        Ans = vec_set(Ans, (j, 0), l_c / 2)
        Ans = vec_set(Ans, (j, 1), y)
        j = j + 1
    x = -e / kx + w_c / 2 * (ky / kx)
    if x >= -l_c / 2 and x <= l_c / 2:
        Ans = vec_set(Ans, (j, 0), x)
        Ans = vec_set(Ans, (j, 1), -w_c / 2)
        j = j + 1
    x = -e / kx - w_c / 2 * (ky / kx)
    if x > -l_c / 2 and x < l_c / 2:
        Ans = vec_set(Ans, (j, 0), x)
        Ans = vec_set(Ans, (j, 1), w_c / 2)
        j = j + 1
    return Ans

# Case info:

print(LS[j])

print(ID[j])

print(Side[j])

print(Case[j])

print(WindDir[j])

# Section forces (incl imperfections):

print(disp((N[j]), ureg.kN))

print(disp((M_x[j]), ureg.kN * ureg.m))

print(disp((M_y[j]), ureg.kN * ureg.m))

# Resulting strain parameters:

e, kx, ky = tuple(E[j])
print([e, kx, ky])

NA = Neutral(e, kx, ky)
print(NA)

# find location of resultants:

t_only = lambda x: mc_max(0, x)
t_only = elementwise(t_only)

c_only = lambda x: mc_min(0, x)
c_only = elementwise(c_only)

# Concrete strains/stress at corners:

e_c = epsilon_c(e, kx, ky)
print(e_c)

print(disp((vectorize(sigma_c(e_c))), ureg.MPa))

T = lambda e, kx, ky: total(vectorize(t_only(F_si(e, kx, ky))))

C = lambda e, kx, ky: total(vectorize(c_only(F_ci(e, kx, ky)))) + total(vectorize(c_only(F_si(e, kx, ky))))

print(disp((mc_min(vectorize(sigma_c(e_c)))), ureg.MPa))

CG = lambda e, kx, ky: matrix(2, 2, total(vectorize(t_only(F_si(e, kx, ky)) * X_s)) / T(e, kx, ky), (total(vectorize(c_only(F_ci(e, kx, ky)) * X_c)) + total(vectorize(c_only(F_si(e, kx, ky)) * X_s))) / C(e, kx, ky), total(vectorize(t_only(F_si(e, kx, ky)) * Y_s)) / T(e, kx, ky), (total(vectorize(c_only(F_ci(e, kx, ky)) * Y_c)) + total(vectorize(c_only(F_si(e, kx, ky)) * Y_s))) / C(e, kx, ky))

# Strain/stress in rebar:

e_s = epsilon_s(e, kx, ky)
print(e_s)

print(vectorize(sigma_s(e_s)))

CGi = CG(e, kx, ky)
print(CGi)

print(disp((mc_max(vectorize(sigma_s(e_s)))), ureg.MPa))

def z(e, kx, ky):
    X = CG(e, kx, ky)
    return nth_root((matelem(X, 1, 0) - matelem(X, 0, 0))**2 + (matelem(X, 1, 1) - matelem(X, 0, 1))**2, 2)

# Utilizations (in terms of strain limits):

print(UR_c(e_c))

print(UR_s(e_s))

# Cross section w/ resulting neutral axis (green dash) and location of Compression/Tension resultants (purple stars, lever arm shown dash between resultants):

A_stx = lambda e, kx, ky: t_only(F_si(e, kx, ky)) / t_only(vectorize(sigma_s(epsilon_s(e, kx, ky))))

print(disp((z(e, kx, ky)), ureg.mm))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(matcol(Contour, 0), ureg.mm), plot_axis(matcol(Contour, 1), ureg.mm)), label='matcol(Contour, 0)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(X_s, ureg.mm), plot_axis(Y_s, ureg.mm)), label='X_s', color='#932329')
_ax.plot(*plot_trace(plot_axis(matcol(NA, 0), ureg.mm), plot_axis(matcol(NA, 1), ureg.mm)), label='matcol(NA, 0)', color='#068149')
_ax.plot(*plot_trace(plot_axis(matcol(CGi, 0), ureg.mm), plot_axis(matcol(CGi, 1), ureg.mm)), label='matcol(CGi, 0)', color='#662D91')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('(mm)')
_ax.set_ylabel('(mm)')
_ax.legend()
plt.show()

print(disp((T(e, kx, ky)), ureg.kN))

print(disp((C(e, kx, ky)), ureg.kN))

print(A_stx(e, kx, ky))

# 4.2.1 Maximum tension case:

# Critical case nr:

j = i_s
print(j)

# Case info:

print(LS[j])

print(ID[j])

print(Side[j])

print(Case[j])

print(WindDir[j])

# Section forces (incl imperfections):

print(disp((N[j]), ureg.kN))

print(disp((M_x[j]), ureg.kN * ureg.m))

print(disp((M_y[j]), ureg.kN * ureg.m))

# Resulting strain parameters:

e, kx, ky = tuple(E[j])
print([e, kx, ky])

NA = Neutral(e, kx, ky)
print(NA)

# Concrete strains/stress at corners:

e_c = epsilon_c(e, kx, ky)
print(e_c)

print(disp((vectorize(sigma_c(e_c))), ureg.MPa))

CGi = CG(e, kx, ky)
print(CGi)

print(disp((mc_min(vectorize(sigma_c(e_c)))), ureg.MPa))

# Strain/stress in rebar:

e_s = epsilon_s(e, kx, ky)
print(e_s)

print(vectorize(sigma_s(e_s)))

print(disp((mc_max(vectorize(sigma_s(e_s)))), ureg.MPa))

# Utilizations (in terms of strain limits):

print(UR_c(e_c))

print(UR_s(e_s))

# Cross section w/ resulting neutral axis (green dash) for applied forced and location of Compression/Tension resultants (purple stars, lever arm shown dash between resultants):

print(disp((z(e, kx, ky)), ureg.mm))

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(matcol(Contour, 0), ureg.mm), plot_axis(matcol(Contour, 1), ureg.mm)), label='matcol(Contour, 0)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(X_s, ureg.mm), plot_axis(Y_s, ureg.mm)), label='X_s', color='#932329')
_ax.plot(*plot_trace(plot_axis(matcol(NA, 0), ureg.mm), plot_axis(matcol(NA, 1), ureg.mm)), label='matcol(NA, 0)', color='#068149')
_ax.plot(*plot_trace(plot_axis(matcol(CGi, 0), ureg.mm), plot_axis(matcol(CGi, 1), ureg.mm)), label='matcol(CGi, 0)', color='#662D91')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('(mm)')
_ax.set_ylabel('(mm)')
_ax.legend()
plt.show()

print(disp((T(e, kx, ky)), ureg.kN))

print(disp((C(e, kx, ky)), ureg.kN))

# 5 Shear verification

# Shear resultant:

V = vectorize(nth_root(V_x**2 + V_y**2, 2))
print(disp(V, ureg.kN))

# Effective depth

d = l_c - cov - ø_w - ø / 2
print(disp(d, ureg.mm))

# Shear width

b_w = w_c

# Number of tensile bars:

n_t = mround(w_c / s_y)
print(disp(n_t))

# Area of reinforcement in tension

A_st = n_t * ø**2 * (math.pi / 4)
print(disp(A_st))

# Reinforcement ratio:

rho = mc_min(0.02, A_st / (b_w * d))
print(disp(rho))

# Compression in section:

sigma_cp = vectorize(-N / A_c)
print(disp(sigma_cp, ureg.MPa))

# Size factor:

k = mc_min(2, 1 + nth_root(200 * ureg.mm / d, 2))
print(disp(k))

# Shear strenth parameters:

C_Rdc = 0.18 / 1.5 * ureg.MPa

k_1 = 0.15

# Shear resistance:

v_Rdc = C_Rdc * k * power(100 * rho * (f_ck / ureg.MPa), 1 / 3)
print(disp(v_Rdc, ureg.MPa))

v_min = 0.035 * ureg.MPa * power(k, 3 / 2) * power(f_ck / ureg.MPa, 1 / 2)
print(disp(v_min, ureg.MPa))

# Total design shear resistance:

V_rd = vectorize((mc_max(v_Rdc, v_min) + k_1 * sigma_cp) * b_w * d)
print(disp(V_rd, ureg.kN))

# Shear utilization

UR_vc = vectorize(V / V_rd)
print(disp(UR_vc))

print(mc_max(UR_vc))

print('mc_max(UR_vc) < 1', mc_max(UR_vc) < 1, 'OK!')

# 6 Minimum reinforcement

# Minimum reinforcement for column:

A_smin = mc_max(vectorize(0.1 * -N) / f_yd, 0.002 * A_c)
print(disp(A_smin, ureg.mm**2))

# Maximum reinforcement:

A_smax = 0.04 * A_c
print(disp(A_smax, ureg.mm**2))

# Provided vertical reinforcement:

A_s_total = total(A_s)
print(disp(A_s_total, ureg.mm**2))

print('A_s_total > A_smin and A_s_total < A_smax', A_s_total > A_smin and A_s_total < A_smax, 'OK!')

# Maximum allowed stirrup spacing:

s_max = mc_min(400 * ureg.mm, 20 * ø, l_c, w_c)
print(disp(s_max, ureg.mm))

print('s_w <= s_max', s_w <= s_max, 'OK!')

# 7 Bursting at temp bearing

# Bearing size:

l_b = 420 * ureg.mm

w_b = 490 * ureg.mm

# LT91 / 92 -> 650ton -> 420x460mm

# LT93 ->300t -> 275x330x

# Bearing area

A_0 = l_b * w_b
print(disp(A_0, ureg.mm**2))

# Max veritical bearing force:

print(disp((mc_max(Fz)), ureg.MN))

d_2 = mc_min(3 * l_b, l_c)
print(d_2)

b_2 = mc_min(3 * w_b, w_c)
print(b_2)

A_1 = d_2 * b_2

# Confined concrete strength under bearing:

F_Rdu = A_0 * f_cd * mc_min(nth_root(A_1 / A_0, 2), 3)
print(disp(F_Rdu, ureg.MN))

# Bursting tension force:

T_burst = 1 / 4 * ((l_c - l_b) / l_c) * mc_max(Fz)
print(disp(T_burst, ureg.kN))

# Increased reinforcement near bearing:

ø_b = 16 * ureg.mm

n_leg = 4

# Steel area per layer:

A_swi = n_leg * ø_b**2 * (math.pi / 4)
print(disp(A_swi, ureg.mm**2))

# Height of bursting zone:

h = l_c
print(h)

# Min required stirrups spacing:

s_req = h * A_swi * f_yd / T_burst
print(disp(s_req, ureg.mm))

# Provided spacing:

s_b = 300 * ureg.mm

print('s_b <= s_req', s_b <= s_req, 'OK!')
