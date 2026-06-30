"""Step 2 — The 'twin primes are close' guess (a DEAD END).
Tries Fermat factorization. It does NOT find the primes, on purpose:
this teaches that the primes are close-ish but not close enough.
Run:  ./venv/bin/python3 02_fermat.py
(Press Ctrl-C when you get bored — it won't succeed.)
"""
from gmpy2 import mpz, isqrt
from importlib import import_module
load = import_module('01_inspect').load

n = mpz(load()['n'])
a = isqrt(n)
if a * a < n:
    a += 1

print("Walking up from sqrt(n), looking for a perfect-square gap...")
for i in range(1, 5_000_000):
    b2 = a * a - n
    b = isqrt(b2)
    if b * b == b2:
        print("FOUND (unexpected!) p =", a - b)
        break
    a += 1
    if i % 1_000_000 == 0:
        print(f"  ...{i} steps, still nothing")
else:
    print("No luck. The gap between p and q is too large for plain Fermat.")
    print("=> 'Twin' must mean something subtler. On to the hint h.")
