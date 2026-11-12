# SPDX-License-Identifier: MIT
"""g5-rw (Q230): the design shared by the generator, the scorer and the tests, frozen with them.  Exact rational arithmetic.
Plan: closing5/pixel/exp-pixel-r5.md sections 3 and 4 (decisions R5-3 a, pixel D4 a, D5 a: the dense table).

Template vtx_zws.s: R4's vtx_zw.s (z = A x + B, w = C x + D from the vertex's own UNSCALED x) with o0 = S x and o1 = S y (two fmad
with a zero addend, S a power of two: exact), so the window 32 + 32 S x / w of a job at scale S (w in [S, 2 S)) is the window of the
scale-1 job.  R4's slip (E842): its scale-1/4 jobs had windows -62 to 121, outside the guard band, and were cut; here every vertex of
every job is inside the viewport [0, 64] (`viewport_ok`, asserted by the generator for every row; on R4's design it flags exactly
rw-15 to rw-20, closing5/pixel/rw_band.out).
Rows: rw-k0..k3 and rw-07, rw-10: R4's own programs (vtx_zw.s, S = 1); rw-k4 (w 0.3, S 1/4), rw-k5 (w 0.7, S 1/2): new controls;
q-15..q-20: R4's rw-15..rw-20 (scale 1/4) with S = 1/4; m-01..m-07: R4's rw-01..rw-07 at scale 1/2 (S 1/2); m-08..m-14: R4's rw-08..rw-14
at scale 16 (S 16): the same mantissas at another exponent; d-01..d-20: the dense table.
Dense table (plan 4: "1 + k/64 for odd k and 28 hashed mantissas"): the tool's triangle forces w3 = 0.75 w1 + 0.25 w2, so a job has
two free w: 40 designed (the 32 odd k of 1 + k/64 and 8 hashed mantissas, paired inside a residue class of k mod 3 so that w = C x + D
is exact; a leftover grid index is paired with a hashed mantissa, which is nudged by at most 6 ulps) and 20 derived ones; 60 new mantissas, none read before."""
from __future__ import annotations

import hashlib
import pathlib
import re
import struct
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import rwdesign as D4  # noqa: E402  (R4's design, byte copy of render/closing-r4-pixel/score/rwdesign.py)

bits, fval, hx, rz_word, VX, VY, U23 = D4.bits, D4.fval, D4.hx, D4.rz_word, D4.VX, D4.VY, D4.U23
R4_SCORE = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r4-pixel/out/20261111-210423/score-g4-rw.txt")


def window(i, w, S=F(1)):
    return 32 + 32 * S * VX[i] / w, 32 + 32 * S * VY[i] / w


def viewport_ok(ws, S=F(1)):
    """Every window coordinate of the three vertices inside [0, 64]."""
    return all(0 <= c <= 64 for i in range(3) for c in window(i, ws[i], S))


def params(name, C, D, S, kind, template="vtx_zws"):
    w = tuple(C * VX[i] + D for i in range(3))
    return dict(name=name, C=C, D=D, S=S, w=w, words=tuple(bits(x) for x in w), kind=kind, template=template)


def exact(p):
    ok = lambda v: fval(bits(v)) == v
    return (ok(p["C"]) and ok(p["D"]) and ok(p["S"]) and all(ok(p["C"] * x) and ok(p["C"] * x + p["D"]) for x in VX)
            and all(ok(p["S"] * v) for v in VX + VY))


# ---------------------------------------------------------------- R4's kept words (E842): the m rows' frozen deltas
def r4_words():
    """{(job, vertex): (w word, RZ word, got word or None)} from R4's kept score file (42 read, 18 not)."""
    out = {}
    for ln in R4_SCORE.read_text().splitlines():
        m = re.match(r"(rw-\d\d)\s+(\d)\s+\S+\s+(0x\w+)\s+(0x\w+)\s+(0x\w+|-)\s", ln)
        if m:
            out[(m[1], int(m[2]))] = (int(m[3], 16), int(m[4], 16), None if m[5] == "-" else int(m[5], 16))
    return out


def known_deltas():
    """H-MANT's frozen table {23-bit mantissa: delta} (word - RZ): R4's 42 read words and the w the landed records read at one w at
    all three vertices or a perspective w (closing5/pixel/rw_band.py section 3: E754, E782, E783, E795, E796, E798; RZ + 1 at 9, 0.7,
    1.40625, 1.59375, 1.6875).  A mantissa read with both deltas would be a contradiction: asserted absent."""
    k = {}
    for (_, _), (w, rz, g) in r4_words().items():
        if g is not None:
            k.setdefault(w & 0x7fffff, set()).add(g - rz)
    b = lambda x: struct.unpack("<I", struct.pack("<f", x))[0]
    for w in [3, 7, 0.003, 3e-5, 0.3, 1.3, 5, 6, 11, 19, 23, 1.5, 1 + 2**-23, 1 - 2**-23, 1.0000004, 1.3125, 1.625, 1.0625, 0.875,
              1.4375, 1.1, 0.5, 2, 1.375]:
        k.setdefault(b(w) & 0x7fffff, set()).add(0)
    for w in [9, 0.7, 1.40625, 1.59375, 1.6875]:
        k.setdefault(b(w) & 0x7fffff, set()).add(1)
    assert all(len(v) == 1 for v in k.values()), "a mantissa with both deltas"
    return {m: v.pop() for m, v in k.items()}


# ---------------------------------------------------------------- rows
def controls():
    out = []
    for i in range(4):
        c = D4.control_params(i)
        p = params(c["name"], c["C"], c["D"], F(1), "control-r4", template="vtx_zw")
        p["known"] = c["known"]
        out.append(p)
    for name, w, S, kn in (("rw-k4", 0.3, F(1, 4), 0), ("rw-k5", 0.7, F(1, 2), 1)):
        Dv = fval(bits(w))
        p = params(name, F(0), Dv, S, "control-new")
        p["known"] = (rz_word(bits(w)) + kn,) * 3
        out.append(p)
    return out


def q_rows():
    out = []
    for i in range(14, 20):
        r = D4.job_params(i)
        out.append(params(f"q-{i + 1}", r["C"], r["D"], r["scale"], "q"))
    return out


def m_rows():
    out = []
    for i in range(14):
        r = D4.job_params(i)
        f = F(1, 2) if i < 7 else F(4)                    # scale 1 -> 1/2, scale 4 -> 16
        p = params(f"m-{i + 1:02d}", r["C"] * f, r["D"] * f, r["scale"] * f, "m")
        p["r4"] = r["name"]
        out.append(p)
    return out


def replicates():
    out = []
    for i in (6, 9):
        r = D4.job_params(i)
        p = params(r["name"], r["C"], r["D"], F(1), "replicate", template="vtx_zw")
        out.append(p)
    return out


D_SCALES = [F(1, 4), F(1, 2), F(1), F(2), F(4)]


def other_mantissas(n=8, avoid=()):
    out, i = [], 0
    while len(out) < n:
        r = int(hashlib.sha256(b"r5-rw-dense-%d" % i).hexdigest()[:8], 16) % (U23 - 1) + 1
        i += 1
        if r % (U23 // 64) and r not in out and r not in avoid:
            out.append(r)
    return out


def dense_pairs():
    known = set(known_deltas())
    by = {0: [], 1: [], 2: []}
    for k in range(1, 64, 2):
        by[k % 3].append(k)
    ps, left = [], []
    for r in (1, 0, 2):
        ks = by[r]
        for a in range(0, len(ks) - 1, 2):
            ps.append((U23 + ks[a] * (U23 // 64), U23 + ks[a + 1] * (U23 // 64)))
        if len(ks) % 2:
            left.append(U23 + ks[-1] * (U23 // 64))
    hs = [U23 + r for r in other_mantissas(avoid=known)]
    left = [x for pair in zip(left, hs) for x in pair] + hs[len(left):]   # each leftover grid index first, a hashed one (nudged) after it
    for a in range(0, len(left), 2):
        n1, n2 = left[a], left[a + 1]
        d = n2 - n1
        n2 = n1 + min((12 * round(d / 12), 12 * (d // 12), 12 * (d // 12 + 1)), key=lambda v: abs(v - d))
        ps.append((n1, n2))
    order = [(i * 7) % 20 for i in range(20)]
    return [ps[i] for i in order]


def d_rows():
    out = []
    for i, (n1, n2) in enumerate(dense_pairs()):
        S = D_SCALES[i % 5]
        u = S / U23
        j = (n2 - n1) // 12
        assert (n2 - n1) % 12 == 0
        out.append(params(f"d-{i + 1:02d}", 8 * j * u, (n1 + 6 * j) * u, S, "d"))
    return out


def all_rows():
    return controls() + q_rows() + m_rows() + replicates() + d_rows()


def dense_words():
    return [wd for p in d_rows() for wd in p["words"]]


def split():
    """{word: 'FIT' | 'HELD OUT'} of the 60 dense words: sorted by sha256 of 'r5' + the 4 little-endian bytes, lower 30 FIT."""
    ws = sorted(set(dense_words()), key=lambda b: hashlib.sha256(b"r5" + struct.pack("<I", b)).hexdigest())
    return {b: ("FIT" if i < len(ws) // 2 else "HELD OUT") for i, b in enumerate(ws)}


def hmant(word, kd=None):
    """H-MANT's frozen delta for a w word, or None (mantissa not read)."""
    kd = known_deltas() if kd is None else kd
    return kd.get(word & 0x7fffff)
