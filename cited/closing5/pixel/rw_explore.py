# SPDX-License-Identifier: MIT
"""Round 5 planning, offline EXPLORATION (2026-11-12; post hoc on every 1/w word known, E754, E795, E796, E798, E842:
a hypothesis generator, never a result; anything it finds needs words that were not read yet).
1. Is 'RZ or RZ + 1' a function of the mantissa of w alone (the same mantissa at two exponents)?
2. A wider family than the frozen rwfam (whose 225 models are dead on the read FIT words, rw_fit_alive.py):
   fixed-point table + Newton-Raphson with truncated products of P fraction bits and a final cut,
   declared here before it is run:
     t  index bits 2..11, table point left edge or midpoint, entry cut to s = t+1..t+8 fraction bits (floor / nearest)
     k  Newton steps 1..2, products truncated to P = 24..40 fraction bits
     final: floor, nearest, ceil of the 24-bit mantissa
  python -I rw_explore.py > rw_explore.out"""
import collections
import pathlib
import re
import struct
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path.home() / "src/resgx545-data/render/closing-r4-pixel"


def bits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


obs = []          # (w word, delta = got - RZ, source)
for ln in (R4 / "out/20261111-210423/score-g4-rw.txt").read_text().splitlines():
    m = re.match(r"(rw-\d+)\s+(\d)\s+(\S+)\s+(0x\w+)\s+(0x\w+)\s+(0x\w+)\s+(\S+)\s+(FIT|HELD OUT)\s", ln)
    if m:
        obs.append((int(m[4], 16), int(m[6], 16) - int(m[5], 16), "E842"))
# the 23 earlier words (closing4/pixel/rhw_frac.py: E754, E795, E796, E798, E782)
for w in [3, 7, 0.003, 3e-5, 0.3, 1.3, 5, 6, 11, 19, 23, 1.5, 1 + 2**-23, 1 - 2**-23, 1.0000004, 1.3125, 1.625, 1.0625]:
    obs.append((bits(w), 0, "earlier"))
for w in [9, 0.7, 1.40625, 1.59375, 1.6875]:
    obs.append((bits(w), 1, "earlier"))
print(f"{len(obs)} words: RZ {sum(1 for o in obs if o[1] == 0)}, RZ + 1 {sum(1 for o in obs if o[1] == 1)}, other {sum(1 for o in obs if o[1] not in (0, 1))}")

by = collections.defaultdict(set)
ex = collections.defaultdict(set)
for w, d, s in obs:
    by[w & 0x7fffff].add(d)
    ex[w & 0x7fffff].add((w >> 23) - 127)
multi = {m: e for m, e in ex.items() if len(e) > 1}
print(f"distinct mantissas {len(by)}; mantissas read at more than one exponent: {len(multi)}; "
      f"of those with both RZ and RZ + 1: {sum(1 for m in multi if len(by[m]) > 1)}")
for m in sorted(multi):
    print(f"   mantissa 1 + {m:#08x}/2^23 = {1 + m / 2**23:.7g}  exponents {sorted(multi[m])}  delta {sorted(by[m])}")
print("mantissas with both deltas at any exponent:", [hex(m) for m in by if len(by[m]) > 1])
grid = {}
for m, ds in by.items():
    if m % (1 << 18) == 0:
        grid[m >> 18] = sorted(ds)
print("grid 1 + k/32: RZ + 1 at k =", [k for k in sorted(grid) if grid[k] == [1]], " RZ at k =", [k for k in sorted(grid) if grid[k] == [0]],
      " unread k =", [k for k in range(32) if k not in grid])

data = sorted((m | 0x800000, min(ds)) for m, ds in by.items() if len(ds) == 1)
ONE = 1 << 47


def run(t, mid, s, near, k, P, fin):
    hits = 0
    for M, d in data:
        if M == 0x800000:
            continue
        i = (M - 0x800000) >> (23 - t)
        num = (1 << t) + i
        # table point m0 = (2 num + mid) / 2^(t+1); x0 = 1/m0 with s fraction bits
        den = 2 * num + mid
        x0n = (1 << (t + 1 + s))
        x0 = (x0n + (den // 2 if near else 0)) // den           # s fraction bits
        x = x0 << (P - s) if P >= s else x0 >> (s - P)          # P fraction bits
        for _ in range(k):
            mx = (M * x) >> 23                                   # m x, P fraction bits (m has 23)
            two = (2 << P) - mx
            x = (x * two) >> P
        # mantissa of 1/m in [2^23, 2^24): x * 2^24 (x in (0.5, 1])
        sh = P - 24
        if fin == "floor":
            R = x >> sh
        elif fin == "near":
            R = (x + (1 << (sh - 1))) >> sh if sh > 0 else x
        else:
            R = -((-x) >> sh)
        if R - ONE // M == d:
            hits += 1
    return hits


n = len([1 for M, d in data if M != 0x800000])
best = []
count = 0
for t in range(2, 12):
    for mid in (0, 1):
        for s in range(t + 1, t + 9):
            for near in (0, 1):
                for k in (1, 2):
                    for P in range(24, 41):
                        if P < s:
                            continue
                        for fin in ("floor", "near", "ceil"):
                            if fin == "near" and P == 24:
                                continue
                            count += 1
                            h = run(t, mid, s, near, k, P, fin)
                            best.append((h, t, mid, s, near, k, P, fin))
best.sort(reverse=True)
print(f"wider family: {count} models on {n} distinct mantissas (the w = 1 mantissa left out); all fit: {sum(1 for b in best if b[0] == n)}")
print("top 12 (hits, t, mid, s, near, k, P, final):")
for b in best[:12]:
    print("  ", b)
base = sum(1 for M, d in data if M != 0x800000 and d == 0)
print(f"baseline 'always RZ' fits {base} of {n}")
