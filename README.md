# Twin Postcards — A Crypto Bedtime Story 🏯

> *"A digital Angkor Wat postcard was broadcast to five recipients.*
> *You have intercepted the encrypted postcard sent to each of them.*
> *Can you recover the original image?"*

This is the story of how we took a wall of seemingly-random numbers and turned
it back into a photograph of a temple — and pulled a hidden flag out of the
mud along the way.

It's written for someone who has *heard* of RSA but never wrestled with it.
We build every idea from scratch, in the order we actually discovered it: the
hunches, the dead ends, and the two "aha" moments that cracked it open. Grab a
cup of tea. ☕

Throughout, the matching code lives in small files inside `dist/` — each
chapter names the file that implements it, so the narrative and the scripts
line up one-to-one.

---

## Table of Contents

1. [The crime scene: what we were handed](#1-the-crime-scene)
2. [Fundamentals you need](#2-fundamentals)
3. [Reading the challenge code like a detective](#3-reading-the-code)
4. [The two locked doors](#4-two-locked-doors)
5. [Door #1: factoring `n` — the long road of dead ends](#5-door-1-the-dead-ends)
6. [The breakthrough: Coppersmith's method](#6-coppersmith)
7. [From primes to the AES key](#7-primes-to-key)
8. [Door #2: Håstad's broadcast attack](#8-hastad)
9. [Putting it all together](#9-the-full-pipeline)
10. [The reveal](#10-the-reveal)
11. [What each clue *really* meant](#11-the-clues-decoded)
12. [Files & environment](#12-files-and-environment)
13. [The lessons to take away](#13-lessons)

---

<a name="1-the-crime-scene"></a>
## 1. The crime scene

We were handed three things:

```
dist/
├── chal.py          # the encryption program (38 lines) — how the data was made
├── description.png  # the story + the challenge title "Twin Postcards"
└── output.txt       # 3600+ lines of giant numbers — the intercepted data
```

`output.txt` opens like this (numbers truncated for sanity):

```
W = 640                         # image width
H = 480                         # image height
n = 16252830909199146961...     # RSA modulus — 617 digits, 2048 bits
e = 65537                       # RSA public exponent
h = 38467697831318575620...     # a mystery "hint" — 181 digits, 600 bits
c = 50516919910041163512...     # the RSA-encrypted secret
iv = a9f82cc40041264f           # 8-byte AES nonce
blocks = 3607                   # number of ciphertext chunks
chunk_size = 256                # bytes per chunk

d0 = 144ac1370784b4b8...        # chunk 0  (256 bytes = 512 hex chars)
d1 = ...
...
d3606 = af211f944c9531abf51a7effcd08    # the LAST chunk — only 14 bytes!
```

The very first thing worth doing is measuring these numbers instead of being
intimidated by them. The tiny helper `01_inspect.py` parses `output.txt` and
reports the bit-lengths:

```
n bits : 2048      (a 2048-bit modulus → two primes of ~1024 bits each)
h bits : 600       ← the hint is unusually large
c bits : 2046
e      : 65537
image  : 640 x 480 x 3 = 921600 raw RGB bytes
```

Two early observations from `01_inspect.py` shape the whole solve:

- **`h` is 600 bits.** A "hint" that is more than *half* the size of a 1024-bit
  prime is a giant red flag (in the good sense). Keep it in your pocket.
- **The image is 921,600 raw RGB bytes**, but the total ciphertext is
  `3606 × 256 + 14 = 923,150` bytes. The extra **1,550 bytes** are something
  appended *after* the image. We'll find out what.

Our mission: turn `d0 … d3606` back into a picture — and whatever is hiding in
those trailing 1,550 bytes.

---

<a name="2-fundamentals"></a>
## 2. Fundamentals

Three building blocks. If you already know them, skim. If not, this *is* the
whole game.

### 2.1 Modular arithmetic — "clock math"

Everything in RSA happens **mod `n`**: you do ordinary arithmetic, then take the
remainder after dividing by `n`. Think of a clock: 10 o'clock + 5 hours = 3
o'clock, because `15 mod 12 = 3`. RSA uses a clock with an astronomically huge
number of hours (`n` ≈ 10⁶¹⁷).

Two operations matter:

- **Modular exponentiation** `pow(m, e, n)` = `mᵉ mod n`. Fast even for huge
  numbers (repeated squaring).
- **Modular inverse** `e⁻¹ mod m`: the number that "undoes" multiplication by
  `e` on the clock. It exists only when `e` and `m` share no common factor.

### 2.2 RSA in one picture

RSA is a lock where **the key that locks is public** and **the key that unlocks
is secret**.

```
        PUBLIC                              SECRET
   ┌──────────────┐                   ┌───────────────┐
   │  n  (modulus)│                   │  d  (private  │
   │  e  (=65537) │                   │      exponent)│
   └──────┬───────┘                   └──────┬────────┘
          │ encrypt: c = mᵉ mod n            │ decrypt: m = c^d mod n
          ▼                                  ▼
       message m  ───────────────────────► message m
```

The modulus `n` is built by multiplying **two big secret primes**:

```
   n = p × q
```

- Anyone can see `n`, `e`, and `c`.
- **Nobody can easily recover `p` and `q`.** Multiplying two 1024-bit primes is
  instant; *un*-multiplying (factoring) the 2048-bit result is, for *random*
  primes, beyond all the computers on Earth.

The private key is derived from the primes:

```
   φ(n) = (p − 1)(q − 1)         ← Euler's totient
   d    = e⁻¹ mod φ(n)           ← needs φ(n), which needs p and q
```

So the entire security of RSA rests on one sentence:

> **If you can find `p` and `q`, you win. Everything else falls instantly.**

Burn that into your brain. The rest of this challenge is one long fight to find
`p` and `q`.

### 2.3 Why "small primes leak" — the seed of the whole challenge

Random primes are unfactorable. But primes generated *carelessly* are not.
Three classic weaknesses:

- **Primes too close together** → Fermat factorization.
- **Part of a prime is known/leaked** → Coppersmith's method.
- **Primes shared between two moduli** → a simple GCD.

The challenge title "Twin Postcards" is daring us to find which weakness applies.

### 2.4 AES-CTR — turning a block cipher into a keystream

AES normally scrambles 16 bytes at a time. **CTR (counter) mode** turns AES into
a "tape of random-looking bytes" — a *keystream* — that you simply XOR onto your
data:

```
   counter:   0        1        2        3      ...
              │        │        │        │
   block =  AES(K, nonce‖0) AES(K, nonce‖1) ...      ← depends ONLY on K and nonce
              │        │        │        │
   keystream: KS0      KS1      KS2      KS3   ...
              ⊕        ⊕        ⊕        ⊕
   plaintext: P0       P1       P2       P3    ...
              =        =        =        =
   ciphertext:C0       C1       C2       C3    ...
```

Here the `iv` (8 bytes) is the *nonce*; the other 8 bytes of each 16-byte AES
input are a counter that climbs 0, 1, 2, … Two consequences matter enormously:

1. **It is a stream cipher** → ciphertext length equals plaintext length, with
   **no padding**. *That is exactly why the final chunk `d3606` is only 14 bytes:*
   `923,150` is not a multiple of 256, so the last slice is just the leftover
   tail. Nothing mysterious.
2. **The keystream depends only on `K` and the nonce** — not on the data. You
   cannot derive block 57,600's keystream from block 0's. So even if we *knew*
   part of the image, it would not help us read the bytes that come after it.
   **We must obtain the key `K` itself.**

### 2.5 The cube (e = 3) — small exponents are fragile

If you encrypt with `e = 3`, then `c = m³ mod n`. If `m` is small enough that
`m³` never exceeds `n` (never "wraps around the clock"), then `c` *is* `m³` as an
ordinary integer, and you recover `m` with a plain cube root — no secret key
needed. This fragility is the entire basis of Door #2.

---

<a name="3-reading-the-code"></a>
## 3. Reading the code

Here is the given encryption program `chal.py`, annotated:

```python
E = 65537            # public exponent used to lock the AES key
N_STAMPS = 5         # the flag gets "stamped" 5 times

def stamp(m, n):
    return pow(m, 3, n)          # flag³ mod n   ← note the exponent is 3!

def lock(key, iv, data):
    return AES.new(key, AES.MODE_CTR, nonce=iv).encrypt(data)

def generate(image_bytes, flag_int, n, hastad_moduli):
    K  = os.urandom(16)                 # random 16-byte AES key
    c  = pow(bytes_to_long(K), E, n)    # K locked inside RSA  → this is `c`
    iv = os.urandom(8)                  # random nonce

    payload = image_bytes
    for n_h in hastad_moduli:           # append 5 stamps of the flag
        payload += f"{n_h} {stamp(flag_int, n_h)}\n".encode()

    enc    = lock(K, iv, payload)       # AES-encrypt (image ‖ stamps)
    chunks = [enc[i:i+256] for i in range(0, len(enc), 256)]
    return c, iv, chunks
```

Reading it slowly tells us precisely what the `payload` is — and explains those
mysterious 1,550 trailing bytes:

```
┌──────────────────────────────────────────┬────────────────────────────────┐
│   raw image: 640 × 480 × 3 = 921,600 B    │  5 text lines: "n_h  flag³"    │
└──────────────────────────────────────────┴────────────────────────────────┘
                  the postcard                   the hidden flag "stamps"
                                                  (≈ 1,550 bytes total)
```

The layering is:

- The **flag** is cubed (`e = 3`) under five different moduli `n_h` → five stamps.
- The **image + the five stamps** are concatenated and AES-encrypted with `K`.
- The **AES key `K`** is itself RSA-encrypted with the public `(n, e=65537)` → `c`.

So the flag is wrapped twice: once by AES (along with the picture) and once,
indirectly, by RSA (which guards the AES key).

---

<a name="4-two-locked-doors"></a>
## 4. Two locked doors

To reach the flag we must open **two nested doors**:

```
   ┌─ DOOR 1: RSA ─────────────────────────────────┐
   │   c = K^65537 mod n                            │
   │   Open it  ⇒  recover the AES key K            │
   │                                                │
   │     ┌─ DOOR 2: AES + Håstad ───────────────┐   │
   │     │  Use K to AES-decrypt the payload     │   │
   │     │  → get the image + 5 flag stamps      │   │
   │     │  → combine the stamps to get the flag │   │
   │     └───────────────────────────────────────┘  │
   └────────────────────────────────────────────────┘
```

Door 2 sits *inside* Door 1: we cannot touch the flag stamps until we have `K`,
and we cannot get `K` until we factor `n`. **Everything hinges on Door 1 —
factoring `n`.**

And factoring a *random* 2048-bit number is hopeless... unless the primes are
not random. The challenge name is shouting at us: **Twin Postcards.**

---

<a name="5-door-1-the-dead-ends"></a>
## 5. Door 1: the dead ends

This is the honest part of the story. Real cryptanalysis is mostly trying things
that *don't* work until one does — and each failure narrows the search. The
probing in this chapter is implemented in `02_fermat.py` and `03_guess_h.py`.

### 5.1 "Twin" → are the primes close? (Fermat factorization)

When `p` and `q` are close together, `n = p·q` is *almost* a perfect square, and
**Fermat factorization** finds them quickly:

> Write `n = a² − b² = (a − b)(a + b)`. Start at `a = ⌈√n⌉` and step `a` upward;
> at each step check whether `a² − n` is a perfect square `b²`. The first time it
> is, you have `p = a − b` and `q = a + b`.

```
   number line:        p        √n        q
                       •─────────•─────────•
                        \        |        /
                         \  the gap q−p   /
                          → Fermat is fast ONLY if this gap is tiny
```

`02_fermat.py` runs exactly this loop. We let it grind **200 million** steps.
**Nothing.** The number of Fermat steps grows like `(q−p)² / (4√n)`, so the
silence tells us the gap is large — the primes are *not* naively close. "Twin"
must mean something subtler.

### 5.2 Interrogating the hint `h`

If brute force won't do it, the 600-bit `h` must be the key. `03_guess_h.py`
tests the obvious relationships one by one — and every one fails:

| Guess about `h`                           | Test in `03_guess_h.py`         | Result |
|-------------------------------------------|---------------------------------|--------|
| `h` is a prime factor of `n`              | `n mod h == 0` ?                | ❌ no   |
| `h` shares a factor with `n`              | `gcd(n, h)`                     | ❌ = 1  |
| `h = q − p` (the gap between primes)      | is `h² + 4n` a perfect square ? | ❌ no   |
| `h` = the top bits of `√n`                | `h == (isqrt(n) >> 424)` ?      | ❌ no   |

Why those particular tests?

- *If `h` were a factor*, division ends the game immediately.
- *If `h` were the gap `q − p`*, then `(p+q)² = (q−p)² + 4n = h² + 4n` would be a
  perfect square — and it isn't.
- *If `h` were the leading bits of `√n`*, the primes would sit symmetrically
  around `√n`; they don't.

Every handle came off in our hands. But the failures left one precise fact
standing: **`h` is exactly 600 bits, and each prime is ~1024 bits.** And 600 is
*more than half* of 1024.

> That phrase — *"we know more than half the bits of a prime"* — is the secret
> handshake of one specific, beautiful technique.

---

<a name="6-coppersmith"></a>
## 6. The breakthrough: Coppersmith's method

Here is the single most important idea in the whole challenge.

> **Coppersmith's theorem (intuition):** if you know *enough of the leading
> bits* of a secret prime `p`, you can recover the rest and factor `n`.
> "Enough" turns out to be a little **over half** the bits.

An analogy: imagine someone gives you a phone number but smudges the last few
digits. If they smudged only 4 of 10 digits, you could realistically pin down
the real number from context. Smudge 9 of 10 and you're lost. Coppersmith makes
this precise for prime factors: smudge fewer than ~half the bits and the answer
is uniquely, *efficiently* recoverable.

Our situation, with `h` as the leading 600 bits of `p`:

```
   p  (1024 bits) =  [ known top 600 bits = h ][ unknown low 424 bits ]
                      └──────── given ────────┘└───── to recover ─────┘
```

424 unknown bits sits comfortably under the recoverability limit (≈ 512 bits,
i.e. ¼ of the 2048-bit modulus). So `h` was never a riddle — it is literally the
**high half of `p`**, handed to us.

### 6.1 How Coppersmith actually works (the machinery)

You don't need to *implement* this from memory, but the shape is worth seeing.

1. Write the unknown as `p = p₀ + x`, where `p₀ = h · 2⁴²⁴` (the known part,
   with the low bits zeroed) and `x` is the unknown low part, `0 ≤ x < 2⁴²⁴`.
2. Consider the polynomial `f(x) = p₀ + x`. We are looking for a *small* root `x`
   such that `f(x) ≡ 0 (mod p)` — i.e. `f(x)` is an exact multiple of the
   unknown prime `p`, which divides `n`.
3. **Howgrave-Graham's trick:** build a family of related polynomials that all
   vanish modulo `pᵐ`, and arrange their coefficient vectors as rows of a matrix
   — a **lattice**.
4. Run **LLL** (the Lenstra–Lenstra–Lovász algorithm) to find a *short* vector in
   that lattice. Short vector ⇒ a new polynomial with such small coefficients
   that its small root holds over the integers, not just modulo `p`.
5. Find the integer root of that polynomial (ordinary algebra). That root is the
   missing low bits → reconstruct `p` → `q = n / p`.

```
   known top bits (h)            build lattice            LLL finds
        │                         of polynomials           a short vector
        ▼                              │                        │
   p = p₀ + x   ───────────────────────┘                        ▼
                                                       a polynomial whose
                                                       integer root = x
                                                                │
                                                                ▼
                                                    p = p₀ + x ,  q = n/p
```

### 6.2 The lesson hiding in our *first* failure

Coppersmith's power depends on how big a lattice you build:

- A **small** lattice is fast but **weak** — it only certifies a few unknown bits.
- A **large** lattice is slower but **strong** — it reaches the full "~half the
  bits" guarantee.

Our first attempt used a tiny lattice. With the optimization parameters small,
its provable reach was only ≈ 256 unknown bits — but we needed **424**. So it
returned nothing, *even though the underlying idea was exactly right.* This is a
crucial distinction:

> "The attack produced nothing" is **not** the same as "the attack is wrong."
> Very often the idea is correct and only the *parameters* are too weak.

The working solver `cop2.py` rebuilds the lattice properly using the `fpylll`
library. It takes three knobs on the command line — `shift mm tt`:

- `shift = 424` — how many low bits of `p` are unknown,
- `mm`, `tt` — the lattice-size parameters (bigger ⇒ stronger ⇒ slower).

With `shift=424 mm=16 tt=16` it assembles a 33-dimensional lattice and prints:

```
   shift=424 mm=16 tt=16 dim=33
   p = 166653468717959387803861022942304273175374418256885420773...
   q = 975247082117749098255499984668267849970086287770945254234...
```

💥 `p × q == n`. **Door 1 is open.** (Curious readers can shrink the knobs, e.g.
`cop2.py 424 4 4`, and watch the too-small lattice come up empty — the very
failure we hit first-hand.)

`cop2.py` also exposes this as a function, `factor_with_hint(N, h, shift, mm, tt)`,
so the next stage can factor live instead of pasting the primes around.

---

<a name="7-primes-to-key"></a>
## 7. From primes to the AES key

With `p` and `q` in hand, RSA unravels in three lines (done at the top of
`final.py`):

```
   φ(n) = (p − 1)(q − 1)
   d    = e⁻¹ mod φ(n)
   K    = c^d mod n   →   bd33d6b0c20caaf7e14f06712e8b48d5   (the 16-byte AES key)
```

That hex string is the AES key that was sealed inside `c` the whole time. Door 1
delivered exactly what Door 2 needs.

---

<a name="8-hastad"></a>
## 8. Door 2: Håstad's broadcast attack

`final.py` now reassembles all 3,607 ciphertext chunks in order, AES-CTR-decrypts
them with `K` and the `iv`, and splits the result at byte 921,600:

```
   payload[:921600]   →  the raw RGB postcard  (written to postcard.bin)
   payload[921600:]   →  5 text lines:  "<n_h>  <flag³ mod n_h>"
```

Those five lines are the heart of the *other* classic attack. Recall
`stamp(m, n) = m³ mod n`: the **same** flag was cubed (`e = 3`) under **five
different moduli**. That is precisely the setup for **Håstad's Broadcast Attack**.

### 8.1 Why one stamp is useless but several are fatal

A single `flag³ mod n_h` is safe: the cube *did* wrap around that modulus, so you
can't just cube-root it, and you'd need that modulus's private key to invert it.
But collect **`e` = 3 or more** of them under different moduli and the **Chinese
Remainder Theorem (CRT)** stitches them into one congruence modulo the *product*
of the moduli:

```
   flag³ mod n₁ ┐
   flag³ mod n₂ ├── CRT ──►  flag³ mod (n₁·n₂·n₃·n₄·n₅)
   flag³ mod n₃ │
   flag³ mod n₄ │
   flag³ mod n₅ ┘
```

Picture gears of different sizes: CRT finds the single rotation that lines up all
five gears at once.

### 8.2 The cube root that needs no key

Here is the magic. The real number `flag³` is far smaller than the giant product
`n₁·n₂·n₃·n₄·n₅`. So when CRT reduces `flag³` modulo that product, **nothing
wraps around** — the result *is* `flag³` as a plain integer. Then:

```
   flag = ∛(flag³)        ← an ordinary integer cube root, no private key at all
```

`final.py` combines the five stamps with CRT, takes an exact integer cube root
(it reports `exact cube root: True`, confirming no wrap-around occurred), and
converts the resulting integer back into bytes:

```
   MPTC{c0pp3rSm1th_m33ts_h4St4d_4t_4ngk0r_W4t}
```

The flag literally names the two techniques you just learned. 🎉

---

<a name="9-the-full-pipeline"></a>
## 9. Putting it all together

The end-to-end flow, with the file that performs each stage:

```
   output.txt
       │  parse n, e, h, c, iv, 3607 chunks            ← 01_inspect.py (and final.py)
       ▼
   [ COPPERSMITH ]  h = top 600 bits of p              ← cop2.py
       │            recover low 424 bits  ⇒  p, q
       ▼
   φ(n) = (p−1)(q−1)  ;  d = e⁻¹ mod φ(n)              ← final.py
       │
       ▼
   K = c^d mod n            (unlock the AES key)        ← final.py
       │
       ▼
   [ AES-CTR decrypt ]  all chunks  ──►  payload        ← final.py
       │
       ├── payload[:921600]  ──►  postcard.bin → .png   ← render.py
       │
       └── payload[921600:]  ──►  5 × (nᵢ, flag³ mod nᵢ)
                  │
                  ▼
            [ HÅSTAD / CRT ]  ──►  flag³  ──►  ∛  ──►  FLAG    ← final.py
```

The dead-end explorations (`02_fermat.py`, `03_guess_h.py`) are not part of the
final path — they are the trail of eliminations that *led* us to Coppersmith,
preserved so the reasoning is reproducible.

---

<a name="10-the-reveal"></a>
## 10. The reveal

Rendering the 921,600 recovered RGB bytes as a 640×480 image (`render.py` turns
`postcard.bin` into `postcard.png`) gives the "digital Angkor Wat postcard" the
story promised:

![The recovered Angkor Wat postcard](postcard.png)

Bright sky on top, the dark temple towers across the middle, darker grounds and
foreground below. A crude brightness map of the same picture:

```
   ##########%%%%%%      ← sky (bright)
   ##########%%%%%%
   ##########%%%%%%
   +****=**+*=*+=*#      ← temple silhouette
   :-::+-----:++:-*
   ::..:::::::::::=
   :::::::::-::::-:      ← grounds / water (darker)
   ---:==-----++==*
   ****+=****+**=##      ← foreground
```

---

<a name="11-the-clues-decoded"></a>
## 11. What each clue *really* meant

Reading the challenge backwards, every detail was a signpost:

| Clue in the challenge               | What it secretly meant                                   |
|-------------------------------------|----------------------------------------------------------|
| Title **"Twin Postcards"**          | The primes have *structure*, not randomness — look closer |
| The oversized hint **`h`** (600 b)  | The **leading 600 bits of prime `p`** → Coppersmith       |
| **"broadcast to five recipients"**  | Five copies of one message → **Håstad** broadcast         |
| `stamp = pow(m, 3, n)`              | The small exponent `e = 3` that makes Håstad possible     |
| The short last chunk `d3606`        | AES-CTR is a stream cipher → no padding, just leftovers   |
| The 1,550 trailing payload bytes    | The five flag stamps hidden after the image               |
| The flag text itself                | A confession: *Coppersmith meets Håstad at Angkor Wat*    |

---

<a name="12-files-and-environment"></a>
## 12. Files & environment

Everything was developed in a local virtual environment. The exact dependencies
are pinned in `requirements.txt`:

```
gmpy2          fast big-integer math (isqrt, roots, primality)
pycryptodome   AES-CTR
sympy          exact polynomial root-finding + CRT
fpylll         the LLL lattice reduction behind Coppersmith
cysignals      runtime dependency of fpylll
mpmath         high-precision arithmetic (pulled in by sympy)
pillow         rendering the raw RGB bytes to a PNG
```

> **Note:** `fpylll`/`cysignals` compile against the `fplll` C library and
> install cleanly on Linux and macOS, but not natively on Windows — use WSL
> there. Everything else is pure pip.

### File guide

| File            | Role in the story                                           |
|-----------------|-------------------------------------------------------------|
| `chal.py`       | The original encryption program (given)                     |
| `output.txt`    | The intercepted data (given)                                |
| `description.png` | The challenge brief (given)                               |
| `requirements.txt` | Pinned Python dependencies for the solver                |
| `01_inspect.py` | Ch. 1 — measure the data (bit-lengths, sizes)               |
| `02_fermat.py`  | Ch. 5 — the Fermat "close primes" dead end                  |
| `03_guess_h.py` | Ch. 5 — the wrong guesses that corner us into Coppersmith   |
| `cop2.py`       | Ch. 6 — the working Coppersmith factorization of `n`        |
| `final.py`      | Ch. 7–8 — factor → unlock `K` → decrypt → Håstad → flag     |
| `render.py`     | Ch. 10 — turn `postcard.bin` into `postcard.png`            |
| `postcard.bin` / `postcard.png` | The recovered Angkor Wat image              |

`final.py` is fully self-deriving: it imports `factor_with_hint` from `cop2.py`
and recomputes the primes at runtime, so no value is ever hard-coded between
stages.

---

<a name="13-lessons"></a>
## 13. The lessons to take away

1. **RSA's entire life depends on `p` and `q` staying secret.** Leak even *half*
   of one prime's bits and Coppersmith reconstructs the rest. Never let key
   generation expose partial primes.

2. **Small exponents plus repetition are fatal.** Sending the same message with
   `e = 3` to several recipients lets Håstad reassemble it using nothing but the
   Chinese Remainder Theorem and a cube root — no private key required.

3. **A failed attempt is not a failed idea.** Our first Coppersmith run produced
   nothing only because the lattice was too small. Tuning the parameters, not
   changing the strategy, was the fix.

> **The flag:** `MPTC{c0pp3rSm1th_m33ts_h4St4d_4t_4ngk0r_W4t}`

*The end.* 🏯
