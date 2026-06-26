import math
import pint

ureg = pint.UnitRegistry()


f_cd = 30 * ureg.MPa / 1.5
print(f_cd)

beta = 120 * ureg.deg


# internatl friction angle
phi = 37 * ureg.deg

mu =  math.tan(phi.to(ureg.radian).magnitude)
print(mu)

k = ( 1 + math.sin(phi.to(ureg.radian).magnitude) ) / ( 1 - math.sin(phi.to(ureg.radian).magnitude) )
print(k)

# internal cohesion

c = f_cd / (2 * math.sqrt(k))
print(c)

v = 2/math.sqrt(30)
print(v)

c_eff = v * c
print(c_eff)

f_eff = f_cd * v
print(f_eff)

p = c_eff * (1 / math.tan(phi.to(ureg.radian).magnitude)) * (math.tan(math.pi/4 + phi.to(ureg.radian).magnitude/2)**2 * math.exp((2*beta - math.pi) * math.tan(phi.to(ureg.radian).magnitude)) - 1)
print(p)              


# Semi infinite
p = c_eff * (1 / math.tan(phi.to(ureg.radian).magnitude)) * (math.tan(math.pi/4 + phi.to(ureg.radian).magnitude/2)**2 * math.exp(math.pi * math.tan(phi.to(ureg.radian).magnitude)) - 1)
print(p)                                   
                                                                                                                            
                                                                                                                            