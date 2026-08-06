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

Dr = matrix(
    [0.006, 3],
    [1.967, 4.437],
    [4.925, 6.156],
    [4.752, 7.886],
    [8.114, 9.017],
    [5.871, 11.48],
    [9.552, 10.14],
    [8.52, 11.25],
    [8.457, 14.66],
    [9.737, 12.88],
    [14.94, 13.94],
    [11.6, 24.25],
    [12.04, 25.74],
    [15.66, 18.96],
    [17.01, 22.75],
    [15.83, 27.42],
    [18.25, 26.23],
    [17.29, 30.16],
    [21.92, 36.39],
    [21.6, 33.87],
    [24.38, 34.31],
    [25.78, 27.87],
    [24.7, 37.21],
    [25.31, 31.59],
    [28.31, 41.51],
    [28.9, 42.62],
    [30.98, 41.86],
    [30.06, 50],
    [29.33, 48.37],
    [33.2, 55.33],
    [31.88, 50.28],
    [34.39, 62.26],
    [32.04, 58.29],
    [34.38, 58.04],
    [36.94, 47.71],
    [39.19, 48.7],
    [38.42, 42.91],
    [40.72, 71.5],
    [40.29, 46.89],
    [42.72, 45.09],
    [43, 68.64],
    [44.68, 66.35],
    [44.86, 62.18],
    [43.76, 66.02],
    [46.13, 53.72],
    [47.59, 81.21],
    [49.76, 87.03],
    [47.84, 91.05],
    [50.46, 65.4],
    [52.5, 58.23],
    [50.74, 92.25],
    [51.71, 85.09],
    [55.46, 58.76],
    [55.13, 90.65],
    [58.83, 62.66],
    [55.77, 70.49],
    [60.11, 110.5],
    [57.96, 97.78],
    [62.09, 89.57],
    [59.78, 91.31],
    [63.66, 93.56],
    [62.4, 106],
    [65.41, 102.6],
    [66.61, 66.37],
    [64.62, 73.44],
    [69.17, 124.1],
    [68.59, 118.3],
    [69.13, 95.47],
    [72.75, 108.6],
    [71.75, 137.9],
    [72.36, 85.36],
    [75.23, 83.35],
    [74.28, 143.5],
    [77.91, 78.03],
    [77.7, 81.14],
    [75.98, 87.87],
    [80.2, 144.7],
    [79.5, 135.6],
    [78.14, 82.15],
    [81.86, 137.9],
    [82.66, 100.4],
    [85.22, 97.68],
    [85.29, 113],
    [87.21, 116.5],
    [84.55, 154.4],
    [86.57, 132.8],
    [87.43, 157.6],
    [87.7, 102.6],
    [92.17, 126.4],
    [92, 104.2],
    [91.26, 98.96],
    [91.01, 146.2],
    [96.03, 145.4],
    [94.05, 125],
    [96.77, 173],
    [95.57, 125],
    [99.76, 184.9],
    [99.72, 172.1],
    [100.2, 136.4],
    [102.5, 124.6],
)

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

cer = matrix(
    [1, 1, 1, 608.781, -1, -1, -1],
    [2, 1, 2, 569.67, -1, -1, -1],
    [3, 1, 1, 689.556, -1, -1, -1],
    [4, 1, 2, 747.541, -1, -1, -1],
    [5, 1, 1, 618.134, -1, -1, -1],
    [6, 1, 2, 612.182, -1, -1, -1],
    [7, 1, 1, 680.203, -1, -1, -1],
    [8, 1, 2, 607.766, -1, -1, -1],
    [9, 1, 1, 726.232, -1, -1, -1],
    [10, 1, 2, 605.38, -1, -1, -1],
    [11, 1, 1, 518.655, -1, -1, -1],
    [12, 1, 2, 589.226, -1, -1, -1],
    [13, 1, 1, 740.447, -1, -1, -1],
    [14, 1, 2, 588.375, -1, -1, -1],
    [15, 1, 1, 666.83, -1, -1, -1],
    [16, 1, 2, 531.384, -1, -1, -1],
    [17, 1, 1, 710.272, -1, -1, -1],
    [18, 1, 2, 633.417, -1, -1, -1],
    [19, 1, 1, 751.669, -1, -1, -1],
    [20, 1, 2, 619.06, -1, -1, -1],
    [21, 1, 1, 697.979, -1, -1, -1],
    [22, 1, 2, 632.447, -1, -1, -1],
    [23, 1, 1, 708.583, -1, -1, -1],
    [24, 1, 2, 624.256, -1, -1, -1],
    [25, 1, 1, 624.972, -1, -1, -1],
    [26, 1, 2, 575.143, -1, -1, -1],
    [27, 1, 1, 695.07, -1, -1, -1],
    [28, 1, 2, 549.278, -1, -1, -1],
    [29, 1, 1, 769.391, -1, -1, -1],
    [30, 1, 2, 624.972, -1, -1, -1],
    [61, 1, 1, 720.186, -1, 1, 1],
    [62, 1, 2, 587.695, -1, 1, 1],
    [63, 1, 1, 723.657, -1, 1, 1],
    [64, 1, 2, 569.207, -1, 1, 1],
    [65, 1, 1, 703.7, -1, 1, 1],
    [66, 1, 2, 613.257, -1, 1, 1],
    [67, 1, 1, 697.626, -1, 1, 1],
    [68, 1, 2, 565.737, -1, 1, 1],
    [69, 1, 1, 714.98, -1, 1, 1],
    [70, 1, 2, 662.131, -1, 1, 1],
    [71, 1, 1, 657.712, -1, 1, 1],
    [72, 1, 2, 543.177, -1, 1, 1],
    [73, 1, 1, 609.989, -1, 1, 1],
    [74, 1, 2, 512.394, -1, 1, 1],
    [75, 1, 1, 650.771, -1, 1, 1],
    [76, 1, 2, 611.19, -1, 1, 1],
    [77, 1, 1, 707.977, -1, 1, 1],
    [78, 1, 2, 659.982, -1, 1, 1],
    [79, 1, 1, 712.199, -1, 1, 1],
    [80, 1, 2, 569.245, -1, 1, 1],
    [81, 1, 1, 709.631, -1, 1, 1],
    [82, 1, 2, 725.792, -1, 1, 1],
    [83, 1, 1, 703.16, -1, 1, 1],
    [84, 1, 2, 608.96, -1, 1, 1],
    [85, 1, 1, 744.822, -1, 1, 1],
    [86, 1, 2, 586.06, -1, 1, 1],
    [87, 1, 1, 719.217, -1, 1, 1],
    [88, 1, 2, 617.441, -1, 1, 1],
    [89, 1, 1, 619.137, -1, 1, 1],
    [90, 1, 2, 592.845, -1, 1, 1],
    [151, 2, 1, 753.333, 1, 1, 1],
    [152, 2, 2, 631.754, 1, 1, 1],
    [153, 2, 1, 677.933, 1, 1, 1],
    [154, 2, 2, 588.113, 1, 1, 1],
    [155, 2, 1, 735.919, 1, 1, 1],
    [156, 2, 2, 555.724, 1, 1, 1],
    [157, 2, 1, 695.274, 1, 1, 1],
    [158, 2, 2, 702.411, 1, 1, 1],
    [159, 2, 1, 504.167, 1, 1, 1],
    [160, 2, 2, 631.754, 1, 1, 1],
    [161, 2, 1, 693.333, 1, 1, 1],
    [162, 2, 2, 698.254, 1, 1, 1],
    [163, 2, 1, 625, 1, 1, 1],
    [164, 2, 2, 616.791, 1, 1, 1],
    [165, 2, 1, 596.667, 1, 1, 1],
    [166, 2, 2, 551.953, 1, 1, 1],
    [167, 2, 1, 640.898, 1, 1, 1],
    [168, 2, 2, 636.738, 1, 1, 1],
    [169, 2, 1, 720.506, 1, 1, 1],
    [170, 2, 2, 571.551, 1, 1, 1],
    [171, 2, 1, 700.748, 1, 1, 1],
    [172, 2, 2, 521.667, 1, 1, 1],
    [173, 2, 1, 691.604, 1, 1, 1],
    [174, 2, 2, 587.451, 1, 1, 1],
    [175, 2, 1, 636.738, 1, 1, 1],
    [176, 2, 2, 700.422, 1, 1, 1],
    [177, 2, 1, 731.667, 1, 1, 1],
    [178, 2, 2, 595.819, 1, 1, 1],
    [179, 2, 1, 635.079, 1, 1, 1],
    [180, 2, 2, 534.236, 1, 1, 1],
    [181, 2, 1, 716.926, 1, -1, -1],
    [182, 2, 2, 606.188, 1, -1, -1],
    [183, 2, 1, 759.581, 1, -1, -1],
    [184, 2, 2, 575.303, 1, -1, -1],
    [185, 2, 1, 673.903, 1, -1, -1],
    [186, 2, 2, 590.628, 1, -1, -1],
    [187, 2, 1, 736.648, 1, -1, -1],
    [188, 2, 2, 729.314, 1, -1, -1],
    [189, 2, 1, 675.957, 1, -1, -1],
    [190, 2, 2, 619.313, 1, -1, -1],
    [191, 2, 1, 729.23, 1, -1, -1],
    [192, 2, 2, 624.234, 1, -1, -1],
    [193, 2, 1, 697.239, 1, -1, -1],
    [194, 2, 2, 651.304, 1, -1, -1],
    [195, 2, 1, 728.499, 1, -1, -1],
    [196, 2, 2, 724.175, 1, -1, -1],
    [197, 2, 1, 797.662, 1, -1, -1],
    [198, 2, 2, 583.034, 1, -1, -1],
    [199, 2, 1, 668.53, 1, -1, -1],
    [200, 2, 2, 620.227, 1, -1, -1],
    [201, 2, 1, 815.754, 1, -1, -1],
    [202, 2, 2, 584.861, 1, -1, -1],
    [203, 2, 1, 777.392, 1, -1, -1],
    [204, 2, 2, 565.391, 1, -1, -1],
    [205, 2, 1, 712.14, 1, -1, -1],
    [206, 2, 2, 622.506, 1, -1, -1],
    [207, 2, 1, 663.622, 1, -1, -1],
    [208, 2, 2, 628.336, 1, -1, -1],
    [209, 2, 1, 684.181, 1, -1, -1],
    [210, 2, 2, 587.145, 1, -1, -1],
    [271, 3, 1, 629.012, 1, -1, 1],
    [272, 3, 2, 584.319, 1, -1, 1],
    [273, 3, 1, 640.193, 1, -1, 1],
    [274, 3, 2, 538.239, 1, -1, 1],
    [275, 3, 1, 644.156, 1, -1, 1],
    [276, 3, 2, 538.097, 1, -1, 1],
    [277, 3, 1, 642.469, 1, -1, 1],
    [278, 3, 2, 595.686, 1, -1, 1],
    [279, 3, 1, 639.09, 1, -1, 1],
    [280, 3, 2, 648.935, 1, -1, 1],
    [281, 3, 1, 439.418, 1, -1, 1],
    [282, 3, 2, 583.827, 1, -1, 1],
    [283, 3, 1, 614.664, 1, -1, 1],
    [284, 3, 2, 534.905, 1, -1, 1],
    [285, 3, 1, 537.161, 1, -1, 1],
    [286, 3, 2, 569.858, 1, -1, 1],
    [287, 3, 1, 656.773, 1, -1, 1],
    [288, 3, 2, 617.246, 1, -1, 1],
    [289, 3, 1, 659.534, 1, -1, 1],
    [290, 3, 2, 610.337, 1, -1, 1],
    [291, 3, 1, 695.278, 1, -1, 1],
    [292, 3, 2, 584.192, 1, -1, 1],
    [293, 3, 1, 734.04, 1, -1, 1],
    [294, 3, 2, 598.853, 1, -1, 1],
    [295, 3, 1, 687.665, 1, -1, 1],
    [296, 3, 2, 554.774, 1, -1, 1],
    [297, 3, 1, 710.858, 1, -1, 1],
    [298, 3, 2, 605.694, 1, -1, 1],
    [299, 3, 1, 701.716, 1, -1, 1],
    [300, 3, 2, 627.516, 1, -1, 1],
    [301, 3, 1, 382.133, 1, 1, -1],
    [302, 3, 2, 574.522, 1, 1, -1],
    [303, 3, 1, 719.744, 1, 1, -1],
    [304, 3, 2, 582.682, 1, 1, -1],
    [305, 3, 1, 756.82, 1, 1, -1],
    [306, 3, 2, 563.872, 1, 1, -1],
    [307, 3, 1, 690.978, 1, 1, -1],
    [308, 3, 2, 715.962, 1, 1, -1],
    [309, 3, 1, 670.864, 1, 1, -1],
    [310, 3, 2, 616.43, 1, 1, -1],
    [311, 3, 1, 670.308, 1, 1, -1],
    [312, 3, 2, 778.011, 1, 1, -1],
    [313, 3, 1, 660.062, 1, 1, -1],
    [314, 3, 2, 604.255, 1, 1, -1],
    [315, 3, 1, 790.382, 1, 1, -1],
    [316, 3, 2, 571.906, 1, 1, -1],
    [317, 3, 1, 714.75, 1, 1, -1],
    [318, 3, 2, 625.925, 1, 1, -1],
    [319, 3, 1, 716.959, 1, 1, -1],
    [320, 3, 2, 682.426, 1, 1, -1],
    [321, 3, 1, 603.363, 1, 1, -1],
    [322, 3, 2, 707.604, 1, 1, -1],
    [323, 3, 1, 713.796, 1, 1, -1],
    [324, 3, 2, 617.4, 1, 1, -1],
    [325, 3, 1, 444.963, 1, 1, -1],
    [326, 3, 2, 689.576, 1, 1, -1],
    [327, 3, 1, 723.276, 1, 1, -1],
    [328, 3, 2, 676.678, 1, 1, -1],
    [329, 3, 1, 745.527, 1, 1, -1],
    [330, 3, 2, 563.29, 1, 1, -1],
    [361, 4, 1, 778.333, -1, -1, 1],
    [362, 4, 2, 581.879, -1, -1, 1],
    [363, 4, 1, 723.349, -1, -1, 1],
    [364, 4, 2, 447.701, -1, -1, 1],
    [365, 4, 1, 708.229, -1, -1, 1],
    [366, 4, 2, 557.772, -1, -1, 1],
    [367, 4, 1, 681.667, -1, -1, 1],
    [368, 4, 2, 593.537, -1, -1, 1],
    [369, 4, 1, 566.085, -1, -1, 1],
    [370, 4, 2, 632.585, -1, -1, 1],
    [371, 4, 1, 687.448, -1, -1, 1],
    [372, 4, 2, 671.35, -1, -1, 1],
    [373, 4, 1, 597.5, -1, -1, 1],
    [374, 4, 2, 569.53, -1, -1, 1],
    [375, 4, 1, 637.41, -1, -1, 1],
    [376, 4, 2, 581.667, -1, -1, 1],
    [377, 4, 1, 755.864, -1, -1, 1],
    [378, 4, 2, 643.449, -1, -1, 1],
    [379, 4, 1, 692.945, -1, -1, 1],
    [380, 4, 2, 581.593, -1, -1, 1],
    [381, 4, 1, 766.532, -1, -1, 1],
    [382, 4, 2, 494.122, -1, -1, 1],
    [383, 4, 1, 725.663, -1, -1, 1],
    [384, 4, 2, 620.948, -1, -1, 1],
    [385, 4, 1, 698.818, -1, -1, 1],
    [386, 4, 2, 615.903, -1, -1, 1],
    [387, 4, 1, 760, -1, -1, 1],
    [388, 4, 2, 606.667, -1, -1, 1],
    [389, 4, 1, 775.272, -1, -1, 1],
    [390, 4, 2, 579.167, -1, -1, 1],
    [421, 4, 1, 708.885, -1, 1, -1],
    [422, 4, 2, 662.51, -1, 1, -1],
    [423, 4, 1, 727.201, -1, 1, -1],
    [424, 4, 2, 436.237, -1, 1, -1],
    [425, 4, 1, 642.56, -1, 1, -1],
    [426, 4, 2, 644.223, -1, 1, -1],
    [427, 4, 1, 690.773, -1, 1, -1],
    [428, 4, 2, 586.035, -1, 1, -1],
    [429, 4, 1, 688.333, -1, 1, -1],
    [430, 4, 2, 620.833, -1, 1, -1],
    [431, 4, 1, 743.973, -1, 1, -1],
    [432, 4, 2, 652.535, -1, 1, -1],
    [433, 4, 1, 682.461, -1, 1, -1],
    [434, 4, 2, 593.516, -1, 1, -1],
    [435, 4, 1, 761.43, -1, 1, -1],
    [436, 4, 2, 587.451, -1, 1, -1],
    [437, 4, 1, 691.542, -1, 1, -1],
    [438, 4, 2, 570.964, -1, 1, -1],
    [439, 4, 1, 643.392, -1, 1, -1],
    [440, 4, 2, 645.192, -1, 1, -1],
    [441, 4, 1, 697.075, -1, 1, -1],
    [442, 4, 2, 540.079, -1, 1, -1],
    [443, 4, 1, 708.229, -1, 1, -1],
    [444, 4, 2, 707.117, -1, 1, -1],
    [445, 4, 1, 746.467, -1, 1, -1],
    [446, 4, 2, 621.779, -1, 1, -1],
    [447, 4, 1, 744.819, -1, 1, -1],
    [448, 4, 2, 585.777, -1, 1, -1],
    [449, 4, 1, 655.029, -1, 1, -1],
    [450, 4, 2, 703.98, -1, 1, -1],
    [541, 5, 1, 715.224, -1, -1, -1],
    [542, 5, 2, 698.237, -1, -1, -1],
    [543, 5, 1, 614.417, -1, -1, -1],
    [544, 5, 2, 757.12, -1, -1, -1],
    [545, 5, 1, 761.363, -1, -1, -1],
    [546, 5, 2, 621.751, -1, -1, -1],
    [547, 5, 1, 716.106, -1, -1, -1],
    [548, 5, 2, 472.125, -1, -1, -1],
    [549, 5, 1, 659.502, -1, -1, -1],
    [550, 5, 2, 612.7, -1, -1, -1],
    [551, 5, 1, 730.781, -1, -1, -1],
    [552, 5, 2, 583.17, -1, -1, -1],
    [553, 5, 1, 546.928, -1, -1, -1],
    [554, 5, 2, 599.771, -1, -1, -1],
    [555, 5, 1, 734.203, -1, -1, -1],
    [556, 5, 2, 549.227, -1, -1, -1],
    [557, 5, 1, 682.051, -1, -1, -1],
    [558, 5, 2, 605.453, -1, -1, -1],
    [559, 5, 1, 701.341, -1, -1, -1],
    [560, 5, 2, 569.599, -1, -1, -1],
    [561, 5, 1, 759.729, -1, -1, -1],
    [562, 5, 2, 637.233, -1, -1, -1],
    [563, 5, 1, 689.942, -1, -1, -1],
    [564, 5, 2, 621.774, -1, -1, -1],
    [565, 5, 1, 769.424, -1, -1, -1],
    [566, 5, 2, 558.041, -1, -1, -1],
    [567, 5, 1, 715.286, -1, -1, -1],
    [568, 5, 2, 583.17, -1, -1, -1],
    [569, 5, 1, 776.197, -1, -1, -1],
    [570, 5, 2, 345.294, -1, -1, -1],
    [571, 5, 1, 547.099, 1, -1, 1],
    [572, 5, 2, 570.999, 1, -1, 1],
    [573, 5, 1, 619.942, 1, -1, 1],
    [574, 5, 2, 603.232, 1, -1, 1],
    [575, 5, 1, 696.046, 1, -1, 1],
    [576, 5, 2, 595.335, 1, -1, 1],
    [577, 5, 1, 573.109, 1, -1, 1],
    [578, 5, 2, 581.047, 1, -1, 1],
    [579, 5, 1, 638.794, 1, -1, 1],
    [580, 5, 2, 455.878, 1, -1, 1],
    [581, 5, 1, 708.193, 1, -1, 1],
    [582, 5, 2, 627.88, 1, -1, 1],
    [583, 5, 1, 502.825, 1, -1, 1],
    [584, 5, 2, 464.085, 1, -1, 1],
    [585, 5, 1, 632.633, 1, -1, 1],
    [586, 5, 2, 596.129, 1, -1, 1],
    [587, 5, 1, 683.382, 1, -1, 1],
    [588, 5, 2, 640.371, 1, -1, 1],
    [589, 5, 1, 684.812, 1, -1, 1],
    [590, 5, 2, 621.471, 1, -1, 1],
    [591, 5, 1, 738.161, 1, -1, 1],
    [592, 5, 2, 612.727, 1, -1, 1],
    [593, 5, 1, 671.492, 1, -1, 1],
    [594, 5, 2, 606.46, 1, -1, 1],
    [595, 5, 1, 709.771, 1, -1, 1],
    [596, 5, 2, 571.76, 1, -1, 1],
    [597, 5, 1, 685.199, 1, -1, 1],
    [598, 5, 2, 599.304, 1, -1, 1],
    [599, 5, 1, 624.973, 1, -1, 1],
    [600, 5, 2, 579.459, 1, -1, 1],
    [601, 6, 1, 757.363, 1, 1, 1],
    [602, 6, 2, 761.511, 1, 1, 1],
    [603, 6, 1, 633.417, 1, 1, 1],
    [604, 6, 2, 566.969, 1, 1, 1],
    [605, 6, 1, 658.754, 1, 1, 1],
    [606, 6, 2, 654.397, 1, 1, 1],
    [607, 6, 1, 664.666, 1, 1, 1],
    [608, 6, 2, 611.719, 1, 1, 1],
    [609, 6, 1, 663.009, 1, 1, 1],
    [610, 6, 2, 577.409, 1, 1, 1],
    [611, 6, 1, 773.226, 1, 1, 1],
    [612, 6, 2, 576.731, 1, 1, 1],
    [613, 6, 1, 708.261, 1, 1, 1],
    [614, 6, 2, 617.441, 1, 1, 1],
    [615, 6, 1, 739.086, 1, 1, 1],
    [616, 6, 2, 577.409, 1, 1, 1],
    [617, 6, 1, 667.786, 1, 1, 1],
    [618, 6, 2, 548.957, 1, 1, 1],
    [619, 6, 1, 674.481, 1, 1, 1],
    [620, 6, 2, 623.315, 1, 1, 1],
    [621, 6, 1, 695.688, 1, 1, 1],
    [622, 6, 2, 621.761, 1, 1, 1],
    [623, 6, 1, 588.288, 1, 1, 1],
    [624, 6, 2, 553.978, 1, 1, 1],
    [625, 6, 1, 545.61, 1, 1, 1],
    [626, 6, 2, 657.157, 1, 1, 1],
    [627, 6, 1, 752.305, 1, 1, 1],
    [628, 6, 2, 610.882, 1, 1, 1],
    [629, 6, 1, 684.523, 1, 1, 1],
    [630, 6, 2, 552.304, 1, 1, 1],
    [631, 6, 1, 717.159, -1, 1, -1],
    [632, 6, 2, 545.303, -1, 1, -1],
    [633, 6, 1, 721.343, -1, 1, -1],
    [634, 6, 2, 651.934, -1, 1, -1],
    [635, 6, 1, 750.623, -1, 1, -1],
    [636, 6, 2, 635.24, -1, 1, -1],
    [637, 6, 1, 776.488, -1, 1, -1],
    [638, 6, 2, 641.083, -1, 1, -1],
    [639, 6, 1, 750.623, -1, 1, -1],
    [640, 6, 2, 645.321, -1, 1, -1],
    [641, 6, 1, 600.84, -1, 1, -1],
    [642, 6, 2, 566.127, -1, 1, -1],
    [643, 6, 1, 686.196, -1, 1, -1],
    [644, 6, 2, 647.844, -1, 1, -1],
    [645, 6, 1, 687.87, -1, 1, -1],
    [646, 6, 2, 554.815, -1, 1, -1],
    [647, 6, 1, 725.527, -1, 1, -1],
    [648, 6, 2, 620.087, -1, 1, -1],
    [649, 6, 1, 658.796, -1, 1, -1],
    [650, 6, 2, 711.301, -1, 1, -1],
    [651, 6, 1, 690.38, -1, 1, -1],
    [652, 6, 2, 644.355, -1, 1, -1],
    [653, 6, 1, 737.144, -1, 1, -1],
    [654, 6, 2, 713.812, -1, 1, -1],
    [655, 6, 1, 663.851, -1, 1, -1],
    [656, 6, 2, 696.707, -1, 1, -1],
    [657, 6, 1, 766.63, -1, 1, -1],
    [658, 6, 2, 589.453, -1, 1, -1],
    [659, 6, 1, 625.922, -1, 1, -1],
    [660, 6, 2, 634.468, -1, 1, -1],
    [721, 7, 1, 694.43, 1, 1, -1],
    [722, 7, 2, 599.751, 1, 1, -1],
    [723, 7, 1, 730.217, 1, 1, -1],
    [724, 7, 2, 624.542, 1, 1, -1],
    [725, 7, 1, 700.77, 1, 1, -1],
    [726, 7, 2, 723.505, 1, 1, -1],
    [727, 7, 1, 722.242, 1, 1, -1],
    [728, 7, 2, 674.717, 1, 1, -1],
    [729, 7, 1, 763.828, 1, 1, -1],
    [730, 7, 2, 608.539, 1, 1, -1],
    [731, 7, 1, 695.668, 1, 1, -1],
    [732, 7, 2, 612.135, 1, 1, -1],
    [733, 7, 1, 688.887, 1, 1, -1],
    [734, 7, 2, 591.935, 1, 1, -1],
    [735, 7, 1, 531.021, 1, 1, -1],
    [736, 7, 2, 676.656, 1, 1, -1],
    [737, 7, 1, 698.915, 1, 1, -1],
    [738, 7, 2, 647.323, 1, 1, -1],
    [739, 7, 1, 735.905, 1, 1, -1],
    [740, 7, 2, 811.97, 1, 1, -1],
    [741, 7, 1, 732.039, 1, 1, -1],
    [742, 7, 2, 603.883, 1, 1, -1],
    [743, 7, 1, 751.832, 1, 1, -1],
    [744, 7, 2, 608.643, 1, 1, -1],
    [745, 7, 1, 618.663, 1, 1, -1],
    [746, 7, 2, 630.778, 1, 1, -1],
    [747, 7, 1, 744.845, 1, 1, -1],
    [748, 7, 2, 623.063, 1, 1, -1],
    [749, 7, 1, 690.826, 1, 1, -1],
    [750, 7, 2, 472.463, 1, 1, -1],
    [811, 7, 1, 666.893, -1, 1, 1],
    [812, 7, 2, 645.932, -1, 1, 1],
    [813, 7, 1, 759.86, -1, 1, 1],
    [814, 7, 2, 577.176, -1, 1, 1],
    [815, 7, 1, 683.752, -1, 1, 1],
    [816, 7, 2, 567.53, -1, 1, 1],
    [817, 7, 1, 729.591, -1, 1, 1],
    [818, 7, 2, 821.654, -1, 1, 1],
    [819, 7, 1, 730.706, -1, 1, 1],
    [820, 7, 2, 684.49, -1, 1, 1],
    [821, 7, 1, 763.124, -1, 1, 1],
    [822, 7, 2, 600.427, -1, 1, 1],
    [823, 7, 1, 724.193, -1, 1, 1],
    [824, 7, 2, 686.023, -1, 1, 1],
    [825, 7, 1, 630.352, -1, 1, 1],
    [826, 7, 2, 628.109, -1, 1, 1],
    [827, 7, 1, 750.338, -1, 1, 1],
    [828, 7, 2, 605.214, -1, 1, 1],
    [829, 7, 1, 752.417, -1, 1, 1],
    [830, 7, 2, 640.26, -1, 1, 1],
    [831, 7, 1, 707.899, -1, 1, 1],
    [832, 7, 2, 700.767, -1, 1, 1],
    [833, 7, 1, 715.582, -1, 1, 1],
    [834, 7, 2, 665.924, -1, 1, 1],
    [835, 7, 1, 728.746, -1, 1, 1],
    [836, 7, 2, 555.926, -1, 1, 1],
    [837, 7, 1, 591.193, -1, 1, 1],
    [838, 7, 2, 543.299, -1, 1, 1],
    [839, 7, 1, 592.252, -1, 1, 1],
    [840, 7, 2, 511.03, -1, 1, 1],
    [901, 8, 1, 740.833, -1, -1, 1],
    [902, 8, 2, 583.994, -1, -1, 1],
    [903, 8, 1, 786.367, -1, -1, 1],
    [904, 8, 2, 611.048, -1, -1, 1],
    [905, 8, 1, 712.386, -1, -1, 1],
    [906, 8, 2, 623.338, -1, -1, 1],
    [907, 8, 1, 738.333, -1, -1, 1],
    [908, 8, 2, 679.585, -1, -1, 1],
    [909, 8, 1, 741.48, -1, -1, 1],
    [910, 8, 2, 665.004, -1, -1, 1],
    [911, 8, 1, 729.167, -1, -1, 1],
    [912, 8, 2, 655.86, -1, -1, 1],
    [913, 8, 1, 795.833, -1, -1, 1],
    [914, 8, 2, 715.711, -1, -1, 1],
    [915, 8, 1, 723.502, -1, -1, 1],
    [916, 8, 2, 611.999, -1, -1, 1],
    [917, 8, 1, 718.333, -1, -1, 1],
    [918, 8, 2, 577.722, -1, -1, 1],
    [919, 8, 1, 768.08, -1, -1, 1],
    [920, 8, 2, 615.129, -1, -1, 1],
    [921, 8, 1, 747.5, -1, -1, 1],
    [922, 8, 2, 540.316, -1, -1, 1],
    [923, 8, 1, 775, -1, -1, 1],
    [924, 8, 2, 711.667, -1, -1, 1],
    [925, 8, 1, 760.599, -1, -1, 1],
    [926, 8, 2, 639.167, -1, -1, 1],
    [927, 8, 1, 758.333, -1, -1, 1],
    [928, 8, 2, 549.491, -1, -1, 1],
    [929, 8, 1, 682.5, -1, -1, 1],
    [930, 8, 2, 684.167, -1, -1, 1],
    [931, 8, 1, 658.116, 1, -1, -1],
    [932, 8, 2, 672.153, 1, -1, -1],
    [933, 8, 1, 738.213, 1, -1, -1],
    [934, 8, 2, 594.534, 1, -1, -1],
    [935, 8, 1, 681.236, 1, -1, -1],
    [936, 8, 2, 627.65, 1, -1, -1],
    [937, 8, 1, 704.904, 1, -1, -1],
    [938, 8, 2, 551.87, 1, -1, -1],
    [939, 8, 1, 693.623, 1, -1, -1],
    [940, 8, 2, 594.534, 1, -1, -1],
    [941, 8, 1, 624.993, 1, -1, -1],
    [942, 8, 2, 602.66, 1, -1, -1],
    [943, 8, 1, 700.228, 1, -1, -1],
    [944, 8, 2, 585.45, 1, -1, -1],
    [945, 8, 1, 611.874, 1, -1, -1],
    [946, 8, 2, 555.724, 1, -1, -1],
    [947, 8, 1, 579.167, 1, -1, -1],
    [948, 8, 2, 574.934, 1, -1, -1],
    [949, 8, 1, 720.872, 1, -1, -1],
    [950, 8, 2, 584.625, 1, -1, -1],
    [951, 8, 1, 690.32, 1, -1, -1],
    [952, 8, 2, 555.724, 1, -1, -1],
    [953, 8, 1, 677.933, 1, -1, -1],
    [954, 8, 2, 611.874, 1, -1, -1],
    [955, 8, 1, 674.6, 1, -1, -1],
    [956, 8, 2, 698.254, 1, -1, -1],
    [957, 8, 1, 611.999, 1, -1, -1],
    [958, 8, 2, 748.13, 1, -1, -1],
    [959, 8, 1, 530.68, 1, -1, -1],
    [960, 8, 2, 689.942, 1, -1, -1],
)

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

DATA = matrix(
    [1, 0.1, 0.4],
    [2, -0.86, 0.72],
    [3, -1.075, 1.1],
    [4, -1.16, 1.45],
    [5, -1.53, 1.8],
    [6, -2.72, 2.17],
    [7, -2.64, 2.4],
    [8, -2.91, 2.8],
    [9, -3.58, 3.2],
    [10, -3.7, 3.4],
)

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

Table = matrix([0, 2, 13, 4], [2, 5, 7, 10], [3, 2, 1, 0])

print(kendltau2(Table))

c = contingtbl(Table)
print(c)
