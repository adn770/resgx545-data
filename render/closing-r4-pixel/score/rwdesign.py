# SPDX-License-Identifier: MIT
"""g4-rw (Q230): the design shared by the generator and the scorer, frozen with them.  Pure functions, exact rational arithmetic.

Template vtx_zw.s: z = A x + B (A = B = 0 here), w = C x + D from the vertex's own x.  The tool's triangle (--vtx-coords 2) has clip
x = -0.75, 0.75, -0.375 and y = -0.75, -0.375, 0.75, so w3 = 0.75 w1 + 0.25 w2: two words are free a job, the third follows.
Exactness: with u = scale * 2^-23 and integers n1, n2 (w1 = n1 u, w2 = n2 u, all three w in [scale, 2 scale)) the template computes
w = C x + D exactly in float32 (fused or not) iff 12 | (n2 - n1): then j = (n2 - n1) / 12, C = 8 j u, D = (n1 + 6 j) u, the
products C x are -6 j u, +6 j u and -3 j u (multiples of u, at most 24 bits) and w3 = (n1 + 3 j) u.  A grid pair whose mantissa
indices k1, k2 (1 + k/32) differ by a multiple of 3 needs no nudge (2^18 (k2 - k1) is then a multiple of 12); the other w2 are
moved to the nearest word with the property (at most 6 ulps)."""
from __future__ import annotations

import hashlib
import struct
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True

VX = (F(-3, 4), F(3, 4), F(-3, 8))
VY = (F(-3, 4), F(-3, 8), F(3, 4))
U23 = 1 << 23


def bits(x) -> int:
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


def fval(b: int) -> F:
    return F(struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0])


def hx(b: int) -> str:
    return f"0x{b:08x}"


def rz_word(wb: int) -> int:
    """float32 word of RZ(1 / w) for a positive normal float32 word wb."""
    r = 1 / fval(wb)
    e = 0
    while r >= 2:
        r /= 2
        e += 1
    while r < 1:
        r *= 2
        e -= 1
    m = int(r * U23)                       # floor: RZ (1 <= r < 2)
    return ((127 + e) << 23) | (m - U23)


def window(i: int, w: F, xs=VX, ys=VY):
    return 32 + 32 * xs[i] / w, 32 + 32 * ys[i] / w


# ---- the table: 20 jobs
GRID = list(range(1, 32))
SCALES = [F(1)] * 7 + [F(4)] * 7 + [F(1, 4)] * 6


def other_mantissas(n=9):
    out, i = [], 0
    while len(out) < n:
        r = int(hashlib.sha256(b"r4-rw-other-%d" % i).hexdigest()[:8], 16) % (U23 - 1) + 1
        i += 1
        if r % (U23 // 32) and r not in out:        # not on the 1/32 grid
            out.append(r)
    return out


def pairs():
    """20 pairs (n1, n2) of mantissa indices (units 2^-23, 2^23 + frac) before the scale: grid pairs inside a residue class of k mod 3
    (no nudge), then the leftover grid index with the 9 other mantissas (nudged).  Deterministic."""
    by = {0: [], 1: [], 2: []}
    for k in GRID:
        by[k % 3].append(k)
    ps, left = [], []
    for r in (1, 0, 2):
        ks = by[r]
        for a in range(0, len(ks) - 1, 2):
            ps.append((U23 + ks[a] * (U23 // 32), U23 + ks[a + 1] * (U23 // 32)))
        if len(ks) % 2:
            left.append(U23 + ks[-1] * (U23 // 32))
    left += [U23 + r for r in other_mantissas()]
    for a in range(0, len(left), 2):
        n1, n2 = left[a], left[a + 1]
        d = n2 - n1
        n2 = n1 + min((12 * round(d / 12) , 12 * (d // 12), 12 * (d // 12 + 1)), key=lambda v: abs(v - d))
        ps.append((n1, n2))
    # interleave so that the classes are spread over the scales: a fixed permutation
    order = [(i * 7) % 20 for i in range(20)]
    assert sorted(order) == list(range(20))
    return [ps[i] for i in order]


def job_params(idx: int):
    """idx 0..19 -> dict(name, scale, n1, n2, j, C, D, w=(w1, w2, w3) as Fractions, words)."""
    n1, n2 = pairs()[idx]
    assert (n2 - n1) % 12 == 0, (idx, n1, n2)
    s = SCALES[idx]
    u = s / U23
    j = (n2 - n1) // 12
    C, D = 8 * j * u, (n1 + 6 * j) * u
    w = tuple(C * VX[i] + D for i in range(3))
    return dict(name=f"rw-{idx + 1:02d}", scale=s, n1=n1, n2=n2, j=j, C=C, D=D, w=w, words=tuple(bits(x) for x in w))


CONTROLS = [  # name, C, D, known exact rhw words per vertex (None = not known)
    ("rw-k0", F(0), F(1), (0x3f800000,) * 3),
    ("rw-k1", F(4), F(6), (0x3eaaaaaa, 0x3de38e39, None)),            # w = 3 (RZ), 9 (RZ+1), 4.5
    ("rw-k2", F(2), F(17, 2), (0x3e124924, None, None)),               # w = 7 (RZ), 10, 7.75
    ("rw-k3", F(1, 4), F(51, 32), (0x3f360b61, None, 0x3f2aaaaa)),     # w = 1.40625 (RZ+1), 1.78125, 1.5 (RZ)
]


def control_params(i: int):
    name, C, D, known = CONTROLS[i]
    w = tuple(C * VX[v] + D for v in range(3))
    return dict(name=name, C=C, D=D, w=w, words=tuple(bits(x) for x in w), known=known)


def exact_in_float32(C, D, fused: bool) -> bool:
    """The three w = C x + D are float32 values, and so is each product when unfused."""
    ok = lambda v: fval(bits(v)) == v
    if not (ok(C) and ok(D)):
        return False
    for x in VX:
        if not ok(C * x + D):
            return False
        if not fused and not ok(C * x):
            return False
    return True


def table_words():
    """The 60 distinct table w words in job order (w1, w2, w3 of jobs 1..20)."""
    return [wd for i in range(20) for wd in job_params(i)["words"]]


def split():
    """{word: 'FIT' | 'HELD OUT'}: the distinct table words sorted by sha256 of their 4 little-endian bytes, lower 30 FIT."""
    ws = sorted(set(table_words()), key=lambda b: hashlib.sha256(struct.pack("<I", b)).hexdigest())
    return {b: ("FIT" if i < len(ws) // 2 else "HELD OUT") for i, b in enumerate(ws)}
