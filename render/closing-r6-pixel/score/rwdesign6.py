# SPDX-License-Identifier: MIT
"""g6-rw (Q230): the design shared by the generator, the scorer, the fake tool and the tests, frozen with them.  Exact rational
arithmetic.  Plan: closing6/pixel/exp-pixel-r6.md sections 3 and 4 (decisions R6-2 a, pixel decisions 6 a, 7 a).

R5's template vtx_zws.s and design (rwdesign5.py): a job (n1, j) at scale S has w = (n1, n1 + 12 j, n1 + 3 j) * S / 2^23 at its three
vertices (w = C x + D exact: C = 8 j u, D = (n1 + 6 j) u), every w in [S, 2 S), every vertex inside the viewport.
frac(M) = the fractional part of 2^47 / M for the 24-bit mantissa M (2^23 <= M < 2^24): how far the exact 1/w lies above its RZ word,
in ulp of the stored word (E872).  H-FRAC (E872): a mantissa with frac < 0.5 never stores RZ + 1.
Rows:
  g6-rwa (8, controls): rw-k0..k5 (R5's programs byte for byte, the known words), d-01, d-02 (R5's programs byte for byte, R5's six
         words, 2 of them RZ + 1; 4 of the six are words of E859's HELD OUT half, used here as replicate controls, never for a fit)
  g6-rw (106): L, 6 windows (strides 1, 2^8, 2^16; bases a and b) of 12 jobs, n1 = Bw + i s for i in IOFF, j = s: 36 mantissas
         Bw + o s, o in 0..41, S = 1, bases from sha256 of 'r6-rw-win-<n>', inside [2^23, 2^24) and clear of every read mantissa;
         B, 8 jobs (n1, j) from a frozen search (sha256 of 'r6-rw-b-<n>') whose three mantissas all have frac in [0.42, 0.62), S = 1;
         two L jobs again (replicates); E, the 4 rows of R4's rw-01..rw-14 with the most RZ + 1 words (ties by name) at S = 2^e for
         e in -12, -6, -3, 5, 8, 12 (w in [2^e, 2^(e+1))), H-MANT with R4's delta."""
from __future__ import annotations

import hashlib
import pathlib
import re
import struct
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import rwdesign as D4  # noqa: E402
import rwdesign5 as D5  # noqa: E402

bits, fval, hx, rz_word, U23 = D4.bits, D4.fval, D4.hx, D4.rz_word, D4.U23
params, exact, viewport_ok, window = D5.params, D5.exact, D5.viewport_ok, D5.window
R5_OUT = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel/out/20261112-091752")
R5_BINS = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel/bins")
IOFF = (0, 1, 2, 6, 7, 8, 21, 22, 23, 27, 28, 29)
STRIDES = ((1, "1"), (1 << 8, "8"), (1 << 16, "16"))
EXPS = (-12, -6, -3, 5, 8, 12)
FRAC_LO, FRAC_HI = F(42, 100), F(62, 100)
ROW = re.compile(r"(\S+)\s+(\d)\s+\S+\s+(0x[0-9a-f]{8})\s+(0x[0-9a-f]{8})\s+(0x[0-9a-f]{8}|-)\s")


def mant(word):
    return (word & 0x7fffff) | 0x800000


def frac(M):
    return F((1 << 47) % M, M)


def read_mantissas():
    """Every 24-bit mantissa a kept job or a landed record has read (E754 .. E859: R4's table, R5's 126 words, the early w).  Only
    the w column is parsed: no stored word of E859's HELD OUT half is read here."""
    out = set()
    for p in (R5_OUT / "score-g5-rw.txt", R5_OUT / "score-g5-rwa.txt", D5.R4_SCORE):
        for ln in p.read_text().splitlines():
            m = ROW.match(ln)
            if m:
                out.add(mant(int(m[3], 16)))
    out |= {m | 0x800000 for m in D5.known_deltas()}
    return out


def r5_words(name):
    """R5's kept words of a g5-rw job (the controls d-01, d-02): (w words, got words)."""
    ws, gs = [], []
    for ln in (R5_OUT / "score-g5-rw.txt").read_text().splitlines():
        m = ROW.match(ln)
        if m and m[1] == name:
            ws.append(int(m[3], 16))
            gs.append(int(m[5], 16))
    assert len(ws) == 3 and None not in gs, name
    return tuple(ws), tuple(gs)


def job(name, n1, j, S, kind):
    u = S / U23
    p = params(name, 8 * j * u, (n1 + 6 * j) * u, S, kind)
    p["n"] = (n1, n1 + 12 * j, n1 + 3 * j)
    return p


def controls():
    out = D5.controls()
    for name in ("d-01", "d-02"):
        p = next(q for q in D5.d_rows() if q["name"] == name)
        p = dict(p, kind="control-r5", template="r5")
        ws, gs = r5_words(name)
        assert ws == p["words"], name
        p["known"] = gs
        out.append(p)
    return out


def windows():
    """[(tag, stride, base)] of the six L windows: strides 1, 2^8, 2^16, bases a and b."""
    read, used, out, n = read_mantissas(), set(), [], 0
    for s, sn in STRIDES:
        for wn in "ab":
            while True:
                h = int(hashlib.sha256(b"r6-rw-win-%d" % n).hexdigest()[:12], 16)
                n += 1
                Bw = U23 + h % (U23 - 41 * s)
                ms = {Bw + o * s for o in range(42)}
                if Bw + 41 * s < 2 * U23 and not (ms & read) and not (ms & used):
                    used |= ms
                    out.append((sn + wn, s, Bw))
                    break
    return out


def window_mantissas(s, Bw):
    return sorted({Bw + (i + d) * s for i in IOFF for d in (0, 3, 12)})


def l_rows():
    out = []
    for tag, s, Bw in windows():
        for i in IOFF:
            p = job(f"l-{tag}-{i:02d}", Bw + i * s, s, F(1), "l")
            p["window"] = (tag, s, Bw)
            out.append(p)
    return out


def b_rows(n=8):
    read = read_mantissas()
    used = {M for _, s, Bw in windows() for M in window_mantissas(s, Bw)} | read
    out, i = [], 0
    while len(out) < n:
        h = hashlib.sha256(b"r6-rw-b-%d" % i).digest()
        i += 1
        n1 = U23 + int.from_bytes(h[:4], "little") % U23
        j = 1 + int.from_bytes(h[4:8], "little") % (1 << 16)
        ms = (n1, n1 + 12 * j, n1 + 3 * j)
        if ms[1] >= 2 * U23 or set(ms) & used or not all(FRAC_LO <= frac(M) < FRAC_HI for M in ms):
            continue
        used |= set(ms)
        out.append(job(f"b-{len(out) + 1:02d}", n1, j, F(1), "b"))
    return out


def replicates():
    ls = {p["name"]: p for p in l_rows()}
    out = []
    for src in ("l-1a-00", "l-16a-00"):
        p = dict(ls[src], name="r" + src, kind="replicate")
        p["of"] = src
        out.append(p)
    return out


def e_source():
    """The 4 rows of R4's rw-01..rw-14 with the most RZ + 1 words, ties by name (E842's kept table)."""
    r4 = D5.r4_words()
    cnt = {f"rw-{i:02d}": sum(1 for v in range(3) if r4[(f"rw-{i:02d}", v)][2] - r4[(f"rw-{i:02d}", v)][1] == 1) for i in range(1, 15)}
    return sorted(cnt, key=lambda n: (-cnt[n], n))[:4]


def e_rows():
    r4 = D5.r4_words()
    out = []
    for e in EXPS:
        for name in e_source():
            i = int(name[3:]) - 1
            r = D4.job_params(i)
            f = F(2) ** e / r["scale"]
            p = params(f"e{'m' if e < 0 else 'p'}{abs(e):02d}-{name}", r["C"] * f, r["D"] * f, r["scale"] * f, "e")
            p["r4"], p["exp"] = name, e
            p["hmant"] = tuple(r4[(name, v)][2] - r4[(name, v)][1] for v in range(3))
            out.append(p)
    return out


def g6_rows():
    return l_rows() + b_rows() + replicates() + e_rows()


def new_mantissas():
    """The mantissas g6-rw reads for the first time (L and B): H-FRAC's words."""
    return {mant(w) for p in l_rows() + b_rows() for w in p["words"]}
