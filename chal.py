from Crypto.Cipher import AES
from Crypto.Util.number import bytes_to_long
import os

W, H       = 640, 480
CHUNK_SIZE = 256
KEY_BYTES  = 16
E          = 65537
N_STAMPS   = 5


def pack(m, e, n):
    return pow(m, e, n)


def lock(key, iv, data):
    return AES.new(key, AES.MODE_CTR, nonce=iv).encrypt(data)


def stamp(m, n):
    return pow(m, 3, n)


def generate(image_bytes, flag_int, n, hastad_moduli):
    K  = os.urandom(KEY_BYTES)
    c  = pack(bytes_to_long(K), E, n)
    iv = os.urandom(8)

    payload = image_bytes
    for n_h in hastad_moduli:
        payload += f"{n_h} {stamp(flag_int, n_h)}\n".encode()

    enc    = lock(K, iv, payload)
    chunks = [enc[i:i + CHUNK_SIZE] for i in range(0, len(enc), CHUNK_SIZE)]
    return c, iv, chunks
