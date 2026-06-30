# Step 4 — Coppersmith factorization of n using the hint h.
# h = top 600 bits of prime p; this recovers the bottom 424 bits.
# Run:  ./venv/bin/python3 cop2.py 424 16 16
from fpylll import IntegerMatrix, LLL
from math import gcd
from sympy import symbols, Poly, ZZ
import re

def _load():
    out = {}
    for line in open('output.txt'):
        m = re.match(r'^(n|h|e|c)\s*=\s*([0-9a-fA-F]+)\s*$', line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out

_v = _load()
N = int(_v['n']); h = int(_v['h'])

def coppersmith_linear(a, N, beta, mm, tt, X):
    # find small root x0 of f(x)=x+a modulo p (p|N, p>=N^beta), |x0|<X
    # Howgrave-Graham, degree d=1
    d=1
    rows=[]
    # g_{i}(x) = N^(mm-i) * (x+a)^i , i=0..mm   (degree i)
    # h_{j}(x) = x^j * (x+a)^mm , j=1..tt
    def fpow(i):
        # coeffs ascending of (x+a)^i
        c=[1]
        for _ in range(i):
            nc=[0]*(len(c)+1)
            for k,v in enumerate(c):
                nc[k]+=v*a
                nc[k+1]+=v
            c=nc
        return c
    polys=[]
    for i in range(mm+1):
        c=fpow(i)
        c=[(N**(mm-i))*v for v in c]
        polys.append(c)
    for j in range(1,tt+1):
        c=fpow(mm)
        c=[0]*j+c
        polys.append(c)
    dim=len(polys)
    deg=max(len(p) for p in polys)
    M=IntegerMatrix(dim,deg)
    for r,p in enumerate(polys):
        for cidx,v in enumerate(p):
            M[r,cidx]=int(v)*(X**cidx)
    LLL.reduction(M)
    xs=symbols('x')
    for r in range(dim):
        coeffs=[M[r,cidx]//(X**cidx) for cidx in range(deg)]
        if all(v==0 for v in coeffs): continue
        expr=sum(coeffs[i]*xs**i for i in range(len(coeffs)))
        try:
            P=Poly(expr,xs,domain=ZZ)
        except Exception:
            continue
        try:
            roots=P.ground_roots()
        except Exception:
            continue
        for rt in roots:
            x0=int(rt)
            g=gcd(int(x0+a),N)
            if 1<g<N:
                return g
    return None

def factor_with_hint(N=N, h=h, shift=424, mm=16, tt=16):
    """Recover a prime factor of N given h = top bits of that prime."""
    p0 = int(h) << shift
    X = 1 << shift
    return coppersmith_linear(p0, int(N), 0.49, mm, tt, X)

if __name__ == '__main__':
    import sys
    shift=int(sys.argv[1]) if len(sys.argv)>1 else 424
    mm=int(sys.argv[2]) if len(sys.argv)>2 else 16
    tt=int(sys.argv[3]) if len(sys.argv)>3 else 16
    print(f"shift={shift} mm={mm} tt={tt} dim={mm+1+tt}",flush=True)
    g=factor_with_hint(N,h,shift,mm,tt)
    print("MSB result:",g)
    if g:
        print("p=",g); print("q=",N//g)
