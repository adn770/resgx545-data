# SPDX-License-Identifier: MIT
"""Round 6 planning, Q230 (1/w): the fold-time fit E859 left undone, run offline.  Standard library only.
STEP 1 (this script, default): every model of the families declared below is scored on the FIT set (100 mantissas: every
mantissa read except the 30 dense-table words E859's frozen hash marked HELD OUT; rw6_data.load() does not parse those).
STEP 2 (`--heldout`, only if step 1 printed at least one model fitting 100 of 100, and only once): those models, and no other,
are scored on the 30 HELD OUT mantissas.  A model that fits FIT but misses a HELD OUT word is refuted.
Target per mantissa M (w = M / 2^23 in [1, 2)): T = floor(2^47 / M) + delta, the stored mantissa in units of 2^-24 (1/w in (1/2, 1)).
M = 2^23 (w a power of two, word exact) is left out of the fits.

Families, declared before the run (2026-11-12):
 A  fixed-point table + Newton-Raphson, wider than E851's (rw_explore.py):
    t index bits 4..10; table point left / mid / right of the interval; entry = 1/point cut to s = t+1..t+6 fraction bits by
    floor / nearest / ceil; k = 1..2 steps x <- x * (2 - m x); m x truncated to P1 = 24..36 fraction bits; the product x * (..)
    truncated to P2 = 24..36; `2 - v` exact or one's complement (2 - v - 1 unit of P1); final cut to 24 bits floor or nearest.
 B  binary32 compositions (R = RZ, RN, RU, RD; all operations exact then rounded to 24 bits):
    B1  R1(1 / R2(1 / R3(1 / w)))
    B2  y0 = Rp(1 / w) kept to p = 8, 10, 12, 14, 16, 18, 20, 24 bits (Rp = RZ, RN, RU), one Newton step
        y = Rc(y0 * Rb(2 - Ra(w * y0)))   and the fused form   y = Rc(y0 * Rb(2 - w * y0))
    B3  the same y0, y = Rc(y0 + Rb(y0 * Ra(1 - w * y0)))  (fused residual)
 C  RZ of 1/w' with w' = w cut to c = 12..23 mantissa bits by RZ / RN / RU, and RZ / RN / RU of that (36 x 3)
 baseline: always RZ."""
import itertools, math, sys, time
from fractions import Fraction as F
sys.dont_write_bytecode = True
import rw6_data as D

HELD = "--heldout" in sys.argv
data = sorted((M, d) for M, d in D.load(held=HELD).items() if M != 1 << 23)
# order the FIT points so that RZ + 1 words come early (fast rejection)
data.sort(key=lambda t: (-t[1], t[0]))
TGT = [((1 << 47) // M + d) for M, d in data]
N = len(data)
print(f"{'HELD OUT' if HELD else 'FIT'} set: {N} mantissas (w = 1 left out), RZ + 1 {sum(d for _, d in data)}; baseline always RZ fits {sum(1 for _, d in data if d == 0)}")

def score(fn, stop=True):
    h = 0
    for (M, d), T in zip(data, TGT):
        if fn(M) == T: h += 1
        elif stop: return h, False
    return h, h == N

# ---------------------------------------------------------------- family A
def famA():
    for t in range(4, 11):
        for pt in (0, 1, 2):
            for s in range(t + 1, t + 7):
                for er in ("f", "n", "c"):
                    den_of = lambda i: 2 * ((1 << t) + i) + pt          # point = den / 2^(t+1)
                    def entry(i, s=s, er=er, t=t, pt=pt):
                        den = 2 * ((1 << t) + i) + pt
                        num = 1 << (t + 1 + s)
                        return num // den if er == "f" else (num + den // 2) // den if er == "n" else -((-num) // den)
                    tab = [entry(i) for i in range(1 << t)]
                    for k in (1, 2):
                        for P1 in range(24, 37):
                            for P2 in range(24, 37):
                                for oc in (0, 1):
                                    for fin in ("f", "n"):
                                        yield (f"A:t{t}:pt{pt}:s{s}:{er}:k{k}:P1={P1}:P2={P2}:oc{oc}:{fin}", (t, tab, s, k, P1, P2, oc, fin))

def runA(p):
    t, tab, s, k, P1, P2, oc, fin = p
    def fn(M):
        x = tab[(M - (1 << 23)) >> (23 - t)]; xs = s                     # x with xs fraction bits
        for _ in range(k):
            sh1 = 23 + xs - P1
            mx = (M * x) >> sh1 if sh1 >= 0 else (M * x) << -sh1         # P1 fraction bits
            two = (2 << P1) - mx - oc
            sh = xs + P1 - P2
            x = (x * two) >> sh if sh >= 0 else (x * two) << -sh; xs = P2
        sh = xs - 24
        if sh <= 0: return x << -sh
        return x >> sh if fin == "f" else (x + (1 << (sh - 1))) >> sh
    return fn

# ---------------------------------------------------------------- family B, C: exact rationals rounded to p bits
def rnd(v, mode, p=24):
    """v > 0 rational rounded to p significant bits; returns a Fraction."""
    e = v.numerator.bit_length() - v.denominator.bit_length()
    if F(2) ** e > v: e -= 1
    q = v / F(2) ** (e - p + 1)                                          # in [2^(p-1), 2^p)
    fl = q.numerator // q.denominator
    if mode == "RZ" or mode == "RD": n = fl
    elif mode == "RU": n = fl if q == fl else fl + 1
    else:
        r = q - fl
        n = fl + 1 if r > F(1, 2) or (r == F(1, 2) and fl & 1) else fl
    return n * F(2) ** (e - p + 1)
def mant(y):
    """y in (1/2, 1] as the stored mantissa in units of 2^-24 (exact multiples only)."""
    v = y * (1 << 24)
    return v.numerator if v.denominator == 1 else None
MODES = ("RZ", "RN", "RU")
def famBC():
    for r1, r2, r3 in itertools.product(MODES, repeat=3):
        yield f"B1:{r1}(1/{r2}(1/{r3}(1/w)))", (lambda M, r1=r1, r2=r2, r3=r3: mant(rnd(1 / rnd(1 / rnd(F(1 << 23, M), r3), r2), r1)))
    for p in (8, 10, 12, 14, 16, 18, 20, 24):
        for rp in MODES:
            y0 = lambda M, p=p, rp=rp: rnd(F(1 << 23, M), rp, p)
            for ra, rb, rc in itertools.product(MODES, repeat=3):
                yield (f"B2:p{p}:{rp}:{ra}:{rb}:{rc}",
                       lambda M, y0=y0, ra=ra, rb=rb, rc=rc: (lambda w, y: mant(rnd(y * rnd(2 - rnd(w * y, ra), rb), rc)))(F(M, 1 << 23), y0(M)))
            for rb, rc in itertools.product(MODES, repeat=2):
                yield (f"B2f:p{p}:{rp}:{rb}:{rc}",
                       lambda M, y0=y0, rb=rb, rc=rc: (lambda w, y: mant(rnd(y * rnd(2 - w * y, rb), rc)))(F(M, 1 << 23), y0(M)))
            for ra, rb, rc in itertools.product(MODES, repeat=3):
                def b3(M, y0=y0, ra=ra, rb=rb, rc=rc):
                    w, y = F(M, 1 << 23), y0(M)
                    r = 1 - w * y
                    if r == 0: return mant(rnd(y, rc))
                    sg = 1 if r > 0 else -1
                    flip = {"RZ": "RZ", "RN": "RN", "RU": "RZ"} if sg < 0 else {"RZ": "RZ", "RN": "RN", "RU": "RU"}
                    rr = sg * rnd(abs(r), flip[ra])
                    c = y * rr
                    cc = sg * rnd(abs(c), flip[rb])
                    return mant(rnd(y + cc, rc))
                yield f"B3:p{p}:{rp}:{ra}:{rb}:{rc}", b3
    for c in range(12, 24):
        for rw in MODES:
            for r1 in MODES:
                yield f"C:c{c}:{rw}:{r1}", (lambda M, c=c, rw=rw, r1=r1: mant(rnd(1 / rnd(F(M, 1 << 23), rw, c), r1)))

def safe(fn):
    def g(M):
        try: return fn(M)
        except (ZeroDivisionError, AttributeError): return None
    return g

if not HELD:
    t0 = time.time(); fits = []; nA = nB = 0; first = {}
    for name, p in famA():
        nA += 1
        h, ok = score(runA(p))
        first[h] = first.get(h, 0) + 1
        if ok: fits.append(name)
    bestB = []
    for name, fn in famBC():
        nB += 1
        h, ok = score(safe(fn), stop=False)
        bestB.append((h, name))
        if ok: fits.append(name)
    bestB.sort(reverse=True)
    print(f"family A: {nA} models; fitting {N} of {N}: {sum(1 for f in fits if f.startswith('A'))}")
    print("  family A, models by the number of FIT words matched before the first miss (RZ + 1 words first):", dict(sorted(first.items())))
    print(f"families B, C: {nB} models; fitting {N} of {N}: {sum(1 for f in fits if not f.startswith('A'))}; best 8 (full count): {bestB[:8]}")
    print("FITTING MODELS:", fits if fits else "none")
    print(f"({time.time() - t0:.0f} s)")
else:
    names = [ln.strip() for ln in open("rw6_fit.models") if ln.strip()]
    print("HELD OUT scoring of the models that fit FIT:", names)
    allA = dict(famA()) if any(n.startswith("A") for n in names) else {}
    allB = dict(famBC())
    for n in names:
        fn = runA(allA[n]) if n in allA else safe(allB[n])
        print(n, "HELD OUT", score(fn, stop=False))
