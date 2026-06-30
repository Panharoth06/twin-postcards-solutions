from Crypto.Cipher import AES
from Crypto.Util.number import inverse, long_to_bytes, bytes_to_long
from sympy.ntheory.modular import crt
from gmpy2 import iroot, mpz
import re

# parse output.txt
vals={}
chunks={}
for line in open('output.txt'):
    line=line.strip()
    m=re.match(r'^([a-zA-Z_]\w*)\s*=\s*([0-9a-fA-F]+)$',line)
    if not m: continue
    k,v=m.group(1),m.group(2)
    if k in ('n','e','h','c','blocks','chunk_size','W','H'):
        vals[k]=int(v)
    elif k=='iv':
        vals['iv']=bytes.fromhex(v)
    elif re.match(r'^d\d+$',k):
        chunks[int(k[1:])]=bytes.fromhex(v)

n=vals['n']; e=vals['e']; c=vals['c']; iv=vals['iv']
# Door 1: factor n live using Coppersmith (h = top 600 bits of p)
print("[*] factoring n with Coppersmith (this takes a moment)...")
from cop2 import factor_with_hint
p=factor_with_hint(n, vals['h'], shift=424, mm=16, tt=16)
assert p and n % p == 0, "factoring failed"
q=n//p
assert p*q==n, "factor mismatch"
print("[+] factored n")

d=inverse(e,(p-1)*(q-1))
K=long_to_bytes(pow(c,d,n),16)
print("[+] recovered AES key:",K.hex())

# reassemble ciphertext in order
enc=b''.join(chunks[i] for i in range(len(chunks)))
payload=AES.new(K,AES.MODE_CTR,nonce=iv).decrypt(enc)
print("[+] payload len",len(payload))

img_len=vals['W']*vals['H']*3
image=payload[:img_len]
stamp_data=payload[img_len:]
open('postcard.bin','wb').write(image)
print("[+] stamp region:")
print(stamp_data.decode(errors='replace'))

# Hastad broadcast: pairs (n_i, flag^3 mod n_i)
mods=[]; rems=[]
for line in stamp_data.decode(errors='replace').splitlines():
    line=line.strip()
    if not line: continue
    a,b=line.split()
    mods.append(int(a)); rems.append(int(b))
print("[+] got",len(mods),"stamps")
X,_=crt(mods,rems)
X=int(X)
root,exact=iroot(mpz(X),3)
print("[+] exact cube root:",exact)
flag=long_to_bytes(int(root))
print("[+] FLAG:",flag)
