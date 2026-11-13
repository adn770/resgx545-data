#!/usr/bin/env python3
"""Q282: g-bl-st-a only. Miss rate of the family-1 best by integer fraction ix, iy; the error of
stage 1 alone (fx with fy = 0 rows if any) and the exact real value's position between halves."""
import collections, sys
sys.dont_write_bytecode = True
from q282_fit import *
rec, pix = corners("g-bl-st-a"), hw("g-bl-st-a")
m = dict(decode="half", arith="half2", order="xy", P=64, fr="trunc", out="rne")
byy = collections.defaultdict(lambda: [0, 0]); byx = collections.defaultdict(lambda: [0, 0])
pos = collections.Counter()
for (ch, fx, fy), w in zip(rec, pix):
    ix, iy = int(fx * 64), int(fy * 64)
    for c in (0, 1):
        p = model(ch[c], fx, fy, m); h = w >> 16 * c & 0xffff
        byy[iy][0] += h != p; byy[iy][1] += 1
        byx[ix][0] += h != p; byx[ix][1] += 1
        # exact real value of decode-to-half then exact bilinear
        d = [h2f(half_rne(s2l(b))) for b in ch[c]]
        wx, wy = ix / 64, iy / 64
        ex = (d[0] * (1 - wx) + d[1] * wx) * (1 - wy) + (d[2] * (1 - wx) + d[3] * wx) * wy
        lo = half_rz(ex); f = (ex - h2f(lo)) / (h2f(lo + 1) - h2f(lo)) if h2f(lo) != ex else 0.0
        pos[(round(f, 1), h - lo)] += 1
print("iy: miss/total", {k: tuple(v) for k, v in sorted(byy.items())})
print("ix: miss/total", {k: tuple(v) for k, v in sorted(byx.items())})
print("(position of the exact value between RZ and RZ+1 in tenths, hw - RZ):")
for k in sorted(pos): print("  ", k, pos[k])
