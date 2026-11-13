#!/usr/bin/env python3
"""Q288 design aid (round 10, no data read): the nine gradient-word rules E731/Q288 left unsplit
(mantissa truncated to 16, 17, 18, 20 significant bits; round to nearest at 16; fixed point with a
least bit of 2^-30, 2^-31, 2^-32 truncated or 2^-30 rounded) on candidate x gradients A = 1/D,
reporting how many distinct words the nine give and the smallest pairwise step difference over a
32-pixel tile row in float32 ulps at depth 0.5 (2^-24). E731's A = 1/6400 gives one word for all."""
import struct, math
def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]
def mant_trunc(a, k):
    m, e = math.frexp(a); s = 2 ** k; return math.floor(m * s) / s * 2 ** e
def mant_rn(a, k):
    m, e = math.frexp(a); s = 2 ** k; return math.floor(m * s + 0.5) / s * 2 ** e
def fix(a, n, rn=False):
    s = 2 ** n; return (math.floor(a * s + (0.5 if rn else 0))) / s
R = {"T16": lambda a: mant_trunc(f32(a), 16), "T17": lambda a: mant_trunc(f32(a), 17),
     "T18": lambda a: mant_trunc(f32(a), 18), "T20": lambda a: mant_trunc(f32(a), 20),
     "RN16": lambda a: mant_rn(f32(a), 16), "F30": lambda a: fix(f32(a), 30), "F31": lambda a: fix(f32(a), 31),
     "F32": lambda a: fix(f32(a), 32), "F30RN": lambda a: fix(f32(a), 30, True)}
ULP = 2 ** -24
def score(a):
    w = {k: f(a) for k, f in R.items()}
    vals = sorted(set(w.values()))
    gaps = [ (b - c) * 32 / ULP for b, c in zip(vals[1:], vals[:-1])]
    return len(vals), min(gaps) if gaps else 0, w
print("E731 1/6400:", score(1 / 6400)[:2])
best = []
for D in list(range(100, 20000, 1)):
    n, g, _ = score(1 / D)
    if n == 9: best.append((g, D))
best.sort(reverse=True)
print("A = 1/D splitting all nine, by smallest step gap over 32 pixels (ulps at 0.5):")
for g, D in best[:12]:
    print(f"  D {D}: A {1/D:.6e}, min gap {g:.1f} ulp")
print("count of D in 100..19999 splitting all nine:", len(best))
print("larger gradients (D 64..99) and depth base 2^-k (ulp of the base binade):")
for base_exp in (1, 4, 8):
    U = 2 ** (-base_exp - 24 + 1) / 2
    best = []
    for D in range(64, 20000):
        w = {k: f(1 / D) for k, f in R.items()}
        vals = sorted(set(w.values()))
        if len(vals) == 9:
            best.append((min((b - c) * 32 / U for b, c in zip(vals[1:], vals[:-1])), D))
    best.sort(reverse=True)
    print(f"  depth near 2^-{base_exp}: best {[(D, round(g, 2)) for g, D in best[:4]]}")
