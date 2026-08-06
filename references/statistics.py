"""Auto-generated from a Mathcad worksheet by mcad2py."""
import math
import matplotlib.pyplot as plt
import pint

from mcad2py.runtime import disp, nth_root, col, matrix, transpose, vec_set, matcol, rows, submatrix, mean, sort, median, mode, gmean, hmean, var, Var, stdev, Stdev, skew, kurt, percentile, Rank, histogram, cvar, corr, slope, intercept, Ftest, Spear, kendltau, kendltau2, contingtbl, dnorm, pnorm, qnorm, rnorm, pt, qt, rt, rweibull, vlookup, index_build, summation, total, arange, sample, plot_domain, plot_axis, plot_trace
ureg = pint.UnitRegistry()


data = col(79, 85, 46, 86, 81)

print(mean(data))

N = len(data)

print(disp(1 / N * summation(lambda i: data[i], 0, N - 1)))

# Change one of the data points before recalculating the mean.

data = vec_set(data, 2, 1.2 * data[2])

print(mean(data))

print(median(data))

print(sort(data))

# Since there are no repeated values in data, an error is returned.

# Mathcad reports an error here: No value occurs more frequently than any others.
try:
    print(mode(data))
except Exception as _err:
    print('error:', _err)

i = arange(0, N - 1, 1)

Data = index_build(i, lambda i: data[i])

def _recur_Data(_idx, Data):
    for i in _idx:
        Data = vec_set(Data, i + N, data[i])
    return Data

Data = _recur_Data(i, Data)
print(Data[i + N])

print(transpose(Data))

print(gmean(Data))

print(mean(Data))

print(hmean(Data))

# Use the mode function to show that an error is returned when more than one data value is repeated with the same frequency.

# Mathcad reports an error here: Can not return the mode of the data, because the data is multimodal. More than one value occurs at the highest frequency.
try:
    print(mode(Data))
except Exception as _err:
    print('error:', _err)

Data = col(1, 2, 3, 4, 4, 5, 6)

print(mode(Data))

# percentile

i = arange(0, 10, 1)

X = index_build(i, lambda i: i)

print(transpose(X))

print(percentile(X, 50 * ureg.percent))

print(percentile(X, 0.90))

quartile1 = percentile(data, 0.25)
print(quartile1)

# Example: Confidence Interval for the Mean

data = col(6.802, 4.137, 5.405, 4.611, 6.86, 5.158, 0.741, 5.716, 6.672, 4.019, 5.7, 3.473, 5.143, 4.913, 6.234, 4.126, 4.295, 5.762, 4.933, 4.938, 4.865, 5.866, 3.161, 5.521, 4.477, 6.742, 3.915, 5.211, 5.319, 5.503, 4.794, 4.783, 6.468, 3.547, 4.566, 5.992, 6.762, 5.366, 4.163, 1.596)

N = len(data)
print(N)

m_s = mean(data)
print(m_s)

s = stdev(data) * nth_root(N / (N - 1), 2)
print(disp(s))

nu = N - 1
print(nu)

# Enter the two-tailed significance level:

alpha = 0.05

# Use function qt to calculate the 95th percentile of the Student t-distribution for a two-tailed test.

p = abs(qt(alpha / 2, nu))
print(disp(p))

# Calculate the lower and upper limits of the confidence interval.

l = m_s - p * (s / nth_root(N, 2))
print(disp(l))

u = m_s + p * (s / nth_root(N, 2))
print(disp(u))

# Plot the sample data, its mean and confidence interval.

i = arange(0, N - 1, 1)

range = index_build(i, lambda i: i)

upper = index_build(i, lambda i: u)

data_mean = index_build(i, lambda i: m_s)

lower = index_build(i, lambda i: l)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(data, None)), label='range', color='#662D91')
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(upper, None)), label='range', color='#FF0000')
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(data_mean, None)), label='range', color='#2E3192')
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(lower, None)), label='range', color='#ED1D2F')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Use function pt to calculate the cumulative probability distribution for the confidence interval:

print(pt(1 - alpha, nu))

# Use function rt to create a vector of random numbers having a Student's t-distribution:

print(rt(7, nu))

# Example: Hypothesis Test of a Normal Mean

X = col(2.323, 1.988, 3.476, -1.186, 2.425, 2.334, 0.758, 0.25, 3.052, 1.209, 1.186, 1.878, 2.433, 0.536, 1.515, -0.58, 2.465, 1.335, -0.409, -0.107, 2.058, 1.898, 1.519, -1.044, -0.425, 2.952, 2.792, 3.32, 3.362, 3.996, 1.519, 3.801, 0.528, 1.967, 1.679, 0.939, 2.737, 3.162, -0.64, 3.167, 1.552, 0.342, -0.435, 0.905, 3.073, 2.517, 3.584, 1.363, 1.689, 0.08)

n = len(X)
print(n)

print(mean(2))

m_s = mean(X)
print(m_s)

alpha = 0.1

mu = 2

sigma = 1.5

# Calculate the Z score.

z = (m_s - mu) / (sigma / nth_root(n, 2))
print(disp(z))

# Two-Tailed Test

# State the null and the alternative hypothesis for a two-tailed test.
# H0: m = μ
# H1: m ≠ μ
# Use function pnorm to test the hypothesis in terms of p-values for the two-tailed test. In this example, all of the Boolean expressions evaluate to 1 when the null hypothesis is true (you do not reject H0).

print(disp(alpha / 2 < pnorm(z, 0, 1) and pnorm(z, 0, 1) < 1 - alpha / 2))

# Use function qnorm to test the hypothesis in terms of q-values for the two-tailed test.

z_t = qnorm(1 - alpha / 2, 0, 1)
print(disp(z_t))

print(abs(z) < z_t)

# Reject the null hypothesis. There is evidence that the mean is significantly different from μ.

# Use function dnorm to calculate the standard normal distribution

normal = lambda q: dnorm(q, 0, 1)

_domain_q = plot_domain(-4.0, 4.0, 499)
_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(_domain_q, None), plot_axis(sample(lambda q: normal(q), _domain_q), None)), label='normal(q)', color='#00008B')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('q')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Left-Tailed Test

# 1.State the null and the alternative hypothesis for a left-tailed test.
# H0: m >= μ
# H1: m < μ
# 2.Use function pnorm to test the hypothesis in terms of p-values for the left-tailed test.

print(pnorm(z, 0, 1) > alpha)

# Use function qnorm to test the hypothesis in terms of q-values for the left-tailed test.

z_L = qnorm(alpha, 0, 1)
print(z_L)

print(z > z_L)

# Reject the null hypothesis. There is evidence that the mean is smaller than μ.

# Right-Tailed Test

# 1.State the null and the alternative hypothesis for a right-tailed test.
# H0: m <= μ
# H1: m > μ
# 2.Use the pnorm function to test the hypothesis in terms of p-values for the right-tailed test:

print(pnorm(z, 0, 1) < 1 - alpha)

z_R = qnorm(1 - alpha, 0, 1)
print(z_R)

print(z < z_R)

# Accept the null hypothesis. There is no evidence that the mean is greater than μ.

# Example: Variance and Standard Deviation

points = 2000

i = arange(0, points, 1)

WeibDist = rweibull(points, 2) * ureg.kg

NormDist = rnorm(points, .87, .5) * ureg.kg

WeibHist = histogram(15, WeibDist)

NormHist = histogram(15, NormDist)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(matcol(NormHist, 0), ureg.kg), plot_axis(matcol(NormHist, 1), None)), label='matcol(NormHist, 0)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(matcol(WeibHist, 0), ureg.kg), plot_axis(matcol(WeibHist, 1), None)), label='matcol(WeibHist, 0)', color='#FF0000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('(kg)')
_ax.set_ylabel('')
_ax.legend()
plt.show()

print(disp((mean(WeibDist)), ureg.kg))

print(disp((mean(NormDist)), ureg.kg))

# Calculate the sample variance of the distributions.

print(disp((Var(WeibDist)), ureg.kg**2))

print(disp((Var(NormDist)), ureg.kg**2))

Variance = lambda V: 1 / (rows(V) - 1) * summation(lambda i: (V[i] - mean(V))**2, 0, rows(V) - 1)

print(disp((Variance(WeibDist)), ureg.kg**2))

# Calculate the sample standard deviation of the Weibull distribution.

print(disp((Stdev(WeibDist)), ureg.kg))

print(disp((nth_root(Var(WeibDist), 2)), ureg.kg))

# Calculate the population variance and standard deviations for the Weibull distribution:

print(disp((var(WeibDist)), ureg.kg**2))

print(disp((stdev(WeibDist)), ureg.kg))

variance = lambda V: 1 / rows(V) * summation(lambda i: (V[i] - mean(V))**2, 0, rows(V) - 1)

print(disp((variance(WeibDist)), ureg.kg**2))

# Example: Computing Standard Errors

D = col(10.23, 10.12, 9.841, 10.28, 9.35, 10.03, 9.734, 9.325, 7.16, 12.01, 9.366, 9.537, 9.857, 9.946, 10.8, 9.912, 9.911, 13.22, 10.74, 9.962, 10.42, 10.21, 9.002, 9.799, 10.03, 9.227, 9.851, 11.78, 3.63, 10.57, 11.37, 10.18, 10.02, 13.93, 10.48, 6.377)

N = len(D)
print(N)

SE_mean = nth_root(N / (N - 1) * var(D), 2)
print(disp(SE_mean))

# Standard Error of a Proportion

Dp = col(0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0)

Np = rows(Dp)
print(Np)

p = total(Dp) / Np
print(disp(p))

SE_pr = nth_root(p * (1 - p) / Np, 2)
print(disp(SE_pr))

# Standard Error of a Regression

Dr = matrix(100, 2, 0.006, 1.967, 4.925, 4.752, 8.114, 5.871, 9.552, 8.52, 8.457, 9.737, 14.94, 11.6, 12.04, 15.66, 17.01, 15.83, 18.25, 17.29, 21.92, 21.6, 24.38, 25.78, 24.7, 25.31, 28.31, 28.9, 30.98, 30.06, 29.33, 33.2, 31.88, 34.39, 32.04, 34.38, 36.94, 39.19, 38.42, 40.72, 40.29, 42.72, 43, 44.68, 44.86, 43.76, 46.13, 47.59, 49.76, 47.84, 50.46, 52.5, 50.74, 51.71, 55.46, 55.13, 58.83, 55.77, 60.11, 57.96, 62.09, 59.78, 63.66, 62.4, 65.41, 66.61, 64.62, 69.17, 68.59, 69.13, 72.75, 71.75, 72.36, 75.23, 74.28, 77.91, 77.7, 75.98, 80.2, 79.5, 78.14, 81.86, 82.66, 85.22, 85.29, 87.21, 84.55, 86.57, 87.43, 87.7, 92.17, 92, 91.26, 91.01, 96.03, 94.05, 96.77, 95.57, 99.76, 99.72, 100.2, 102.5, 3, 4.437, 6.156, 7.886, 9.017, 11.48, 10.14, 11.25, 14.66, 12.88, 13.94, 24.25, 25.74, 18.96, 22.75, 27.42, 26.23, 30.16, 36.39, 33.87, 34.31, 27.87, 37.21, 31.59, 41.51, 42.62, 41.86, 50, 48.37, 55.33, 50.28, 62.26, 58.29, 58.04, 47.71, 48.7, 42.91, 71.5, 46.89, 45.09, 68.64, 66.35, 62.18, 66.02, 53.72, 81.21, 87.03, 91.05, 65.4, 58.23, 92.25, 85.09, 58.76, 90.65, 62.66, 70.49, 110.5, 97.78, 89.57, 91.31, 93.56, 106, 102.6, 66.37, 73.44, 124.1, 118.3, 95.47, 108.6, 137.9, 85.36, 83.35, 143.5, 78.03, 81.14, 87.87, 144.7, 135.6, 82.15, 137.9, 100.4, 97.68, 113, 116.5, 154.4, 132.8, 157.6, 102.6, 126.4, 104.2, 98.96, 146.2, 145.4, 125, 173, 125, 184.9, 172.1, 136.4, 124.6)

X = matcol(Dr, 0)
print(X)

Y = matcol(Dr, 1)
print(Y)

m = slope(X, Y)
print(m)

b = intercept(X, Y)
print(b)

# Calculate the standard error of the slope.

Nr = rows(Dr)
print(Nr)

SE_slope = nth_root(summation(lambda i: (Y[i - 1] - (m * X[i - 1] + b))**2, 1, Nr) / ((Nr - 2) * Nr * var(X)), 2)
print(disp(SE_slope))

# Calculate the standard error of the intercept.

SE_intercept = 1 / Nr * nth_root(summation(lambda i: (Y[i - 1] - (m * X[i - 1] + b))**2, 1, Nr) * summation(lambda i: X[i - 1]**2, 1, Nr) / var(X), 2)
print(disp(SE_intercept))

# Example: Kurtosis and Skewness

points = 2000

i = arange(0, points, 1)

WD = rweibull(points, 2) * ureg.kg

ND = rnorm(points, 0.87, 0.5) * ureg.kg

WH = histogram(15, WD / ureg.kg)

NH = histogram(15, ND / ureg.kg)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(matcol(WH, 0), None), plot_axis(matcol(WH, 1), None)), label='matcol(WH, 0)', color='#00008B')
_ax.plot(*plot_trace(plot_axis(matcol(NH, 0), None), plot_axis(matcol(NH, 1), None)), label='matcol(NH, 0)', color='#F79646')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

# Compare the peak of the distributions by calculating the kurtosis of the distributions.

print(kurt(WD))

print(kurt(ND))

# The bins of the histogram account for the slight deviation of the kurtosis of the normal distribution from zero. The kurtosis of the Weibull distribution indicates that it is slightly peaked compared to a normal distribution.
# Population kurtosis can be estimated by the following sample kurtosis coefficient:

kurtosis = lambda v: rows(v) * (rows(v) + 1) * total((v - mean(v))**4) / ((rows(v) - 1) * (rows(v) - 2) * (rows(v) - 3) * Stdev(v)**4) - 3 * (rows(v) - 1)**2 / ((rows(v) - 2) * (rows(v) - 3))

print(disp(kurtosis(WD / ureg.kg)))

# Compare the skew of the distributions.

print(skew(WD))

print(skew(ND))

# Example: F-Test

cer = matrix(480, 7, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 608.781, 569.67, 689.556, 747.541, 618.134, 612.182, 680.203, 607.766, 726.232, 605.38, 518.655, 589.226, 740.447, 588.375, 666.83, 531.384, 710.272, 633.417, 751.669, 619.06, 697.979, 632.447, 708.583, 624.256, 624.972, 575.143, 695.07, 549.278, 769.391, 624.972, 720.186, 587.695, 723.657, 569.207, 703.7, 613.257, 697.626, 565.737, 714.98, 662.131, 657.712, 543.177, 609.989, 512.394, 650.771, 611.19, 707.977, 659.982, 712.199, 569.245, 709.631, 725.792, 703.16, 608.96, 744.822, 586.06, 719.217, 617.441, 619.137, 592.845, 753.333, 631.754, 677.933, 588.113, 735.919, 555.724, 695.274, 702.411, 504.167, 631.754, 693.333, 698.254, 625, 616.791, 596.667, 551.953, 640.898, 636.738, 720.506, 571.551, 700.748, 521.667, 691.604, 587.451, 636.738, 700.422, 731.667, 595.819, 635.079, 534.236, 716.926, 606.188, 759.581, 575.303, 673.903, 590.628, 736.648, 729.314, 675.957, 619.313, 729.23, 624.234, 697.239, 651.304, 728.499, 724.175, 797.662, 583.034, 668.53, 620.227, 815.754, 584.861, 777.392, 565.391, 712.14, 622.506, 663.622, 628.336, 684.181, 587.145, 629.012, 584.319, 640.193, 538.239, 644.156, 538.097, 642.469, 595.686, 639.09, 648.935, 439.418, 583.827, 614.664, 534.905, 537.161, 569.858, 656.773, 617.246, 659.534, 610.337, 695.278, 584.192, 734.04, 598.853, 687.665, 554.774, 710.858, 605.694, 701.716, 627.516, 382.133, 574.522, 719.744, 582.682, 756.82, 563.872, 690.978, 715.962, 670.864, 616.43, 670.308, 778.011, 660.062, 604.255, 790.382, 571.906, 714.75, 625.925, 716.959, 682.426, 603.363, 707.604, 713.796, 617.4, 444.963, 689.576, 723.276, 676.678, 745.527, 563.29, 778.333, 581.879, 723.349, 447.701, 708.229, 557.772, 681.667, 593.537, 566.085, 632.585, 687.448, 671.35, 597.5, 569.53, 637.41, 581.667, 755.864, 643.449, 692.945, 581.593, 766.532, 494.122, 725.663, 620.948, 698.818, 615.903, 760, 606.667, 775.272, 579.167, 708.885, 662.51, 727.201, 436.237, 642.56, 644.223, 690.773, 586.035, 688.333, 620.833, 743.973, 652.535, 682.461, 593.516, 761.43, 587.451, 691.542, 570.964, 643.392, 645.192, 697.075, 540.079, 708.229, 707.117, 746.467, 621.779, 744.819, 585.777, 655.029, 703.98, 715.224, 698.237, 614.417, 757.12, 761.363, 621.751, 716.106, 472.125, 659.502, 612.7, 730.781, 583.17, 546.928, 599.771, 734.203, 549.227, 682.051, 605.453, 701.341, 569.599, 759.729, 637.233, 689.942, 621.774, 769.424, 558.041, 715.286, 583.17, 776.197, 345.294, 547.099, 570.999, 619.942, 603.232, 696.046, 595.335, 573.109, 581.047, 638.794, 455.878, 708.193, 627.88, 502.825, 464.085, 632.633, 596.129, 683.382, 640.371, 684.812, 621.471, 738.161, 612.727, 671.492, 606.46, 709.771, 571.76, 685.199, 599.304, 624.973, 579.459, 757.363, 761.511, 633.417, 566.969, 658.754, 654.397, 664.666, 611.719, 663.009, 577.409, 773.226, 576.731, 708.261, 617.441, 739.086, 577.409, 667.786, 548.957, 674.481, 623.315, 695.688, 621.761, 588.288, 553.978, 545.61, 657.157, 752.305, 610.882, 684.523, 552.304, 717.159, 545.303, 721.343, 651.934, 750.623, 635.24, 776.488, 641.083, 750.623, 645.321, 600.84, 566.127, 686.196, 647.844, 687.87, 554.815, 725.527, 620.087, 658.796, 711.301, 690.38, 644.355, 737.144, 713.812, 663.851, 696.707, 766.63, 589.453, 625.922, 634.468, 694.43, 599.751, 730.217, 624.542, 700.77, 723.505, 722.242, 674.717, 763.828, 608.539, 695.668, 612.135, 688.887, 591.935, 531.021, 676.656, 698.915, 647.323, 735.905, 811.97, 732.039, 603.883, 751.832, 608.643, 618.663, 630.778, 744.845, 623.063, 690.826, 472.463, 666.893, 645.932, 759.86, 577.176, 683.752, 567.53, 729.591, 821.654, 730.706, 684.49, 763.124, 600.427, 724.193, 686.023, 630.352, 628.109, 750.338, 605.214, 752.417, 640.26, 707.899, 700.767, 715.582, 665.924, 728.746, 555.926, 591.193, 543.299, 592.252, 511.03, 740.833, 583.994, 786.367, 611.048, 712.386, 623.338, 738.333, 679.585, 741.48, 665.004, 729.167, 655.86, 795.833, 715.711, 723.502, 611.999, 718.333, 577.722, 768.08, 615.129, 747.5, 540.316, 775, 711.667, 760.599, 639.167, 758.333, 549.491, 682.5, 684.167, 658.116, 672.153, 738.213, 594.534, 681.236, 627.65, 704.904, 551.87, 693.623, 594.534, 624.993, 602.66, 700.228, 585.45, 611.874, 555.724, 579.167, 574.934, 720.872, 584.625, 690.32, 555.724, 677.933, 611.874, 674.6, 698.254, 611.999, 748.13, 530.68, 689.942, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1)

Batch = submatrix(cer, 1, rows(cer) - 1, 2, 3)

i = arange(1, rows(cer), 1)

batch1 = vlookup(1, Batch, 1)

batch2 = vlookup(2, Batch, 1)

range = index_build(i, lambda i: i)

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(batch1, None)), label='range', color='#00008B')
_ax.plot(*plot_trace(plot_axis(range, None), plot_axis(batch2, None)), label='range', color='#FF0000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

f = Var(batch1) / Var(batch2)
print(disp(f))

print(Ftest(batch1, batch2))

# Example: Covariance and Correlation Coefficient

DATA = matrix(10, 3, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0.1, -0.86, -1.075, -1.16, -1.53, -2.72, -2.64, -2.91, -3.58, -3.7, 0.4, 0.72, 1.1, 1.45, 1.8, 2.17, 2.4, 2.8, 3.2, 3.4)

V_1 = matcol(DATA, 1)

V_2 = matcol(DATA, 2)

a = slope(V_1, V_2)

b = intercept(V_1, V_2)

y = lambda x: a * x + b

_fig, _ax = plt.subplots()
_ax.plot(*plot_trace(plot_axis(V_1, None), plot_axis(V_2, None)), label='V_1', color='#00008B')
_ax.plot(*plot_trace(plot_axis(V_1, None), plot_axis(y(V_1), None)), label='V_1', color='#000000')
_ax.axhline(0, color='0.6', linewidth=0.8)
_ax.axvline(0, color='0.6', linewidth=0.8)
_ax.grid(True, alpha=0.3)
_ax.set_xlabel('')
_ax.set_ylabel('')
_ax.legend()
plt.show()

print(cvar(V_1, V_2))

print(disp(cvar(V_1, V_2) / var(V_1)))

print(a)

# Pearson's Correlation Coefficient

r = corr(V_1, V_2)
print(r)

N = rows(DATA)

i = arange(0, N - 1, 1)

print(disp(1 / N * summation(lambda i: (V_1[i] - mean(V_1)) / stdev(V_1) * ((V_2[i] - mean(V_2)) / stdev(V_2)), 0, N - 1)))

print(r**2)

# Spearman Rank Correlation

Rank1 = Rank(V_1)
print(Rank1)

Rank2 = Rank(V_2)
print(Rank2)

print(corr(Rank1, Rank2))

print(corr(V_1, V_2))

# Example: Correlation and Contingency Tables

Meds = col(0, 150, 300, 200, 400, 0, 350, 150, 0, 0, 500, 0, 0, 250)

Resp = col(1, 0, 0, -1, 0, 1, 1, 0, 0, 0, 1, -1, 1, 0)

print(Spear(Meds, Resp))

print(kendltau(Meds, Resp))

# Functions: kendltau2 and contingtbl

# When there are only a few possible values for each variable, you can record the data as a contingency table, with the frequency of responses as entries.

Table = matrix(3, 4, 0, 2, 3, 2, 5, 2, 13, 7, 1, 4, 10, 0)

print(kendltau2(Table))

c = contingtbl(Table)
print(c)
