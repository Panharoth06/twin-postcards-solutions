"""Step 3 — What is the hint h? (a tour of WRONG guesses).
Each test below fails; together they corner us into the right answer:
h is the TOP 600 bits of prime p (a job for Coppersmith, step 4).
Run:  ./venv/bin/python3 03_guess_h.py
"""
from gmpy2 import mpz, isqrt, is_square, gcd
from importlib import import_module
load = import_module('01_inspect').load

v = load()
n, h = mpz(v['n']), mpz(v['h'])

print("Is h a factor of n?           ", n % h == 0)                 # no
print("Does h share a factor with n? ", gcd(n, h) != 1)             # no (gcd=1)
print("Is h the gap q-p?  (h^2+4n □) ", bool(is_square(h * h + 4 * n)))  # no
print("Is h the top bits of sqrt(n)? ", h == (isqrt(n) >> 424))     # no

print()
print("All false. But h is 600 bits and p is ~1024 bits, so")
print("p = [ top 600 bits = h ][ unknown bottom 424 bits ].")
print("424 < half of 1024  =>  Coppersmith can recover the rest.")
print("Next:  ./venv/bin/python3 cop2.py 424 16 16")
