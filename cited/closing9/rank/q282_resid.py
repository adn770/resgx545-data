#!/usr/bin/env python3
"""Q282 post-fit look at g-bl-st-a only (fit job): residuals of the best family member in half ulps,
by fraction and by corner spread. No held-out data read."""
import collections, sys
sys.dont_write_bytecode = True
from q282_fit import *
rec, pix = corners("g-bl-st-a"), hw("g-bl-st-a")
m = dict(decode="half", arith="half2", order="xy", P=64, fr="trunc", out="rne")
d = collections.Counter(); byf = collections.defaultdict(lambda: [0, 0]); ex = []
for (ch, fx, fy), w in zip(rec, pix):
    for c in (0, 1):
        p = model(ch[c], fx, fy, m); h = w >> 16 * c & 0xffff
        d[h - p] += 1
        k = (int(fx * 64) == 0, int(fy * 64) == 0)
        byf[k][0] += h == p; byf[k][1] += 1
        if h != p and len(ex) < 25:
            ex.append((ch[c], int(fx * 64), int(fy * 64), hex(h), hex(p), h2f(h), h2f(p)))
print("hw - model (half ulps):", sorted(d.items()))
print("by (fx==0, fy==0):", dict(byf))
print("fx frac values:", sorted({round(fx * 64, 3) for (_, fx, _) in rec})[:20])
for e in ex: print(e)
