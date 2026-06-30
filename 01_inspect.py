"""Step 1 — Look at what we were given.
Run:  ./venv/bin/python3 01_inspect.py
"""
import re

def load():
    vals = {}
    for line in open('output.txt'):
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([0-9a-fA-F]+)\s*$', line)
        if not m:
            continue
        k, v = m.group(1), m.group(2)
        if k in ('n', 'e', 'h', 'c', 'blocks', 'chunk_size', 'W', 'H'):
            vals[k] = int(v)
        elif k == 'iv':
            vals['iv'] = bytes.fromhex(v)
    return vals

if __name__ == '__main__':
    v = load()
    print("n bits :", v['n'].bit_length(), "(2048 = two ~1024-bit primes)")
    print("h bits :", v['h'].bit_length(), "<-- the mystery hint")
    print("c bits :", v['c'].bit_length())
    print("e      :", v['e'])
    print()
    img = v['W'] * v['H'] * 3
    print("image  :", v['W'], "x", v['H'], "x3 =", img, "raw RGB bytes")
    print("Notice: h is 600 bits, more than HALF of a 1024-bit prime.")
    print("        Keep that '> half the bits' fact in mind for step 4.")
