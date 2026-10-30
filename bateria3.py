from fractions import Fraction as F
from math import comb
import hashlib
def m(n): return F(0) if n%2 else F(comb(n,n//2), 2**n)
def E(P):
    M=2*P; s=F(0)
    for i in range(0,M+1,2):
        for j in range(0,M+1-i,2):
            s+=F(comb(M,i)*comb(M-i,j))*F(2,5)**(i+j)*F(1,10)**(M-i-j)*m(i)*m(j)
    return s
for P in (40, 120):
    e=E(P); t=f"{e.numerator}/{e.denominator}"
    print(f"P={P} digitos={len(str(e.numerator))} sha256={hashlib.sha256(t.encode()).hexdigest()}")
c=E(40)**3; t=f"{c.numerator}/{c.denominator}"
print(f"E40_cubo digitos={len(str(c.numerator))} sha256={hashlib.sha256(t.encode()).hexdigest()}")
